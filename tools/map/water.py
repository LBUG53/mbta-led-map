"""Water for the print: the Charles, the Mystic and the harbor, as simple
shapes steered between stations and labels. Positions are taken from the
layout where the spec ties them to it (which stations a river passes between).
"""
import math

import params as P
from geometry import point_in_polygon, point_to_segment

COLOR = "#D9E2F2"           # a 15% tint of the Blue Line's blue
LABEL_GAP = 1.0             # labels keep at least this far from water
HOLE = P.HOLE_D / 2
RIVER = 5.5                 # every river's width, mm
BASIN = 11.0                # the Charles by BU, at its widest
BASIN_RAMP = 70.0           # how far along the river it takes to widen from RIVER to BASIN, at each end
MOUTH = 8.0                 # the Charles where it meets the harbor: rivers widen downstream, roads don't
COAST = 5.0                 # corner radius all along the harbor's shore
CHANNEL = 6.0               # Fort Point Channel's width
LOGAN_CUT = 9.0             # Logan's two outer corners are cut off at 45 degrees, this much each way


def smooth(points, radius):
    """A polyline with its corners rounded, as a dense list of points. `radius` is one number, or one
    per corner."""
    out = [points[0]]
    for i in range(1, len(points) - 1):
        a, p, c = points[i - 1], points[i], points[i + 1]
        la, lc = math.dist(a, p), math.dist(p, c)
        t = min(radius if isinstance(radius, (int, float)) else radius[i - 1], la * 0.45, lc * 0.45)
        start = (p[0] + (a[0] - p[0]) * t / la, p[1] + (a[1] - p[1]) * t / la)
        end = (p[0] + (c[0] - p[0]) * t / lc, p[1] + (c[1] - p[1]) * t / lc)
        for k in range(9):
            u = k / 8
            out.append(((1 - u) ** 2 * start[0] + 2 * (1 - u) * u * p[0] + u * u * end[0],
                        (1 - u) ** 2 * start[1] + 2 * (1 - u) * u * p[1] + u * u * end[1]))
    out.append(points[-1])
    return out


def dense(pts, step=2.0):
    """The same polyline with a point at least every `step` mm, so a width can change along it."""
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]
    return out


def widths_along(pts, ends, middle, ramp, lead=0.0):
    """A width for each point: `ends` at both ends, easing up to `middle` over `ramp` mm.
    The widening starts `lead` mm from the first point."""
    run = [0.0]
    for a, b in zip(pts, pts[1:]):
        run.append(run[-1] + math.dist(a, b))
    out = []
    for d in run:
        u = max(0.0, min(1.0, min(d - lead, run[-1] - d) / ramp))
        out.append(ends + (middle - ends) * (1 - math.cos(math.pi * u)) / 2)
    return out


def build(stations):
    """Returns (rivers, areas): rivers are ([points], [width at each point]); areas are polygons."""
    at = {(s["line"], s["name"]): (s["x"], s["y"]) for s in stations}

    def between(a, b):
        return ((at[a][0] + at[b][0]) / 2, (at[a][1] + at[b][1]) / 2)

    kenmore, kendall = at[("GL", "Kenmore")], at[("RL", "Kendall/MIT")]
    alewife = at[("RL", "Alewife")]
    # The Charles runs down the middle of the gap between the Red Line's
    # Cambridge stations and the B branch (both at 45 degrees).
    red_k = alewife[0] - alewife[1]                 # x - y along the Red diagonal
    b_k = kenmore[0] - kenmore[1]                   # x - y along the B diagonal
    k = (red_k + b_k) / 2
    y_in = 98.0                                     # where it comes in from the west
    y_low = (kendall[1] + P.TRUNK_Y) / 2            # between the Red row and the Green trunk
    x_cross = between(("RL", "Kendall/MIT"), ("RL", "Charles/MGH"))[0]
    y_green = between(("GL", "Lechmere"), ("GL", "Science Park/West End"))[1]
    y_orange = between(("OL", "Community College"), ("OL", "North Station"))[1]
    mouth = (P.OX + 40.5, y_orange)                 # where the Charles, the Mystic and the harbor meet

    # In from the west and down the gap (upper); then a narrow stretch between the Red row's lights and
    # the trunk's, north past Bowdoin and east to the mouth (low).
    upper = dense(smooth([(-8, y_in), (y_in + k, y_in), (y_low + k - 3, y_low - 3)], 10))
    low = smooth([(y_low + k - 7, y_low - 7), (y_low + k, y_low), (x_cross, y_low), (x_cross, y_green),
                  (P.GX + 10, y_green),                                   # midway between the columns' lights
                  (P.GX + 10 + (y_orange - y_green), y_orange), (mouth[0] - 1.5, mouth[1])], [7, 8, 10, 10, 10])
    # (It stops just short of the mouth so its round end stays inside the harbor channel.)
    # Inner harbor: down from the mouth, then at 45 degrees across the Blue Line between Aquarium and
    # Maverick and into the harbor.
    inner = smooth([mouth, (mouth[0], mouth[1] + 26), (mouth[0] + 30, mouth[1] + 56)], 6)
    # Mystic: north from the mouth, across the Orange Line between Assembly and Wellington, then
    # northwest and straight up off the top of the paper, clear of the Green Line.
    y_mystic = between(("OL", "Assembly"), ("OL", "Wellington"))[1]
    # It leaves the inner harbor's channel a little below the mouth, so its round end is hidden in the water
    # and the two meet in a clean corner.
    mystic = smooth([(mouth[0], mouth[1] + 9), (mouth[0] + 9, y_orange), (mouth[0] + 9, y_mystic),
                     (P.OX - 16, y_mystic), (P.OX - 56, y_mystic - 40), (P.OX - 83, y_mystic - 67), (P.OX - 83, -8)], 10)
    # The first stretch widens into the basin by BU and narrows again.
    rivers = [(upper, widths_along(upper, RIVER, BASIN, BASIN_RAMP, lead=y_in + k + 8))]
    low = dense(low)
    run = [0.0]
    for a, b in zip(low, low[1:]):
        run.append(run[-1] + math.dist(a, b))
    rivers.append((low, [RIVER + (MOUTH - RIVER) * d / run[-1] for d in run]))
    rivers.append((inner, [RIVER] * len(inner)))
    rivers.append((mystic, [RIVER] * len(mystic)))

    # The harbor, drawn like the lines: straight edges, flat or at 45 degrees. Its north shore runs 13 mm
    # off the Blue Line from Maverick on, with Logan Airport hanging off it; to the south, South Boston
    # sticks out into it, with Fort Point Channel between it and downtown, crossing the Red Line between
    # South Station and Broadway as the real one does. Below South Boston it follows the Red Line 13 mm
    # off, then two flat steps take it east under the Braintree branch's labels to the paper's edge.
    off = 13 * math.sqrt(2)                          # 13 mm square to a 45-degree line, measured along y
    maverick, south, jfk = at[("BL", "Maverick")], at[("RL", "South Station")], at[("RL", "JFK/UMass")]
    orient = at[("BL", "Orient Heights")]
    north_k = maverick[0] + maverick[1] + off        # x + y along the north shore
    west_k = jfk[1] - jfk[0] - off                   # y - x along the shore below South Boston
    x_west = south[0] + 3.4                          # the short straight shore by South Station
    y_step = jfk[1] - 5.3
    y_south = y_step + 45.1
    edge = P.FACE + 5
    # South Boston and the channel. The channel ends a little past the Red Line, short of Broadway's label.
    y_seaport = 235.0                                # South Boston's north shore
    x_channel = 450.0
    channel_end = south[1] + 7.0
    x_castle = 515.0                                 # South Boston's east end, cut at 45 degrees
    # Logan: from the shore past Orient Heights down at 45 degrees, its corner cut, then flat along the
    # runways' side all the way to the shore where the inner harbor's channel comes in, so the channel
    # opens straight into the harbor below it.
    b = (orient[0] + 6, north_k - orient[0] - 6)
    y_logan = 205.0
    x_east = b[0] + y_logan - b[1]                   # where Logan's 45-degree east side meets its south side
    # The downtown shore runs straight down from the channel's mouth, then at 45 degrees into Fort Point Channel.
    harbor = [(x_west, north_k - x_west), (x_west, y_seaport - (x_channel - x_west)), (x_channel, y_seaport),
              (x_channel, channel_end), (x_channel + CHANNEL, channel_end), (x_channel + CHANNEL, y_seaport),
              (x_castle - 14, y_seaport), (x_castle, y_seaport + 14), (x_castle, y_step),
              (y_step - west_k + 22.9, y_step),
              (y_step - west_k + 68.0, y_south), (edge, y_south), (edge, north_k - edge),
              b, (x_east - LOGAN_CUT / 2, y_logan - LOGAN_CUT / 2), (x_east - LOGAN_CUT, y_logan),
              (north_k - y_logan, y_logan)]
    # Corner radii, from the second point round to the first: one radius everywhere except Fort Point
    # Channel, which is too narrow for it.
    radii = [COAST, 3.0, 1.5, 1.5, 3.0] + [COAST] * (len(harbor) - 5)
    return rivers, [smooth(harbor + harbor[:2], radii)[1:-1]]


# --- checks
def point_gap(p, rivers, areas):
    """How far a point is from the nearest water (0 if in it)."""
    best = float("inf")
    for pts, widths in rivers:
        for a, b, wa, wb in zip(pts, pts[1:], widths, widths[1:]):
            best = min(best, point_to_segment(p, a, b) - max(wa, wb) / 2)
    for poly in areas:
        if point_in_polygon(poly, p):
            return 0.0
        for i in range(len(poly)):
            best = min(best, point_to_segment(p, poly[i], poly[(i + 1) % len(poly)]))
    return max(0.0, best)


def box_gap(box, rivers, areas):
    """How far a label box is from the nearest water (0 if they touch).
    Sampled around the box's edge and middle, every half millimeter."""
    x0, y0, x1, y1 = box[:4]
    pts = []
    n = max(2, int((x1 - x0) / 0.5))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        pts += [(x, y0), (x, y1), (x, (y0 + y1) / 2)]
    pts += [(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)]
    return min(point_gap(p, rivers, areas) for p in pts)


def outline(pts, widths):
    """A river as a closed shape: both banks, with a round end at each mouth."""
    left, right = [], []
    for i, (p, w) in enumerate(zip(pts, widths)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        n = math.dist(a, b) or 1.0
        nx, ny = -(b[1] - a[1]) / n, (b[0] - a[0]) / n
        left.append((p[0] + nx * w / 2, p[1] + ny * w / 2))
        right.append((p[0] - nx * w / 2, p[1] - ny * w / 2))

    def cap(p, q, w):
        """Half a circle round p, from the left bank to the right, bulging away from q."""
        h = math.atan2(p[1] - q[1], p[0] - q[0])
        return [(p[0] + w / 2 * math.cos(h + math.pi / 2 - math.pi * k / 8),
                 p[1] + w / 2 * math.sin(h + math.pi / 2 - math.pi * k / 8)) for k in range(1, 8)]

    return left + cap(pts[-1], pts[-2], widths[-1]) + right[::-1] + cap(pts[0], pts[1], widths[0])


def svg_lines(rivers, areas):
    # Filled shapes, not stroked lines: the basin's width changes along its length, which a stroke can't do.
    shapes = list(areas) + [outline(pts, widths) for pts, widths in rivers]
    return ['<polygon points="%s"/>' % " ".join("%.2f,%.2f" % p for p in poly) for poly in shapes]
