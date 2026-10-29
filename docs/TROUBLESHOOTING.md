# Troubleshooting

Every problem here happened during this build. Check the simple things first: power, cables, and
whether the board is running (its serial console at 115200 baud says what it is doing).

## The sign

| What you see | Why | What to do |
|---|---|---|
| The sign flickers red, or shows garbage, over part or all of the panel | The panel isn't getting its own 5 V. The Matrix Portal can't power it; the panel picks up a little through the data pins, and red LEDs light first on too little voltage. | Plug in the panel's 4-pin power cable and check it at the lever nuts. |
| The sign is upside down | The panel is mounted the other way round. | Set `sign.rotation: 180` in `config.yaml` and install the firmware again. |
| The sign stops after `LOADING...`, or never starts | A library is missing from `/lib`. The console says which: `ImportError: no module named 'adafruit_httpserver'`. | Copy that library from the CircuitPython bundle that matches your CircuitPython version. |
| `NO DATA` on the bottom row | Three requests in a row failed. | Check the Wi-Fi and the MBTA key in `settings.toml`. It keeps trying, waiting longer each time. |
| The sign shows `NO API KEY` | `settings.toml` has no `MBTA_API_KEY`. | `python tools/build_firmware.py --deploy D: --secrets` writes it from `.env`. |

## The map's lights

| What you see | Why | What to do |
|---|---|---|
| A whole line lights in the wrong places, or SKIP pixels light up | A chain is plugged into a different Sparkle Motion output than the plan says. | Light each output in its own color from WLED to see which chain is where. Plug the chains into the right outputs, or change the `output` column of `data/wiring_plan.csv` to match and run `python tools/wiring_plan.py`, then install the firmware. |
| From some point along a chain, every light is one station off | A pixel went into the wrong hole (or one meant for a cup went into a hole), so every pixel after it is shifted. | Find the first wrong one with the pixel placer (`data/pixel_placer.html`) and move the pixels, or edit `data/wiring_plan.csv` to say what you built. Tape on every tenth pixel prevents it. |
| Nothing lights at all | WLED isn't getting frames: its address in `config.yaml` is wrong, or WLED's realtime override is on. | Check `hardware.wled_ip` and that WLED's info shows "live" from the Matrix Portal's address. Turn realtime override off. |
| Orange and red trains look alike | At WLED brightness 15/255 there is little green left in the orange; gamma correction removes the rest. | Turn WLED's gamma correction off (both switches), and give `map.colors.OL` more green (#FF6000 to #FF7800). Judge it through the print. |
| The last pixels of a chain are dim or pinkish | Voltage drop along the thin wire. | Feed 5 V and ground to the far end of that chain (step 9). |
| A train someone is riding doesn't turn purple | The message didn't make sense to the board, or it was sent too early. | Spell the stations as the map does (capitals and punctuation don't matter). Send it on getting on, not while waiting. Check `AIO_USERNAME` and `AIO_KEY` in `settings.toml`. |

## The computer and the boards

| What you see | Why | What to do |
|---|---|---|
| The laptop doesn't see the board at all | A charge-only USB cable. | Use a cable that carries data. Press reset once if `CIRCUITPY` still doesn't appear. |
| The phone remote's page stopped loading | The router gave the board a new address. | Reserve an address for the Matrix Portal, and one for the Sparkle Motion, in the router. The board shows its address at start-up. |
| `curl` to the remote's `/api/...` answers 403 | Every `api/` call needs the header `X-Remote: 1` (so other websites can't drive it). | Add the header. |
| Print jobs sit at 0 bytes and never print | The printer was added through Windows' network discovery, which stalls. | Add it again by its IP address, as a standard TCP/IP port. |

## Building

| What you see | Why | What to do |
|---|---|---|
| A printed guide doesn't line up | It printed scaled ("Fit to page"). | Print at 100% / Actual size and measure the 100 mm bar or the 50 mm grid before using it. |
| Bubbles or ripples in the print after gluing | Solvent trapped under the plastic film, or patches with too little adhesive. | Wait a day. Prick bubbles at their edge with a pin and press the air out with a fingertip. **No heat of any kind**: a hair dryer on low warped this build's polypropylene print beyond saving. Next time, order the print adhesive-backed, or let the spray adhesive dry longer before the two sides meet (Mounting the print, in the build guide). |
| The bezel won't stay on | Most glues, hot glue included, barely hold polypropylene; hot glue can also pucker it. | A light mist of Hi-Strength 90 on both, or 3M 300LSE tape. |
| The hardware store's screws won't go into the sign | They are inch sizes (6-32 looks close). | M3-0.5 metric, 6 or 8 mm long. |
| The window was cut a little too big | It happens with a jigsaw. | Nothing: the print's window is cut to size, and the bezel covers the edge. Square the sign to the print's opening when gluing the brackets. |
