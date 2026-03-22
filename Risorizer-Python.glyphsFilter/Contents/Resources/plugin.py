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
from math import pi, cos, sin, atan2, sqrt, log, exp
from random import uniform, random


def trianglePoints(initialPoint, side=30, variance=0.4):
	# Calculate the minimum and maximum side lengths
	min_side = side - side * variance
	max_side = side + side * variance

	# Generate the second point
	angle = uniform(0, 2 * pi)
	x2 = initialPoint.x + uniform(min_side, max_side) * cos(angle)
	y2 = initialPoint.y + uniform(min_side, max_side) * sin(angle)

	# Calculate the angle between the first and second points
	angle12 = atan2(y2 - initialPoint.y, x2 - initialPoint.x)

	# Generate the third point
	angle23 = angle12 + uniform(pi / 3 - pi / 6, pi / 3 + pi / 6)  # 60 degrees +/- 30 degrees
	distance23 = uniform(min_side, max_side)
	x3 = x2 + distance23 * cos(angle23)
	y3 = y2 + distance23 * sin(angle23)

	# Check if the points make a counter-clockwise turn
	cross_product = (x2 - initialPoint.x) * (y3 - initialPoint.y) - (y2 - initialPoint.y) * (x3 - initialPoint.x)
	if cross_product < 0:
		# If not, swap the second and third points
		x2, x3 = x3, x2
		y2, y3 = y3, y2

	return (initialPoint, NSPoint(x2, y2), NSPoint(x3, y3))


def buildTriangle(position=NSPoint(0,0), averageSize=20, variance=0.5):
	path = GSPath()
	for newPosition in trianglePoints(position, side=averageSize, variance=variance):
		newNode = GSNode()
		newNode.position = newPosition
		path.nodes.append(newNode)
	path.closed = True
	return path


def distanceBetweenPoints(point1, point2):
	return ((point2.x - point1.x) ** 2 + (point2.y - point1.y) ** 2) ** 0.5


def allowedByDistribution(distribute, randomPos, initialSpark, measure=1000):
	if distribute == 0:
		return True
	
	# 1: Gauss
	# 2: Uniform
	# 3: Exponential
	# 4: Smooth

	def probForDistanceGauss(d, m=1000):
		if d >= m:
			return 0
		else:
			sigma = m / sqrt(-2 * log(0.01))
			return exp(-d**2 / (2 * sigma**2))

	def probForDistanceUniform(d, m=1000):
		if d >= m:
			return 0
		else:
			return 1 - d / m

	def probForDistanceExponential(d, m=1000):
		if d >= m:
			return 0
		else:
			lambda_val = -log(0.01) / m
			return exp(-lambda_val * d)

	def probForDistanceSmooth(d, m=1000):
		if d >= m:
			return 0
		else:
			return (1 - (d / m) ** 0.5) ** 2
	
	distance = distanceBetweenPoints(initialSpark, randomPos)
	randomNumber = random()
	if distribute == 1:
		return randomNumber <= probForDistanceGauss(distance, measure)
	elif distribute == 2:
		return randomNumber <= probForDistanceUniform(distance, measure)
	elif distribute == 3:
		return randomNumber <= probForDistanceExponential(distance, measure)
	elif distribute == 4:
		return randomNumber <= probForDistanceSmooth(distance, measure)
	
	# if all else fails:
	return True

	

def spotsForLayer(layer, density=0.002, size=15, variance=0.5, distribution=0):
	print("SPOTS", layer, density, size, variance, distribution)
	
	layerArea = layer.bezierPath

	layerBounds = layer.fastBounds() # bug in Glyphs 3 does not allow layer.bounds
	bottom = layerBounds.origin.y
	height = layerBounds.size.height
	left = layerBounds.origin.x
	width = layerBounds.size.width
	diagonal = (width**2 + height**2) ** 0.5

	count = int(width * height * density)
	if distribution > 0:
		count *= 2
	
	initialSpark = NSPoint(
		left + width * random(),
		bottom + height * random(),
		)
	
	print("SPARK", initialSpark, count)

	dirtLayer = GSLayer()
	addedShapes = 0
	for i in range(count):
		x = left + width * random()
		y = bottom + height * random()
		randomPos = NSPoint(x, y)
		
		if not layerArea.containsPoint_(randomPos):
			continue

		virtualArea = dirtLayer.bezierPath
		if virtualArea is not None:
			if virtualArea.containsPoint_(randomPos):
				continue

		if not allowedByDistribution(distribution, randomPos, initialSpark, measure=diagonal):
			continue

		triangle = buildTriangle(position=randomPos, averageSize=size, variance=variance)
		if triangle:
			if Glyphs.versionNumber >= 3:
				# GLYPHS 3
				dirtLayer.shapes.append(triangle)
				addedShapes += 1
			else:
				# GLYPHS 2
				dirtLayer.paths.append(triangle)
	
	print("ITERATION", len(dirtLayer.shapes), "=", addedShapes)
	
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
	distributeField = objc.IBOutlet()


	@objc.python_method
	def prefName(self, name):
		return "com.mekkablue.Risorizer." + name.strip()


	@objc.python_method
	def getPref(self, name):
		prefURL = self.prefName(name)
		pref = Glyphs.defaults[prefURL]
		return pref


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
		Glyphs.registerDefault(self.prefName('size'), 15.0)
		Glyphs.registerDefault(self.prefName('density'), 2)
		Glyphs.registerDefault(self.prefName('inset'), 15.0)
		Glyphs.registerDefault(self.prefName('variance'), 0.5)
		Glyphs.registerDefault(self.prefName('distribute'), 0)
		
		# Set value of text field
		self.insetField.setStringValue_(self.getPref('inset'))
		self.densityField.setStringValue_(self.getPref('density'))
		self.sizeField.setStringValue_(self.getPref('size'))
		self.varianceField.setValue_(float(self.getPref('variance')))
		self.distributeField.selectItemAtIndex_(int(self.getPref('distribute')))
		
		# Set focus to text field
		self.insetField.becomeFirstResponder()

	@objc.IBAction
	def setInset_(self, sender):
		Glyphs.defaults[self.prefName('inset')] = sender.floatValue()
		self.update()

	@objc.IBAction
	def setDensity_(self, sender):
		Glyphs.defaults[self.prefName('density')] = sender.floatValue()
		self.update()

	@objc.IBAction
	def setSize_(self, sender):
		Glyphs.defaults[self.prefName('size')] = sender.floatValue()
		self.update()

	@objc.IBAction
	def setVariance_(self, sender):
		Glyphs.defaults[self.prefName('variance')] = sender.floatValue()
		self.update()

	@objc.IBAction
	def setDistribute_(self, sender):
		Glyphs.defaults[self.prefName('distribute')] = sender.indexOfSelectedItem()
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
				distribute = 0
		
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
					if "distribute" in customParameters:
						distribute = int( customParameters['distribute'] )
				
				else:
					# Called through UI, use stored values:
					try:
						sizePref = self.getPref('size')
						size = float(sizePref)
					except:
						self.logToConsole("Risorizer in %s: Could not retrieve float value for size (%s)" % (layer.parent.name, sizePref))
				
					try:
						densityPref = self.getPref('density')
						density = float(densityPref)
					except:
						self.logToConsole("Risorizer in %s: Could not retrieve float value for density (%s)" % (layer.parent.name, densityPref))
				
					try:
						insetPref = self.getPref('inset')
						inset = float(insetPref)
					except:
						self.logToConsole("Risorizer in %s: Could not retrieve float value for inset (%s)" % (layer.parent.name, insetPref))
				
					try:
						variancePref = self.getPref('variance')
						variance = float(variancePref)
					except:
						self.logToConsole("Risorizer in %s: Could not retrieve float value for variance (%s)" % (layer.parent.name, variancePref))

					try:
						distributePref = self.getPref('distribute')
						distribute = int(distributePref)
					except:
						self.logToConsole("Risorizer in %s: Could not retrieve int value for variance (%s)" % (layer.parent.name, distributePref))

				layer.removeOverlap()
				layerCopy = layer.copyDecomposedLayer()
				layerCopy.correctPathDirection()
				offsetLayer(layerCopy, -2*inset)
				
				if Glyphs.versionNumber >= 3:
					# GLYPHS 3
					newPaths = spotsForLayer(layerCopy, density*0.0001, size, variance, distribution=distribute).shapes
					for newPath in newPaths:
						layer.shapes.append(newPath)
				else:
					# GLYPHS 2
					newPaths = spotsForLayer(layerCopy, density*0.0001, size, variance, distribution=distribute).paths
					if newPaths:
						layer.paths.extend(newPaths)
				
				layer.roundCoordinates()
				layer.cleanUpPaths()
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
		return "%s; size:%s; density:%s; inset:%s; variance:%s; distribute:%s" % (
			self.__class__.__name__, 
			self.getPref('size'),
			self.getPref('density'),
			self.getPref('inset'),
			self.getPref('variance'),
			self.getPref('distribute'),
			)


	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
