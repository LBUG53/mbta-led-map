# How it works

## The two controllers

```
                      Wi-Fi                            Wi-Fi
  MBTA, weather,  ───────────>  Matrix Portal S3  ───────────>  Sparkle Motion (WLED)
  scores                        (firmware/)        colors for    │
                                │                  300 pixels    └─> 264 lights behind the map
                                └─> the 64 x 32 sign
```

The **Matrix Portal S3** does all the thinking. It asks the MBTA where the trains are, works out
which lights should be on, draws the sign, and about once a second sends the Sparkle Motion a list
of 300 colors (one network packet, in a format called DDP).

The **Sparkle Motion** runs WLED, unmodified. It only does what it is told: show these colors.
If the packets stop for 20 seconds it goes dark.

## One program, two places

The display's behavior is written once, in `firmware/`, and runs in two places:

- on the board, started by `firmware/code.py`, which owns the hardware (Wi-Fi, clock, LED panel);
- on your computer, started by `server.py`, which stands in for the hardware and shows the result
  in a browser.

Both hand the same code a function called `fetch(url)` and call the same three functions in a loop:
`tick` (move the ticker on, maybe make one request), `sign_frame` (the sign's picture), and
`ddp_packet` / `map_chains` (the map's colors). So what you see in the simulator is what the board
will do, bugs included.

That is also why the firmware's files are written in very plain Python: lists, dicts, numbers and
strings, no classes, no f-strings, no `os` or `time`. CircuitPython on this board has about 2 MB of
memory and lacks parts of full Python. Keep to that style in `firmware/app.py`, `feeds.py`,
`rides.py`, `remote.py`, `leds.py` and `sign.py`; the tests check for it.

## The files

| File | Runs on | What it does |
|---|---|---|
| `firmware/code.py` | board | Hardware only: Wi-Fi, the clock, the LED panel, sending to WLED, a tiny web server, the main loop. |
| `firmware/app.py` | both | The conductor: what to fetch and when, the ticker, night mode, the sign's frames, the packet for WLED. |
| `firmware/leds.py` | both | Trains and alerts in, a color for every pixel out. |
| `firmware/sign.py` | both | The sign's fonts and drawing, countdown rules, which alerts are worth showing. |
| `firmware/feeds.py` | both | Weather and scores: the addresses to ask, how to read the answers, the short texts. Boston's clock. |
| `firmware/rides.py` | both | Rides: a message from a phone says which train or bus someone is on; finds that trip and follows it. |
| `firmware/remote.py`, `remote.html` | both | The phone remote: the other modes and the extras. |
| `firmware/data.json` | both | Made by `tools/build_firmware.py`: your settings and the map, in the one format the board reads. |
| `server.py` | PC | The simulator's web server. |
| `sim/` | PC | Reading the config and data files, the MBTA client, sample data for the simulator and tests. |
| `static/` | PC | The simulator's pages. `app.js` draws the lights shining through the paper. |
| `tools/` | PC | The map generator, wiring planner, firmware installer and smaller helpers. |

All of the display's state lives in one dictionary, called `st` throughout `app.py` and `remote.py`.
`app.setup()` builds it and lists what is in it.

## Where the data comes from, and how it flows

```
tools/map/generate.py    ─>  data/print_*.svg, data/stations.csv      where every station and light is
tools/match_stations.py  ─>  data/station_ids.csv                     each station's MBTA ID
tools/wiring_plan.py     ─>  data/wiring_plan.csv                     which pixel is which light
sim/live.py              ─>  cache/                                   lookup tables from the MBTA

config.yaml + data/ + cache/  ─>  tools/build_firmware.py  ─>  firmware/data.json  ─>  board and simulator
```

### Requests

The board can do only one thing at a time: while it waits for an answer from the network, nothing
moves. So it makes **one request at a time, and only while the ticker is holding still**, never
during a slide or a scroll. Each thing it fetches ("source") has an interval; whichever is most
overdue goes next.

| Source | Asked | How often |
|---|---|---|
| predictions | MBTA: departures at the sign's stops, both rows in one request | 25 s (60 s at night) |
| vehicles | MBTA: every train on the map's eight routes, in one request | 25 s (60 s at night) |
| alerts | MBTA: current alerts for the map's and the sign's routes | 2 min |
| weather | Open-Meteo | 30 min |
| each team, "find" | ESPN: which game is yesterday's or today's | 30 min, and just after midnight |
| each team, the game | ESPN: that game's score | 15 min; 1 min while it is on |

The MBTA key is sent only to `api-v3.mbta.com`. A failed request keeps the old data and tries again.

**When a request fails**, the old data stays on show. The source tries again after its usual interval
(at most 30 s), and each further failure in a row doubles the wait, up to 2 minutes, so an outage
isn't hammered; the first success puts it back to normal. One source failing doesn't slow the others. After five failures in a row anywhere, the
board rejoins the Wi-Fi.

**WLED** gets the map's colors in a stream of small UDP packets, which never wait for an answer. The
one thing that does wait is a setting sent over HTTP (the brightness slider), so it waits at most
1.5 seconds. If WLED doesn't take it, the setting stays queued and is tried again after 2 s, 4 s,
8 s... up to a minute apart, so a WLED that is switched off costs the display a short pause once in a
while, not every time round the loop. Moving the slider again tries at once. A newer brightness
replaces an older one that hasn't gone yet.

## The rules the display follows

### From a train to a light (`leds.py`)

1. The train's route says which line it is on (Red, Mattapan, Orange, Blue; Green-B/C/D/E are all
   "Green").
2. The MBTA reports the *platform* a train is at or heading for. A lookup table turns the platform
   into its station.
3. The station has two lights, A and B. The train's direction picks one: a train lights the light
   on its right-hand side.
4. Standing at the station (`STOPPED_AT`): full line color. On its way (`INCOMING_AT`,
   `IN_TRANSIT_TO`) or no train: off. (Trains between stations were once a dimmer glow at the next
   station; with the whole system running, nearly every station was lit, so it was dropped.) A train
   someone is riding is the exception; see Rides.

A transfer station has a separate pair of lights for each line through it.

### Which direction is which (`sim/directions.py`)

The MBTA numbers each route's two directions 0 and 1, and which is which differs from line to line.
Nothing in the code says "direction 0 is southbound". Instead, for every branch, the order of stops
the MBTA gives for direction 0 is compared with the order the branch is drawn in on the map. If they
agree, direction 0 lights light A there; if not, direction 1 does. If the MBTA ever renumbers a
route, deleting `cache/` and reinstalling is all it takes.

### Rides (`rides.py`)

When someone gets on a train or a bus, a message reaches the board, `NAME;ROUTE;FROM;TO` (for example
`ALEX;Orange;Ruggles;Downtown Crossing`): from the phone remote's page (its `ride` command), or from a phone
through an Adafruit IO feed that the board reads every 15 seconds. Starting a ride under a name that is already
riding replaces it. The board asks the MBTA for predictions at FROM and TO and picks the trip that stops at both,
FROM first: the one leaving FROM within two minutes of the message, or, if the message came after
the train left, the one that left last. From then on it follows only that trip: its vehicle lights
purple on the map, over the line color, and the ticker shows the name, then the line and the time it
reaches TO (`ALEX`, then `OL 9:36`). The ride ends when that trip's prediction at TO is gone (it has
arrived), on `NAME;DONE`, or after three hours. A bus is on the sign only; the map has no buses.

On the simulator's sample scenes the same code runs against a made-up timetable (`sim/sample_feeds.py`: a
train every five minutes, seven minutes end to end), and `sim/sample.py` moves a made-up train along the map, so
a ride can be tried without live data.

### The sign (`sign.py`, `app.py`)

Three rows of 9-pixel text. The top two are your stops, each with the next two departures in
minutes ("4, 11"). A row can have a walking time: departures you could no longer catch are left
out. Predictions more than two minutes old are not trusted and the row shows "--".

The bottom row is the ticker. It rotates through: day and time; weather now; today's high and low;
rain, if it is likely; each team that plays today (start time, then the score, then the result until
the next morning); MBTA alerts for your routes, scrolling if they are long. A new alert or a score
jumps the queue.

Alerts are filtered: elevator, escalator and parking notices never show; others show if they are
severe enough or name one of your own stops.

### Night mode

Between 11 pm and 7 am the sign dims and shows only the time, the weather and anyone on their way
home, the map dims by half, and requests slow down.

### Music mode (`remote.py`)

In Music mode the board stops sending trains. It posts a segment layout to WLED instead, one segment
per string, or for the "Lines" effect one per stretch of a line in that line's color, running a
sound-reactive effect from the `music:` list in `config.yaml`. WLED reacts to its own microphone.
Leaving the mode needs no message: WLED goes back to the board's frames as soon as they arrive again.
The simulator has no WLED, so its map goes dark in this mode.

### The wiring order

The lights are not wired in any order the code could guess, so the order is data:
`data/wiring_plan.csv` has one row per pixel. `leds.render()` produces each output's colors in that
order, with black for the unused (SKIP) pixels. If the real wiring ends up different, the file is
edited, not the code.

## The map generator (`tools/map/`)

The print is made by a program, not drawn by hand, so that moving a line or changing the panel
size regenerates everything consistently.

| File | Does |
|---|---|
| `params.py` | Every number: panel size, margins, where each line runs, spacings. |
| `layout.py` | Each line as a path of straight and 45-degree legs, with its stations placed along it. |
| `labels.py`, `overrides.py` | Places a label for each station by rule; `overrides.py` holds the few hand-placed exceptions, each with its reason. |
| `water.py`, `furniture.py` | Rivers and harbor; the branch tags, the caption under the sign and the credit. Colors follow the MBTA's brand guidelines. The T logo is used with the MBTA's permission; labels keep the brand guide's clear space round it. |
| `render.py` | Puts it all into an SVG with named layers. |
| `validate.py` | Checks the physical rules: lights inside the frame, far enough apart to drill, near enough for the wire. |
| `geometry.py`, `font.py` | Distance helpers; text widths read from the font file. |
| `generate.py` | Runs all of the above and writes the outputs. |

The rules `validate.py` checks, each set by a number in `params.py`; `data/validation_report.md`
gives the result of each:

1. Every light between 44 and 566 mm from the edges, inside the frame with room to spare.
2. Two lights per station, 14 mm apart, 7 mm either side of the line and square to it.
3. Lights of different stations at least 13 mm apart, so the holes can be drilled.
4. Stations along a line at least 20 mm apart.
5. No light within 6 mm of the sign panel.
6. Neighboring stations on a line no more than 85 mm apart: the wire between two pixels is about
   90 mm.
7. No station within 14.5 mm of a right-angle turn, so stations on either side of it don't end up
   too close.
8. No label overlaps another label, a line, a light, the sign, the T or the caption, and
   labels stay off the water.
