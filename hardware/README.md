# hardware/

The 3D-printed parts, as programs. Each `make_*.py` script builds a shape and saves it as an STL
file next to itself; nothing here was drawn in a CAD program. The STL files are not in git: run
the script to get them.

```bash
pip install -r hardware/requirements.txt
```

| Script | Makes | Printed and used? |
|---|---|---|
| `make_tile.py` | The three tiles that hold the pixels behind the wood. | Yes |
| `make_parts.py` | Small parts on one plate, the Matrix Portal cradle on its own, and the sign's bezel and brackets. | Yes; the sign parts not yet |
| `make_hardware_view.py` | Not a part: a drawing of the back of the panel with everything on it (`data/hardware_back_view.html`). | |
| `stl.py` | Shared by the scripts: saves a shape as an STL file. | |

The measured sizes (the panel, the sign, the pixel bore, the printer's bed) come from `build.yaml`
at the top of the repository; `make_tile.py check` and `make_parts.py` say whether each part fits
the bed. The most important for the tiles are `pixels.bore` (the hole that grips a pixel, 13.0 mm
for 12 mm bullet pixels) and `pixels.collar_depth` (how much of the pixel a collar holds). The other
numbers at the top of each script are design choices, each with a comment.

## How the tiles are made

`make_tile.py` reads `data/stations.csv` (where every light is) and `data/wiring_plan.csv` (each
pixel's number), so the tiles always match the map. For each tile it:

1. puts a double collar at every station;
2. joins neighboring stations on a line with flat ribs, adds braces between stations that have
   nothing between them, and makes sure the result is one piece;
3. adds round glue tabs along the ribs;
4. puts a number plate beside each hole, wherever there is room, with the pixel's number in raised
   digits and dots for its output;
5. adds knob-and-socket joints where two tiles meet;
6. cuts a slot in the rim of two far-apart collars, the locating collars that sit over the drill
   guide's reference holes.

The tiles are drawn as the panel looks from behind, so they print floor down and the numbers read
correctly from the back.

## To improve

- **The number plates are hard to read.** Found while wiring the first string into the finished
  panel: the raised digits beside each hole are small (set by `DIGIT_W`, `DIGIT_H`, `STROKE` and
  `RAISE` in `make_tile.py`) and black on black. Before the next print, make them bigger or easier
  to read some other way: larger or taller digits where there is room, digits sunk into the plate
  so they can be filled with paint, or a second filament color for the top layers. Until then,
  wire from `data/wiring_back_view.html` and use the plates only to confirm.

## License

The STL files these scripts produce, and parts printed from them, are CC BY-NC 4.0 (see
`LICENSE-DESIGN.md`). One tile carries a small raised credit; `CREDIT` in `make_tile.py` sets it.
