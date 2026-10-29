# License for the designs

The source code in this repository is under the MIT License (see `LICENSE`).

The following are **not** code and are licensed under
**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**:

- the map artwork: `data/print_no_outline.svg`, `data/print_with_outline.svg` and any print made from them;
- the 3D-printable designs: every STL file made by the scripts in `hardware/`, and any part printed from one;
- photographs of the finished display.

Copyright (c) 2026 Lucian Bessmer.

In short: you may copy, adapt and share these for non-commercial purposes, as long as you give credit
("Lucian Bessmer, 2026", with a link to this repository) and say what you changed. You may not sell them
or things made from them. The full terms are at https://creativecommons.org/licenses/by-nc/4.0/legalcode

The scripts in `hardware/` are code, so they are MIT: anyone may run, change and share them. The STL
files they write, and the parts printed from those, are designs, so they are CC BY-NC like the rest of
this list.

## The T logo

The T logo in the upper left of the print is the MBTA's trademark and is not covered by either license
above. The MBTA's guidance, which their developer team confirmed to me in October 2026, is that the T may
be used and redistributed freely to identify the MBTA's service, as it is here, where it marks the agency
on a map of its lines and stops. There are two conditions. The logo must not be so prominent that the work
could be taken for an official MBTA application or an endorsement by the MBTA; a credit and a statement
like the one below help to avoid that. And using the T as the main branding of something, or in anything
commercial, needs a license from the MBTA, which you can ask their developer team about.

So you may keep the T when you print or share this map, on those terms. To leave it off, make `title()` in
`tools/map/furniture.py` return nothing.

## Not affiliated with the MBTA

This is a personal project. It is not affiliated with, endorsed by or sponsored by the Massachusetts Bay
Transportation Authority or MassDOT. Transit data comes from the MBTA's public V3 API and is subject to
the MassDOT Developers License Agreement. The map is an original schematic, not a copy of the official map.
