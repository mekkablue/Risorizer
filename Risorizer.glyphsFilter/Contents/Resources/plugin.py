# encoding: utf-8
from __future__ import division, print_function, unicode_literals

###########################################################################################################
#
#
#	Filter with dialog Plugin
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
from Foundation import NSClassFromString
from AppKit import NSAffineTransform, NSAffineTransformStruct, NSPoint, NSView
from math import pi, cos, sin, atan2

import random


def trianglePoints(initialPoint, side=30, variance=0.4):
	# Calculate the minimum and maximum side lengths
	min_side = side - side * variance
	max_side = side + side * variance

	# Generate the second point
	angle = random.uniform(0, 2 * pi)
	x2 = initialPoint.x + random.uniform(min_side, max_side) * cos(angle)
	y2 = initialPoint.y + random.uniform(min_side, max_side) * sin(angle)

	# Calculate the angle between the first and second points
	angle12 = atan2(y2 - initialPoint.y, x2 - initialPoint.x)

	# Generate the third point
	angle23 = angle12 + random.uniform(pi / 3 - pi / 6, pi / 3 + pi / 6)  # 60 degrees +/- 30 degrees
	distance23 = random.uniform(min_side, max_side)
	x3 = x2 + distance23 * cos(angle23)
	y3 = y2 + distance23 * sin(angle23)

	# Check if the points make a counter-clockwise turn
	cross_product = (x2 - initialPoint.x) * (y3 - initialPoint.y) - (y2 - initialPoint.y) * (x3 - initialPoint.x)
	if cross_product < 0:
		# If not, swap the second and third points
		x2, x3 = x3, x2
		y2, y3 = y3, y2

	return [initialPoint, NSPoint(x2, y2), NSPoint(x3, y3)]


def buildTriangle(position=NSPoint(0,0), averageSize=20, variance=0.5):
	path = GSPath()
	for newPosition in trianglePoints(position, side=averageSize, variance=variance):
		newNode = GSNode()
		newNode.position = newPosition
		path.nodes.append(newNode)
	path.closed = True
	return path


def spotsForLayer(layer, density=0.002, size=15, variance=0.5):
	layerArea = layer.bezierPath

	layerBounds = layer.fastBounds()
	bottom = layerBounds.origin.y
	height = layerBounds.size.height
	left = layerBounds.origin.x
	width = layerBounds.size.width

	count = int(width*height*density)

	dirtLayer = GSLayer()
	
	for i in range(count):
		x = left + width * random.random()
		y = bottom + height * random.random()
		randomPos = NSPoint(x, y)
		
		if layerArea.containsPoint_(randomPos):
			virtualArea = dirtLayer.bezierPath
			if virtualArea is None or not virtualArea.containsPoint_(randomPos):
				triangle = buildTriangle(position=randomPos, averageSize=size, variance=variance)
				if triangle:
					if Glyphs.versionNumber >= 3:
						# GLYPHS 3
						dirtLayer.shapes.append(triangle)
					else:
						# GLYPHS 2
						dirtLayer.paths.append(triangle)
	
	dirtLayer.removeOverlap()
	return dirtLayer


def offsetLayer(thisLayer, offset, makeStroke=False, position=0.5, autoStroke=False):
	offsetFilter = NSClassFromString("GlyphsFilterOffsetCurve")
	if Glyphs.versionNumber >= 3:
		# GLYPHS 3:	
		offsetFilter.offsetLayer_offsetX_offsetY_makeStroke_autoStroke_position_metrics_error_shadow_capStyleStart_capStyleEnd_keepCompatibleOutlines_(
			thisLayer,
			offset, offset, # horizontal and vertical offset
			makeStroke,     # if True, creates a stroke
			autoStroke,     # if True, distorts resulting shape to vertical metrics
			position,       # stroke distribution to the left and right, 0.5 = middle
			None, None, None, 0, 0, False )
	else:
		# GLYPHS 2:
		offsetFilter.offsetLayer_offsetX_offsetY_makeStroke_autoStroke_position_error_shadow_(
			thisLayer,
			offset, offset, # horizontal and vertical offset
			makeStroke,     # if True, creates a stroke
			autoStroke,     # if True, distorts resulting shape to vertical metrics
			position,       # stroke distribution to the left and right, 0.5 = middle
			None, None )


class Risorizer(FilterWithDialog):

	# The NSView object from the User Interface. Keep this here!
	dialog = objc.IBOutlet()

	# Text field in dialog
	insetField = objc.IBOutlet()
	densityField = objc.IBOutlet()
	sizeField = objc.IBOutlet()
	varianceField = objc.IBOutlet()

	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': 'Risorizer',
			'de': 'Risorisieren',
			'fr': 'Risoriser',
			'es': 'Risorizar',
			})
		
		# Word on Run Button (default: Apply)
		self.actionButtonLabel = Glyphs.localize({
			'en': 'Apply',
			'de': 'Anwenden',
			'fr': 'Appliquer',
			'es': 'Aplicar',
			'pt': 'Aplique',
			'jp': '申し込む',
			'ko': '대다',
			'zh': '应用',
			})
		
		# Load dialog from .nib (without .extension)
		self.loadNib('IBdialog', __file__)

	# On dialog show
	@objc.python_method
	def start(self):
		
		# Set default value
		Glyphs.registerDefault('com.mekkablue.Risorizer.size', 15.0)
		Glyphs.registerDefault('com.mekkablue.Risorizer.density', 2)
		Glyphs.registerDefault('com.mekkablue.Risorizer.inset', 15.0)
		Glyphs.registerDefault('com.mekkablue.Risorizer.variance', 0.5)
		
		# Set value of text field
		self.insetField.setStringValue_(Glyphs.defaults['com.mekkablue.Risorizer.inset'])
		self.densityField.setStringValue_(Glyphs.defaults['com.mekkablue.Risorizer.density'])
		self.sizeField.setStringValue_(Glyphs.defaults['com.mekkablue.Risorizer.size'])
		self.varianceField.setValue_(float(Glyphs.defaults['com.mekkablue.Risorizer.variance']))
		
		# Set focus to text field
		self.insetField.becomeFirstResponder()

	@objc.IBAction
	def setInset_( self, sender ):
		Glyphs.defaults['com.mekkablue.Risorizer.inset'] = sender.floatValue()
		self.update()

	@objc.IBAction
	def setDensity_( self, sender ):
		Glyphs.defaults['com.mekkablue.Risorizer.density'] = sender.floatValue()
		self.update()

	@objc.IBAction
	def setSize_( self, sender ):
		Glyphs.defaults['com.mekkablue.Risorizer.size'] = sender.floatValue()
		self.update()

	@objc.IBAction
	def setVariance_( self, sender ):
		Glyphs.defaults['com.mekkablue.Risorizer.variance'] = sender.floatValue()
		self.update()

	# Actual filter
	@objc.python_method
	def filter(self, layer, inEditView, customParameters):
		if layer.parent.name != ".notdef":
			try:
				# fallback:
				size = 15
				density = 2
				inset = 15
				variance = 0.5
		
				if not inEditView:
					# Called on font export, get value from customParameters
					if "size" in customParameters:
						size = float( customParameters['size'] )
					if "density" in customParameters:
						density = float( customParameters['density'] )
					if "inset" in customParameters:
						inset = float( customParameters['inset'] )
					if "variance" in customParameters:
						variance = float( customParameters['variance'] )
				
				else:
					# Called through UI, use stored values:
					try:
						sizePref = Glyphs.defaults['com.mekkablue.Risorizer.size']
						size = float(sizePref)
					except:
						self.logToConsole("Risorizer in %s: Could not retrieve float value for size (%s)" % (layer.parent.name, sizePref))
				
					try:
						densityPref = Glyphs.defaults['com.mekkablue.Risorizer.density']
						density = float(densityPref)
					except:
						self.logToConsole("Risorizer in %s: Could not retrieve float value for density (%s)" % (layer.parent.name, densityPref))
				
					try:
						insetPref = Glyphs.defaults['com.mekkablue.Risorizer.inset']
						inset = float(insetPref)
					except:
						self.logToConsole("Risorizer in %s: Could not retrieve float value for inset (%s)" % (layer.parent.name, insetPref))
				
					try:
						variancePref = Glyphs.defaults['com.mekkablue.Risorizer.variance']
						variance = float(variancePref)
					except:
						self.logToConsole("Risorizer in %s: Could not retrieve float value for variance (%s)" % (layer.parent.name, variancePref))
				
				layerCopy = layer.copyDecomposedLayer()
				layerCopy.removeOverlap()
				layerCopy.correctPathDirection()
				offsetLayer(layerCopy, -2*inset)
				
				if Glyphs.versionNumber >= 3:
					# GLYPHS 3
					newPaths = spotsForLayer(layerCopy, density*0.0001, size, variance).shapes
					for newPath in newPaths:
						layer.shapes.append(newPath)
				else:
					# GLYPHS 2
					newPaths = spotsForLayer(layerCopy, density*0.0001, size, variance).paths
					if newPaths:
						layer.paths.extend(newPaths)
				
				layer.correctPathDirection()
			except Exception as e:
				import traceback
				if inEditView:
					print("\nRisorizer Error:")
					print(traceback.format_exc())
					print(e)
				else:
					self.logToConsole("Risorizer Error: %s\n%s" % (str(e), traceback.format_exc()) )


	@objc.python_method
	def generateCustomParameter( self ):
		return "%s; size:%s; density:%s; inset:%s; variance:%s" % (
			self.__class__.__name__, 
			Glyphs.defaults['com.mekkablue.Risorizer.size'],
			Glyphs.defaults['com.mekkablue.Risorizer.density'],
			Glyphs.defaults['com.mekkablue.Risorizer.inset'],
			Glyphs.defaults['com.mekkablue.Risorizer.variance'],
			)


	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
