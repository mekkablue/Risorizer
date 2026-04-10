# encoding: utf-8

###########################################################################################################
#
#
#	Filter with Dialog Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Filter%20with%20Dialog
#
#	For help on the use of Interface Builder:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates
#
#
###########################################################################################################

import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from Foundation import NSClassFromString, NSMutableArray
from math import cos, sin, radians
from random import choice, uniform


# Glyph names that are always excluded when running as a custom parameter
EXCLUDED_GLYPH_NAMES = frozenset(['.notdef', 'uniF8FF', 'apple'])


def getSubtractGlyphs(font, prefix='_subtract'):
	"""Return glyphs named exactly prefix or prefix.xxx from the font."""
	return [g for g in font.glyphs
	        if g.name == prefix or g.name.startswith(prefix + '.')]


def applyRandomTransform(layer, maxRotate, maxOffset):
	"""Randomly rotate (around bbox centre) and offset all shapes in layer."""
	bounds = layer.bounds
	cx = bounds.origin.x + bounds.size.width / 2.0
	cy = bounds.origin.y + bounds.size.height / 2.0
	angle = radians(uniform(-maxRotate, maxRotate))
	dx = uniform(-maxOffset, maxOffset)
	dy = uniform(-maxOffset, maxOffset)
	cosA = cos(angle)
	sinA = sin(angle)
	# Rotate around (cx, cy), then translate by (dx, dy)
	tX = cx * (1.0 - cosA) + cy * sinA + dx
	tY = cy * (1.0 - cosA) - cx * sinA + dy
	layer.applyTransform((cosA, sinA, -sinA, cosA, tX, tY))


def subtractFromLayer(targetLayer, subtractLayer, maxRotate=0.0, maxOffset=0.0):
	"""
	Boolean-subtract subtractLayer's shapes from targetLayer.
	Mirrors the subtract=YES branch in Risorizer.m (processLayer:…subtract:).
	"""
	# 1. Clean target layer in place
	targetLayer.removeOverlap()

	# 2. Decomposed, cleaned copy of the subtract shapes
	subtractCopy = subtractLayer.copyDecomposedLayer()
	subtractCopy.removeOverlap()
	subtractCopy.correctPathDirection()

	# 3. Apply random rotation and offset before subtracting
	if maxRotate != 0.0 or maxOffset != 0.0:
		applyRandomTransform(subtractCopy, maxRotate, maxOffset)

	# 4. Boolean subtraction via GSPathOperator (same class used by Risorizer.m)
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

	# 5. Put the result back and normalise directions
	targetLayer.shapes = minuends
	targetLayer.correctPathDirection()


class Subtractor(FilterWithDialog):

	# The NSView object from the User Interface. Keep this here!
	dialog = objc.IBOutlet()

	# Text fields in dialog
	subtractField = objc.IBOutlet()
	rotateField   = objc.IBOutlet()
	offsetField   = objc.IBOutlet()


	@objc.python_method
	def prefName(self, name):
		return "com.mekkablue.Subtractor." + name.strip()


	@objc.python_method
	def getPref(self, name):
		return Glyphs.defaults[self.prefName(name)]


	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': 'Subtractor',
			'de': 'Subtrahieren',
			'fr': 'Soustracteur',
			'es': 'Sustractor',
		})
		self.actionButtonLabel = Glyphs.localize({
			'en': 'Subtract',
			'de': 'Subtrahieren',
			'fr': 'Soustraire',
			'es': 'Sustraer',
			'pt': 'Subtrair',
			'jp': '削除',
			'ko': '빼기',
			'zh': '减去',
		})
		# Load dialog from .nib (without .extension)
		self.loadNib('IBdialog', __file__)


	# On dialog show
	@objc.python_method
	def start(self):
		# Set default values
		Glyphs.registerDefault(self.prefName('subtractShapes'), '_subtract')
		Glyphs.registerDefault(self.prefName('randomRotate'),   5.0)
		Glyphs.registerDefault(self.prefName('randomOffset'),   20.0)

		# Populate fields
		self.subtractField.setStringValue_(self.getPref('subtractShapes'))
		self.rotateField.setStringValue_(self.getPref('randomRotate'))
		self.offsetField.setStringValue_(self.getPref('randomOffset'))

		# Focus first field
		self.subtractField.becomeFirstResponder()


	@objc.IBAction
	def setSubtractShapes_(self, sender):
		Glyphs.defaults[self.prefName('subtractShapes')] = sender.stringValue()
		self.update()

	@objc.IBAction
	def setRandomRotate_(self, sender):
		Glyphs.defaults[self.prefName('randomRotate')] = sender.floatValue()
		self.update()

	@objc.IBAction
	def setRandomOffset_(self, sender):
		Glyphs.defaults[self.prefName('randomOffset')] = sender.floatValue()
		self.update()


	# Actual filter
	@objc.python_method
	def filter(self, layer, inEditView, customParameters):
		try:
			glyphName = layer.parent.name

			# Defaults
			subtractShapes = '_subtract'
			maxRotate      = 5.0
			maxOffset      = 20.0

			if not inEditView:
				# Batch export via custom parameter — read settings and apply exclusions
				if 'subtractShapes' in customParameters:
					subtractShapes = str(customParameters['subtractShapes'])
				if 'randomRotate' in customParameters:
					maxRotate = float(customParameters['randomRotate'])
				if 'randomOffset' in customParameters:
					maxOffset = float(customParameters['randomOffset'])

				if glyphName in EXCLUDED_GLYPH_NAMES:
					return
				if glyphName.startswith(subtractShapes):
					return
				if not layer.shapes:
					return
			else:
				# Interactive — read stored preferences
				try:
					subtractShapes = str(self.getPref('subtractShapes') or '_subtract')
				except:
					pass
				try:
					maxRotate = float(self.getPref('randomRotate'))
				except:
					pass
				try:
					maxOffset = float(self.getPref('randomOffset'))
				except:
					pass

			font = layer.parent.parent
			subtractGlyphs = getSubtractGlyphs(font, subtractShapes)

			if not subtractGlyphs:
				if inEditView:
					Message(
						"No subtract glyphs found.\n\n"
						"Please add a glyph named \u2018%s\u2019 "
						"(or \u2018%s.xxx\u2019 with a dot suffix) to your font." % (
							subtractShapes, subtractShapes),
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

			subtractFromLayer(layer, subtractLayer, maxRotate, maxOffset)

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
		return "%s; subtractShapes:%s; randomRotate:%s; randomOffset:%s" % (
			self.__class__.__name__,
			self.getPref('subtractShapes'),
			self.getPref('randomRotate'),
			self.getPref('randomOffset'),
		)


	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
