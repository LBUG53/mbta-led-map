"""The tiles that hold the pixels behind the wood.

  python make_tile.py lower_left     (or upper_left, upper_right) writes tile_<name>.stl
  python make_tile.py check          builds all three and checks they don't collide

A tile is a double collar per station (one bore per light, 14 mm apart) joined by
flat ribs, printed floor-down so on the bed it looks like the back of the panel.
Next to each bore is a plate with the pixel's number on its output and 1-3 dots
for the output, so wiring is "pixel 0 in the hole marked 0".

Sizes come from the fit tests: 13.0 mm bore, walls 15 mm above a 2 mm floor,
6 mm light opening (the 8 mm bulb went straight through 9 mm).
"""
import csv
import math
import os
import sys

import yaml
from manifold3d import Manifold

from stl import write_stl

# The map's data files (stations, wiring plan): the data folder beside this one; the sizes in build.yaml.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_DATA = os.path.join(ROOT, "data")
with open(os.path.join(ROOT, "build.yaml"), encoding="utf-8") as f:
    BUILD = yaml.safe_load(f)               # the measured sizes of this build

BORE = BUILD["pixels"]["bore"]      # bore diameter that fits the pixel
WALL = 1.2              # wall round the bores
FLOOR = 2.0             # floor under each collar; the bulb must stop inside this thickness
BORE_DEPTH = BUILD["pixels"]["collar_depth"]   # how much of the pixel the collar holds (15 holds; 9.5 was too short)
OPENING = 6.0           # light opening through the floor: smaller than the bulb, so the bulb can't pass
RIB_WIDTH = 5.0         # flat ribs between collars
RIB_HEIGHT = 2.0
RIB_MAX = 70.0          # no brace longer than this
TAB_RADIUS = 6.0        # glue tabs: flat pads on the ribs, away from the light openings
TAB_HOLE = 3.4          # middle hole (also takes a small screw)
TAB_SPACING = 45.0      # about one tab every this far, spread over the whole tile
GLUE_HOLE = 2.0         # four small holes round the middle one: glue pushed up through them keys the tab down
TAB_ARM = 14.0          # a tab may sit this far off a rib, on its own short arm
GLUE_RING = 3.8         # how far those are from the middle
KNOB = 4.0              # joint between tiles: radius of the knob
SOCKET = 6.8            # and the outer radius of the socket round it
JOINT_SLACK = 0.35      # gap between knob and socket
JOINT_REACH = 75.0      # stations this close across a boundary can carry a joint
JOINTS = 3              # joints per boundary, at most
MARK_WIDTH, MARK_DEPTH = 2.5, 2.5   # the slot across a locating collar's rim
PANEL = BUILD["panel"]["size"]     # the wood panel, mm
# The LED panel (front: x 259.9-577.9, y 419.3-577.3) plus 4.2 mm round it, in tile coordinates (the front's,
# negated). No number plate goes in it.
SIGN_KEEP = (-577.9 - 4.2, -577.3 - 4.2, -259.9 + 4.2, -419.3 + 4.2)
CREDIT = "L BESSMER 2026"                       # raised lettering on one tile, in the emptiest spot on a rib
CREDIT_TILES = ["upper_right", "upper_left"]    # the first of these with room carries it
CREDIT_DOT = 0.7        # size of one dot of the 5 x 7 lettering
SEGMENTS = 64

DIGIT_W, DIGIT_H, STROKE = 2.1, 3.4, 0.6    # raised 7-segment digits
DIGIT_GAP = 0.6
MARGIN = 0.6
DOT = 0.9               # output dots
RAISE = 0.7             # how far digits, dots and the bar stand above the plate
BAR = 0.9               # extra plate on the side that touches the bore, carrying the bar

HEIGHT = FLOOR + BORE_DEPTH
RADIUS = BORE / 2 + WALL

# Which stations each tile carries (line, and x, y in mm on the front of the panel).
# The lower-left tile is the outer ends of the Green branches beside the sign.


def lower_left(line, x, y):
    """True for the stations on the lower-left tile: the outer ends of the Green branches, beside the sign."""
    return line == "GL" and y > 400 and x < 248


TILES = {
    "lower_left": lower_left,
    "upper_left": lambda line, x, y: not lower_left(line, x, y) and x < 306,
    "upper_right": lambda line, x, y: not lower_left(line, x, y) and x >= 306,
}

#          a (top)  b       c       d       e       f       g (middle)
SEGMENTS_OF = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgecd",
               "7": "abc", "8": "abcdefg", "9": "abfgcd"}


def back(x, y):
    """Front-of-panel mm (y down) to the tile's coordinates: the view from behind, y up."""
    return (-x, -y)


def disc(diameter, height, at, z=0.0):
    return Manifold.cylinder(height, diameter / 2, diameter / 2, SEGMENTS).translate((at[0], at[1], z))


def box(x, y, w, h, z0, z1):
    return Manifold.cube((w, h, z1 - z0)).translate((x, y, z0))


def bar(a, b, width, height):
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    return Manifold.cube((length, width, height)).translate((0.0, -width / 2, 0.0)).rotate((0.0, 0.0, angle)).translate(
        (a[0], a[1], 0.0))


def load(tile):
    """The tile's stations, each with its two lights and their place in the wiring."""
    inside = TILES[tile]
    wired = {}
    with open(os.path.join(MAP_DATA, "wiring_plan.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["light"] != "SKIP":
                wired[(r["line"], r["station"], r["light"])] = (int(r["output"]), int(r["index"]))
    out = []
    with open(os.path.join(MAP_DATA, "stations.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            x, y = float(r["x_mm"]), float(r["y_mm"])
            if inside(r["line"], x, y):
                key = (r["line"], r["station"])
                out.append({"name": r["line"] + " " + r["station"], "branch": r["branch"], "c": back(x, y),
                            "a": back(float(r["light_A_x"]), float(r["light_A_y"])),
                            "b": back(float(r["light_B_x"]), float(r["light_B_y"])),
                            "wa": wired[key + ("A",)], "wb": wired[key + ("B",)]})
    return out


def rib_edges(stations):
    """Ribs: neighbors on a line, plus braces wherever two stations have nothing between them."""
    n = len(stations)
    pts = [s["c"] for s in stations]

    def d(i, j):
        return math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
    edges = set()
    for i in range(n - 1):
        if stations[i]["branch"] == stations[i + 1]["branch"] and d(i, i + 1) <= 90:
            edges.add((i, i + 1))
    for i in range(n):
        for j in range(i + 1, n):
            if d(i, j) > RIB_MAX:
                continue
            mid = ((pts[i][0] + pts[j][0]) / 2, (pts[i][1] + pts[j][1]) / 2)
            r = d(i, j) / 2
            if all(math.hypot(pts[k][0] - mid[0], pts[k][1] - mid[1]) >= r - 1e-6 for k in range(n) if k not in (i, j)):
                edges.add((i, j))
    # make sure it is one piece
    group = list(range(n))

    def find(i):
        while group[i] != i:
            i = group[i]
        return i
    for i, j in edges:
        group[find(i)] = find(j)
    for dist, i, j in sorted((d(i, j), i, j) for i in range(n) for j in range(i + 1, n)):
        if find(i) != find(j):
            edges.add((i, j))
            group[find(i)] = find(j)
    return sorted(edges), d


def nearest_on_ribs(m, pts, edges):
    """The closest point to m on any rib."""
    best = None
    for i, j in edges:
        (x0, y0), (x1, y1) = pts[i], pts[j]
        dx, dy = x1 - x0, y1 - y0
        k = max(0.0, min(1.0, ((m[0] - x0) * dx + (m[1] - y0) * dy) / ((dx * dx + dy * dy) or 1.0)))
        q = (x0 + k * dx, y0 + k * dy)
        gap = math.hypot(m[0] - q[0], m[1] - q[1])
        if best is None or gap < best[0]:
            best = (gap, q)
    return best


def pick_tabs(stations, edges, plates, others, joints):
    """Glue tabs: on a rib or on a short arm beside one, clear of every collar and number plate, spread evenly. Start at a
    corner, then keep adding the spot farthest from the tabs chosen so far until none is more than
    TAB_SPACING from a tab."""
    pts = [s["c"] for s in stations]
    lights = [p for s in stations for p in (s["a"], s["b"])]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    spots = []
    y = min(ys)
    while y <= max(ys):
        x = min(xs)
        while x <= max(xs):
            m = (x, y)
            if min(math.hypot(x - p[0], y - p[1]) for p in lights) >= RADIUS + TAB_RADIUS + 0.5 \
                    and nearest_on_ribs(m, pts, edges)[0] <= TAB_ARM \
                    and all(gap_to_rect(m, q["rect"]) >= TAB_RADIUS + 0.5 for q in plates) \
                    and all(point_to_segment(m, f["a"], f["b"]) >= TAB_RADIUS + TAB_ARM + SOCKET for f in joints) \
                    and all(math.hypot(x - p[0], y - p[1]) >= RADIUS + TAB_RADIUS + TAB_ARM
                            for o in others for p in o["lights"]) \
                    and all(point_to_segment(m, r0, r1) >= TAB_RADIUS + TAB_ARM + RIB_WIDTH
                            for o in others for r0, r1 in o["ribs"]):
                spots.append((x, y))
            x += 3.0
        y += 3.0
    if not spots:
        return []
    corner = (min(xs), min(ys))
    tabs = [min(spots, key=lambda m: math.hypot(m[0] - corner[0], m[1] - corner[1]))]
    while True:
        far = max(spots, key=lambda m: min(math.hypot(m[0] - t[0], m[1] - t[1]) for t in tabs))
        if min(math.hypot(far[0] - t[0], far[1] - t[1]) for t in tabs) < TAB_SPACING:
            return tabs
        tabs.append(far)


# --- number plates
def plate_size(number):
    """(width, height) of the number plate for a pixel number: room for its digits and the output dots."""
    digits = len(str(number))
    w = MARGIN + DOT + DIGIT_GAP + digits * DIGIT_W + (digits - 1) * DIGIT_GAP + MARGIN
    return w, DIGIT_H + 2 * MARGIN


def gap_to_rect(p, rect):
    """Distance from a point to a rectangle (x0, y0, x1, y1); 0 inside."""
    dx = max(rect[0] - p[0], 0.0, p[0] - rect[2])
    dy = max(rect[1] - p[1], 0.0, p[1] - rect[3])
    return math.hypot(dx, dy)


def place_plates(stations, tabs, others=(), keep_out=()):
    """A plate for every light: beside its bore, clear of every bore, tab and other plate, and of
    everything on the neighbouring tiles (others: their plans, with "plates" once those are placed).
    Tries the outer side first (away from the partner), then along the track, then the angles between."""
    lights = []
    for s in stations:
        for me, other, wired in ((s["a"], s["b"], s["wa"]), (s["b"], s["a"], s["wb"])):
            n = math.hypot(me[0] - other[0], me[1] - other[1])
            lights.append({"p": me, "out": ((me[0] - other[0]) / n, (me[1] - other[1]) / n), "output": wired[0],
                           "number": wired[1], "name": s["name"]})
    bores = [l["p"] for l in lights]
    collars = [(s["a"][0] + (s["b"][0] - s["a"][0]) * k / 6.0, s["a"][1] + (s["b"][1] - s["a"][1]) * k / 6.0)
               for o in others for s in o["stations"] for k in range(7)]
    ribs = []
    for o in others:
        for a, b in o["ribs"]:
            steps = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 2.0) + 1
            ribs += [(a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps) for k in range(steps + 1)]
    theirs = [q for o in others for q in o.get("plates", [])]
    placed, failed = [], []
    for l in lights:
        ox, oy = l["out"]
        tx, ty = -oy, ox
        tries = []
        for deg in (0, 90, -90, 45, -45, 22.5, -22.5, 67.5, -67.5, 112.5, -112.5, 135, -135):
            c, sn = math.cos(math.radians(deg)), math.sin(math.radians(deg))
            tries.append((ox * c + tx * sn, oy * c + ty * sn))
        w, h = plate_size(l["number"])
        for ux, uy in tries:
            side = "x" if abs(ux) >= abs(uy) else "y"           # the plate's edge that faces the bore
            pw, ph = (w + BAR, h) if side == "x" else (w, h + BAR)
            reach = RADIUS - 0.4 + (pw / 2) * abs(ux) + (ph / 2) * abs(uy)
            cx, cy = l["p"][0] + ux * reach, l["p"][1] + uy * reach
            rect = (cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2)
            if any(gap_to_rect(b, rect) < BORE / 2 + 0.3 for b in bores):
                continue
            if any(gap_to_rect(t, rect) < GLUE_RING + GLUE_HOLE / 2 + 0.6 for t in tabs):
                continue
            if any(gap_to_rect(c, rect) < RADIUS + 0.5 for c in collars):
                continue
            if any(rect[0] < k[2] and k[0] < rect[2] and rect[1] < k[3] and k[1] < rect[3] for k in keep_out):
                continue
            if any(gap_to_rect(m, rect) < RIB_WIDTH / 2 + 0.5 for m in ribs):
                continue
            if any(rect[0] < q["rect"][2] + 0.5 and q["rect"][0] < rect[2] + 0.5 and
                   rect[1] < q["rect"][3] + 0.5 and q["rect"][1] < rect[3] + 0.5 for q in placed + theirs):
                continue
            toward = (-1 if ux > 0 else 1) if side == "x" else (-1 if uy > 0 else 1)   # which edge faces the bore
            placed.append(dict(l, rect=rect, side=side, toward=toward))
            break
        else:
            failed.append(l)
    return placed, failed


def digit(ch, x, y, z0, z1):
    """One raised digit in seven-segment style, its lower-left corner at (x, y), between heights z0 and z1."""
    w, h, t = DIGIT_W, DIGIT_H, STROKE
    half = (h + t) / 2
    seg = {"a": (x, y + h - t, w, t), "g": (x, y + (h - t) / 2, w, t), "d": (x, y, w, t),
           "f": (x, y + (h - t) / 2, t, half), "b": (x + w - t, y + (h - t) / 2, t, half),
           "e": (x, y, t, half), "c": (x + w - t, y, t, half)}
    out = Manifold()
    for name in SEGMENTS_OF[ch]:
        out += box(*seg[name], z0, z1)
    return out


def plate(q):
    """The plate with its raised bar, dots and digits."""
    x0, y0, x1, y1 = q["rect"]
    top = RIB_HEIGHT + RAISE
    out = box(x0, y0, x1 - x0, y1 - y0, 0.0, RIB_HEIGHT)
    # the bar on the bore's side, and the plain area left for the number
    if q["side"] == "x":
        bx = x0 if q["toward"] < 0 else x1 - STROKE
        out += box(bx, y0 + MARGIN, STROKE, (y1 - y0) - 2 * MARGIN, RIB_HEIGHT, top)
        ax0 = x0 + (BAR if q["toward"] < 0 else 0.0)
        ay0 = y0
    else:
        by = y0 if q["toward"] < 0 else y1 - STROKE
        out += box(x0 + MARGIN, by, (x1 - x0) - 2 * MARGIN, STROKE, RIB_HEIGHT, top)
        ax0 = x0
        ay0 = y0 + (BAR if q["toward"] < 0 else 0.0)
    for k in range(q["output"]):                    # output dots, in a column on the left
        cy = ay0 + MARGIN + DIGIT_H / 2 + (k - (q["output"] - 1) / 2.0) * 1.25
        out += Manifold.cylinder(RAISE, DOT / 2, DOT / 2, 16).translate((ax0 + MARGIN + DOT / 2, cy, RIB_HEIGHT))
    x = ax0 + MARGIN + DOT + DIGIT_GAP
    for ch in str(q["number"]):
        out += digit(ch, x, ay0 + MARGIN, RIB_HEIGHT, top)
        x += DIGIT_W + DIGIT_GAP
    return out


# --- joints between tiles
def point_to_segment(m, a, b):
    """Distance from point m to the segment from a to b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    k = max(0.0, min(1.0, ((m[0] - a[0]) * dx + (m[1] - a[1]) * dy) / ((dx * dx + dy * dy) or 1.0)))
    return math.hypot(m[0] - a[0] - k * dx, m[1] - a[1] - k * dy)


def segment_gap(a, b, c, d):
    """Distance between segments ab and cd; 0 if they cross."""
    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    if side(a, b, c) * side(a, b, d) < 0 and side(c, d, a) * side(c, d, b) < 0:
        return 0.0
    return min(point_to_segment(a, c, d), point_to_segment(b, c, d), point_to_segment(c, a, b), point_to_segment(d, a, b))


def make_plans():
    """Every tile's stations and ribs, then its number plates, each tile keeping clear of the others."""
    plans = {}
    for tile in sorted(TILES):
        stations = load(tile)
        edges, d = rib_edges(stations)
        pts = [s["c"] for s in stations]
        plans[tile] = {"tile": tile, "stations": stations, "edges": edges, "pts": pts,
                       "lights": [p for s in stations for p in (s["a"], s["b"])],
                       "ribs": [(pts[i], pts[j]) for i, j in edges]}
    for tile in sorted(TILES):                  # drop any brace that would run into a neighbouring tile's collar
        me = plans[tile]
        theirs = [(s["a"][0] + (s["b"][0] - s["a"][0]) * k / 6.0, s["a"][1] + (s["b"][1] - s["a"][1]) * k / 6.0)
                  for t in plans if t != tile for s in plans[t]["stations"] for k in range(7)]
        keep = [e for e in me["edges"]
                if all(point_to_segment(c, me["pts"][e[0]], me["pts"][e[1]]) >= RADIUS + RIB_WIDTH / 2 + 0.5 for c in theirs)]
        group = list(range(len(me["pts"])))     # and if that left a station on its own, tie it back in another way

        def find(i):
            while group[i] != i:
                i = group[i]
            return i
        for i, j in keep:
            group[find(i)] = find(j)
        pts = me["pts"]
        for dist, i, j in sorted((math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]), i, j)
                                 for i in range(len(pts)) for j in range(i + 1, len(pts))):
            if find(i) != find(j) and all(point_to_segment(c, pts[i], pts[j]) >= RADIUS + RIB_WIDTH / 2 + 0.5 for c in theirs):
                keep.append((i, j))
                group[find(i)] = find(j)
        keep.sort()
        me["edges"] = keep
        me["ribs"] = [(me["pts"][i], me["pts"][j]) for i, j in keep]
    for tile in sorted(TILES):
        me = plans[tile]
        me["plates"], me["failed"] = place_plates(me["stations"], [], [plans[t] for t in plans if t != tile],
                                                  [SIGN_KEEP])
    return plans


def half_clear(start, j, mine, other):
    """A rib from one of my stations to the joint must not touch anything of the other tile."""
    if any(point_to_segment(p, start, j) < RADIUS + RIB_WIDTH / 2 + 0.6 for p in other["lights"]):
        return False
    if any(segment_gap(start, j, a, b) < RIB_WIDTH + 0.6 for a, b in other["ribs"]):
        return False
    for q in other["plates"]:
        for k in range(11):
            m = (start[0] + (j[0] - start[0]) * k / 10.0, start[1] + (j[1] - start[1]) * k / 10.0)
            if gap_to_rect(m, q["rect"]) < RIB_WIDTH / 2 + 0.5:
                return False
    # nor run over one of my own bores, other than the two of the station it starts from
    if sum(1 for p in mine["lights"] if point_to_segment(p, start, j) < RADIUS + RIB_WIDTH / 2 + 0.6) > 2:
        return False
    return True


def joints_between(pa, pb):
    """Up to JOINTS places where a rib of tile pa (knob) meets a rib of tile pb (socket), spread out."""
    found = []
    for a in pa["pts"]:
        for b in pb["pts"]:
            if math.hypot(a[0] - b[0], a[1] - b[1]) > JOINT_REACH:
                continue
            for k in (0.5, 0.4, 0.6, 0.3, 0.7):
                j = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
                if any(math.hypot(j[0] - p[0], j[1] - p[1]) < RADIUS + SOCKET + 0.6 for p in pa["lights"]):
                    continue
                if any(math.hypot(j[0] - p[0], j[1] - p[1]) < RADIUS + KNOB + JOINT_SLACK + 0.6 for p in pb["lights"]):
                    continue
                if any(gap_to_rect(j, q["rect"]) < SOCKET + 0.5 for q in pa["plates"] + pb["plates"]):
                    continue
                if any(point_to_segment(j, r0, r1) < SOCKET + RIB_WIDTH / 2 + 0.6 for r0, r1 in pa["ribs"]):
                    continue
                if half_clear(a, j, pa, pb) and half_clear(b, j, pb, pa):
                    found.append({"knob": pa["tile"], "socket": pb["tile"], "a": a, "b": b, "j": j})
                    break
    if not found:
        return []
    found.sort(key=lambda f: (f["j"][0], f["j"][1]))
    chosen = [found[0]]
    while len(chosen) < JOINTS:
        far = max(found, key=lambda f: min(math.hypot(f["j"][0] - c["j"][0], f["j"][1] - c["j"][1]) for c in chosen))
        if min(math.hypot(far["j"][0] - c["j"][0], far["j"][1] - c["j"][1]) for c in chosen) < 40:
            break
        chosen.append(far)
    return chosen


def all_joints(plans):
    names = sorted(plans)
    out = []
    for i in range(len(names)):
        for k in range(i + 1, len(names)):
            out += joints_between(plans[names[i]], plans[names[k]])
    return out


def locating(stations):
    """The two stations farthest apart; their light A bores are the locating collars."""
    best = None
    for i in range(len(stations)):
        for k in range(i + 1, len(stations)):
            a, b = stations[i]["a"], stations[k]["a"]
            dist = math.hypot(a[0] - b[0], a[1] - b[1])
            if best is None or dist > best[0]:
                best = (dist, stations[i], stations[k])
    return [best[1], best[2]]


# --- the credit
FONT = {
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110", "D": "11110 10001 10001 10001 10001 10001 11110",
    "E": "11111 10000 10000 11110 10000 10000 11111", "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111", "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110", "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 11001 10101 10011 10001 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 11011 10001", "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100", "Z": "11111 00001 00010 00100 01000 10000 11111",
    "0": "01110 10001 10011 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111", "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    " ": "00000 00000 00000 00000 00000 00000 00000",
}


def credit_size():
    """(width, height) of the plate that carries the credit lettering."""
    return len(CREDIT) * 6 * CREDIT_DOT - CREDIT_DOT + 2 * MARGIN, 7 * CREDIT_DOT + 2 * MARGIN


def along(segments, step=2.0):
    """Points every `step` mm along some segments: the places a plate could be tried."""
    out = []
    for a, b in segments:
        n = int(math.hypot(b[0] - a[0], b[1] - a[1]) / step) + 1
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n + 1)]
    return out


def place_credit(plans, joints):
    """Where the credit goes: (tile, rect), lying across one of that tile's ribs, as far from the bores as it can be
    and clear of every plate, joint and neighbouring tile. None if there is no room."""
    if not CREDIT:
        return None
    w, h = credit_size()
    for tile in CREDIT_TILES:
        me = plans[tile]
        others = [plans[t] for t in plans if t != tile]
        collars = along([(s["a"], s["b"]) for o in plans.values() for s in o["stations"]], 2.0)
        mine = along(me["ribs"])
        theirs = along([r for o in others for r in o["ribs"]])
        plates = [q["rect"] for o in plans.values() for q in o["plates"]]
        jpts = along([(f["a"], f["b"]) for f in joints])
        xs, ys = [q[0] for q in me["pts"]], [q[1] for q in me["pts"]]
        best = None
        y = min(ys)
        while y + h <= max(ys):
            x = min(xs)
            while x + w <= max(xs):
                rect = (x, y, x + w, y + h)
                inner = (x + 2, y + 1, x + w - 2, y + h - 1)
                x += 3.0
                room = min(gap_to_rect(c, rect) for c in collars)
                if room < RADIUS + 0.6 or (best and room <= best[0]):
                    continue
                if not any(gap_to_rect(m, inner) == 0 for m in mine):
                    continue
                if any(gap_to_rect(m, rect) < RIB_WIDTH / 2 + 0.6 for m in theirs):
                    continue
                if any(gap_to_rect(m, rect) < SOCKET + 0.6 for m in jpts):
                    continue
                if any(rect[0] < q[2] + 0.5 and q[0] < rect[2] + 0.5 and rect[1] < q[3] + 0.5 and q[1] < rect[3] + 0.5
                       for q in plates):
                    continue
                best = (room, rect)
            y += 1.5
        if best:
            return tile, best[1]
    return None


def credit_plate(rect):
    """The credit as a solid: a flat plate with the lettering raised on it in 5 x 7 dots."""
    out = box(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1], 0.0, RIB_HEIGHT)
    d = CREDIT_DOT
    for i, ch in enumerate(CREDIT.upper()):
        rows = FONT.get(ch, FONT[" "]).split()
        for r, row in enumerate(rows):
            for c, bit in enumerate(row):
                if bit == "1":
                    out += box(rect[0] + MARGIN + (i * 6 + c) * d, rect[1] + MARGIN + (6 - r) * d, d, d,
                               RIB_HEIGHT, RIB_HEIGHT + RAISE)
    return out


# --- the tile
def build(tile, plans, joints, credit=None):
    """One tile as a solid, from the shared plans. Returns (solid, ribs, glue tabs, number plates,
    plates that found no room, the two locating stations, this tile's joints).
    """
    me = plans[tile]
    stations, edges, plates, failed, pts = me["stations"], me["edges"], me["plates"], me["failed"], me["pts"]
    others = [plans[t] for t in plans if t != tile]
    mark = credit[1] if credit and credit[0] == tile else None
    tabs = pick_tabs(stations, edges, plates + ([{"rect": mark}] if mark else []), others, joints)
    marks = locating(stations)
    solid = Manifold()
    holes = Manifold()
    for s in stations:
        solid += disc(2 * RADIUS, HEIGHT, s["a"]) + disc(2 * RADIUS, HEIGHT, s["b"]) + bar(s["a"], s["b"], 2 * RADIUS, HEIGHT)
        for p in (s["a"], s["b"]):
            holes += disc(BORE, HEIGHT, p, FLOOR) + disc(OPENING, FLOOR + 2, p, -1.0)
    for s in marks:                                             # the slot across a locating collar's rim
        a, b = s["a"], s["b"]
        n = math.hypot(b[0] - a[0], b[1] - a[1])
        tx, ty = -(b[1] - a[1]) / n * (RADIUS + 1), (b[0] - a[0]) / n * (RADIUS + 1)
        holes += bar((a[0] - tx, a[1] - ty), (a[0] + tx, a[1] + ty), MARK_WIDTH, MARK_DEPTH + 1).translate(
            (0.0, 0.0, HEIGHT - MARK_DEPTH))
    for i, j in edges:
        solid += bar(pts[i], pts[j], RIB_WIDTH, RIB_HEIGHT)
    for t in tabs:
        solid += disc(2 * TAB_RADIUS, RIB_HEIGHT, t)
        gap, q = nearest_on_ribs(t, pts, edges)
        if gap > 0.5:
            solid += bar(t, q, RIB_WIDTH, RIB_HEIGHT)           # the arm from the rib to the tab
        holes += disc(TAB_HOLE, RIB_HEIGHT + 2, t, -1.0)
        for gx, gy in ((GLUE_RING, 0), (-GLUE_RING, 0), (0, GLUE_RING), (0, -GLUE_RING)):
            holes += disc(GLUE_HOLE, RIB_HEIGHT + 2, (t[0] + gx, t[1] + gy), -1.0)
    for q in plates:
        solid += plate(q)
    if mark:
        solid += credit_plate(mark)
    mine = [f for f in joints if tile in (f["knob"], f["socket"])]
    for f in mine:
        j = f["j"]
        if f["knob"] == tile:
            solid += bar(f["a"], j, RIB_WIDTH, RIB_HEIGHT) + disc(2 * KNOB, RIB_HEIGHT, j)
        else:
            solid += bar(f["b"], j, RIB_WIDTH, RIB_HEIGHT) + disc(2 * SOCKET, RIB_HEIGHT, j)
            n = math.hypot(f["a"][0] - j[0], f["a"][1] - j[1])
            out = (j[0] + (f["a"][0] - j[0]) / n * (SOCKET + 1), j[1] + (f["a"][1] - j[1]) / n * (SOCKET + 1))
            holes += disc(2 * (KNOB + JOINT_SLACK), RIB_HEIGHT + 2, j, -1.0)
            holes += bar(j, out, RIB_WIDTH + 2 * JOINT_SLACK, RIB_HEIGHT + 2).translate((0.0, 0.0, -1.0))
    return solid - holes, edges, tabs, plates, failed, marks, mine


def write_preview(stations, edges, tabs, plates, path):
    """A top view, as the tile lies on the bed (the panel seen from behind)."""
    pts = [s["c"] for s in stations]
    xs = [q["rect"][0] for q in plates] + [q["rect"][2] for q in plates] + [p[0] for p in pts]
    ys = [q["rect"][1] for q in plates] + [q["rect"][3] for q in plates] + [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs) - 14, max(xs) + 14, min(ys) - 14, max(ys) + 20

    def P(p):
        return (p[0] - x0, y1 - p[1])
    colors = {1: "#c02a1c", 2: "#b36a00", 3: "#00763a"}
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.0f %.0f" width="1000" style="background:#fff">'
         % (x1 - x0, y1 - y0)]
    for i, j in edges:
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#b8c4d0" stroke-width="%g"/>'
                 % (P(pts[i]) + P(pts[j]) + (RIB_WIDTH,)))
    for t in tabs:
        c = P(t)
        o.append('<circle cx="%.1f" cy="%.1f" r="%g" fill="#b8c4d0"/><circle cx="%.1f" cy="%.1f" r="%g" fill="#fff"/>'
                 % (c + (TAB_RADIUS,) + c + (TAB_HOLE / 2,)))
    for q in plates:
        a, b = P((q["rect"][0], q["rect"][3])), P((q["rect"][2], q["rect"][1]))
        o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#e8edf2" stroke="%s" stroke-width="0.3"/>'
                 % (a[0], a[1], b[0] - a[0], b[1] - a[1], colors[q["output"]]))
        if q["side"] == "x":
            bx = a[0] if q["toward"] < 0 else b[0]
            o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.8"/>'
                     % (bx, a[1], bx, b[1], colors[q["output"]]))
        else:
            by = b[1] if q["toward"] < 0 else a[1]
            o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.8"/>'
                     % (a[0], by, b[0], by, colors[q["output"]]))
        o.append('<text x="%.2f" y="%.2f" font-size="3.4" font-family="Arial" font-weight="bold" text-anchor="middle" '
                 'fill="%s">%d</text>' % ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 1.2, colors[q["output"]], q["number"]))
    for s in stations:
        a, b = P(s["a"]), P(s["b"])
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#345" stroke-width="%g" stroke-linecap="round"/>'
                 % (a + b + (2 * RADIUS,)))
        for p in (a, b):
            o.append('<circle cx="%.1f" cy="%.1f" r="%g" fill="#fff"/><circle cx="%.1f" cy="%.1f" r="%g" fill="#ccc"/>'
                     % (p + (BORE / 2,) + p + (OPENING / 2,)))
        c = P(s["c"])
        o.append('<text x="%.1f" y="%.1f" font-size="2.2" font-family="Arial" text-anchor="middle" fill="#fff">%s</text>'
                 % (c[0], c[1] - 5.2, s["name"].replace("&", "&amp;")))
    o.append('<text x="3" y="7" font-size="4.5" font-family="Arial">Seen from the back, as it lies on the printer bed. '
             'Number = pixel on its output; orange = output 2, green = output 3.</text></svg>')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(o))


def bed_turn(part, bed=None):
    """The smallest turn, in whole degrees, at which a part fits on the printer's bed (build.yaml), or None."""
    w, h = bed or BUILD["printer"]["bed"]
    for deg in range(90):
        b = part.rotate((0.0, 0.0, float(deg))).bounding_box()
        x, y = b[3] - b[0], b[4] - b[1]
        if (x <= w and y <= h) or (x <= h and y <= w):
            return deg
    return None


def main():
    """Build the tile named on the command line (or check all three against each other) and report on it."""
    tile = sys.argv[1] if len(sys.argv) > 1 else "lower_left"
    plans = make_plans()
    joints = all_joints(plans)
    credit = place_credit(plans, joints)
    if tile == "check":
        parts = dict((t, build(t, plans, joints, credit)[0]) for t in TILES)
        names = sorted(parts)
        bad = 0
        for i in range(len(names)):
            for k in range(i + 1, len(names)):
                v = (parts[names[i]] ^ parts[names[k]]).volume()
                n = len([f for f in joints if set((f["knob"], f["socket"])) == set((names[i], names[k]))])
                print("%s and %s: %d joints, overlap %.2f mm3" % (names[i], names[k], n, v))
                bad += v > 0.01
        for t in names:
            deg = bed_turn(parts[t])
            print("%s on the %g x %g mm bed: %s" % (t, BUILD["printer"]["bed"][0], BUILD["printer"]["bed"][1],
                  "TOO BIG: cut the map into more tiles (TILES)" if deg is None else
                  "fits" if deg == 0 else "fits turned %d degrees" % deg))
            bad += deg is None
        return 1 if bad else 0
    stations = plans[tile]["stations"]
    part, edges, tabs, plates, failed, marks, mine = build(tile, plans, joints, credit)
    bb = part.bounding_box()
    here = os.path.dirname(os.path.abspath(__file__))
    count = write_stl(part, os.path.join(here, "tile_%s.stl" % tile), "tile_" + tile)
    write_preview(stations, edges, tabs, plates, os.path.join(here, "tile_%s_preview.svg" % tile))
    print("tile %s: %d stations (%d lights), %d ribs, %d glue tabs, %d number plates" % (
        tile, len(stations), 2 * len(stations), len(edges), len(tabs), len(plates)))
    print("  size %.0f x %.0f x %.1f mm, %.1f cm3, %d separate pieces" % (
        bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2], part.volume() / 1000, len(part.decompose())))
    if credit and credit[0] == tile:
        r = credit[1]
        print("  credit \"%s\": %.0f x %.1f mm plate, centred %.0f mm from the left, %.0f mm from the top (front view)" % (
            CREDIT, r[2] - r[0], r[3] - r[1], -(r[0] + r[2]) / 2, -(r[1] + r[3]) / 2))
    elif CREDIT and not credit:
        print("  NO ROOM for the credit on", " or ".join(CREDIT_TILES))
    for f in mine:
        print("  joint with %s: %s" % (f["socket"] if f["knob"] == tile else f["knob"],
                                       "knob" if f["knob"] == tile else "socket"))
    print("  locating collars (slotted rim), light A, measured on the FRONT of the panel:")
    for s in marks:
        x, y = -s["a"][0], -s["a"][1]
        print("    %-28s %6.1f mm from the left edge, %6.1f mm from the top   (%.1f from the right, %.1f from the bottom)"
              % (s["name"], x, y, PANEL - x, PANEL - y))
    print("  collar: bore %.1f, wall %.1f, %.1f tall with a %.1f floor and a %.1f opening" % (
        BORE, WALL, HEIGHT, FLOOR, OPENING))
    sides = {}
    for q in plates:
        ox, oy = q["out"]
        cx, cy = (q["rect"][0] + q["rect"][2]) / 2 - q["p"][0], (q["rect"][1] + q["rect"][3]) / 2 - q["p"][1]
        along = abs(cx * ox + cy * oy) / math.hypot(cx, cy)
        k = "outer side" if along > 0.9 else ("along the track" if along < 0.1 else "diagonal")
        sides[k] = sides.get(k, 0) + 1
    print("  plates:", ", ".join("%d %s" % (v, k) for k, v in sides.items()))
    by_output = {}
    for q in plates:
        by_output.setdefault(q["output"], []).append(q["number"])
    for o in sorted(by_output):
        nums = sorted(by_output[o])
        print("  output %d: %d lights, numbers %d to %d" % (o, len(nums), nums[0], nums[-1]))
    for l in failed:
        print("  NO ROOM for a plate: %s, output %d pixel %d" % (l["name"], l["output"], l["number"]))
    print("wrote tile_%s.stl (%d triangles) and tile_%s_preview.svg" % (tile, count, tile))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
