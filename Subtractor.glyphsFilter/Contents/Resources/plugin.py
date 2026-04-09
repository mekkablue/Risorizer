# encoding: utf-8
from __future__ import division, print_function, unicode_literals

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


def isLayerEmpty(layer):
	"""Return True if the layer has no outlines or components."""
	if Glyphs.versionNumber >= 3:
		return not layer.shapes
	else:
		return not layer.paths and not layer.components


def subtractFromLayer(targetLayer, subtractLayer):
	"""
	Boolean-subtract the shapes of subtractLayer from targetLayer.
	A decomposed copy of subtractLayer is added with reversed path directions,
	then removeOverlap() performs the boolean subtraction.
	"""
	subtractCopy = subtractLayer.copyDecomposedLayer()
	subtractCopy.correctPathDirection()

	# Reverse all paths so they punch holes in the target layer
	if Glyphs.versionNumber >= 3:
		for shape in subtractCopy.shapes:
			if isinstance(shape, GSPath):
				shape.reverse()
	else:
		for path in subtractCopy.paths:
			path.reverse()

	# Append the reversed paths to the target layer
	if Glyphs.versionNumber >= 3:
		for shape in subtractCopy.shapes:
			targetLayer.shapes.append(shape)
	else:
		for path in subtractCopy.paths:
			targetLayer.paths.append(path)

	targetLayer.removeOverlap()
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
				if isLayerEmpty(layer):
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

			if subtractLayer is None or isLayerEmpty(subtractLayer):
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
