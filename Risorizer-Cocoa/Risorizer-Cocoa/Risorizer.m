//
//  Risorizer.m
//  Risorizer-Cocoa
//
//  Native Objective-C implementation of the Risorizer glyphsFilter plugin.
//  Adds random triangular debris/spots inside glyph outlines (Risograph effect).
//
//  Algorithm ported from the Python version by Rainer Erich Scheichelbauer (mekkablue).
//

#import "Risorizer.h"

#import <GlyphsCore/GSFont.h>
#import <GlyphsCore/GSFontMaster.h>
#import <GlyphsCore/GSGlyph.h>
#import <GlyphsCore/GSLayer.h>
#import <GlyphsCore/GSPath.h>
#import <GlyphsCore/GSNode.h>
#import <GlyphsCore/GSCallbackHandler.h>

#import <math.h>

// Forward-declare the class method on GlyphsFilterOffsetCurve so the compiler
// knows the selector when we call it via NSClassFromString.
@interface NSObject (GlyphsFilterOffsetCurve)
+ (void)offsetLayer:(GSLayer *)layer
             offsetX:(CGFloat)offsetX
             offsetY:(CGFloat)offsetY
          makeStroke:(BOOL)makeStroke
          autoStroke:(BOOL)autoStroke
            position:(CGFloat)position
             metrics:(id)metrics
               error:(id)error
              shadow:(id)shadow
       capStyleStart:(NSUInteger)capStyleStart
         capStyleEnd:(NSUInteger)capStyleEnd
keepCompatibleOutlines:(BOOL)keepCompatibleOutlines;
@end

// ---------------------------------------------------------------------------
// Preference keys
// ---------------------------------------------------------------------------

static NSString * const kPrefInset      = @"com.mekkablue.Risorizer.inset";
static NSString * const kPrefDensity    = @"com.mekkablue.Risorizer.density";
static NSString * const kPrefSize       = @"com.mekkablue.Risorizer.size";
static NSString * const kPrefVariance   = @"com.mekkablue.Risorizer.variance";
static NSString * const kPrefDistribute = @"com.mekkablue.Risorizer.distribute";

// ---------------------------------------------------------------------------
// Distribution defaults
// ---------------------------------------------------------------------------

static const CGFloat kDefaultInset      = 15.0;
static const CGFloat kDefaultDensity    =  2.0;
static const CGFloat kDefaultSize       = 15.0;
static const CGFloat kDefaultVariance   =  0.5;
static const NSInteger kDefaultDistribute = 0;

// ---------------------------------------------------------------------------
// Math helpers (static / inline for speed)
// ---------------------------------------------------------------------------

static inline CGFloat uniformRandom(CGFloat lo, CGFloat hi) {
    return lo + (CGFloat)drand48() * (hi - lo);
}

static inline CGFloat pointDistance(NSPoint a, NSPoint b) {
    CGFloat dx = b.x - a.x, dy = b.y - a.y;
    return (CGFloat)sqrt(dx * dx + dy * dy);
}

// ---------------------------------------------------------------------------
// Triangle geometry
// ---------------------------------------------------------------------------

/// Returns three NSPoint values (as NSValue objects) forming a CCW-wound triangle
/// centred near `origin`, with legs of average length `side` ± `variance` fraction.
static NSArray<NSValue *> *RisorizerTrianglePoints(NSPoint origin,
                                                   CGFloat side,
                                                   CGFloat variance) {
    CGFloat minSide = side - side * variance;
    CGFloat maxSide = side + side * variance;

    // Second vertex
    CGFloat angle = uniformRandom(0.0, 2.0 * M_PI);
    CGFloat len1  = uniformRandom(minSide, maxSide);
    CGFloat x2 = origin.x + len1 * cos(angle);
    CGFloat y2 = origin.y + len1 * sin(angle);

    // Third vertex: 60° ± 30° from the first edge direction
    CGFloat angle12 = atan2(y2 - origin.y, x2 - origin.x);
    CGFloat angle23 = angle12 + uniformRandom(M_PI / 6.0, M_PI / 2.0);
    CGFloat len2    = uniformRandom(minSide, maxSide);
    CGFloat x3 = x2 + len2 * cos(angle23);
    CGFloat y3 = y2 + len2 * sin(angle23);

    // Ensure counter-clockwise winding
    CGFloat cross = (x2 - origin.x) * (y3 - origin.y)
                  - (y2 - origin.y) * (x3 - origin.x);
    if (cross < 0.0) {
        CGFloat tmp;
        tmp = x2; x2 = x3; x3 = tmp;
        tmp = y2; y2 = y3; y3 = tmp;
    }

    return @[
        [NSValue valueWithPoint:origin],
        [NSValue valueWithPoint:NSMakePoint(x2, y2)],
        [NSValue valueWithPoint:NSMakePoint(x3, y3)],
    ];
}

/// Builds a closed GSPath triangle at `position`.
static GSPath *RisorizerBuildTriangle(NSPoint position, CGFloat avgSize, CGFloat variance) {
    NSArray<NSValue *> *pts = RisorizerTrianglePoints(position, avgSize, variance);
    GSPath *path = [[GSPath alloc] init];
    for (NSValue *val in pts) {
        GSNode *node = [[GSNode alloc] init];
        node.position = val.pointValue;
        node.type = LINE;
        [path addNode:node];
    }
    path.closed = YES;
    return path;
}

// ---------------------------------------------------------------------------
// Distribution probability
// ---------------------------------------------------------------------------

/// Returns YES when a randomly-placed spot at `pos` should be kept,
/// given the distribution type and origin `spark`.
static BOOL RisorizerAllowedByDistribution(NSInteger distribute,
                                           NSPoint   pos,
                                           NSPoint   spark,
                                           CGFloat   measure) {
    if (distribute == 0) return YES; // Linear / uniform

    CGFloat d = pointDistance(spark, pos);
    if (d >= measure) return NO;

    CGFloat prob;
    switch (distribute) {
        case 1: { // Gauss
            CGFloat sigma = measure / sqrt(-2.0 * log(0.01));
            prob = exp(-(d * d) / (2.0 * sigma * sigma));
            break;
        }
        case 2: { // Uniform (linear falloff)
            prob = 1.0 - d / measure;
            break;
        }
        case 3: { // Exponential
            CGFloat lambda = -log(0.01) / measure;
            prob = exp(-lambda * d);
            break;
        }
        case 4: { // Smooth
            CGFloat t = d / measure;
            prob = (1.0 - sqrt(t)) * (1.0 - sqrt(t));
            break;
        }
        default:
            return YES;
    }

    return drand48() <= (double)prob;
}

// ---------------------------------------------------------------------------
// Core spot-generation logic
// ---------------------------------------------------------------------------

/// Generates a GSLayer containing random triangular spots that fit inside `sourceLayer`.
/// `density` is the fraction of bounding-box area to attempt to fill (e.g. 0.0002).
static GSLayer *RisorizerSpotsForLayer(GSLayer   *sourceLayer,
                                       CGFloat    density,
                                       CGFloat    size,
                                       CGFloat    variance,
                                       NSInteger  distribution) {
    NSBezierPath *layerPath = sourceLayer.bezierPath;
    if (!layerPath) return nil;

    NSRect  bounds   = sourceLayer.fastBounds;
    CGFloat left     = NSMinX(bounds);
    CGFloat bottom   = NSMinY(bounds);
    CGFloat width    = NSWidth(bounds);
    CGFloat height   = NSHeight(bounds);
    CGFloat diagonal = sqrt(width * width + height * height);

    NSInteger count = (NSInteger)(width * height * density);
    if (distribution > 0) count *= 2; // extra candidates for non-linear distributions

    // Random origin point for distribution calculations
    NSPoint spark = NSMakePoint(left + uniformRandom(0, width),
                                bottom + uniformRandom(0, height));

    GSLayer *dirtLayer = [[GSLayer alloc] init];
    for (NSInteger i = 0; i < count; i++) {
        NSPoint randomPos = NSMakePoint(left   + uniformRandom(0, width),
                                        bottom + uniformRandom(0, height));

        // Must be inside the source layer outline
        if (![layerPath containsPoint:randomPos]) continue;

        // Must not overlap with already-placed spots
        NSBezierPath *dirtPath = dirtLayer.bezierPath;
        if (dirtPath && [dirtPath containsPoint:randomPos]) continue;

        // Apply distribution filter
        if (!RisorizerAllowedByDistribution(distribution, randomPos, spark, diagonal)) continue;

        GSPath *triangle = RisorizerBuildTriangle(randomPos, size, variance);
        if (triangle) {
            [dirtLayer addShape:triangle];
        }
    }

    return dirtLayer;
}

// ---------------------------------------------------------------------------
// Offset-curve helper (calls the built-in GlyphsFilterOffsetCurve)
// ---------------------------------------------------------------------------

static void RisorizerOffsetLayer(GSLayer *layer, CGFloat offset) {
    Class offsetFilter = NSClassFromString(@"GlyphsFilterOffsetCurve");
    if (!offsetFilter) return;

    // Glyphs 3 API
    [offsetFilter offsetLayer:layer
                      offsetX:offset
                      offsetY:offset
                   makeStroke:NO
                   autoStroke:NO
                     position:0.5
                      metrics:nil
                        error:nil
                       shadow:nil
                capStyleStart:0
                  capStyleEnd:0
      keepCompatibleOutlines:NO];
}

// ---------------------------------------------------------------------------
// GSFilterPlugin subclass
// ---------------------------------------------------------------------------

@implementation Risorizer

@synthesize insetField, densityField, sizeField, varianceField, distributeField;

// ---------------------------------------------------------------------------
// Plugin lifecycle

- (void)loadPlugin {
    // Load the dialog NIB; sets the "view" outlet (→ _view) that the
    // framework checks to decide whether to show the filter dialog.
    NSBundle *bundle = [NSBundle bundleForClass:[self class]];
    [bundle loadNibNamed:@"Risorizer" owner:self topLevelObjects:nil];
}

// ---------------------------------------------------------------------------
// GSFilterPlugin identity

- (NSUInteger)interfaceVersion {
    return 1;
}

- (NSString *)title {
    return @"Risorizer";
}

- (NSString *)actionName {
    return NSLocalizedString(@"Apply", @"Risorizer action button");
}

- (NSString *)keyEquivalent {
    return nil;
}

// ---------------------------------------------------------------------------
// Setup (called when dialog opens; restore saved values into UI)

- (NSError *)setup {
    [super setup];

    NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];

    // Register defaults
    NSDictionary *defs = @{
        kPrefInset:      @(kDefaultInset),
        kPrefDensity:    @(kDefaultDensity),
        kPrefSize:       @(kDefaultSize),
        kPrefVariance:   @(kDefaultVariance),
        kPrefDistribute: @(kDefaultDistribute),
    };
    [ud registerDefaults:defs];

    _inset      = [ud floatForKey:kPrefInset];
    _density    = [ud floatForKey:kPrefDensity];
    _size       = [ud floatForKey:kPrefSize];
    _variance   = [ud floatForKey:kPrefVariance];
    _distribute = [ud integerForKey:kPrefDistribute];

    [insetField    setFloatValue:(float)_inset];
    [densityField  setFloatValue:(float)_density];
    [sizeField     setFloatValue:(float)_size];
    [varianceField setFloatValue:(float)_variance];
    [distributeField selectItemAtIndex:_distribute];

    [self process:nil];
    return nil;
}

// ---------------------------------------------------------------------------
// IBActions – update stored value and trigger live-preview redraw

- (IBAction)setInset:(id)sender {
    _inset = [sender floatValue];
    [[NSUserDefaults standardUserDefaults] setFloat:(float)_inset forKey:kPrefInset];
    [self process:nil];
}

- (IBAction)setDensity:(id)sender {
    _density = [sender floatValue];
    [[NSUserDefaults standardUserDefaults] setFloat:(float)_density forKey:kPrefDensity];
    [self process:nil];
}

- (IBAction)setSize:(id)sender {
    _size = [sender floatValue];
    [[NSUserDefaults standardUserDefaults] setFloat:(float)_size forKey:kPrefSize];
    [self process:nil];
}

- (IBAction)setVariance:(id)sender {
    _variance = [sender floatValue];
    [[NSUserDefaults standardUserDefaults] setFloat:(float)_variance forKey:kPrefVariance];
    [self process:nil];
}

- (IBAction)setDistribute:(id)sender {
    _distribute = [sender indexOfSelectedItem];
    [[NSUserDefaults standardUserDefaults] setInteger:_distribute forKey:kPrefDistribute];
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

        // Restore selection
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
                     inset:_inset
                   density:_density
                      size:_size
                  variance:_variance
                distribute:_distribute];
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
// Actions menu — "Copy Custom Parameter"

- (NSString *)generateCustomParameter {
    return [NSString stringWithFormat:
            @"Risorizer; inset:%g; density:%g; size:%g; variance:%g; distribute:%ld",
            _inset, _density, _size, _variance, (long)_distribute];
}

- (NSString *)generateCustomPreFilterParameter {
    return [self generateCustomParameter];
}

// ---------------------------------------------------------------------------
// Batch-export entry point (called via Custom Parameter)
//
// Custom Parameter syntax:
//   Risorizer; inset:15; density:2; size:15; variance:0.5; distribute:0

- (void)processFont:(GSFont *)font withArguments:(NSArray *)arguments {
    // Parse arguments (index 0 = class name, rest = key:value pairs)
    CGFloat   inset      = kDefaultInset;
    CGFloat   density    = kDefaultDensity;
    CGFloat   size       = kDefaultSize;
    CGFloat   variance   = kDefaultVariance;
    NSInteger distribute = kDefaultDistribute;

    for (NSUInteger i = 1; i < arguments.count; i++) {
        NSArray<NSString *> *pair = [[arguments[i] stringByTrimmingCharactersInSet:
                                      [NSCharacterSet whitespaceCharacterSet]]
                                     componentsSeparatedByString:@":"];
        if (pair.count != 2) continue;
        NSString *key = [pair[0] stringByTrimmingCharactersInSet:
                         [NSCharacterSet whitespaceCharacterSet]];
        CGFloat   val = [pair[1] floatValue];

        if ([key isEqualToString:@"inset"])           inset      = val;
        else if ([key isEqualToString:@"density"])    density    = val;
        else if ([key isEqualToString:@"size"])       size       = val;
        else if ([key isEqualToString:@"variance"])   variance   = val;
        else if ([key isEqualToString:@"distribute"]) distribute = (NSInteger)val;
    }

    _checkSelection = NO;
    NSString *masterId = font.fontMasters.firstObject.id;

    // Optional glyph-list filtering from arguments
    BOOL include = NO;
    NSSet *glyphNames = getIncludeExcludeGlyphListFilter(arguments, &include, font, nil);

    for (GSGlyph *glyph in font.glyphs) {
        if ([glyph.name isEqualToString:@".notdef"]) continue;
        if (glyphNames && ([glyphNames containsObject:glyph.name] != include)) continue;

        GSLayer *layer = [glyph layerForId:masterId];
        if (!layer) continue;

        [self processLayer:layer
                     inset:inset
                   density:density
                      size:size
                  variance:variance
                distribute:distribute];
    }
}

// ---------------------------------------------------------------------------
// Core filter — operates on a single layer in place

- (void)processLayer:(GSLayer *)layer
               inset:(CGFloat)inset
             density:(CGFloat)density
                size:(CGFloat)size
            variance:(CGFloat)variance
          distribute:(NSInteger)distribute {

    if (layer.shapes.count == 0) return;
    if ([layer.parent.name isEqualToString:@".notdef"]) return;

    @try {
        // 1. Remove overlap on original layer
        [layer flattenOutlinesRemoveOverlap:YES origHints:nil secondaryPath:nil extraHandles:nil error:nil];

        // 2. Work on an inset copy to avoid placing spots outside the outline
        GSLayer *workLayer = [layer copyDecomposedLayer];
        [workLayer correctPathDirection];
        RisorizerOffsetLayer(workLayer, -2.0 * inset);

        // 3. Generate spots inside the inset outline
        //    density UI value is "per 10 000 units²"; convert to fraction
        GSLayer *spotLayer = RisorizerSpotsForLayer(workLayer,
                                                    density * 0.0001,
                                                    size,
                                                    variance,
                                                    distribute);
        if (!spotLayer) return;

        // 4. Clean up spots: correct direction, remove overlap, then reverse
        //    so they act as counter-shapes when added to the main outline.
        [spotLayer correctPathDirection];
        [spotLayer flattenOutlinesRemoveOverlap:YES origHints:nil secondaryPath:nil extraHandles:nil error:nil];
        for (GSShape *shape in spotLayer.shapes) {
            if ([shape isKindOfClass:[GSPath class]]) {
                [(GSPath *)shape reverse];
            }
        }

        // 5. Add reversed spots to the original layer
        for (GSShape *shape in spotLayer.shapes) {
            [layer addShape:shape];
        }

        // 6. Clean up
        [layer roundCoordinates];
        [layer cleanUpPaths];
        [layer correctPathDirection];
    }
    @catch (NSException *ex) {
        NSLog(@"Risorizer: exception processing layer '%@': %@",
              layer.parent.name, ex);
    }
}

@end
