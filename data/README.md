# data/

The map, as files. Everything else in the repository reads from here.

| File | What it is | Edit by hand? |
|---|---|---|
| `print_no_outline.svg`, `print_with_outline.svg` | The print, 610 x 610 mm. The second has a thin outline round the sign window. | No. Made by `tools/map/generate.py`. |
| `stations.csv` | All 132 stations: line, name, position in mm from the top-left corner, the positions of its two lights (A and B), and which way trains that light A are heading. | No. Made by `tools/map/generate.py`. |
| `station_ids.csv` | Each station's MBTA ID (`place-...`). | No. Made by `tools/match_stations.py`. |
| `wiring_plan.csv` | Every pixel on the three outputs, in wiring order: output, position on the output, station, line, and light (A, B, or SKIP for an unused pixel). | **Yes.** After wiring, change it to match what you built; the simulator and the board follow it. |
| `wled_settings.md` | What to enter in WLED, and notes on the wire runs. | No. Made by `tools/wiring_plan.py`. |
| `validation_report.md` | The result of every physical check on the map. | No. Made by `tools/map/generate.py`. |
| `wiring_back_view.html` | The back of the panel at full size with pixel numbers, to print. | No. Made by `tools/wiring_sheet.py`. |
| `drill_guide_back.svg`, `drill_guide_back_pages.html` | The drilling guide for the back of the panel: the size of the opening (569.6 mm square), mirrored, a cross at every hole. One sheet for a print shop, and the same on nine Letter pages. | No. Made by `tools/drill_guide.py`. |
| `test_page.html` | One Letter page of the print at full size, to check before ordering it. | No. Made by `tools/test_page.py`. |
| `sign_window_template.html` | The jigsaw template for the sign window, two Letter pages. | No. Made by `tools/sign_template.py`. |
| `pixel_placer.html` | Each pixel's hole, one at a time, to open while wiring. | No. Made by `tools/pixel_placer.py`. |
| `power_guide.html` | The power wiring, step by step. | No. Made by `tools/power_guide.py`. |
| `hardware_back_view.html` | The back of the panel with the tiles and a proposed place for each part. | No. Made by `hardware/make_hardware_view.py`. |

Positions are millimeters on the front of the panel, x from the left edge and y from the top.

Light A is on the right-hand side of a train travelling the way the line is drawn; `stations.csv`
says in words which way that is for each station.

The print and the files made from it are licensed CC BY-NC 4.0; see `LICENSE-DESIGN.md`.
