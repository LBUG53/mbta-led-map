"""The 64x32 sign: fonts, drawing, and the rules for countdowns and alerts.

Output is a grid of palette indexes plus a palette, which is what displayio wants.
Rows 1-9 and 11-19 are the two routes, 21-29 the ticker (what goes in it is
decided in app.py). The outer rows and columns sit behind the edge of the window
in the wood, so nothing is drawn there.
"""

W = 64
H = 32
LEFT = 2           # first column used (column 0 is half hidden by the window edge)
RIGHT = 61         # last column used

# Palette indexes. The palette itself is built by palette().
OFF = 0
TIME = 1           # countdown numbers
DIM = 2            # "--" when a row has no times
ALERT = 3          # alert text and icon
RULE = 4           # (unused; kept so the indexes below stay put)
NOTE = 5           # the start-up and error messages
FIRST_ROW_COLOR = 6  # route colors: 6, 7, 8
WHITE = 9            # ticker: clock, weather, and the text after a team's name
SOX = 10             # ticker: team colors
BRUINS = 11
PATS = 12
RIDER = 14           # ticker: the name of someone on their way home (remote.palette sets 13-15)

TIME_RGB = (255, 214, 160)     # warm white, so amber route colors stand apart
DIM_RGB = (150, 136, 120)
ALERT_RGB = (255, 200, 0)      # yellow
# Pure hues: at the sign's low brightness any green in a red turns it orange on the panel.
# The ticker's "white" is the countdowns' warm white: pure white flickered on the
# panel at the sign's low brightness, the warm white doesn't.
TICKER_RGB = (TIME_RGB, (255, 0, 0), (255, 170, 0), (40, 90, 255))   # white, Sox, Bruins, Pats
RULE_RGB = (40, 36, 32)
NOTE_RGB = (200, 190, 175)

# 3 x 5 pixel font ('#' = lit): only a fallback for characters the 6 x 9 font lacks.
FONT = {
    "0": ("###", "#.#", "#.#", "#.#", "###"), "1": (".#.", "##.", ".#.", ".#.", "###"),
    "2": ("###", "..#", "###", "#..", "###"), "3": ("###", "..#", ".##", "..#", "###"),
    "4": ("#.#", "#.#", "###", "..#", "..#"), "5": ("###", "#..", "###", "..#", "###"),
    "6": ("###", "#..", "###", "#.#", "###"), "7": ("###", "..#", ".#.", ".#.", ".#."),
    "8": ("###", "#.#", "###", "#.#", "###"), "9": ("###", "#.#", "###", "..#", "###"),
    "A": (".#.", "#.#", "###", "#.#", "#.#"), "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".##", "#..", "#..", "#..", ".##"), "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"), "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".##", "#..", "#.#", "#.#", ".##"), "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"), "J": ("..#", "..#", "..#", "#.#", ".#."),
    "K": ("#.#", "#.#", "##.", "#.#", "#.#"), "L": ("#..", "#..", "#..", "#..", "###"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#"), "N": ("#..#", "##.#", "#.##", "#..#", "#..#"),
    "O": (".#.", "#.#", "#.#", "#.#", ".#."), "P": ("##.", "#.#", "##.", "#..", "#.."),
    "Q": (".#.", "#.#", "#.#", "##.", ".##"), "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": (".##", "#..", ".#.", "..#", "##."), "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#.#", "#.#", "#.#", "#.#", "###"), "V": ("#.#", "#.#", "#.#", "#.#", ".#."),
    "W": ("#...#", "#...#", "#.#.#", "##.##", "#...#"), "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."), "Z": ("###", "..#", ".#.", "#..", "###"),
    " ": ("..", "..", "..", "..", ".."), ":": (".", "#", ".", "#", "."),
    ".": (".", ".", ".", ".", "#"), ",": (".", ".", ".", "#", "#"),
    "-": ("...", "...", "###", "...", "..."), "+": ("...", ".#.", "###", ".#.", "..."),
    "/": ("..#", "..#", ".#.", "#..", "#.."), "'": ("#", "#", ".", ".", "."),
    "(": (".#", "#.", "#.", "#.", ".#"), ")": ("#.", ".#", ".#", ".#", "#."),
    "!": ("#", "#", "#", ".", "#"), "?": ("##.", "..#", ".#.", "...", ".#."),
    "&": (".#.", "#.#", ".#.", "#.#", ".##"), "%": ("#.#", "..#", ".#.", "#..", "#.#"),
}


# 6 x 9 font (two-pixel stems). Every row uses it.
LARGE = {
    "0": (".####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."),
    "1": ("..##..", ".###..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", ".####."),
    "2": (".####.", "##..##", "....##", "....##", "...##.", "..##..", ".##...", "##....", "######"),
    "3": (".####.", "##..##", "....##", "....##", "..###.", "....##", "....##", "##..##", ".####."),
    "4": ("...##.", "..###.", ".####.", "##.##.", "##.##.", "######", "...##.", "...##.", "...##."),
    "5": ("######", "##....", "##....", "#####.", "....##", "....##", "....##", "##..##", ".####."),
    "6": ("..###.", ".##...", "##....", "#####.", "##..##", "##..##", "##..##", "##..##", ".####."),
    "7": ("######", "....##", "....##", "...##.", "...##.", "..##..", "..##..", "..##..", "..##.."),
    "8": (".####.", "##..##", "##..##", "##..##", ".####.", "##..##", "##..##", "##..##", ".####."),
    "9": (".####.", "##..##", "##..##", "##..##", "##..##", ".#####", "....##", "...##.", ".###.."),
    "A": ("..##..", ".####.", "##..##", "##..##", "##..##", "######", "##..##", "##..##", "##..##"),
    "B": ("#####.", "##..##", "##..##", "##..##", "#####.", "##..##", "##..##", "##..##", "#####."),
    "C": (".####.", "##..##", "##....", "##....", "##....", "##....", "##....", "##..##", ".####."),
    "D": ("####..", "##.##.", "##..##", "##..##", "##..##", "##..##", "##..##", "##.##.", "####.."),
    "E": ("######", "##....", "##....", "##....", "#####.", "##....", "##....", "##....", "######"),
    "F": ("######", "##....", "##....", "##....", "#####.", "##....", "##....", "##....", "##...."),
    "G": (".####.", "##..##", "##....", "##....", "##.###", "##..##", "##..##", "##..##", ".####."),
    "H": ("##..##", "##..##", "##..##", "##..##", "######", "##..##", "##..##", "##..##", "##..##"),
    "I": ("####", ".##.", ".##.", ".##.", ".##.", ".##.", ".##.", ".##.", "####"),
    "J": ("....##", "....##", "....##", "....##", "....##", "....##", "##..##", "##..##", ".####."),
    "K": ("##..##", "##.##.", "##.##.", "####..", "###...", "####..", "##.##.", "##.##.", "##..##"),
    "L": ("##....", "##....", "##....", "##....", "##....", "##....", "##....", "##....", "######"),
    "M": ("##...##", "###.###", "#######", "##.#.##", "##.#.##", "##...##", "##...##", "##...##", "##...##"),
    "N": ("##..##", "###.##", "###.##", "######", "######", "##.###", "##.###", "##..##", "##..##"),
    "O": (".####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."),
    "P": ("#####.", "##..##", "##..##", "##..##", "#####.", "##....", "##....", "##....", "##...."),
    "Q": (".####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##.###", "##.##.", ".###.#"),
    "R": ("#####.", "##..##", "##..##", "##..##", "#####.", "####..", "##.##.", "##.##.", "##..##"),
    "S": (".####.", "##..##", "##....", "###...", ".####.", "...###", "....##", "##..##", ".####."),
    "T": ("######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."),
    "U": ("##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."),
    "V": ("##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####.", ".####.", "..##.."),
    "W": ("##...##", "##...##", "##...##", "##...##", "##.#.##", "##.#.##", "#######", "###.###", "##...##"),
    "X": ("##..##", "##..##", ".####.", ".####.", "..##..", ".####.", ".####.", "##..##", "##..##"),
    "Y": ("##..##", "##..##", "##..##", ".####.", "..##..", "..##..", "..##..", "..##..", "..##.."),
    "Z": ("######", "....##", "...##.", "...##.", "..##..", ".##...", ".##...", "##....", "######"),
    " ": ("...", "...", "...", "...", "...", "...", "...", "...", "..."),
    ":": ("..", "..", "##", "##", "..", "..", "##", "##", ".."),
    ".": ("..", "..", "..", "..", "..", "..", "..", "##", "##"),
    ",": ("..", "..", "..", "..", "..", "..", "##", "##", "#."),
    "-": (".....", ".....", ".....", ".....", "#####", ".....", ".....", ".....", "....."),
    "+": ("......", "......", "..##..", "..##..", "######", "..##..", "..##..", "......", "......"),
    "/": ("....##", "....##", "...##.", "...##.", "..##..", "..##..", ".##...", ".##...", "##...."),
    "'": ("##", "##", "#.", "..", "..", "..", "..", "..", ".."),
    "(": ("..##", ".##.", "##..", "##..", "##..", "##..", "##..", ".##.", "..##"),
    ")": ("##..", ".##.", "..##", "..##", "..##", "..##", "..##", ".##.", "##.."),
    "!": ("##", "##", "##", "##", "##", "##", "..", "##", "##"),
    "?": (".####.", "##..##", "....##", "...##.", "..##..", "..##..", "......", "..##..", "..##.."),
    "&": (".###..", "##.##.", "##.##.", ".###..", ".###.#", "##.###", "##.##.", "##.##.", ".##.##"),
    "%": ("##..##", "##..##", "...##.", "...##.", "..##..", ".##...", ".##...", "##..##", "##..##"),
    "\u00b0": (".##.", "#..#", "#..#", ".##.", "....", "....", "....", "....", "...."),
    "@": (".####.", "##..##", "##.###", "##.###", "##.###", "##.##.", "##....", "##..##", ".####."),
}

# 5 x 5 warning triangle shown beside a scrolling alert.
ALERT_ICON = ("..#..", ".#.#.", ".#.#.", "#...#", "#####")


# --- time
def days_from_civil(y, m, d):
    """Days since 1970-01-01 for a calendar date (no datetime module needed)."""
    y -= m <= 2
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def parse_iso(s):
    """'2026-09-28T17:03:22-04:00' (the MBTA) or '2026-09-28T21:03:22Z' (Adafruit IO) -> seconds since the epoch (UTC)."""
    days = days_from_civil(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    secs = int(s[11:13]) * 3600 + int(s[14:16]) * 60 + int(s[17:19])
    if len(s) < 25:
        return days * 86400 + secs
    sign = -1 if s[19] == "-" else 1
    offset = sign * (int(s[20:22]) * 3600 + int(s[23:25]) * 60)
    return days * 86400 + secs - offset


def countdown(pred, now):
    """Text for one prediction, or None if it can't be boarded.

    Uses the departure time (arrival-only predictions are trips ending here).
    Under a minute shows NOW; over an hour shows 60+.
    """
    if pred.get("schedule_relationship") in ("SKIPPED", "CANCELLED"):
        return None
    t = pred.get("departure_time")
    if not t:
        return None
    secs = parse_iso(t) - now
    if secs < -30:
        return None                     # already gone
    if secs < 60:
        return "NOW"
    mins = secs // 60
    if mins >= 60:
        return "60+"
    return str(mins)


def row_times(preds, now, branch_letter=False, count=2, walk_minutes=0):
    """The next `count` countdowns for a sign row as [time, letter] pairs,
    e.g. [["3", ""], ["12", ""]] or [["NOW", "B"], ["9", "A"]].

    walk_minutes: leave out departures sooner than this, the ones you can't
    catch if you leave now (the times shown still count to the departure)."""
    out = []
    for p in preds:
        if walk_minutes and p.get("departure_time") and parse_iso(p["departure_time"]) - now < walk_minutes * 60:
            continue
        text = countdown(p, now)
        if text is None:
            continue
        letter = ""
        if branch_letter and p.get("headsign"):
            letter = p["headsign"][0].upper()
        out.append([text, letter])
        if len(out) == count:
            break
    return out


# --- alerts
# Alert effects about station facilities rather than riding; never shown.
FACILITY_EFFECTS = ("ELEVATOR_CLOSURE", "ESCALATOR_CLOSURE", "ACCESS_ISSUE", "PARKING_CLOSURE",
                    "PARKING_ISSUE", "BIKE_ISSUE", "FACILITY_ISSUE")


def alert_text(alerts, my_stops, parents, min_severity=3):
    """Text for the alert row: serious alerts on the sign's routes, plus any
    alert that names one of the sign's own stops.

    alerts   list of {"header", "short_header", "effect", "severity", "entities"}
    my_stops dict (used as a set) of the sign rows' stop IDs
    """
    parts = []
    for a in alerts:
        if a.get("effect") in FACILITY_EFFECTS:
            continue
        mine = False
        for e in a.get("entities") or []:
            s = e.get("stop")
            if s and (s in my_stops or parents.get(s, s) in my_stops):
                mine = True
                break
        if mine or (a.get("severity") or 0) >= min_severity:
            text = a.get("short_header") or a.get("header") or ""
            if text:
                parts.append(" ".join(text.split()).upper())
    return "   +   ".join(parts)


# --- drawing
def char_glyph(ch, font=None):
    """The rows of pixels for one character: from `font` if it has it, otherwise from the small fallback font."""
    if font is not None:
        g = font.get(ch.upper())
        if g is not None:
            return g
    return FONT.get(ch.upper(), FONT["?"] if ch.strip() else FONT[" "])


def text_width(s, font=None):
    """Width of a text in pixels, with one empty column between characters."""
    w = 0
    for ch in s:
        w += len(char_glyph(ch, font)[0]) + 1
    return w - 1 if w else 0


def blank():
    return [bytearray(W) for _ in range(H)]


def draw_text(bitmap, x, y, s, color, clip_left=0, clip_right=W - 1, font=None,
              clip_top=0, clip_bottom=H - 1):
    """Draw s with its top-left at (x, y). Returns the x after the text."""
    for ch in s:
        g = char_glyph(ch, font)
        if x + len(g[0]) > clip_left and x <= clip_right:   # skip characters scrolled out of view
            for gy in range(len(g)):
                row = g[gy]
                for gx in range(len(row)):
                    px = x + gx
                    if row[gx] == "#" and clip_left <= px <= clip_right and clip_top <= y + gy <= clip_bottom:
                        bitmap[y + gy][px] = color
        x += len(g[0]) + 1
    return x


# --- layout
BAND_TOP = 21          # the ticker's rows: 21-29
BAND_H = 9
BAND_ALERT_LEFT = 9    # alert text starts here, right of the warning icon


def render_ticker_base(rows):
    """Everything except the ticker: two routes in the 6 x 9 font (rows 1-9 and
    11-19), each with its next two times, "4, 11"."""
    bm = blank()
    for n in range(min(2, len(rows))):
        y = 1 + n * 10
        r = rows[n]
        badge_end = draw_text(bm, LEFT, y, r["badge"], FIRST_ROW_COLOR + n, font=LARGE)
        times = r["times"]
        right = RIGHT + 1
        if not times:
            draw_text(bm, right - text_width("--", LARGE), y, "--", DIM, font=LARGE)
            continue
        comma = text_width(",", LARGE)
        total = 0
        for num, letter in times:
            total += text_width(num, LARGE)
        gap = 3                                 # after each comma; 1 when it's tight (NOW, NOW)
        if right - total - (len(times) - 1) * (comma + 1 + gap) < badge_end + 1:
            gap = 1
        for k in range(len(times) - 1, -1, -1):
            if k < len(times) - 1:
                right -= gap + comma
                draw_text(bm, right, y, ",", TIME, font=LARGE)
                right -= 1
            right -= text_width(times[k][0], LARGE)
            draw_text(bm, right, y, times[k][0], TIME, font=LARGE)
    return bm


def segs_width(segs):
    """Width of a ticker item: a list of [text, color index]."""
    w = 0
    for text, color in segs:
        w += text_width(text, LARGE) + 1
    return w - 1 if w else 0


def ticker_band(base, layers, icon=False):
    """A copy of the base picture with the ticker drawn in.

    layers  list of [segs, x, dy, clip_left]: an item drawn at column x, moved
            down dy rows (negative = up), clipped to the band
    icon    the alert warning triangle at the left
    """
    out = list(base)
    for y in range(BAND_TOP, BAND_TOP + BAND_H):
        out[y] = bytearray(W)
    if icon:
        for gy in range(5):
            for gx in range(5):
                if ALERT_ICON[gy][gx] == "#":
                    out[BAND_TOP + 2 + gy][1 + gx] = ALERT
    for segs, x, dy, left in layers:
        for text, color in segs:
            x = draw_text(out, x, BAND_TOP + dy, text, color, left, RIGHT + 1, LARGE,
                          BAND_TOP, BAND_TOP + BAND_H - 1)
    return out


def palette(row_colors, brightness=1.0, bit_depth=8):
    """Palette of (r, g, b) after brightness scaling and the panel's color depth.

    The Matrix Portal drives the panel with `bit_depth` bits per channel
    (typically 4 to 6), so dim colors come out coarser than 8-bit values suggest.
    """
    base = [(0, 0, 0), TIME_RGB, DIM_RGB, ALERT_RGB, RULE_RGB, NOTE_RGB] + list(row_colors)[:3]
    while len(base) < WHITE:
        base.append((0, 0, 0))
    base += list(TICKER_RGB)
    levels = (1 << bit_depth) - 1
    out = []
    for c in base:
        q = []
        for v in c:
            v = v * brightness
            q.append(int(int(v * levels / 255 + 0.5) * 255 / levels + 0.5))
        out.append((q[0], q[1], q[2]))
    return out
