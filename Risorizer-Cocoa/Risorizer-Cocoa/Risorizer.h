//
//  Risorizer.h
//  Risorizer-Cocoa
//
//  Native Objective-C + Interface Builder version of the Risorizer glyphsFilter.
//  Adds random triangular debris/spots to glyph outlines (Risograph-like effect).
//
//  Based on the Python plugin by Rainer Erich Scheichelbauer (mekkablue).
//  ObjC port: see GlyphsSDK Filter Plugin template (branch Glyphs4).
//

#import <Cocoa/Cocoa.h>

// Glyphs 4 moved the plug-in base classes out of GlyphsCore and into the
// GlyphsApp framework. GSFilterPlugin therefore has to be imported from
// <GlyphsApp/…>, while the object model (GSFont, GSLayer, GSPath, …) stays
// in GlyphsCore. Compare GlyphsSDK, branch Glyphs4:
// Xcode Templates/Glyphs Dev/Glyphs Filter Plugin.xctemplate
#import <GlyphsApp/GSFilterPlugin.h>
#import <GlyphsCore/GlyphsCore.h>
#import <GlyphsCore/GSFont.h>
#import <GlyphsCore/GSFontMaster.h>
#import <GlyphsCore/GSGlyph.h>
#import <GlyphsCore/GSLayer.h>
#import <GlyphsCore/GSPath.h>
#import <GlyphsCore/GSNode.h>

@interface Risorizer : GSFilterPlugin

@property (weak) IBOutlet NSTextField   *insetField;
@property (weak) IBOutlet NSTextField   *densityField;
@property (weak) IBOutlet NSTextField   *sizeField;
@property (weak) IBOutlet NSTextField   *minSizeField;
@property (weak) IBOutlet NSButton      *subtractField;
@property (weak) IBOutlet NSSlider      *varianceField;
@property (weak) IBOutlet NSPopUpButton *distributeField;

- (IBAction)setInset:(id)sender;
- (IBAction)setDensity:(id)sender;
- (IBAction)setSize:(id)sender;
- (IBAction)setMinSize:(id)sender;
- (IBAction)setSubtract:(id)sender;
- (IBAction)setVariance:(id)sender;
- (IBAction)setDistribute:(id)sender;

/// Returns the Custom Parameter string for pasting into Font Info → Custom Parameters.
- (NSString *)generateCustomParameter;

/// Returns the PreFilter Custom Parameter string (same value, different parameter name).
- (NSString *)generateCustomPreFilterParameter;

/// Apply the filter to a single layer.
- (void)processLayer:(GSLayer *)layer
               inset:(CGFloat)inset
             density:(CGFloat)density
                size:(CGFloat)size
             minSize:(CGFloat)minSize
            variance:(CGFloat)variance
          distribute:(NSInteger)distribute
            subtract:(BOOL)subtract;

@end
