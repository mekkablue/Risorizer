# Subtractor

Effect plug-in for the [Glyphs.app](https://www.glyphsapp.com) font editor for subtracting prebuilt shapes from your glyph layers.

## Installation

1. One-click install *Subtractor* from *Window > Plugin Manager*
2. Restart Glyphs.

## Usage

The filter boolean-subtracts shapes from the affected glyph layers. The shapes come from special glyphs in your font named `_subtract`, or with a dot suffix such as `_subtract.rough` or `_subtract.edge`. If multiple subtract glyphs are present, one is chosen at random each time the filter is applied, creating natural variation across glyphs.

### Preparing subtract glyphs

1. Add a glyph named `_subtract` (or `_subtract.xxx` with a dot suffix) to your font.
2. Draw the shapes you want to subtract from your glyphs in that special glyph.
3. Apply *Filter > Subtractor* to the glyph layers you want to process.

### Settings

- **Subtract Shapes:** Name prefix of the subtract glyphs in your font. Default: `_subtract`. Change this if you want to use a different set of shapes for different effects.
- **Random Rotate:** Maximum rotation angle in degrees. The subtract shape is rotated by a random amount between −*n*° and +*n*° around its bounding-box centre before subtracting. Default: `5`.
- **Random Offset:** Maximum displacement in font units. The subtract shape is shifted by a random amount up to ±*n* units in both X and Y before subtracting. Default: `20`.

### Notes

- **Multiple subtract glyphs:** If several glyphs match the prefix (e.g., `_subtract`, `_subtract.variant1`, `_subtract.rough`), one is picked at random on each application for natural variation.
- **Components:** Components inside `_subtract` glyphs are automatically decomposed before the subtraction.
- **Masters:** The layer matching the current master is used. If no matching master layer exists, the first available layer is used as a fallback.

You can also add the filter as a custom parameter to one of your (static) instances in *Font Info > Exports.* Use the actions menu in the lower left to copy the current settings as a custom parameter into the clipboard, then paste it in Font Info.

When applied as a custom parameter (during batch export), the following glyphs are always excluded from processing:

- All glyphs whose name starts with the *Subtract Shapes* prefix
- `.notdef`
- The Apple glyph (`uniF8FF`), which many foundries use for their own logo
- Empty glyphs (no outlines or components on the layer)

Keep in mind that boolean operations are CPU-intensive, so exporting a whole font with this effect may take some time.

### License

Copyright 2024–2026 Rainer Erich Scheichelbauer (@mekkablue).

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

See the License file included in this repository for further details.
