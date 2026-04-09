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
from random import choice


# Glyph names that are always excluded when running as a custom parameter
EXCLUDED_GLYPH_NAMES = frozenset(['.notdef', 'uniF8FF', 'apple'])


def getSubtractGlyphs(font):
	"""Return all glyphs named _subtract or _subtract.xxx from the font."""
	return [g for g in font.glyphs
	        if g.name == '_subtract' or g.name.startswith('_subtract.')]


def subtractFromLayer(targetLayer, subtractLayer):
	"""
	Subtract the shapes of subtractLayer from targetLayer.
	Both layers are decomposed and have overlaps removed first.
	The subtract shapes are then added to the target layer and
	correctPathDirection() lets nested paths become counter-forms.
	"""
	# Clean up the target layer in place
	targetLayer.removeOverlap()

	# Get a clean, decomposed copy of the subtract shapes
	subtractCopy = subtractLayer.copyDecomposedLayer()
	subtractCopy.removeOverlap()

	# Add subtract shapes to the target layer (no direction reversal)
	for shape in subtractCopy.shapes:
		targetLayer.shapes.append(shape)

	# Path direction correction turns overlapping inner shapes into holes
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
