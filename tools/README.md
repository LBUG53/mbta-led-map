# tools/

Scripts you run on your computer, from the top folder of the repository.

| Script | What it does | When you run it |
|---|---|---|
| `build_firmware.py` | Packs your settings and the map into `firmware/data.json`, and with `--deploy` copies the firmware to the board. | After changing `config.yaml`, the map or the wiring plan. |
| `find_stops.py` | Lists the stops on a route with their IDs and direction numbers. | When choosing the sign's rows. |
| `wiring_plan.py` | Checks `data/wiring_plan.csv` and rewrites `data/wled_settings.md`. With `--force`, makes a new plan from scratch. | After editing the plan to match what you wired. |
| `wiring_sheet.py` | Writes `data/wiring_back_view.html`: the back of the panel, full size, with every pixel's number. | Before wiring. |
| `drill_guide.py` | Writes the drilling guide: the whole map mirrored at full size with a cross at every hole, to lay inside the frame and drill through. One sheet for a print shop (`data/drill_guide_back.svg`) and the same on nine Letter pages (`data/drill_guide_back_pages.html`). | Before drilling. |
| `printables.py` | Makes every page below in one go and lists them in build order. | Before you start building, and after changing the map or the wiring plan. |
| `test_page.py` | Writes `data/test_page.html`: downtown at full size on one Letter page. | Before ordering the print. |
| `sign_template.py` | Writes `data/sign_window_template.html`: the jigsaw template for the sign window, two Letter pages that fit into the panel's corner. | Before cutting the window. |
| `pixel_placer.py` | Writes `data/pixel_placer.html`: a page that shows each pixel's hole, one at a time (template: `pixel_placer.html`). | While wiring. |
| `power_guide.py` | Writes `data/power_guide.html`: the power wiring step by step, with the checks before power-on (template: `power_guide.html`). | While wiring the power. |
| `match_stations.py` | Matches the map's station names to MBTA station IDs and writes `data/station_ids.csv`. | Only after adding or renaming stations on the map. |
| `map/generate.py` | Makes the print, `data/stations.csv` and the validation report. | Only after changing the map. |

Each script starts with a description and its options; `python tools/<name>.py --help` works for
those that take options.

## map/

The map generator. `params.py` holds every number, `overrides.py` the few hand-placed exceptions;
the rest turn those into the print. See "The map generator" in
[How it works](../docs/HOW_IT_WORKS.md).

It measures label widths from Arial's font file. It looks for Arial in the usual places on
Windows, macOS and Linux, and for Liberation Sans (made to match Arial's widths) on Linux; to use other
files, set `PRINT_FONT_REGULAR` and `PRINT_FONT_BOLD` to their paths. Without a suitable font the widths
are only estimates, the label checks fail, and `generate.py` writes nothing, so the files in `data/`
(made on Windows with Arial) stay as the reference.
