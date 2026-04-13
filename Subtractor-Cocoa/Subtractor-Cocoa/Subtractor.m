//
//  Subtractor.m
//  Subtractor-Cocoa
//
//  Native Objective-C implementation of the Subtractor glyphsFilter plugin.
//  Boolean-subtracts prebuilt shapes (from _subtract glyphs) out of glyph outlines.
//
//  Algorithm ported from the Python plugin by Rainer Erich Scheichelbauer (@mekkablue).
//

#import "Subtractor.h"

#import <GlyphsCore/GSFont.h>
#import <GlyphsCore/GSFontMaster.h>
#import <GlyphsCore/GSGlyph.h>
#import <GlyphsCore/GSLayer.h>
#import <GlyphsCore/GSPath.h>
#import <GlyphsCore/GSNode.h>
#import <GlyphsCore/GSPathOperator.h>

#import <math.h>

// ---------------------------------------------------------------------------
// Preference keys
// ---------------------------------------------------------------------------

static NSString * const kPrefSubtractShapes = @"com.mekkablue.Subtractor.subtractShapes";
static NSString * const kPrefRandomRotate   = @"com.mekkablue.Subtractor.randomRotate";
static NSString * const kPrefRandomOffset   = @"com.mekkablue.Subtractor.randomOffset";
static NSString * const kPrefCenterBounds   = @"com.mekkablue.Subtractor.centerBounds";

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

static NSString * const kDefaultSubtractShapes = @"_subtract";
static const CGFloat    kDefaultRandomRotate   = 5.0;
static const CGFloat    kDefaultRandomOffset   = 20.0;
static const BOOL       kDefaultCenterBounds   = NO;

// ---------------------------------------------------------------------------
// Glyph names always excluded during batch export
// ---------------------------------------------------------------------------

static NSSet<NSString *> *SubtractorExcludedGlyphNames(void) {
    static NSSet<NSString *> *names = nil;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        names = [NSSet setWithObjects:@".notdef", @"uniF8FF", @"apple", nil];
    });
    return names;
}

// ---------------------------------------------------------------------------
// Helper: collect subtract glyphs matching prefix
// ---------------------------------------------------------------------------

/// Returns all glyphs in font named exactly `prefix` or `prefix.xxx`.
static NSArray<GSGlyph *> *SubtractorGetSubtractGlyphs(GSFont *font, NSString *prefix) {
    NSString *dotPrefix = [prefix stringByAppendingString:@"."];
    NSMutableArray<GSGlyph *> *result = [NSMutableArray array];
    for (GSGlyph *glyph in font.glyphs) {
        if ([glyph.name isEqualToString:prefix] || [glyph.name hasPrefix:dotPrefix]) {
            [result addObject:glyph];
        }
    }
    return result;
}

// ---------------------------------------------------------------------------
// Helper: compute bounding-box centre from node positions
// (works correctly on detached layers returned by copyDecomposedLayer)
// ---------------------------------------------------------------------------

static BOOL SubtractorLayerCenter(GSLayer *layer, CGFloat *outX, CGFloat *outY) {
    CGFloat minX = CGFLOAT_MAX,  minY = CGFLOAT_MAX;
    CGFloat maxX = -CGFLOAT_MAX, maxY = -CGFLOAT_MAX;
    BOOL found = NO;
    for (GSShape *shape in layer.shapes) {
        if (![shape isKindOfClass:[GSPath class]]) continue;
        for (GSNode *node in ((GSPath *)shape).nodes) {
            NSPoint p = node.position;
            if (p.x < minX) minX = p.x;
            if (p.x > maxX) maxX = p.x;
            if (p.y < minY) minY = p.y;
            if (p.y > maxY) maxY = p.y;
            found = YES;
        }
    }
    if (!found) return NO;
    *outX = (minX + maxX) / 2.0;
    *outY = (minY + maxY) / 2.0;
    return YES;
}

// ---------------------------------------------------------------------------
// Helper: apply affine transform to every GSPath in a layer
// (layer.applyTransform is unreliable on detached layers)
// ---------------------------------------------------------------------------

static void SubtractorApplyTransformToLayer(GSLayer *layer, NSAffineTransformStruct t) {
    for (GSShape *shape in layer.shapes) {
        if ([shape isKindOfClass:[GSPath class]]) {
            [(GSPath *)shape applyTransform:t];
        }
    }
}

// ---------------------------------------------------------------------------
// Helper: translate subtractCopy so its bbox centre aligns with targetLayer's
// ---------------------------------------------------------------------------

static void SubtractorCenterOnTarget(GSLayer *subtractCopy, GSLayer *targetLayer) {
    CGFloat scX, scY, tcX, tcY;
    if (!SubtractorLayerCenter(subtractCopy, &scX, &scY)) return;
    if (!SubtractorLayerCenter(targetLayer,  &tcX, &tcY)) return;
    NSAffineTransformStruct t = { 1, 0, 0, 1, tcX - scX, tcY - scY };
    SubtractorApplyTransformToLayer(subtractCopy, t);
}

// ---------------------------------------------------------------------------
// Helper: randomly rotate (around bbox centre) and offset all shapes in layer
// ---------------------------------------------------------------------------

static void SubtractorApplyRandomTransform(GSLayer *layer,
                                           CGFloat  maxRotate,
                                           CGFloat  maxOffset) {
    CGFloat cx, cy;
    if (!SubtractorLayerCenter(layer, &cx, &cy)) return;

    // Random angle in radians
    CGFloat angleDeg = -maxRotate + (CGFloat)drand48() * 2.0 * maxRotate;
    CGFloat angle    = angleDeg * M_PI / 180.0;
    CGFloat cosA     = (CGFloat)cos(angle);
    CGFloat sinA     = (CGFloat)sin(angle);

    // Random translation
    CGFloat dx = -maxOffset + (CGFloat)drand48() * 2.0 * maxOffset;
    CGFloat dy = -maxOffset + (CGFloat)drand48() * 2.0 * maxOffset;

    // Rotation around (cx, cy) combined with translation (dx, dy)
    NSAffineTransformStruct t = {
        .m11 = cosA,
        .m12 = sinA,
        .m21 = -sinA,
        .m22 = cosA,
        .tX  = cx * (1.0 - cosA) + cy * sinA  + dx,
        .tY  = cy * (1.0 - cosA) - cx * sinA  + dy,
    };
    SubtractorApplyTransformToLayer(layer, t);
}

// ---------------------------------------------------------------------------
// GSFilterPlugin subclass
// ---------------------------------------------------------------------------

@implementation Subtractor

@synthesize subtractField, rotateField, offsetField, centerBoundsField;

// ---------------------------------------------------------------------------
// Plugin lifecycle

- (void)loadPlugin {
    NSBundle *bundle = [NSBundle bundleForClass:[self class]];
    [bundle loadNibNamed:@"Subtractor" owner:self topLevelObjects:nil];
}

// ---------------------------------------------------------------------------
// GSFilterPlugin identity

- (NSUInteger)interfaceVersion {
    return 1;
}

- (NSString *)title {
    return @"Subtractor";
}

- (NSString *)actionName {
    return NSLocalizedString(@"Subtract", @"Subtractor action button");
}

- (NSString *)keyEquivalent {
    return nil;
}

- (NSString *)customParameterString {
    return [NSString stringWithFormat:
            @"Subtractor; subtractShapes:%@; randomRotate:%g; randomOffset:%g; centerBounds:%d",
            _subtractShapes, _randomRotate, _randomOffset, (int)_centerBounds];
}

// ---------------------------------------------------------------------------
// Setup (called when dialog opens; restore saved values into UI)

- (NSError *)setup {
    [super setup];

    NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];

    [ud registerDefaults:@{
        kPrefSubtractShapes: kDefaultSubtractShapes,
        kPrefRandomRotate:   @(kDefaultRandomRotate),
        kPrefRandomOffset:   @(kDefaultRandomOffset),
        kPrefCenterBounds:   @(kDefaultCenterBounds),
    }];

    _subtractShapes = [ud stringForKey:kPrefSubtractShapes] ?: kDefaultSubtractShapes;
    _randomRotate   = [ud floatForKey:kPrefRandomRotate];
    _randomOffset   = [ud floatForKey:kPrefRandomOffset];
    _centerBounds   = [ud boolForKey:kPrefCenterBounds];

    [subtractField    setStringValue:_subtractShapes];
    [rotateField      setFloatValue:(float)_randomRotate];
    [offsetField      setFloatValue:(float)_randomOffset];
    [centerBoundsField setState:_centerBounds ? NSControlStateValueOn : NSControlStateValueOff];

    [self process:nil];
    return nil;
}

// ---------------------------------------------------------------------------
// IBActions – update stored value and trigger live-preview redraw

- (IBAction)setSubtractShapes:(id)sender {
    _subtractShapes = [sender stringValue] ?: kDefaultSubtractShapes;
    [[NSUserDefaults standardUserDefaults] setObject:_subtractShapes forKey:kPrefSubtractShapes];
    [self process:nil];
}

- (IBAction)setRandomRotate:(id)sender {
    _randomRotate = [sender floatValue];
    [[NSUserDefaults standardUserDefaults] setFloat:(float)_randomRotate forKey:kPrefRandomRotate];
    [self process:nil];
}

- (IBAction)setRandomOffset:(id)sender {
    _randomOffset = [sender floatValue];
    [[NSUserDefaults standardUserDefaults] setFloat:(float)_randomOffset forKey:kPrefRandomOffset];
    [self process:nil];
}

- (IBAction)setCenterBounds:(id)sender {
    _centerBounds = ([sender state] == NSControlStateValueOn);
    [[NSUserDefaults standardUserDefaults] setBool:_centerBounds forKey:kPrefCenterBounds];
    [self process:nil];
}

// ---------------------------------------------------------------------------
// Live-preview reprocessing (shadow-layer pattern from GSFilterPlugin template)

- (void)process:(id)sender {
    for (NSUInteger k = 0; k < _shadowLayers.count; k++) {
        GSLayer *shadowLayer = _shadowLayers[k];
        GSLayer *layer       = _layers[k];

        // Restore paths from shadow (non-destructive preview)
        layer.shapes = [[[NSMutableArray alloc] initWithArray:shadowLayer.shapes
                                                    copyItems:YES] mutableCopy];
        layer.selection = [NSOrderedSet orderedSet];
        if (_checkSelection && shadowLayer.selection.count > 0) {
            for (NSUInteger i = 0; i < shadowLayer.shapes.count; i++) {
                GSPath *shadowPath = (GSPath *)shadowLayer.shapes[i];
                GSPath *layerPath  = (GSPath *)layer.shapes[i];
                if (![shadowPath isKindOfClass:[GSPath class]]) continue;
                for (NSUInteger j = 0; j < shadowPath.nodes.count; j++) {
                    GSNode *shadowNode = shadowPath.nodes[j];
                    if ([shadowLayer.selection containsObject:shadowNode]) {
                        [layer addSelection:layerPath.nodes[j]];
                    }
                }
            }
        }

        [self processLayer:layer
            subtractShapes:_subtractShapes
              randomRotate:_randomRotate
              randomOffset:_randomOffset
              centerBounds:_centerBounds];
        [layer clearSelection];
    }
    [super process:nil];
}

// ---------------------------------------------------------------------------
// GlyphsFilter protocol — delegate to super so the dialog is always shown.

- (BOOL)runFilterWithLayer:(GSLayer *)layer error:(out NSError **)error {
    return [super runFilterWithLayer:layer error:error];
}

// ---------------------------------------------------------------------------
// Actions menu — "Copy Custom Parameter" / "Copy PreFilter Parameter"

- (NSString *)generateCustomParameter {
    return [NSString stringWithFormat:
            @"Subtractor; subtractShapes:%@; randomRotate:%g; randomOffset:%g; centerBounds:%d",
            _subtractShapes, _randomRotate, _randomOffset, (int)_centerBounds];
}

- (NSString *)generateCustomPreFilterParameter {
    return [self generateCustomParameter];
}

// ---------------------------------------------------------------------------
// Batch-export entry point (called via Custom Parameter during font export)
//
// Custom Parameter syntax (semicolon-separated key:value pairs):
//   Subtractor; subtractShapes:_subtract; randomRotate:5; randomOffset:20; centerBounds:0

- (void)processFont:(GSFont *)font withArguments:(NSArray *)arguments {
    NSString *subtractShapes = kDefaultSubtractShapes;
    CGFloat   randomRotate   = kDefaultRandomRotate;
    CGFloat   randomOffset   = kDefaultRandomOffset;
    BOOL      centerBounds   = kDefaultCenterBounds;

    // Parse key:value pairs (index 0 is the class name, skip it)
    for (NSUInteger i = 1; i < arguments.count; i++) {
        NSString *arg = [[arguments[i] stringByTrimmingCharactersInSet:
                          [NSCharacterSet whitespaceCharacterSet]] copy];
        NSArray<NSString *> *pair = [arg componentsSeparatedByString:@":"];
        if (pair.count < 2) continue;
        NSString *key = [pair[0] stringByTrimmingCharactersInSet:
                         [NSCharacterSet whitespaceCharacterSet]];
        // Value may contain colons (unlikely here, but be safe)
        NSString *valStr = [[pair subarrayWithRange:NSMakeRange(1, pair.count - 1)]
                            componentsJoinedByString:@":"];
        valStr = [valStr stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceCharacterSet]];

        if ([key isEqualToString:@"subtractShapes"])      subtractShapes = valStr;
        else if ([key isEqualToString:@"randomRotate"])   randomRotate   = (CGFloat)[valStr doubleValue];
        else if ([key isEqualToString:@"randomOffset"])   randomOffset   = (CGFloat)[valStr doubleValue];
        else if ([key isEqualToString:@"centerBounds"])   centerBounds   = (BOOL)[valStr integerValue];
    }

    NSSet<NSString *> *excluded  = SubtractorExcludedGlyphNames();
    NSString          *dotPrefix = [subtractShapes stringByAppendingString:@"."];

    _checkSelection = NO;

    for (GSGlyph *glyph in font.glyphs) {
        // Skip system-reserved glyphs
        if ([excluded containsObject:glyph.name]) continue;
        // Skip glyphs that are themselves subtract shapes
        if ([glyph.name isEqualToString:subtractShapes] || [glyph.name hasPrefix:dotPrefix]) continue;

        for (GSFontMaster *master in font.fontMasters) {
            GSLayer *layer = [glyph layerForId:master.id];
            if (!layer || layer.shapes.count == 0) continue;

            [self processLayer:layer
                subtractShapes:subtractShapes
                  randomRotate:randomRotate
                  randomOffset:randomOffset
                  centerBounds:centerBounds];
        }
    }
}

// ---------------------------------------------------------------------------
// Core filter — operates on a single layer in place

- (void)processLayer:(GSLayer *)layer
      subtractShapes:(NSString *)subtractShapes
        randomRotate:(CGFloat)maxRotate
        randomOffset:(CGFloat)maxOffset
        centerBounds:(BOOL)centerBounds {

    if (layer.shapes.count == 0) return;

    GSGlyph *glyph = layer.parent;
    GSFont  *font  = glyph.parent;
    if (!font) return;

    @try {
        // 1. Clean target layer in place
        [layer flattenOutlinesRemoveOverlap:YES
                                  origHints:nil
                              secondaryPath:nil
                              extraHandles:nil
                                      error:nil];

        // 2. Collect subtract glyphs; bail if none found
        NSArray<GSGlyph *> *subtractGlyphs = SubtractorGetSubtractGlyphs(font, subtractShapes);
        if (subtractGlyphs.count == 0) return;

        // 3. Pick one subtract glyph at random
        GSGlyph *subtractGlyph = subtractGlyphs[arc4random_uniform((uint32_t)subtractGlyphs.count)];

        // 4. Use the master-matching layer; fall back to first layer
        NSString *masterId    = layer.associatedMasterId;
        GSLayer  *subtractLayer = [subtractGlyph layerForId:masterId];
        if (!subtractLayer && subtractGlyph.layers.count > 0) {
            subtractLayer = subtractGlyph.layers[0];
        }
        if (!subtractLayer || subtractLayer.shapes.count == 0) return;

        // 5. Decomposed, cleaned copy of the subtract shapes
        GSLayer *subtractCopy = [subtractLayer copyDecomposedLayer];
        [subtractCopy flattenOutlinesRemoveOverlap:YES
                                         origHints:nil
                                     secondaryPath:nil
                                     extraHandles:nil
                                             error:nil];
        [subtractCopy correctPathDirection];

        // 6. Optionally centre subtract shape on target, then apply random transform
        if (centerBounds) {
            SubtractorCenterOnTarget(subtractCopy, layer);
        }
        if (maxRotate != 0.0 || maxOffset != 0.0) {
            SubtractorApplyRandomTransform(subtractCopy, maxRotate, maxOffset);
        }

        // 7. Boolean subtraction via GSPathOperator
        NSMutableArray<GSPath *> *subtrahends = [NSMutableArray array];
        for (GSShape *shape in subtractCopy.shapes) {
            if ([shape isKindOfClass:[GSPath class]])
                [subtrahends addObject:(GSPath *)shape];
        }
        NSMutableArray<GSPath *> *minuends = [NSMutableArray array];
        for (GSShape *shape in layer.shapes) {
            if ([shape isKindOfClass:[GSPath class]])
                [minuends addObject:(GSPath *)shape];
        }

        if (subtrahends.count == 0 || minuends.count == 0) return;

        NSError *subtractError = nil;
        [GSPathOperator subtractPaths:subtrahends from:minuends error:&subtractError];

        // 8. Put result back and normalise
        layer.shapes = (NSMutableArray<GSShape *> *)minuends;
        [layer correctPathDirection];
    }
    @catch (NSException *ex) {
        NSLog(@"Subtractor: exception processing layer '%@': %@", glyph.name, ex);
    }
}

@end
