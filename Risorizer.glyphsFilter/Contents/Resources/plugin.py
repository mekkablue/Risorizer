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
from math import pi, cos, sin

import random

def buildTriangle(position=NSPoint(0,0), averageSize=20, variance=0.5):
	path = GSPath()
	for i in range(random.randrange(3,6)):
		x = position.x + cos( 2*pi*random.random() ) * averageSize * ( 1+random.gauss(0, variance) )
		y = position.y + sin( 2*pi*random.random() ) * averageSize * ( 1+random.gauss(0, variance) )
		path.nodes.append(GSNode((x,y)))
	path.closed = True
	return path

def spotsForLayer(layer, density=0.002, size=15, variance=0.5):
	dirtLayer = GSLayer()
	layerArea = layer.bezierPath
	
	if Glyphs.versionNumber == 3.2:
		bottom = layer.bounds.origin.y
		height = layer.bounds.size.height
		left = layer.bounds.origin.x
		width = layer.bounds.size.width
	else:
		bottom = layer.bounds.origin.y
		height = layer.bounds.size.height
		left = layer.bounds.origin.x
		width = layer.bounds.size.width
	# top = bottom + height
	# right = left + width
	
	count = int(width*height*density)
	virtualArea = dirtLayer.bezierPath
	
	for i in range(count):
		x = left + width * random.random()
		y = bottom + height * random.random()
		randomPos = NSPoint(x,y)
		if layerArea.containsPoint_(randomPos):
			if not virtualArea or (virtualArea and not virtualArea.containsPoint_(randomPos)):
				triangle = buildTriangle(position=randomPos, averageSize=size, variance=variance)
				if triangle:
					dirtLayer.paths.append(triangle)
	
	dirtLayer.removeOverlap()
	return dirtLayer

def offsetLayer( thisLayer, offset, makeStroke=False, position=0.5, autoStroke=False ):
	offsetFilter = NSClassFromString("GlyphsFilterOffsetCurve")
	try:
		# GLYPHS 3:	
		offsetFilter.offsetLayer_offsetX_offsetY_makeStroke_autoStroke_position_metrics_error_shadow_capStyleStart_capStyleEnd_keepCompatibleOutlines_(
			thisLayer,
			offset, offset, # horizontal and vertical offset
			makeStroke,     # if True, creates a stroke
			autoStroke,     # if True, distorts resulting shape to vertical metrics
			position,       # stroke distribution to the left and right, 0.5 = middle
			None, None, None, 0, 0, False )
	except:
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
				offsetLayer( layerCopy, -2*inset )
				if Glyphs.versionNumber >= 3:
					# GLYPHS 3
					
					newPaths = spotsForLayer(layer, density*0.0001, size, variance).shapes
					if newPaths:
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
					self.logToConsole( "Risorizer Error: %s\n%s" % (str(e), traceback.format_exc()) )

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
