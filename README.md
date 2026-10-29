# MBTA LED map

A wall display of Boston's subway that shows where the trains are, live.

A 24 x 24 inch wood panel carries a printed map of the Red, Orange, Blue, Green and Mattapan lines.
Behind each of its 132 stations are two small lights, one for each direction of travel. A train
standing at a station lights that station in its line's color; trains between stations show nothing,
so the lit stations are where trains are right now. In the lower right corner a 64 x 32 LED sign counts down to the next bus and the next
train at your own stops, and a ticker underneath rotates through the time, the weather, Boston
sports scores and MBTA alerts. Tell it which train you are on, from your phone, and that train turns
purple on the map while the sign shows when you get off.

You don't need any hardware to try it. A simulator in this repository draws the whole display in a
web browser from the same live data, running the very code that runs on the real thing.

## Try it in five minutes

You need Python 3 (it is tested with 3.12).

```bash
python -m venv .venv
```

Activate it. On Windows:

```bash
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
```

```bash
python server.py
```

Open http://127.0.0.1:8000. On Windows you can double-click `Start Simulator.bat` instead of all of
the above.

The first start needs the internet: it fetches a few small lookup tables from the MBTA (kept in `cache/`),
and says so if it can't. After that the sample scenes work offline.

It works without an MBTA API key, at a lower request limit. For your own build, get a free key at
https://api-v3.mbta.com and put it in a file named `.env` in this folder:

```
MBTA_API_KEY=your-key-here
```

`.env` is in `.gitignore`. The key is read in one place (`sim/mbta_api.py`), sent only to the MBTA,
and never printed or written anywhere else.

## What is in here

| Folder | What it is |
|---|---|
| `firmware/` | Everything that runs on the display's controller (an Adafruit Matrix Portal S3, in CircuitPython). |
| `server.py`, `sim/`, `static/` | The simulator. It imports the firmware's own files, so the two can't drift apart. |
| `tools/` | Scripts you run on your computer: the map generator, the wiring planner, the firmware installer. |
| `data/` | The map itself: the print (SVG), where every station and light is, and the order the lights are wired in. |
| `hardware/` | Scripts that make the 3D-printed parts. |
| `tests/` | Automated tests. They need no hardware and no network. |
| `docs/` | The guides below. |

Two files at the top hold everything you would change: `config.yaml` (your copy of
`config.example.yaml`) for what the display shows, and `build.yaml` for the measured sizes of your
panel, sign, pixels and printer. `firmware/`, `tools/`, `data/` and `hardware/` each have a README.

## Guides

1. **[Order of work](docs/CHECKLIST.md)**: the whole build as a checklist, in the order that works.
2. **[Measure first](docs/MEASURE.md)**: what to measure on your parts, and where the numbers go (`build.yaml`).
3. **[Parts and equipment](docs/PARTS.md)**: everything to buy and the tools, with the sizes that matter.
4. **[Printed parts](docs/PRINTED_PARTS.md)**: every 3D-printed part, its file, and how it was printed.
5. **[Build guide](docs/BUILD.md)**: every step, in detail.
6. **[How it works](docs/HOW_IT_WORKS.md)**: how the code is organised and the rules the display follows.
7. **[Make it yours](docs/MAKE_IT_YOURS.md)**: your settings, your parts, a little code, another city.
8. **[Testing](docs/TESTING.md)**: the automated tests and the checks to do by hand.
9. **[Troubleshooting](docs/TROUBLESHOOTING.md)**: what went wrong during this build, and the fix for each.

Every page to print or open while building comes from one command: `python tools/printables.py`.

## Where the project stands

This is a build in progress, published as it goes. As of October 2026:

- **Working:** the simulator, with a switch for every mode; the map generator; the wiring planner;
  the sign and the phone remote on the real board; the map's lights, through the print.
- **Written but not yet run on the real board:** rides (tell the display which train you are on) and the
  phone remote's Music mode and alignment rings. Rides work in the simulator, on live data and on the
  sample scenes, so you can try one without any hardware. Music mode needs the board and WLED's microphone.
- **In progress:** the print is on and the sign window cut; the pixels are being placed again after a
  first attempt ended up one hole off in places; the sign's brackets, bezel and stand feet are
  printing.

The build guide marks every step that has not been done for real yet.

## License

Code: MIT (`LICENSE`). Map artwork, 3D-printable designs and photos: CC BY-NC 4.0
(`LICENSE-DESIGN.md`). The T logo is the MBTA's trademark; it may be used to identify MBTA service, as
it is on the map, but not as your own branding or commercially (see `LICENSE-DESIGN.md`). This project is
not affiliated with, or endorsed by, the MBTA or MassDOT.

Data: [MBTA V3 API](https://api-v3.mbta.com) (trains, predictions, alerts),
[Open-Meteo](https://open-meteo.com) (weather), and ESPN's scoreboard pages (scores). ESPN doesn't publish
those pages for other people's projects, so they are unofficial, may change without notice, and are used here
for one personal, non-commercial display. Turn them off with `sox`, `bruins` and `patriots` under `ticker:` in
`config.yaml`.

## How it was made

I designed the display and built the hardware. The code was written with an AI coding assistant (Claude
Code), from my design and under my direction; the tests and the simulator are how I checked it.
