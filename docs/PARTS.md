# Parts and equipment

Everything this build used, with the sizes that matter. Where a number was measured on the real
parts, it says so; where it came from a maker's drawing, it says that. Batches of LED panels and
artist's panels vary, so measure yours before printing or cutting anything.

The printed parts are listed separately, in [PRINTED_PARTS.md](PRINTED_PARTS.md).

## The panel and the print

| Part | Qty | Sizes that matter |
|---|---|---|
| Cradled wood artist's panel, 24 x 24 in | 1 | Measured: 609.6 mm square, 41.3 mm (1 5/8 in) deep, frame walls 20 mm wide, so the opening behind the face is 569.6 mm. The pixels stand about 40 mm out of the back of the face, which is the panel's whole depth. |
| The print, 24 x 24 in, matte polypropylene | 1 | From a print shop, as a 300 dpi CMYK JPG at 100% (about $40). Polypropylene stays flat where paper waves with humidity. Order it adhesive-backed if the shop offers it: there is then no spray adhesive, which is what left bubbles the first time. |

## Electronics

| Part | Qty | Sizes that matter |
|---|---|---|
| 64 x 32 RGB LED matrix, 5 mm pitch (Adafruit 2277) | 1 | The sign. Adafruit's drawing says 319.7 x 159.7 mm with a 13 mm frame; the one in this build measured 317.5 x 158.75 mm (`sign.width` and `sign.height` in `build.yaml`) and 15 mm thick at the edge. Measure yours. Six M3 threaded inserts on the back, 7.85 mm in from the edges: one near each corner and one in the middle of each long side, 152 mm apart along the long sides and 144 mm across. Comes with a power cable and a short ribbon cable, but no screws since 2020. Up to 4 A at 5 V with every LED on. |
| Adafruit Matrix Portal S3 | 1 | Runs the display (CircuitPython 10). Needs `adafruit_requests`, `adafruit_connection_manager`, `adafruit_ntp` and `adafruit_httpserver` in `/lib`. |
| Ribbon cable, 16-pin (2 x 8), 2.54 mm, IDC, male to female, 6 to 8 in | 1 | Joins the Matrix Portal (on its cradle) to the sign's input socket. The panel's own ribbon is female at both ends, like the Matrix Portal's socket, so it doesn't fit. |
| Adafruit Sparkle Motion (the full-size board) | 1 | Drives the map's lights with WLED. Three outputs used, 100 LEDs each. |
| WS2811 12 mm bullet pixel strings, 5 V, 50 per string | 6 | 264 lights and 5 SKIP pixels, with 31 left over. 80 mm of wire between pixels (ALITOVE WS2811-5V, 50 pixels on 4 m); the wiring plan allows 72 mm in a straight line. Each string has a 3-pin plug at each end; most also have a spare power pair at the ends. |

## Power

| Part | Qty | Sizes that matter |
|---|---|---|
| 5 V 10 A power supply with a 5.5 x 2.1 mm barrel plug | 1 | In normal use the whole display draws 1 to 2 A. |
| Barrel jack (female) to screw terminals | 1 | Where the supply plugs in. |
| Barrel plug (male) to screw terminals | 1 | Feeds the Sparkle Motion. A pigtail works too. |
| USB-C plug to screw terminals | 1 | Feeds the Matrix Portal. |
| 5-port lever nuts | 2 to 4 | One for 5 V and one for ground; two more if the far ends of the light chains need their own feed. |
| Wire, 16 AWG, red and black | about 1 m each | From the supply to the lever nuts. |
| Wire, 20 AWG, red and black | about 2 m each | From the lever nuts to each part. |

## Fixings and glue

| Part | Qty | Used for |
|---|---|---|
| M3-0.5 x 8 mm pan-head machine screws | 6 | Hold the sign's brackets to its inserts. Buy M3 x 6 as well, in case the 8 mm ones bottom out. Not 6-32: it looks close but won't thread. |
| M3 flat washers | 6 | Under the screw heads, over the brackets' slots. |
| E6000 (or clear silicone) | 1 tube | The tiles, and the sign brackets' bases, to the wood. Wood glue does not hold PLA; hot glue only as a temporary hold. |
| 3M Hi-Strength 90 spray adhesive | 1 can | The print to the wood, and the bezel to the print. Most glues barely hold polypropylene. |
| Black PLA | about 750 g | The tiles (about 600 g) and the sign parts and feet (about 120 g). Black stops light leaking sideways. |
| Small zip ties | a handful | The boards on their tray and cradle. |
| Isopropyl alcohol, 320-grit sandpaper, masking tape | | Preparing the back of the print; the tape hinge when gluing it. |

## Equipment

| Tool | Used for |
|---|---|
| 3D printer with a 400 x 400 mm bed (an Anycubic Kobra Max here) | The two big tiles need the whole bed; the sign parts plate is 322 x 257 mm. PrusaSlicer, with the Kobra Max profiles. |
| Drill, with 1/8 in, 1/4 in and 3/8 in bits | 1/8 in pilot holes from the back, 1/4 in finished holes from the front, 3/8 in starter holes in the corners of the sign window. |
| Jigsaw with a fine wood blade | The sign window, cut from the front. |
| Utility knife with fresh blades, steel ruler, cutting mat | The print's window, after the print is glued down. |
| Home printer that prints at exactly 100% | The drill guide pages, the jigsaw template and the test page. |
| Multimeter | Polarity and short checks before power goes on; the ribbon cable's ground pins. |
| Wire stripper or flush cutters; small flat screwdriver; Phillips #1 | Stripping wire for the lever nuts, the screw terminals, the M3 screws. |
| Ruler or tape measure, and calipers if you have them | Checking the panel, the sign and the printed guides before cutting. |
| Rubber roller (brayer), squeegee or a clean cloth | Laying the print down. |
| A computer with a USB-C data cable | Installing the firmware and running the simulator. Charge-only cables don't show the board. |
