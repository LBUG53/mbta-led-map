# firmware/

Everything that runs on the Adafruit Matrix Portal S3, in CircuitPython. This folder is exactly
what goes on the board (plus this README and the example settings, which the installer leaves
behind).

| File | What it does |
|---|---|
| `code.py` | The file CircuitPython starts. Hardware only: Wi-Fi, the clock, the LED panel, sending to WLED, a tiny web server for the phone remote, and the main loop. |
| `app.py` | The conductor: what to fetch and when, the ticker, night mode, the sign's frames, the packet for WLED. Start reading here. |
| `leds.py` | Trains and alerts in, a color for every pixel out. |
| `sign.py` | The sign: fonts, drawing, countdown rules, which alerts are worth showing, the palette. |
| `feeds.py` | Weather and scores: what to ask, how to read the answers, the short texts for the ticker. Boston's clock and daylight saving. |
| `remote.py` | The phone remote's logic: modes, life totals, timer, message, brightness, find-a-station, costume mode's sample trains. |
| `remote.html` | The remote's page, served by the board. |
| `data.json` | **Made by the installer; not in git.** Your settings and the map, packed for the board. |
| `settings.toml.example` | What `settings.toml` on the board looks like (Wi-Fi and the MBTA key). The installer writes the real one with `--secrets`. Never commit a filled-in copy. |

## Installing

```bash
python tools/build_firmware.py --deploy D:
```

with your board's `CIRCUITPY` drive in place of `D:`. See step 3 of the [build guide](../docs/BUILD.md).

The board also needs three libraries in its `lib` folder, from the CircuitPython bundle:
`adafruit_requests`, `adafruit_connection_manager`, `adafruit_ntp`, `adafruit_httpserver`.

## Rules for changing these files

Everything except `code.py` also runs on a PC, inside the simulator and the tests, so a change can
be tried without touching the board. To keep that working, and to fit the board's small memory:

- Plain lists, dicts, numbers and strings. No classes, f-strings, type hints, `os` or `time`.
- Never fetch anything except through the `fetch(url)` function `app.py` is handed, and only from
  `fetch_one()`: the board freezes while it waits, so requests happen one at a time while the
  ticker holds still.
- Functions take the time as arguments (`now_ms`, `epoch`, `t`) instead of reading a clock. That is
  what lets the tests run hours of display time in milliseconds.
- All state is in one dict, `st`. `app.setup()` builds it and says what each part is.

Run the tests after any change: `python -m unittest discover -s tests`.

## Not proven on the board yet

The web server for the phone remote (the `serve()` function in `code.py`) has only run in the
simulator so far.
