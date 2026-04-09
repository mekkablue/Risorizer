# Subtractor

Effect plug-in for the [Glyphs.app](https://www.glyphsapp.com) font editor for subtracting prebuilt shapes from your glyph layers.

## Installation

1. One-click install *Subtractor* from *Window > Plugin Manager*
2. Restart Glyphs.

## Usage

The filter subtracts shapes from the affected glyph layers. The shapes to be subtracted come from special glyphs in your font file named `_subtract`, or with a dot suffix such as `_subtract.rough` or `_subtract.edge`. If multiple subtract glyphs are present, one is chosen at random each time the filter is applied, creating natural variation across glyphs.

### Preparing subtract glyphs

1. Add a glyph named `_subtract` (or `_subtract.xxx` with a dot suffix) to your font.
2. Draw the shapes you want to subtract from your glyphs in that special glyph.
3. Apply *Filter > Subtractor* to the glyph layers you want to process.

### Notes

- **Multiple subtract glyphs**: If several `_subtract*` glyphs exist (e.g., `_subtract`, `_subtract.variant1`, `_subtract.rough`), one is picked at random on each application, giving you varied results across different glyphs or repeated runs.
- **Components**: Components in `_subtract` glyphs are automatically decomposed before the subtraction.
- **Masters**: The subtract glyph layer matching the current master is used. If no matching master layer exists, the first available layer is used as a fallback.

You can also add the filter as a custom parameter to one of your (static) instances in *Font Info > Exports.* Use the actions menu in the lower left to copy the parameter name into the clipboard for pasting in Font Info.

When applied as a custom parameter (during batch export), the following glyphs are always excluded from processing:

- All `_subtract*` glyphs
- `.notdef`
- The Apple glyph (`uniF8FF`)
- Empty glyphs (no outlines or components on the layer)

Keep in mind that boolean operations are CPU-intensive, so exporting a whole font with this effect may take some time.

### License

Copyright 2024–2026 Rainer Erich Scheichelbauer (@mekkablue).

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

See the License file included in this repository for further details.
