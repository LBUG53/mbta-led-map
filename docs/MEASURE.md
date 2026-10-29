# Measure first

Before printing, drilling or cutting anything, measure your parts and put the numbers in
`build.yaml`. Everything that has to fit your parts reads them from there: the drill guide, the sign
window template, the tiles, the sign's brackets, the bezel and the stand feet. Then remake them:

```bash
python tools/printables.py
python hardware/make_tile.py check
python hardware/make_parts.py
```

Artist's panels and LED panels vary from batch to batch, so measure even if you bought the same
ones. Calipers are best; a steel ruler read carefully will do for most of these.

## The wood panel (`panel:`)

| Setting | How to measure | What follows it | This build |
|---|---|---|---|
| `size` | Across the front, edge to edge, both ways. The map assumes a square. | The drill guide, the sign template. | 609.6 mm |
| `frame_wall` | From the back: the width of one frame wall, from the outside edge to its inside face. | The drill guide's size (it drops into the opening), the sign template's dashed line. The map fits walls up to 38.1 mm; wider and the scripts stop with an error. | 20.0 mm |
| `depth` | At an edge: from the front face to the back of the frame. | The stand feet's channel. | 41.3 mm |
| `hole` | The drill bit for the light holes. | The drill guide's crosses, and the map's checks (the rivers keep clear of the holes). | 6.35 mm (1/4 in) |

## The LED sign (`sign:`)

| Setting | How to measure | What follows it | This build |
|---|---|---|---|
| `width`, `height` | The panel's outside. | Where the window goes on the map, the template, the bezel. | 317.5 x 158.75 mm |
| `edge` | Not measured: your choice. How far the sign sits from the right and bottom edges of the print. It has to clear the frame wall by enough for a jigsaw (12 mm here). | The map, the template. Changing it changes the map: regenerate it (`python tools/map/generate.py`) and check its report. | 32.35 mm |
| `window_inset` | Not measured: how much smaller than the sign the cut window is, on each side, so the wood stops the sign. | The template, the print's black window, the bezel. | 1.0 mm |
| `thickness` | At the edge, face to back of the frame round its edge, where a bracket's tab will sit. | The brackets' height. | 15.0 mm |

Also check its six mounting holes against Adafruit's drawing: a corner hole about 7.85 mm in from
both edges, and 152 mm from a corner hole to the middle one. The brackets' slots allow 5 to 13 mm.

![What to measure for the brackets](images/sign-bracket-measurements.png)

## The pixels (`pixels:`)

| Setting | How to measure | What follows it | This build |
|---|---|---|---|
| `bore` | Print the lower-left tile first, or a test collar, and try a pixel: it should push in firmly and not fall out. 1 mm over the pixel's diameter worked here; 12.0 to 12.6 mm gripped too tight for 12 mm pixels. | The tiles. | 13.0 mm |
| `collar_depth` | How much of the pixel's body a collar holds. 15 mm held; 9.5 mm let them fall out. | The tiles. | 15.0 mm |
| `wire_spacing` | Between two pixels on a string, along the wire, center to center. | The wiring plan: no two pixels in a row can be further apart than this, less 8 mm. Changing it needs a new plan (`python tools/wiring_plan.py --force`), so measure before wiring. | 80 mm |

## The 3D printer (`printer:`)

| Setting | How to measure | What follows it | This build |
|---|---|---|---|
| `bed` | The usable print area, from the printer's specifications. | `make_tile.py check` and `make_parts.py` say whether each part fits and at what turn. On a smaller bed the map has to be cut into more tiles (`TILES` in `hardware/make_tile.py`). | 400 x 400 mm |

## Before the print goes on

Print `data/test_page.html` at 100% and measure its 100 mm bar: if the bar is wrong, so is every
other page from the same printer settings. Every page to print has either a 100 mm bar or a 50 mm
grid for this.
