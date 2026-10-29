# Make it yours

Four levels, from a setting to a rewrite:

1. **Your settings** in `config.yaml` (your copy of `config.example.yaml`): stops, teams, colors, who rides.
2. **Your parts** in `build.yaml`: a different panel, sign, pixels or 3D printer.
3. **A little code**: other teams, another time zone, different wiring, moving things on the map.
4. **Another city**: what has to be rewritten.

After changing `config.yaml`, restart the simulator to see the result, and install the firmware
again to put it on the board:

```bash
python tools/build_firmware.py --deploy D:
```

## 1. Settings

### Your stops

The sign shows two rows. Each is one route at one stop in one direction. To find the IDs:

```bash
python tools/find_stops.py 77
```

lists every stop on route 77 in both directions, with the direction number. Add part of a name to
narrow it down:

```bash
python tools/find_stops.py Red porter
```

Then in `config.yaml`, under `sign: rows:`, set for each row:

| Setting | Meaning |
|---|---|
| `label` | What the sign shows at the left of the row. Keep it short ("77", "RL"). |
| `route` | The MBTA route ID ("77", "Red", "Green-D", "CR-Fitchburg"...). |
| `stop_id` | From `find_stops.py`. For the subway, a station's `place-...` ID covers all its platforms. |
| `direction_id` | 0 or 1, as `find_stops.py` printed it. |
| `color` | The label's color. |
| `walk_minutes` | Optional. Departures sooner than this are left out, because you couldn't reach them. |

### Other settings

Every setting in `config.example.yaml` has a comment saying what it does. The ones people change:

- `ticker.latitude` / `longitude`: where the weather is for.
- `music.effects`: the effects Music mode offers, as `[name, WLED effect number]` (numbers from `http://<wled_ip>/json/effects`); add `lines` as a third item for the one that runs each line by itself in its color.
- `ticker.sox`, `bruins`, `patriots`: turn a team off with `false`.
- `sign.brightness`, `night.*`: how bright, and when night mode runs.
- `map.colors`: the LED color for each line. The print's ink colors look washed out on real LEDs,
  so these are purer; adjust them on your own pixels.
- `ride.buses`: the bus routes and stops a ride message can name (step 12 of the build guide).

## 2. Your parts

`build.yaml` holds the measured sizes of the physical parts: the panel (size, frame walls, depth,
hole), the sign (size, thickness, where it sits), the pixels (bore, collar depth, wire spacing) and
the printer's bed. [MEASURE.md](MEASURE.md) says how to measure each and what follows from it.
Change the numbers, then remake everything that has to fit:

```bash
python tools/printables.py
python hardware/make_tile.py check
python hardware/make_parts.py
```

The scripts stop with an error, or say so, when a number won't work: frame walls wider than the map
was drawn for, a part bigger than the bed. A smaller bed means cutting the map into more tiles
(`TILES` in `hardware/make_tile.py`). Moving the sign (`sign.edge`) or changing its size moves the
window on the print, so regenerate the map as well (`python tools/map/generate.py`).

## 3. A little code

### Different teams

Teams are listed in `TEAMS` near the top of `firmware/feeds.py`: a label, ESPN's sport, league and
team number, and a palette color from `firmware/sign.py`. Change an entry to follow a different
team. Adding a fourth also needs its name in the loop in `setup_sources()` in `firmware/app.py`, and
a `true`/`false` setting under `ticker:`.

The Bruins mode on the phone remote is written for the Bruins by name (`firmware/remote.py`).

### A different time zone

The clock is Boston's: `eastern_offset()` in `firmware/feeds.py` holds the US Eastern daylight-saving
rule, and the weather request asks for `America/New_York` and Fahrenheit. Both are in that file.

### Different wiring

Where each output's chain starts, and which lines it carries, is the `OUTPUTS` table at the top of
`tools/wiring_plan.py`. Change it and make a new plan:

```bash
python tools/wiring_plan.py --force
```

`--force` replaces `data/wiring_plan.csv`, so don't use it once you have edited that file by hand.
Then make the tiles again (`hardware/make_tile.py` reads the plan for the numbers it prints beside
each hole) and reinstall the firmware.

### Moving things on the map

Change numbers in `tools/map/params.py` (or add a nudge with its reason to
`tools/map/overrides.py`) and run

```bash
python tools/map/generate.py
```

It refuses to finish if the result breaks a physical rule. Afterwards, in this order: check
`data/validation_report.md`; run `python tools/wiring_plan.py --force` if stations moved far; rebuild
the tiles; reinstall the firmware. Everything downstream follows `data/stations.csv`.

## 4. Another city

The idea carries over to any system with a live vehicle feed, but three things here are specific
to Boston and would need rewriting:

1. **The map** (`tools/map/layout.py`, `water.py`, `params.py`): every line is described leg by
   leg. This is the bulk of the work.
2. **The data source** (`firmware/app.py`, the `got_...` functions and the request addresses in
   `setup_sources()`): they read the MBTA's V3 API format.
3. **Lines and routes** (`ROUTE_LINE` and `LINE_COLORS` in `firmware/leds.py`, `ROUTES` in
   `sim/directions.py` and `tools/match_stations.py`).

The lighting rules, the sign, the ticker, the wiring planner, the tile generator and the simulator
do not care which city it is.
