# WLED settings and wiring notes

Made by `tools/wiring_plan.py` from `data/wiring_plan.csv`; run it again after editing the CSV.

## WLED: Config > LED Preferences

| Output | Sparkle Motion GPIO | Start index | LED count | Strings of 50 | Lights | SKIP pixels | Spare at the end |
|---|---|---|---|---|---|---|---|
| 1 | 21 | 0 | 100 | 2 | 94 | 0 | 6 |
| 2 | 22 | 100 | 100 | 2 | 86 | 1 | 13 |
| 3 | 19 | 200 | 100 | 2 | 84 | 4 | 12 |

Total: 300 LEDs on 6 strings, 264 lights. Type WS281x, color order to suit the strings (test with one).
The board sends one DDP packet of 300 x 3 bytes covering all three outputs in this order.

## Wire runs

Each wire between two pixels is 80 mm; the plan allows 72 mm in a straight line (8 mm slack).

- Output 1: 94 pixels; longest wire run 63.7 mm (pixel 56 to 57).
- Output 2: 87 pixels; longest wire run 56.0 mm (pixel 85 to 86).
- Output 3: 88 pixels; longest wire run 53.5 mm (pixel 22 to 23).

## Where each chain leaves a line

The generated plan follows the lines; these are the hops it makes from one line to another.

- Output 1: BL Bowdoin to RL Charles/MGH (stations 36 mm apart)
- Output 2: OL Chinatown to GL Park Street (stations 38 mm apart)
- Output 2: OL Forest Hills to GL Brigham Circle (stations 67 mm apart)

## SKIP pixels (always off; tuck them behind the panel)

| Output | Pixel | Between | Straight-line jump |
|---|---|---|---|
| 2 | 63 | OL Green St A and GL Brigham Circle A | 87 mm |
| 3 | 27 | RL Downtown Crossing B and RL Park Street B | 84 mm |
| 3 | 32 | BL Gov't Center A and BL State A | 84 mm |
| 3 | 53 | BL State B and BL Gov't Center B | 84 mm |
| 3 | 70 | RL Park Street A and RL Downtown Crossing A | 84 mm |
