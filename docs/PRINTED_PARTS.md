# Printed parts

Every 3D-printed part, made by the scripts in `hardware/` (they need `pip install -r
hardware/requirements.txt`). Each script writes its STL files next to itself. Times and weights are
from an Anycubic Kobra Max with PrusaSlicer.

| Part | Qty | File (script) | Color | On the bed | Print settings | Filament, time |
|---|---|---|---|---|---|---|
| Lower-left tile | 1 | `tile_lower_left.stl` (`make_tile.py lower_left`) | black | 142 x 166 mm, floor down | PLA, 0.28 mm layers, 0.6 mm lines, 2 walls, no supports | 86 g, about 5 h |
| Upper-left tile | 1 | `tile_upper_left.stl` (`make_tile.py upper_left`) | black | 287 x 388 mm, floor down, turned 15 degrees to fit a 400 mm bed | as above | 216 g, about 13 h |
| Upper-right tile | 1 | `tile_upper_right.stl` (`make_tile.py upper_right`) | black | 286 x 363 mm, floor down | as above | 218 g, about 13.5 h |
| Small parts plate: 16 wire clips, the Sparkle Motion tray, 6 SKIP-pixel cups, 8 zip-tie anchors, the Matrix Portal cradle | 1 plate | `parts_plate.stl` (`make_parts.py`) | any | 231 x 153 mm | PLA, 0.20 mm layers, 3 walls, 15% infill | |
| Matrix Portal cradle, on its own | 1 | `portal_cradle.stl` (`make_parts.py`) | any | 64 x 34 mm | as above | |
| Sign plate: the bezel, 6 sign brackets and their bases, 2 stand feet | 1 plate | `sign_parts.stl` (`make_parts.py`); the brackets and bases alone are `sign_mounts.stl` | black | 322 x 257 mm; the bezel face down, the brackets and feet on their sides | PLA, 0.20 mm layers, 4 walls, 30% infill | 118 g, about 8 h |

What each one does:

- **Tiles**: hold all 264 pixels behind the wood, a double collar per station, with each pixel's
  number on a plate beside its hole. Glued to the back of the face with E6000. The tiles are cut
  from the map in `make_tile.py` (`TILES`); a smaller bed needs more, smaller tiles. Check with
  `python hardware/make_tile.py check` that no two collide.
- **Sparkle Motion tray, Matrix Portal cradle**: pegs through the boards' mounting holes, a zip tie
  over the top; glued to the wood.
- **SKIP-pixel cups**: hold the five pixels that light nothing.
- **Wire clips, zip-tie anchors**: keep the strings and the power wiring off the pixels.
- **Sign brackets and bases**: a bracket screws into one of the LED panel's M3 inserts, through a
  4.2 mm slot, and its foot's two prongs push into a base glued to the wood beside the sign, so the
  sign can be pulled out with its brackets on. See "Holding the sign" in [BUILD.md](BUILD.md).
- **Bezel**: a 3 mm black frame round the sign window, on the front of the print.
- **Stand feet**: the bottom edge of the frame sits in their channel, leaning back 10 degrees.
  Sized from `panel.depth` in `build.yaml` (41.3 mm here).

