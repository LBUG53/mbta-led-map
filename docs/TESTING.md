# Testing

## Automated tests

The same tests run on every push (`.github/workflows/tests.yml`), on Windows and, informally, Linux.

```bash
python -m unittest discover -s tests -v
```

They need no hardware and no network, and take about 20 seconds. The MBTA lookup tables they use (which
platform belongs to which station, each route's stops) are a snapshot in `tests/fixtures/lookup/`, so
the results are the same on any machine and don't depend on `cache/`. Five tests are skipped by
default: four call the real MBTA, weather or score feeds (below), and one checks your own `.env`, so it
is skipped if you have none.

| File | Covers |
|---|---|
| `tests/test_simulator.py` | The data files (132 stations, 264 lights, every light wired once); direction of travel on every line and branch; the lighting rules; closures; the sign's countdown and alert rules; the simulator's answers. |
| `tests/test_firmware.py` | The board's logic run on the PC against a fake network: what is fetched and when, the ticker, night mode, the sign's pictures, the packet sent to WLED, and that the board's files avoid what CircuitPython lacks. |
| `tests/test_remote.py` | The phone remote: every mode and command, the timer, messages, brightness, find-a-station, costume mode, music mode, the alignment rings and the Korok. |
| `tests/test_map.py` | The map generator: every physical rule, station order, labels, both prints. |
| `tests/test_backoff.py` | What the board does when the network or WLED stops answering: waiting longer between tries, telling a failed request from a bug in reading an answer, the queue of settings for WLED. |
| `tests/test_rides.py` | Ride messages: reading them, finding the trip, following it, the purple light and the ticker text. |
| `tests/test_printables.py` | Every page to print can be made, agrees with the wiring plan and the sizes in `build.yaml`, and is written with Unix line endings. |
| `tests/test_drill_guide.py` | The drilling guide: a cross at every one of the 264 lights, in the mirrored place; the sheet is the size of the opening; the 50 mm grid is 50 mm; a light too near the sheet's edge stops it; the pages overlap enough to join. |
| `tests/test_tiles.py` | The printed tiles (needs `manifold3d`): each collar over its light, the pixel numbers on the tiles agree with the wiring plan, no two tiles collide, each fits the printer. |
| `tests/test_board_files.py` | What goes on the board: the firmware files use only what CircuitPython has, the board serves no files of its own, each API key goes only to its own service. |

Two tests look for the MBTA API key: one checks that `.env` is in `.gitignore`, the other reads your
key and fails if it finds it in any other file in the repository.

### Tests that use the network

Off by default. They call the real MBTA API and the real weather and score feeds.

On Windows (PowerShell):

```
$env:RUN_NETWORK_TESTS = "1"
```

On macOS or Linux:

```
export RUN_NETWORK_TESTS=1
```

then run the tests as above.

### The 3D-printed parts

```bash
python hardware/make_tile.py check
```

builds all three tiles and reports whether any two overlap. It should say `overlap 0.00 mm3` three
times.

## Checks by hand

### In the simulator (http://127.0.0.1:8000)

| Do | Expect |
|---|---|
| Load the page | The print, a few small glows beside the lines (only trains standing at a station), the sign in its window, a status line with the number of vehicles. |
| Data > Sample: moving trains | Trains step along every line both ways; glows on opposite sides of a line move in opposite directions. |
| Data > Sample: every light, train stopped | All 264 lights on, in pairs astride every station. |
| Data > Sample: typical moment | A handful of trains; at Harvard and JFK both lights at once. |
| Night mode | The map half as bright and still; the sign dimmer, showing only time and weather. |
| View > Show the holes and the wiring order | Three colored wires, each going out along one side of its lines and back along the other. |
| Hover a light | Its station, which direction it shows, its output and pixel number. |
| Open `/remote` | The remote page; switching mode changes the sign in the other tab. |
| Modes panel: Game night, Bruins, Off, back to Transit | The sign changes with each; Off darkens the sign and the map. |
| Modes panel: Music | The sign says MUSIC and the effect's name; the simulator's map goes dark (WLED draws it on the real board). |
| Costume panel: Alignment rings on the sign | The sign shows a white outer ring with a yellow ring inside it; off, it goes back to what it showed. |
| Phone remote, Korok > Yahaha! | A Korok rises from the bottom of the sign and says YAHAHA!, then YOU FOUND ME!, then the sign goes back. |
| Costume panel, with a sample scene: Costume mode | Sample trains step along every line; the sign shows sample departures, then HAPPY HALLOWEEN. |
| Rides panel, a sample scene: Orange, Oak Grove to Forest Hills, Start ride | Within about 20 seconds the list says "ALEX on Orange, arriving ...", the button reads Change train, one Orange Line light is purple and moves down the line a stop every 20 seconds or so, and the ticker shows ALEX, then OL and a time. |
| Rides panel: choose Red, Harvard to Alewife, Change train | The Orange light goes out and a Red one turns purple; still one rider in the list. |
| Rides panel: change the name to Sam, Blue, Bowdoin to Wonderland, Start ride | Two riders listed, two purple lights, two ticker items. End on each clears it. |
| Rides panel, live data, with trains running | The same, with the real train: the purple light is where that train is. |
| The phone remote's page (`/remote` in the simulator), Rides section | Starts, changes and ends rides on the live board the same way. |

### On the board

| Check | Expect |
|---|---|
| Serial port, 115200 baud | A status line a minute: `failures 0`, every source's `ok` count rising, free memory well above 1 MB. |
| The sign | No flicker. A row with `walk_minutes` shows only departures you could catch. |
| 11 pm | The sign dims and the ticker shows only time and weather. |

### On the finished display

| Check | Expect |
|---|---|
| Pixel order | Lighting pixels one at a time in WLED matches `data/wiring_plan.csv`. If not, edit the file to match, run `tools/wiring_plan.py`, reinstall. |
| Direction | A real southbound Red Line train lights the light on the west side of the line. |
| Light bleed | A lit light does not show in its partner's hole 14 mm away. |
| Lost link | Unplug the Matrix Portal: the map goes dark after 20 seconds. |
