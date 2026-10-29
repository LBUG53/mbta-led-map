# Order of work

The order matters: some steps can't be undone, and some get in the way of others. Tick them off in
this order; each links to the details.

## Before buying or making anything

- [ ] Run the simulator and choose your stops ([BUILD, step 1](BUILD.md#1-run-the-simulator); [MAKE_IT_YOURS](MAKE_IT_YOURS.md)).
- [ ] Buy the parts ([PARTS](PARTS.md)).
- [ ] **Measure the panel, the sign and the pixels, and put the numbers in `build.yaml`** ([MEASURE](MEASURE.md)).
- [ ] Make every page and part from those numbers: `python tools/printables.py`, then the scripts in `hardware/` ([PRINTED_PARTS](PRINTED_PARTS.md)).
- [ ] Print the test page at 100% and measure its 100 mm bar. If it's wrong, fix the printer settings before printing anything else.

## The electronics, on the bench

- [ ] Set up the sign and the Matrix Portal; see the departures on the sign ([step 3](BUILD.md#3-set-up-the-sign)).
- [ ] Install WLED on the Sparkle Motion and set its outputs ([step 4](BUILD.md#4-set-up-the-light-controller)). Try one string.
- [ ] Order the print ([step 5](BUILD.md#5-print-the-map)). Start the tiles printing ([step 6](BUILD.md#6-print-the-plastic-parts)); they take days.

## The wood

- [ ] **Drill** all the holes through the drill guide: pilot holes from the back, finished holes from the front ([step 7](BUILD.md#7-drill-the-panel-and-mount-the-tiles)).
- [ ] **Glue the tiles** over the holes, locating collars over the reference holes.
- [ ] **Cut the sign window** through the wood with the template, *before* the print goes on.

## The front

- [ ] **Glue the print on** with the pixels out of their holes, one half at a time from a tape hinge ([Mounting the print](BUILD.md#mounting-the-print)).
- [ ] Wait a day; fix any bubbles with a pin, never with heat.
- [ ] **Cut the print's window** with a knife, *after* gluing.
- [ ] **Glue the bezel** over the window's edge.

## The back

- [ ] **Place the pixels**, one output at a time, with the pixel placer and tape on every tenth pixel ([step 8](BUILD.md#8-wire-the-lights)).
- [ ] **Wire the power** with the power guide; do every meter check before switching on ([step 9](BUILD.md#9-power)).
- [ ] Switch on. Light the pixels one at a time from WLED and check each against the wiring sheet. Fix the plan, not the wiring, if they differ.
- [ ] **Fit the sign**: brackets screwed on loosely with their bases under them, sign squared to the bezel's opening with the alignment rings, then the bases glued ([Holding the sign](BUILD.md#holding-the-sign)).
- [ ] Glue down the boards' tray and cradle, the lever nuts' anchors, the wire clips ([step 10](BUILD.md#10-install-the-electronics-and-finish)).

## Finishing

- [ ] Reserve both boards' addresses in your router.
- [ ] Stand it in its feet, or hang it.
- [ ] The phone remote ([step 11](BUILD.md#11-the-phone-remote)) and rides ([step 12](BUILD.md#12-rides-im-on-the-train)).

If something looks wrong, [TROUBLESHOOTING](TROUBLESHOOTING.md) has every problem this build ran into.
