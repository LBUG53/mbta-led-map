"""Hand-placed exceptions to the layout and label rules, each with its reason.

This is the only place exceptions live. generate.py lists every entry in
data/validation_report.md.

GEOMETRY: {(line, station): (dx_mm, dy_mm, "reason")}  nudges a station
LABELS:   {station: {"side": ..., "text": ..., "reason": "..."}}  (stage 2)
"""

GEOMETRY = {}

LABELS = {
    "Downtown Crossing": {
        "dx": 8.0,
        "text": "Downtown\nCrossing",
        "reason": "above its Red circle like the rest of the Red row, on two lines, slid 8 mm right so it "
                  "clears the interchange bar and the Orange column instead of sitting across them",
    },
    "North Station": {
        "text": "North\nStation",
        "reason": "on two lines: at the transfer stations' larger size one line reaches the Charles",
    },
    "Bowdoin": {
        "dx": -6.0,
        "reason": "slid 6 mm left: centred over its station it ran into Gov't Center's label on the same row",
    },
    "Boston College": {
        "text": "Boston\nCollege",
        "reason": "on two lines, so it keeps the same margin from the paper's edge as the T and the credit",
    },
    "Medford/Tufts": {
        "text": "Medford/\nTufts",
        "reason": "on two lines, as on the MBTA's map: in capitals on one line it reaches the Mystic",
    },
    "Central": {
        "side": "L",
        "reason": "left of the line: on the right it crowded Kendall/MIT, which sits just below",
    },
    "Hawes St": {
        "dx": -3.5,
        "reason": "slid 3.5 mm left, away from St. Mary's St beside it",
    },
    # The four below came with making every label bold, which made them wider.
    "St. Mary's St": {
        "dx": -0.5,
        "reason": "below its station, slid 0.5 mm left so it clears Fenway's light",
    },
    "Newton Highlands": {
        "text": "Newton\nHighlands",
        "reason": "on two lines: on one it reaches Washington Sq's light on the C branch",
    },
    "Community College": {
        "text": "Comm College",
        "reason": "shortened: the whole name runs into the Charles",
    },
    "Maverick": {
        "dist": 9.5,
        "reason": "1.5 mm nearer its line than the 11 mm used beside diagonals, to keep clear of the harbor's channel",
    },
}
