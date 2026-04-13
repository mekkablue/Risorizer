//
//  Subtractor.h
//  Subtractor-Cocoa
//
//  Native Objective-C + Interface Builder version of the Subtractor glyphsFilter.
//  Boolean-subtracts prebuilt shapes from glyph outlines.
//
//  Based on the Python plugin by Rainer Erich Scheichelbauer (@mekkablue).
//  ObjC port following the GlyphsSDK Filter Plugin template.
//

#import <Cocoa/Cocoa.h>
#import <GlyphsCore/GSFilterPlugin.h>
#import <GlyphsCore/GSLayer.h>
#import <GlyphsCore/GSPath.h>
#import <GlyphsCore/GSNode.h>
#import <GlyphsCore/GSGlyph.h>
#import <GlyphsCore/GSFont.h>
#import <GlyphsCore/GSFontMaster.h>

@interface Subtractor : GSFilterPlugin {
    NSString *_subtractShapes;
    CGFloat   _randomRotate;
    CGFloat   _randomOffset;
    BOOL      _centerBounds;
}

/// Text field: name prefix for subtract glyphs (default "_subtract").
@property (weak) IBOutlet NSTextField *subtractField;

/// Stepping text field: maximum random rotation in degrees (default 5).
@property (weak) IBOutlet NSTextField *rotateField;

/// Stepping text field: maximum random offset in font units (default 20).
@property (weak) IBOutlet NSTextField *offsetField;

/// Checkbox: center subtract shape over target bounding box before transform.
@property (weak) IBOutlet NSButton    *centerBoundsField;

- (IBAction)setSubtractShapes:(id)sender;
- (IBAction)setRandomRotate:(id)sender;
- (IBAction)setRandomOffset:(id)sender;
- (IBAction)setCenterBounds:(id)sender;

/// Returns the Custom Parameter string for pasting into Font Info → Exports.
- (NSString *)generateCustomParameter;

/// Apply the filter to a single layer with explicit parameter values.
- (void)processLayer:(GSLayer *)layer
      subtractShapes:(NSString *)subtractShapes
        randomRotate:(CGFloat)maxRotate
        randomOffset:(CGFloat)maxOffset
        centerBounds:(BOOL)centerBounds;

@end
