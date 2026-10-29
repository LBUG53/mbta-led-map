"""The network: every line as a path of horizontal, vertical and 45-degree
legs, with its stations in order. All numbers come from params.py."""
import math

from geometry import point_to_segment
import overrides
import params as P

S = math.sqrt(0.5)
DIRS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0),
        "NE": (S, -S), "NW": (-S, -S), "SE": (S, S), "SW": (-S, S)}


class Run:
    """One drawn path. Move with to(); drop stations with stop()."""

    def __init__(self, line, branch, toward, start, after=None):
        """Start a path at `start`. `toward` says, in words, where trains that light the
        A lights are heading; it ends up in the stations file.
        """
        self.line, self.branch, self.toward = line, branch, toward
        self.pts = [start]          # path vertices
        self.pos = start
        self.heading = None
        self.stops = []             # station dicts, in drawing order
        self.after = after          # the station this branch leaves from (for spacing checks)

    def to(self, direction, dist):
        """Move `dist` mm in a compass direction (N, NE, E...), drawing the line."""
        dx, dy = DIRS[direction]
        self.pos = (self.pos[0] + dx * dist, self.pos[1] + dy * dist)
        if self.heading == direction:
            self.pts[-1] = self.pos
        else:
            self.pts.append(self.pos)
        self.heading = direction
        return self

    def to_x(self, direction, x):
        return self.to(direction, abs(x - self.pos[0]) / abs(DIRS[direction][0]))

    def to_y(self, direction, y):
        return self.to(direction, abs(y - self.pos[1]) / abs(DIRS[direction][1]))

    def stop(self, name, heading=None, **flags):
        """A station here. Its lights sit across the line's direction of travel."""
        dx, dy = DIRS[heading or self.heading]
        x, y = self.pos
        nudge = overrides.GEOMETRY.get((self.line, name))
        if nudge:
            x, y = x + nudge[0], y + nudge[1]
        o = P.LIGHT_OFFSET
        st = {"line": self.line, "branch": self.branch, "name": name, "x": x, "y": y, "dir": (dx, dy),
              # Trains keep right: light A is on the right-hand side of a train heading `toward`.
              "A": (x - dy * o, y + dx * o), "B": (x + dy * o, y - dx * o),
              "toward": self.toward, "transfer": flags.get("transfer")}
        self.stops.append(st)
        return st


def orange():
    r = Run("OL", "Orange", "Forest Hills (southbound)",
            (P.OX, P.NORTH_STATION_Y - 6 * P.ORANGE_NORTH_GAP))
    r.stop("Oak Grove", "S")
    for name in ("Malden Center", "Wellington", "Assembly", "Sullivan Sq", "Community College"):
        r.to("S", P.ORANGE_NORTH_GAP).stop(name)
    r.to_y("S", P.NORTH_STATION_Y).stop("North Station", transfer="North Station")
    r.to_y("S", P.HAYMARKET_Y).stop("Haymarket", transfer="Haymarket")
    r.to_y("S", P.STATE_Y).stop("State", transfer="State")
    r.to_y("S", P.DTX_Y).stop("Downtown Crossing", transfer="Downtown Crossing")
    r.to("S", P.COLUMN_TURN)
    r.to_y("SW", P.RED_ROW_Y + P.CHINATOWN_BELOW_RED).stop("Chinatown")
    for name in ("Tufts Medical Ctr", "Back Bay", "Mass. Ave", "Ruggles", "Roxbury Crossing", "Jackson Sq",
                 "Stony Brook", "Green St"):
        r.to("SW", P.ORANGE_DIAG_GAP).stop(name)
    r.to("SW", P.ORANGE_DIAG_GAP).stop("Forest Hills")
    return r


def green_trunk():
    """Medford/Tufts to Kenmore, then the C branch. Returns the run and the stops the other branches start from."""
    west = "Kenmore and the branches (westbound)"
    top = (P.GX, P.LECHMERE_Y - P.COLUMN_TURN)
    far = P.MEDFORD_FIRST + 4 * P.MEDFORD_GAP
    g = Run("GL", "Green trunk", west, (top[0] - far * S, top[1] - far * S))
    g.stop("Medford/Tufts", "SE")
    for name in ("Ball Sq", "Magoun Sq", "Gilman Sq", "East Somerville"):
        g.to("SE", P.MEDFORD_GAP).stop(name)
    g.to("SE", P.MEDFORD_FIRST)
    g.to_y("S", P.LECHMERE_Y).stop("Lechmere")
    lechmere = g.stops[-1]
    g.to_y("S", P.SCIENCE_PARK_Y).stop("Science Park/West End")
    g.to_y("S", P.NORTH_STATION_Y).stop("North Station", transfer="North Station")
    g.to_y("S", P.HAYMARKET_Y).stop("Haymarket", transfer="Haymarket")
    g.to_y("S", P.STATE_Y).stop("Gov't Center", transfer="Gov't Center")
    g.to_y("S", P.DTX_Y).stop("Park Street", transfer="Park Street")
    g.to("S", P.COLUMN_TURN)
    g.to_y("SW", P.TRUNK_Y)
    g.to_x("W", P.BOYLSTON_X).stop("Boylston")
    g.to_x("W", P.ARLINGTON_X).stop("Arlington")
    g.to_x("W", P.COPLEY_X).stop("Copley")
    copley = g.stops[-1]
    g.to_x("W", P.HYNES_X).stop("Hynes Convention Ctr")
    g.to_x("W", P.KENMORE_X).stop("Kenmore")
    kenmore = g.stops[-1]
    # C branch: on west, down a short diagonal, then a column near the left edge.
    g.branch = "Green C"
    g.toward = "Cleveland Circle (westbound)"
    g.to("W", P.C_ST_MARYS).stop("St. Mary's St")
    g.to("W", P.C_HAWES - P.C_ST_MARYS).stop("Hawes St")
    g.to("W", P.C_TURN_AFTER_HAWES)
    diag = (g.pos[0] - P.C_COLUMN_X) / S
    g.to("SW", diag / 2).stop("Kent St")
    g.to("SW", diag / 2)
    g.to_y("S", P.C_COLUMN_FIRST_Y).stop("St. Paul St")
    for name in ("Coolidge Corner", "Summit Ave", "Brandon Hall", "Fairbanks St", "Washington Sq", "Tappan St",
                 "Dean Rd", "Englewood Ave"):
        g.to("S", P.C_COLUMN_GAP).stop(name)
    g.to("S", P.C_COLUMN_GAP).stop("Cleveland Circle")
    return g, lechmere, copley, kenmore


def union_square(lechmere):
    """A short spur off the column just above Lechmere."""
    u = Run("GL", "Green Union Sq", "Lechmere and downtown (westbound)",
            (P.GX - P.UNION_LENGTH, P.LECHMERE_Y - P.UNION_ABOVE_LECHMERE), after=None)
    u.stop("Union Sq", "E")
    u.to_x("E", P.GX)
    u.joins = lechmere
    return u


def green_b(kenmore):
    """One long diagonal into the upper left, then down the left edge."""
    b = Run("GL", "Green B", "Boston College (westbound)", (kenmore["x"], kenmore["y"]), after=kenmore)
    names = ["Blandford St", "BU East", "BU Central", "Amory St", "Babcock St", "Packard's Corner", "Harvard Ave",
             "Griggs St", "Allston St", "Warren St", "Washington St", "Sutherland Rd", "Chiswick Rd",
             "Chestnut Hill Ave", "South St"]
    b.to("NW", P.B_DIAG_FIRST).stop(names[0])
    for name in names[1:P.B_DIAG_COUNT]:
        b.to("NW", P.B_DIAG_GAP).stop(name)
    b.to_x("NW", P.B_COLUMN_X)
    b.to("S", P.B_COLUMN_FIRST_BELOW_PEAK).stop(names[P.B_DIAG_COUNT])
    for name in names[P.B_DIAG_COUNT + 1:]:
        b.to("S", P.B_COLUMN_GAP).stop(name)
    b.to("S", P.B_COLUMN_GAP).stop("Boston College")
    return b


def green_d(kenmore):
    d = Run("GL", "Green D", "Riverside (westbound)", (kenmore["x"], kenmore["y"]), after=kenmore)
    done = 0.0
    for name, at in zip(("Fenway", "Longwood", "Brookline Village"), P.D_DIAG):
        d.to("SW", at - done).stop(name)
        done = at
    d.to_x("SW", P.D_COLUMN_X)
    d.to("S", P.D_COLUMN_FIRST_BELOW_TURN).stop("Brookline Hills")
    for name in ("Beaconsfield", "Reservoir", "Chestnut Hill", "Newton Centre", "Newton Highlands", "Eliot", "Waban",
                 "Woodland"):
        d.to("S", P.D_COLUMN_GAP).stop(name)
    d.to("S", P.D_COLUMN_GAP).stop("Riverside")
    return d


def green_e(copley):
    e = Run("GL", "Green E", "Heath St (westbound)", (copley["x"], copley["y"]), after=copley)
    done = 0.0
    for name, at in zip(("Prudential", "Symphony", "Northeastern", "Museum of Fine Arts"), P.E_DIAG):
        e.to("SW", at - done).stop(name)
        done = at
    e.to_x("SW", P.E_COLUMN_X)
    for name, y in zip(("Longwood Medical Area", "Brigham Circle", "Fenwood Rd", "Mission Park", "Riverway",
                        "Back of the Hill"), P.E_COLUMN_Y):
        e.to_y("S", y).stop(name)
    e.to_y("S", P.E_COLUMN_Y[-1]).stop("Heath St")
    return e


def blue():
    bl = Run("BL", "Blue", "Wonderland (eastbound)", (P.BOWDOIN_X, P.BLUE_ROW_Y))
    bl.stop("Bowdoin", "E")
    bl.to_x("E", P.BLUE_GC_X).stop("Gov't Center", transfer="Gov't Center")
    bl.to_x("E", P.BLUE_STATE_X).stop("State", transfer="State")       # the line turns at this stop
    bl.to("NE", P.BLUE_DIAG_FIRST).stop("Aquarium")
    bl.to("NE", P.BLUE_HARBOR_GAP).stop("Maverick")
    for name in ("Airport", "Wood Island", "Orient Heights", "Suffolk Downs", "Beachmont", "Revere Beach"):
        bl.to("NE", P.BLUE_DIAG_GAP).stop(name)
    bl.to("NE", P.BLUE_DIAG_GAP).stop("Wonderland")
    return bl


def red():
    """Alewife to JFK/UMass, then on to Braintree. Returns the run and JFK/UMass, where the Ashmont branch leaves."""
    south = "Ashmont and Braintree (southbound)"
    corner = (P.KENDALL_X - P.RED_NW_TURN, P.RED_ROW_Y)
    far = P.RED_NW_FIRST + 4 * P.RED_NW_GAP
    rd = Run("RL", "Red", south, (corner[0] - far * S, corner[1] - far * S))
    rd.stop("Alewife", "SE")
    for name in ("Davis", "Porter", "Harvard", "Central"):
        rd.to("SE", P.RED_NW_GAP).stop(name)
    rd.to("SE", P.RED_NW_FIRST)
    rd.to_x("E", P.KENDALL_X).stop("Kendall/MIT")
    rd.to_x("E", P.CHARLES_X).stop("Charles/MGH")
    rd.to_x("E", P.RED_PARK_X).stop("Park Street", transfer="Park Street")
    rd.to_x("E", P.RED_DTX_X).stop("Downtown Crossing", transfer="Downtown Crossing")
    rd.to_x("E", P.SOUTH_STATION_X).stop("South Station")
    rd.to("E", P.RED_SE_TURN)
    rd.to("SE", P.RED_SE_FIRST).stop("Broadway")
    rd.to("SE", P.RED_SE_GAP).stop("Andrew")
    rd.to("SE", P.RED_SE_GAP).stop("JFK/UMass")
    jfk = rd.stops[-1]
    rd.branch = "Red Braintree"
    rd.toward = "Braintree (southbound)"
    done = 0.0
    for name, at in zip(("North Quincy", "Wollaston", "Quincy Center"), P.BRAINTREE_DIAG):
        rd.to("SE", at - done).stop(name)
        done = at
    rd.to("SE", P.BRAINTREE_TURN_AFTER)
    rd.to("S", P.BRAINTREE_FIRST_BELOW_TURN).stop("Quincy Adams")
    rd.to("S", P.BRAINTREE_GAP).stop("Braintree")
    return rd, jfk


def red_ashmont(jfk):
    a = Run("RL", "Red Ashmont", "Ashmont (southbound)", (jfk["x"], jfk["y"]), after=jfk)
    for name in ("Savin Hill", "Fields Corner", "Shawmut"):
        a.to("S", P.ASHMONT_GAP).stop(name)
    a.to("S", P.ASHMONT_GAP).stop("Ashmont", transfer="Ashmont")
    return a, a.stops[-1]


def mattapan(ashmont):
    m = Run("M", "Mattapan", "Mattapan (outbound)", (ashmont["x"] - P.MATTAPAN_FROM_ASHMONT, ashmont["y"]))
    m.stop("Ashmont", "W", transfer="Ashmont")
    for name in ("Cedar Grove", "Butler", "Milton", "Central Ave", "Valley Rd", "Capen St"):
        m.to("W", P.MATTAPAN_GAP).stop(name)
    m.to("W", P.MATTAPAN_GAP).stop("Mattapan")
    return m


def mark_line_ends(runs, stations):
    # The end of a line is a station at the end of a path that no other path runs through (Kenmore,
    # Copley and JFK/UMass start branches but aren't the end of the line). A terminus is a line end
    # that isn't also a transfer: Ashmont ends a Red Line branch but keeps its transfer circle.
    for s in stations:
        s["line_end"] = False
    for run in runs:
        for s in (run.stops[0], run.stops[-1]):
            end = (s["x"], s["y"])
            s["line_end"] = (end in (run.pts[0], run.pts[-1])
                             and all(point_to_segment(end, a, b) > 0.5
                                     for other in runs if other is not run for a, b in segments(other)))
    for s in stations:
        s["terminus"] = s["line_end"] and not s["transfer"]


def build():
    """Returns (runs, stations, transfers). stations is every stop on the map."""
    runs = [orange()]
    trunk, lechmere, copley, kenmore = green_trunk()
    runs += [trunk, union_square(lechmere), green_b(kenmore), green_d(kenmore), green_e(copley), blue()]
    rd, jfk = red()
    ashmont_run, ashmont = red_ashmont(jfk)
    runs += [rd, ashmont_run, mattapan(ashmont)]

    stations = [s for run in runs for s in run.stops]
    mark_line_ends(runs, stations)
    transfers = {}
    for s in stations:
        if s["transfer"]:
            transfers.setdefault(s["transfer"], []).append(s)
    return runs, stations, transfers


# --- path shapes
def turn_degrees(a, b, c):
    """How far the path turns at b (0 = straight on), in degrees."""
    h1 = math.atan2(b[1] - a[1], b[0] - a[0])
    h2 = math.atan2(c[1] - b[1], c[0] - b[0])
    d = abs(math.degrees(h2 - h1)) % 360
    return min(d, 360 - d)


def corners(run):
    """[(vertex, turn in degrees, tangent length)] for every bend in a run."""
    out = []
    pts = run.pts
    for i in range(1, len(pts) - 1):
        deg = turn_degrees(pts[i - 1], pts[i], pts[i + 1])
        if deg < 1:
            continue
        r = P.RADIUS[min(P.RADIUS, key=lambda k: abs(k - deg))]
        t = r * math.tan(math.radians(deg) / 2)
        t = min(t, 0.48 * math.dist(pts[i - 1], pts[i]), 0.48 * math.dist(pts[i], pts[i + 1]))
        out.append((pts[i], deg, t))
    return out


def svg_path(run):
    """The run as an SVG path with rounded bends."""
    pts = run.pts
    bends = {c[0]: c[2] for c in corners(run)}
    d = "M%.2f %.2f" % pts[0]
    for i in range(1, len(pts)):
        p = pts[i]
        t = bends.get(p) if i < len(pts) - 1 else None
        if not t:
            d += " L%.2f %.2f" % p
            continue
        a, c = pts[i - 1], pts[i + 1]
        la, lc = math.dist(a, p), math.dist(p, c)
        start = (p[0] + (a[0] - p[0]) * t / la, p[1] + (a[1] - p[1]) * t / la)
        end = (p[0] + (c[0] - p[0]) * t / lc, p[1] + (c[1] - p[1]) * t / lc)
        deg = turn_degrees(a, p, c)
        if deg < 100:
            d += " L%.2f %.2f Q%.2f %.2f %.2f %.2f" % (start[0], start[1], p[0], p[1], end[0], end[1])
        else:
            # A quadratic is close enough to a circle on gentle bends, but on the B branch's hairpin
            # it comes out pointed, so sharp bends are drawn as true arcs.
            sweep = 1 if (p[0] - a[0]) * (c[1] - p[1]) - (p[1] - a[1]) * (c[0] - p[0]) > 0 else 0
            r = t / math.tan(math.radians(deg) / 2)
            d += " L%.2f %.2f A%.2f %.2f 0 0 %d %.2f %.2f" % (start[0], start[1], r, r, sweep, end[0], end[1])
    return d


def segments(run):
    return list(zip(run.pts, run.pts[1:]))
