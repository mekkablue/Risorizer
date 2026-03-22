//
//  Risorizer.h
//  Risorizer-Cocoa
//
//  Native Objective-C + Interface Builder version of the Risorizer glyphsFilter.
//  Adds random triangular debris/spots to glyph outlines (Risograph-like effect).
//
//  Based on the Python plugin by Rainer Erich Scheichelbauer (mekkablue).
//  ObjC port: see GlyphsSDK Filter Plugin template and mekkablue/GreenHarmony2.
//

#import <Cocoa/Cocoa.h>
#import <GlyphsCore/GSFilterPlugin.h>
#import <GlyphsCore/GSLayer.h>
#import <GlyphsCore/GSPath.h>
#import <GlyphsCore/GSNode.h>
#import <GlyphsCore/GSGlyph.h>
#import <GlyphsCore/GSFont.h>
#import <GlyphsCore/GSFontMaster.h>

@interface Risorizer : GSFilterPlugin {
    // Current parameter values
    CGFloat   _inset;
    CGFloat   _density;
    CGFloat   _size;
    CGFloat   _variance;
    NSInteger _distribute;
}

@property (weak) IBOutlet NSTextField   *insetField;
@property (weak) IBOutlet NSTextField   *densityField;
@property (weak) IBOutlet NSTextField   *sizeField;
@property (weak) IBOutlet NSSlider      *varianceField;
@property (weak) IBOutlet NSPopUpButton *distributeField;

- (IBAction)setInset:(id)sender;
- (IBAction)setDensity:(id)sender;
- (IBAction)setSize:(id)sender;
- (IBAction)setVariance:(id)sender;
- (IBAction)setDistribute:(id)sender;

/// Returns the Custom Parameter string for pasting into Font Info → Custom Parameters.
- (NSString *)generateCustomParameter;

/// Apply the filter to a single layer.
- (void)processLayer:(GSLayer *)layer
               inset:(CGFloat)inset
             density:(CGFloat)density
                size:(CGFloat)size
            variance:(CGFloat)variance
          distribute:(NSInteger)distribute;

@end
