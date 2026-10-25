# Lichtenstein eyes → SVG for embroidery

Repeatable pipeline: `./make_eyes.sh <config>` takes a source painting, rotates it so the
two eyes are level, crops a rectangle around them, and traces each colour to its own layer in one SVG.

Requires ImageMagick (`magick`), `potrace`, and `rsvg-convert` (all installed via Homebrew).

    ./make_eyes.sh drowning_girl.conf
    ./make_eyes.sh crying_girl.conf

Each config sets:

- `SRC`, `NAME` – source image and output folder name (`output/<NAME>/`)
- `EYE1_X/Y`, `EYE2_X/Y` – approximate centre of each eye in the source image; the script
  computes the tilt from these and rotates about their midpoint
- `CROP_W`, `CROP_H` – crop rectangle size, centred on the eye midpoint; `SHIFT_X/Y` nudge it
- `LAYERS` – array of `name|svg fill|sampled colour|fuzz|blur[|grow]`; each becomes a traced
  `<g id="name">` in that colour, later entries drawn on top (hair first, lines last). `grow` fattens
  the shape by that many px (after dropping specks) so it tucks under the layer above with no gap;
  dot knockout still uses the ungrown shape.
- `SKIN` – `all` (every pixel no layer or exclusion claims; best when the crop is all face) or
  `sampled colour|fuzz|blur`. The region is filled with a grid of `DOT_COLOR` circles, `DOT_SPACING`
  apart, radius `DOT_RADIUS`. `DOT_ANGLE_SRC` is the halftone grid angle measured in the *source*
  image (both paintings: 0, axis-aligned); the script adds the eye rotation so the grid tilts the
  same way the painting's dots do in the crop. `DOT_STAGGER=1` gives a hex pattern instead of square.
  `DOT_ROW_SPACING` sets the row pitch separately. Dots whose circle touches the crop edge are kept.
- Dots run underneath the layers named in `DOTS_UNDER` (default `lines`), so the black line work
  stitches over a continuous grid; any other layer (hair) knocks dots out.
- Dot-free pockets: `ENCLOSED_MAX_AREA=N` clears every region fully enclosed by the `ENCLOSED_BY`
  layer's strokes (tears, eye whites, irises) up to N px in area, found by flood-filling the traced
  line mask from the crop border. `ENCLOSED_GAP` fattens the strokes first to close small breaks. Pieces touching the crop edge are
  never pruned by `LAYER_PRUNE`.
- `MANUAL_DOTS=file` – hand edits, one per line: `keep SX SY` or `remove SX SY` in *source image*
  pixels, so they survive crop changes. The nearest grid dot to each point is forced in or out.
  `output/<NAME>/dots.txt` lists every drawn dot as `crop_x crop_y source_x source_y` to copy from.
  Crying Girl uses `crying_girl.dots.txt` to keep the dotted skin at the inner corner of the left eye.
- `LAYER_PRUNE=("layer|inside-layer|max-area")` drops pieces of one layer that lie entirely inside
  another and are small (Drowning Girl: dark flecks in the blue hair that traced as black).
- `UPSCALE`, `TURD`, `ALPHAMAX` – tracing quality knobs (see comments in the script)

The SVG is: white `background` rect, `dots` group, then one group per layer. Each group is a
single thread colour for the embroidery software. `output/<NAME>/layers/` holds the mask bitmaps
(black = traced) so you can see exactly what each colour picked up.

Outputs per painting: `eyes.svg` (the deliverable), `crop_color.png` (the rotated crop),
`crop_bw.png` (what was traced), `check.png` (crop beside the traced result).

Sources in `source/`: `drowning_girl_hires.jpg` is the Lichtenstein catalogue raisonné scan
(1180x1200, lichtensteincatalogue.org entry 452) and is what the config uses; `drowning_girl.jpg`
(432 px) and `crying_girl.jpg` (499 px) came from WikiArt; Wikipedia copies (`*_wiki.jpg`, ~314 px)
are kept as a fallback. Measured halftone: Drowning Girl 3 px with every other row offset by half (brick pattern);
Crying Girl a square grid rotated 45° with ~3.9 px between neighbours. The artwork is copyrighted; this is for
personal craft use.
