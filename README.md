# MBTA LED map

In 2013, I saw a project an MIT student built that used individually programmable LEDs to make a live map of the MBTA. I have had the project in the back of my mind ever since. In the time since then, many people have created really cool projects using live subway data. This project builds on what they did, combining live updating train lines with an LED display that I am really excited to add more functionality to. More on that below.

This display is big, a 24 x 24 inch wood panel that you can hang from the wall if you use a French cleat, or put on a table and use the 3d printed feet included in the design. Most of the space on the display is dedicated to tracking the Red, Orange, Blue, and Green lines.
Behind each of the MBTA's 132 stations are two small lights, one for each direction of travel. A train standing at a station lights that station in its line's color.  In the lower right corner a 64 x 32 LED sign counts down to the next bus and the next train at your own stops, and a ticker underneath rotates through the time, the weather, Boston sports scores and MBTA alerts. 

You don't need any hardware to see the sign in action, as this repository includes a simulator that runs from the same live data you can see in your web browser.

## What is in the repository

| Folder | What it is |
|---|---|
| `firmware/` | Everything that runs on the display's controller (an Adafruit Matrix Portal S3, in CircuitPython). |
| `server.py`, `sim/`, `static/` | The simulator.|
| `tools/` | Scripts you run on your computer: the map generator, the wiring planner, the firmware installer. |
| `data/` | The map itself: the print (SVG), where every station and light is, and the order the lights are wired in. |
| `hardware/` | Scripts that make the 3D-printed parts. |
| `tests/` | Automated tests. |
| `docs/` | The guides below. |

I used very specific parts and tools to make this thing, so if you build this and use other materials, the 3d printed tiles, for example, might not fit quite right. I tried to put every measurement that is dependent on specific hardware into two files:  `config.yaml` (your copy of
`config.example.yaml`) for what the display shows, and `build.yaml` for the measured sizes of your
panel, sign, pixels and printer. `firmware/`, `tools/`, `data/` and `hardware/` each have a README.

## Guides

1. **[Order of work](docs/CHECKLIST.md)**: the whole build as a checklist.
2. **[Measure first](docs/MEASURE.md)**: what to measure on your parts (`build.yaml`).
3. **[Parts and equipment](docs/PARTS.md)**: everything to buy and the tools you will need.
4. **[Printed parts](docs/PRINTED_PARTS.md)**: every 3D-printed part.
5. **[Build guide](docs/BUILD.md)**: Step by step guide. 
6. **[How it works](docs/HOW_IT_WORKS.md)**: how the code is organized.
7. **[Make it yours](docs/MAKE_IT_YOURS.md)**: your settings, your parts, and untested, switching from Boston's MBTA to another city.
8. **[Testing](docs/TESTING.md)**: the automated tests and the checks to do by hand.
9. **[Troubleshooting](docs/TROUBLESHOOTING.md)**: what went wrong during this build, and the fix for each.

Every page to print or open while building comes from one command: `python tools/printables.py`.


## License

Code: MIT (`LICENSE`). Map artwork, 3D-printable designs and photos: CC BY-NC 4.0
(`LICENSE-DESIGN.md`). The T logo is the MBTA's trademark; it may be used to identify MBTA service, as
it is on the map, but not as your own branding or commercially (see `LICENSE-DESIGN.md`). This project is
not affiliated with, or endorsed by, the MBTA or MassDOT. They do know about it though! I got a very nice reply from the API dev team when I reached out to ask if I could use the T symbol in a hobbyist project like this one.

Data: [MBTA V3 API](https://api-v3.mbta.com) (trains, predictions, alerts),
[Open-Meteo](https://open-meteo.com) (weather), and ESPN's scoreboard pages (scores). ESPN doesn't publish
those pages for other people's projects, so they are unofficial, may change without notice, and are used here
for one personal, non-commercial display. Turn them off with `sox`, `bruins` and `patriots` under `ticker:` in
`config.yaml`.

## How it was made

Friends, so much iteration and so many false starts. I designed the display and built the hardware, but I relied heavily on Claude Code for the code. Claude was especially helpful for creating the 3d printed pieces and for getting the distances between stations large enough to look good when lit, but still fit on a 24x24 wooden panel. Claude also helped write the instruction markdown files.
