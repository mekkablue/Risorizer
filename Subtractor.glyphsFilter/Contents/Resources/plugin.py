# encoding: utf-8

###########################################################################################################
#
#
#	Filter without Dialog Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Filter%20without%20Dialog
#
#
###########################################################################################################

import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from Foundation import NSClassFromString, NSMutableArray
from random import choice


# Glyph names that are always excluded when running as a custom parameter
EXCLUDED_GLYPH_NAMES = frozenset(['.notdef', 'uniF8FF', 'apple'])


def getSubtractGlyphs(font):
	"""Return all glyphs named _subtract or _subtract.xxx from the font."""
	return [g for g in font.glyphs
	        if g.name == '_subtract' or g.name.startswith('_subtract.')]


def subtractFromLayer(targetLayer, subtractLayer):
	"""
	Boolean-subtract the shapes of subtractLayer from targetLayer.
	Mirrors the subtract=YES branch in Risorizer.m (processLayer:…subtract:):
	  1. Remove overlap on the target layer (decomposes components)
	  2. Decompose and clean the subtract layer via copyDecomposedLayer + removeOverlap
	  3. Call GSPathOperator.subtractPaths:from:error: for the actual boolean op
	  4. Replace layer shapes with the result and correct path direction
	"""
	# 1. Clean target layer in place
	targetLayer.removeOverlap()

	# 2. Clean subtract shapes
	subtractCopy = subtractLayer.copyDecomposedLayer()
	subtractCopy.removeOverlap()
	subtractCopy.correctPathDirection()

	# 3. Boolean subtraction via GSPathOperator (same class used by Risorizer.m)
	subtrahends = NSMutableArray.arrayWithArray_(
		[s for s in subtractCopy.shapes if isinstance(s, GSPath)]
	)
	minuends = NSMutableArray.arrayWithArray_(
		[s for s in targetLayer.shapes if isinstance(s, GSPath)]
	)

	if not subtrahends or not minuends:
		return

	GSPathOperator = NSClassFromString("GSPathOperator")
	GSPathOperator.subtractPaths_from_error_(subtrahends, minuends, None)

	# 4. Put the result back and normalise directions
	targetLayer.shapes = minuends
	targetLayer.correctPathDirection()


class Subtractor(FilterWithoutDialog):

	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': 'Subtractor',
			'de': 'Subtrahieren',
			'fr': 'Soustracteur',
			'es': 'Sustractor',
		})
		self.keyboardShortcut = None  # Cmd+Shift+key if set

	@objc.python_method
	def filter(self, layer, inEditView, customParameters):
		try:
			glyphName = layer.parent.name

			# When applied as a custom parameter (batch export), skip excluded glyphs
			if not inEditView:
				if glyphName in EXCLUDED_GLYPH_NAMES:
					return
				if glyphName.startswith('_subtract'):
					return
				if not layer.shapes:
					return

			font = layer.parent.parent

			# Collect all _subtract and _subtract.xxx glyphs
			subtractGlyphs = getSubtractGlyphs(font)

			if not subtractGlyphs:
				if inEditView:
					Message(
						"No subtract glyphs found.\n\n"
						"Please add a glyph named \u2018_subtract\u2019 (or \u2018_subtract.xxx\u2019 "
						"with a dot suffix) to your font.",
						title="Subtractor"
					)
				return

			# Pick one subtract glyph at random
			subtractGlyph = choice(subtractGlyphs)
			subtractLayer = subtractGlyph.layers[layer.associatedMasterId]

			# Fall back to first layer if this master has no corresponding layer
			if subtractLayer is None and subtractGlyph.layers:
				subtractLayer = subtractGlyph.layers[0]

			if subtractLayer is None or not subtractLayer.shapes:
				return

			subtractFromLayer(layer, subtractLayer)

		except Exception as e:
			import traceback
			if inEditView:
				print("\nSubtractor Error:")
				print(traceback.format_exc())
				print(e)
			else:
				self.logToConsole("Subtractor Error: %s\n%s" % (str(e), traceback.format_exc()))

	@objc.python_method
	def generateCustomParameter(self):
		return self.__class__.__name__

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
