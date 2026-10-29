"""Every number the map is built from. Millimeters on the 610 x 610 face,
origin top left. Change a value here and rerun generate.py; nothing else
holds a coordinate (hand-placed exceptions go in overrides.py). The sizes of
the physical parts (the panel, the sign, the holes) come from build.yaml."""
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(ROOT, "build.yaml"), encoding="utf-8") as f:
    BUILD = yaml.safe_load(f)               # the measured sizes of this build

# --- the object
FACE = 610.0
CRADLE_WALL = 38.1                  # the widest frame wall the map is drawn to fit: the opening runs wall .. FACE - wall
if BUILD["panel"]["frame_wall"] > CRADLE_WALL:
    raise SystemExit("build.yaml: frame walls of %g mm are wider than the %g mm the map is drawn for; lights would sit "
                     "over the frame. Move the map in (LIGHT_MIN, LIGHT_MAX here) first." % (BUILD["panel"]["frame_wall"], CRADLE_WALL))
LIGHT_MIN, LIGHT_MAX = 44.0, 566.0  # every light center must be inside this, both directions
SIGN_W, SIGN_H = BUILD["sign"]["width"], BUILD["sign"]["height"]      # the LED panel
SIGN_EDGE = BUILD["sign"]["edge"]   # panel's outer edge from the right and bottom of the face: the 20 mm frame plus 12 mm,
                                    # enough for a jigsaw beside the frame wall and 14 mm clear of the glued tiles
SIGN_X0, SIGN_Y0 = FACE - SIGN_EDGE - SIGN_W, FACE - SIGN_EDGE - SIGN_H
SIGN_X1, SIGN_Y1 = FACE - SIGN_EDGE, FACE - SIGN_EDGE
WINDOW_INSET = BUILD["sign"]["window_inset"]    # the cut window is this much smaller than the panel on each side
SIGN_CLEAR = 6.0                    # no light this close to the panel outline

# Parts of the print that labels keep out of (x0, y0, x1, y1); drawn in stage 3.
# The T keeps the same distance from the paper's edges as the sign's window does.
MARGIN = SIGN_EDGE + WINDOW_INSET
CREDIT_MARGIN = 14.0                # the credit line, tucked into the bottom left corner
# The T logo, top left, 50 mm across: any bigger and its clear space reaches the Charles.
# The MBTA's trademark. Their guidance (October 2026) lets it identify their service, as here, as long as
# it is not the main branding and nothing suggests the MBTA made or endorsed the work: hence the last credit line.
TITLE_BOX = (MARGIN, MARGIN, MARGIN + 50.0, MARGIN + 50.0)
# Their brand guide asks for clear space round it as wide as one arm of the T: 23.7% of the diameter.
TITLE_CLEAR = 0.237 * (TITLE_BOX[2] - TITLE_BOX[0])
# DEPARTURES, centred just above the window: the word is 68 mm wide, plus 3 mm round it.
CAPTION_BOX = ((SIGN_X0 + SIGN_X1) / 2 - 37.0, SIGN_Y0 - 14.0, (SIGN_X0 + SIGN_X1) / 2 + 37.0, SIGN_Y0)
CREDIT_BOX = (CREDIT_MARGIN, FACE - CREDIT_MARGIN - 3.0, 200.0, FACE - CREDIT_MARGIN)   # one quiet line, bottom left
CREDIT = ["Lucian Bessmer, 2026", "CC BY-NC 4.0", "Data source: MassDOT", "Not affiliated with the MBTA"]

# --- hard limits
LIGHT_OFFSET = 7.0                  # each light from the line's center (two lights 14 apart)
MIN_LIGHT_GAP = 13.0                # lights of different stations
MIN_STATION_GAP = 20.0              # along a line
MAX_STATION_GAP = 85.0              # wire reach
MIN_FROM_RIGHT_ANGLE = 14.5

# --- drawing
LINE_WIDTH = 4.0
RADIUS = {45: 22.0, 90: 10.0, 135: 5.59}    # corner radius by how far the line turns
STATION_DOT = 2.2                       # diameter of the white dot at an ordinary station
CIRCLE_D, CIRCLE_STROKE = 6.0, 1.0       # the white circles at interchanges and termini
TERMINUS_STROKE = 1.3                   # a terminus ring is in its line's color, a little heavier
CONNECTOR_W, CONNECTOR_CORE = 3.6, 1.6
HOLE_D = BUILD["panel"]["hole"]    # the holes in the wood: drilled 1/4 in
# Colors follow the MBTA Brand Guidelines (10.01.20): the four line colors below are its system colors,
# and text and outlines are "MBTA Gray Dark" (PMS 419 C). Lighter grays are tints of it.
INK = "#212322"
BACKGROUND = "#F4F0E6"
COLORS = {"RL": "#DA291C", "M": "#DA291C", "OL": "#ED8B00", "BL": "#003DA5", "GL": "#00843D"}
GLOW_RADIUS = 5.0                   # what labels treat as a light's glow

# --- the layout
# Downtown: two columns, rows 24 apart.
OX = 378.0                          # Orange column
GX = OX - 40.0                      # Green column
LECHMERE_Y = 130.0
SCIENCE_PARK_Y = LECHMERE_Y + 20
NORTH_STATION_Y = LECHMERE_Y + 40
HAYMARKET_Y = NORTH_STATION_Y + 24
STATE_Y = HAYMARKET_Y + 24          # Gov't Center (Green) and State (Orange)
DTX_Y = STATE_Y + 24                # Park Street (Green) and Downtown Crossing (Orange)
BLUE_ROW_Y = STATE_Y + 12
RED_ROW_Y = DTX_Y + 24
COLUMN_TURN = 11.0                  # both columns turn southwest this far below their last stop
TRUNK_Y = RED_ROW_Y + 28            # Green trunk, clear of the Red row's lights

# Orange
ORANGE_NORTH_GAP = 20.0             # Oak Grove .. Community College
CHINATOWN_BELOW_RED = 11.0          # first stop on the diagonal, clear of the Red row
ORANGE_DIAG_GAP = 20.0

# Green north
MEDFORD_FIRST, MEDFORD_GAP = 14.0, 20.0
UNION_ABOVE_LECHMERE, UNION_LENGTH = 6.0, 40.0

# Green trunk (x positions, west of the column)
BOYLSTON_X, ARLINGTON_X, COPLEY_X, HYNES_X, KENMORE_X = GX - 54, GX - 76, GX - 98, GX - 124, GX - 146

# Green branches
B_COLUMN_X = 54.0
B_DIAG_FIRST, B_DIAG_GAP, B_DIAG_COUNT = 22.0, 21.0, 6    # the last one's label must fit left of the diagonal
B_COLUMN_FIRST_BELOW_PEAK, B_COLUMN_GAP = 16.0, 20.0
C_ST_MARYS, C_HAWES = 40.0, 60.0    # west of Kenmore
C_TURN_AFTER_HAWES = 10.0
C_COLUMN_X = 78.0
C_COLUMN_FIRST_Y, C_COLUMN_GAP = 370.0, 20.0
D_COLUMN_X = 131.0
D_DIAG = (35.0, 55.0, 75.0)         # Fenway, Longwood, Brookline Village from Kenmore (Fenway's label clear of St. Mary's)
D_COLUMN_FIRST_BELOW_TURN, D_COLUMN_GAP = 11.0, 20.0
E_COLUMN_X = 160.0
E_DIAG = (38.0, 58.0, 78.0, 98.0)   # Prudential .. Museum of Fine Arts from Copley (clear of Hynes's lights)
E_COLUMN_Y = (386.0, 411.0, 431.0, 451.0, 471.0, 491.0, 511.0)

# Blue
BOWDOIN_X, BLUE_GC_X = GX - 50, GX - 24     # Gov't Center to State is 84 mm, inside the wire reach
BLUE_STATE_X = OX + 20
BLUE_DIAG_FIRST = 36.8              # Aquarium: its label row falls between the Orange column's rows
BLUE_HARBOR_GAP = 34.0              # Aquarium to Maverick: room for the inner harbor between their labels
BLUE_DIAG_GAP = 21.5

# Red
KENDALL_X, CHARLES_X, RED_PARK_X = GX - 88, GX - 56, GX - 30
RED_DTX_X, SOUTH_STATION_X = OX + 14, OX + 58   # Park Street to Downtown Crossing: 84 mm
RED_NW_TURN = 11.0                  # west of Kendall/MIT
RED_NW_FIRST, RED_NW_GAP = 27.0, 26.0
RED_SE_TURN = 23.0                  # east of South Station
RED_SE_FIRST, RED_SE_GAP = 16.0, 20.0          # Broadway low enough for its label to clear South Station
ASHMONT_GAP = 20.0
BRAINTREE_DIAG = (33.5, 53.5, 73.5)  # North Quincy, Wollaston, Quincy Center from JFK/UMass
BRAINTREE_TURN_AFTER, BRAINTREE_FIRST_BELOW_TURN, BRAINTREE_GAP = 10.0, 13.0, 20.0

# Mattapan
MATTAPAN_FROM_ASHMONT = 20.0        # its Ashmont stop, west of the Red one
MATTAPAN_GAP = 21.0
