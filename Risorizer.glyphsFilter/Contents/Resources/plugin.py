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
from AppKit import NSAffineTransform, NSAffineTransformStruct

import random

def buildTriangle(position=NSPoint(0,0), averageSize=20):
	path = GSPath()
	for i in range(4):
		size = averageSize*(1+random.gauss(0,0.5))
		x = position.x - size*0.5 + size
		size = averageSize*(1+random.gauss(0,0.5))
		y = position.y - size*0.5 + size
		node = GSNode()
		node.position = NSPoint(x,y)
		path.nodes.append(node)
	path.closed = True
	return path
	
def lineInBoundsOfLayer(height=0, layer=None):
	if layer:
		bottom = layer.bounds.origin.y
		top = bottom + layer.bounds.size.height
		if bottom < height < top:
			leftmost = layer.bounds.origin.x
			rightmost = leftmost+layer.bounds.size.width
			intersects = layer.intersectionsBetweenPoints(
				NSPoint(leftmost-1, height),
				NSPoint(rightmost+1, height), 
				components = False)
			if len(intersects) > 2:
				return [p.x for p in intersects[1:-1]]
	return None

def spotsForLayer(layer, density=0.002, size=15):
	virtualLayer = GSLayer()
	layerArea = layer.bezierPath
	
	bottom = layer.bounds.origin.y
	height = layer.bounds.size.height
	top = bottom + height
	left = layer.bounds.origin.x
	width = layer.bounds.size.width
	right = left + width
	
	count = int(width*height*density)
	for i in range(count):
		x = left+width*random.random()
		y = bottom+height*random.random()
		randomPos = NSPoint(x,y)
		virtualArea = virtualLayer.bezierPath
		if layerArea.containsPoint_(randomPos):
			if not virtualArea or (virtualArea and not virtualArea.containsPoint_(randomPos)):
				triangle = buildTriangle(position=randomPos, averageSize=size)
				if triangle:
					virtualLayer.paths.append(triangle)
	
	virtualLayer.removeOverlap()
	shiftBack = NSAffineTransform.transform()
	shiftBack.translateXBy_yBy_(-0.5*size,-0.5*size)
	virtualLayer.applyTransform(shiftBack.transformStruct())
	
	return virtualLayer

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

	# Definitions of IBOutlets

	# The NSView object from the User Interface. Keep this here!
	dialog = objc.IBOutlet()

	# Text field in dialog
	insetField = objc.IBOutlet()
	densityField = objc.IBOutlet()
	sizeField = objc.IBOutlet()

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
		
		# Set value of text field
		self.insetField.setStringValue_(Glyphs.defaults['com.mekkablue.Risorizer.inset'])
		self.densityField.setStringValue_(Glyphs.defaults['com.mekkablue.Risorizer.density'])
		self.sizeField.setStringValue_(Glyphs.defaults['com.mekkablue.Risorizer.size'])
		
		# Set focus to text field
		self.insetField.becomeFirstResponder()

	# Action triggered by UI
	@objc.IBAction
	def setInset_( self, sender ):
		
		# Store value coming in from dialog
		Glyphs.defaults['com.mekkablue.Risorizer.inset'] = sender.floatValue()
		
		# Trigger redraw
		self.update()

	# Action triggered by UI
	@objc.IBAction
	def setDensity_( self, sender ):
		
		# Store value coming in from dialog
		Glyphs.defaults['com.mekkablue.Risorizer.density'] = sender.floatValue()
		
		# Trigger redraw
		self.update()

	# Action triggered by UI
	@objc.IBAction
	def setSize_( self, sender ):
		
		# Store value coming in from dialog
		Glyphs.defaults['com.mekkablue.Risorizer.size'] = sender.floatValue()
		
		# Trigger redraw
		self.update()


	# Actual filter
	@objc.python_method
	def filter(self, layer, inEditView, customParameters):
		# fallback:
		size = 15
		density = 2
		inset = 15
		
		# Called on font export, get value from customParameters
		if not inEditView:
			if "size" in customParameters:
				size = customParameters['size']
			if "density" in customParameters:
				density = customParameters['density']
			if "inset" in customParameters:
				inset = customParameters['inset']
		
		# Called through UI, use stored value
		else:
			size = float(Glyphs.defaults['com.mekkablue.Risorizer.size'])
			density = float(Glyphs.defaults['com.mekkablue.Risorizer.density'])
			inset = float(Glyphs.defaults['com.mekkablue.Risorizer.inset'])
		
		layerCopy = layer.copyDecomposedLayer()
		layerCopy.removeOverlap()
		layerCopy.correctPathDirection()
		offsetLayer( layerCopy, -2*inset )
		newPaths = spotsForLayer(layerCopy, density*0.0001, size).paths
		layer.paths.extend(newPaths)
		layer.correctPathDirection()

	@objc.python_method
	def generateCustomParameter( self ):
		return "%s; size:%s; density:%s; inset:%s" % (
			self.__class__.__name__, 
			Glyphs.defaults['com.mekkablue.Risorizer.size'],
			Glyphs.defaults['com.mekkablue.Risorizer.density'],
			Glyphs.defaults['com.mekkablue.Risorizer.inset'],
			)

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
