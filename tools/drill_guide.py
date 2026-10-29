"""Full-size drilling guide for the back of the panel (mirrored), with a cross at every hole.

  python tools/drill_guide.py                    the whole opening
  python tools/drill_guide.py 20 20 589.6 589.6  or an area: x0 y0 x1 y1, mm on the front

Writes the same guide two ways: one sheet (data/drill_guide_back.svg) for a
print shop, and Letter pages to tape together (data/drill_guide_back_pages.html). The sheet is cut to the opening inside the frame, so it drops in and
the frame lines it up. Using it: docs/BUILD.md, step 7.
"""
import csv
import os
import re
import sys

import yaml

# Light A of each of these is a reference hole: they're the tiles' locating collars (make_tile.py prints them).
LOCATING = {("GL", "Cleveland Circle"), ("GL", "Brigham Circle"), ("GL", "Medford/Tufts"), ("GL", "Coolidge Corner"),
            ("OL", "Oak Grove"), ("RL", "Braintree")}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
with open(os.path.join(ROOT, "build.yaml"), encoding="utf-8") as f:
    BUILD = yaml.safe_load(f)               # the measured sizes of this build
PANEL = BUILD["panel"]["size"]      # the panel's outside, mm (24 in)
FRAME = BUILD["panel"]["frame_wall"]    # how wide the frame's walls are, measured
AREA = (FRAME, FRAME, PANEL - FRAME, PANEL - FRAME)     # the part of the front the sheet covers: the opening
HOLE = BUILD["panel"]["hole"]       # the finished hole, 1/4 in
EDGE_ROOM = 3.5                     # a light's center must be at least this far inside the sheet
GRID = 50                           # faint lines this far apart, for checking the scale and joining pages
PAGE_W, PAGE_H = 195.0, 252.0       # what fits on a Letter page inside 10 mm margins, with a line of text under it
MIN_OVERLAP = 6.0                   # neighboring pages share at least this much
LETTER_W, LETTER_H = 215.9, 279.4   # a US Letter page, mm
COLORS = {"RL": "#DA291C", "M": "#DA291C", "OL": "#ED8B00", "BL": "#003DA5", "GL": "#00843D"}
FONT = 'font-family="Arial, Helvetica, sans-serif"'


def load_stations():
    out = []
    with open(os.path.join(DATA, "stations.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append({"line": r["line"], "name": r["station"],
                        "A": (float(r["light_A_x"]), float(r["light_A_y"])),
                        "B": (float(r["light_B_x"]), float(r["light_B_y"]))})
    return out


def sign_window():
    """The window to cut for the sign, (x0, y0, x1, y1) in front-of-panel mm, from the print."""
    with open(os.path.join(DATA, "print_no_outline.svg"), encoding="utf-8") as f:
        m = re.search(r'<g id="sign-window-cut">\s*<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" '
                      r'height="([\d.]+)"', f.read())
    x, y, w, h = (float(v) for v in m.groups())
    return (x, y, x + w, y + h)


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;")


def sheet(area=AREA):
    """The guide for an area of the front, as the inside of an SVG in sheet millimeters. Returns
    (SVG elements as text, the reference holes, the number of lights); a reference hole is
    (station name, x from the front's left edge, y from the top)."""
    x0, y0, x1, y1 = area
    w, h = x1 - x0, y1 - y0

    def at(p):
        """Front-of-panel mm to a place on the sheet: mirrored left to right."""
        return (x1 - p[0], p[1] - y0)

    names, bars, holes, rings, refs = [], [], [], [], []
    count = 0
    for s in load_stations():
        inside = [k for k in ("A", "B") if x0 <= s[k][0] <= x1 and y0 <= s[k][1] <= y1]
        if not inside:
            continue
        for k in inside:
            if min(s[k][0] - x0, x1 - s[k][0], s[k][1] - y0, y1 - s[k][1]) < EDGE_ROOM:
                sys.exit("%s %s light %s is at the edge of the sheet: choose a bigger area" % (s["line"], s["name"], k))
        a, b = at(s["A"]), at(s["B"])
        if len(inside) == 2:        # a thin bar in the line's color joins a station's two holes
            bars.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.35"/>'
                        % (a[0], a[1], b[0], b[1], COLORS[s["line"]]))
        # The name goes beside the pair, a little way along the line (at right angles to the two holes),
        # on whichever side is lower on the sheet, so it stays clear of both holes.
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ux, uy = (b[1] - a[1]) / 14.0, (a[0] - b[0]) / 14.0
        if uy < -0.1 or (abs(uy) <= 0.1 and ux < 0):
            ux, uy = -ux, -uy
        anchor = "middle" if abs(ux) < 0.3 else ("start" if ux > 0 else "end")
        names.append('<text x="%.2f" y="%.2f" text-anchor="%s">%s</text>'
                     % (mx + ux * 5.0, my + uy * 5.0 + (1.8 if uy > 0.3 else 0.8), anchor, esc(s["name"])))
        for k in inside:
            x, y = at(s[k])
            count += 1
            holes.append('<circle cx="%.2f" cy="%.2f" r="%.3f"/><path d="M%.2f %.2f h5 M%.2f %.2f v5"/>'
                         % (x, y, HOLE / 2, x - 2.5, y, x, y - 2.5))
            if k == "A" and (s["line"], s["name"]) in LOCATING:
                refs.append((s["name"], s[k][0], s[k][1]))
                rings.append('<circle cx="%.2f" cy="%.2f" r="6.5"/>' % (x, y))
                label_y = y - 7.6 if y > 14 else y + 10.6       # under the ring when it is at the top edge
                rings.append('<text x="%.2f" y="%.2f" text-anchor="middle">REF %d</text>' % (x, label_y, len(refs)))

    # Ticks every 10 mm round the edge, numbered every 50 with the distance on the FRONT of the panel,
    # and a faint line right across at every 50.
    ticks, numbers, grid = [], [], []
    first = int(-(-x0 // 10) * 10)
    for v in range(first, int(x1) + 1, 10):
        x, long = x1 - v, v % GRID == 0
        if long and 0 < x < w:
            grid.append("M%.2f 0 V%.2f" % (x, h))
        for y, d in ((0, 1), (h, -1)):
            ticks.append("M%.2f %.2f v%.1f" % (x, y, d * (3.0 if long else 1.5)))
        if long and 6 < x < w - 6:
            numbers.append('<text x="%.2f" y="6" text-anchor="middle">%d</text>' % (x, v))
            numbers.append('<text x="%.2f" y="%.2f" text-anchor="middle">%d</text>' % (x, h - 4.2, v))
    first = int(-(-y0 // 10) * 10)
    for v in range(first, int(y1) + 1, 10):
        y, long = v - y0, v % GRID == 0
        if long and 0 < y < h:
            grid.append("M0 %.2f H%.2f" % (y, w))
        for x, d in ((0, 1), (w, -1)):
            ticks.append("M%.2f %.2f h%.1f" % (x, y, d * (3.0 if long else 1.5)))
        if long and 6 < y < h - 6:
            numbers.append('<text x="4" y="%.2f">%d</text>' % (y + 0.9, v))
            numbers.append('<text x="%.2f" y="%.2f" text-anchor="end">%d</text>' % (w - 4, y + 0.9, v))

    # The sign window, and the notes written inside it (it is cut out, so nothing else is there).
    win = sign_window()
    wx, wy = at((win[2], win[1]))                      # its top-left corner as seen from behind
    ww, wh = win[2] - win[0], win[3] - win[1]
    notes = [
        ("7", "bold", "DRILL GUIDE: THE BACK OF THE PANEL"),
        ("4", "", "This side faces you, inside the cradle. Left and right are swapped compared with the map."),
        ("4", "", "The sheet is the size of the opening: %g x %g mm. Its edges go against the frame." % (w, h)),
        ("4", "bold", "TOP of the panel is toward the top of this sheet."),
        ("4", "", ""),
        ("4", "bold", "1. Check the scale before drilling."),
        ("4", "", "Edge ticks are 10 mm apart, faint lines 50 mm. From the line marked 50 to the line marked 550"),
        ("4", "", "must be 500.0 mm, across and down. The numbers are mm on the FRONT: from its left edge, and from the top."),
        ("4", "", ""),
        ("4", "bold", "2. If the sheet is loose in the frame, pin it through reference holes drilled from the FRONT:"),
    ]
    for n, (name, x, y) in enumerate(refs):
        notes.append(("4", "", "   REF %d   %s, light A:   %.1f mm from the front's left edge,   %.1f mm from the top"
                      % (n + 1, name, x, y)))
    notes += [
        ("4", "", ""),
        ("4", "", "+ is the center of a hole. The circle is the finished 1/4 in (6.35 mm) hole. %d holes." % count),
        ("4", "", "This rectangle is the sign window, %.2f x %.2f mm: cut it out of the wood." % (ww, wh)),
    ]
    lines, y = [], wy + 14
    for size, weight, text in notes:
        lines.append('<text x="%.2f" y="%.2f" font-size="%s"%s>%s</text>'
                     % (wx + 8, y, size, ' font-weight="bold"' if weight else "", esc(text)))
        y += float(size) * 1.7
    window = ('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="#000" stroke-width="0.3" '
              'stroke-dasharray="4 2"/>' % (wx, wy, ww, wh)) if x0 <= win[0] and win[2] <= x1 else ""

    inner = "\n".join([
        '<rect width="%g" height="%g" fill="#fff" stroke="#000" stroke-width="0.3"/>' % (w, h),
        '<path d="%s" stroke="#9cc3e6" stroke-width="0.15" fill="none"/>' % " ".join(grid),
        '<g fill="#8a8a8a" font-size="2.3">', "\n".join(names), "</g>",
        "\n".join(bars),
        window,
        '<g fill="#000">', "\n".join(lines) if window else "", "</g>",
        '<path d="%s" stroke="#000" stroke-width="0.25" fill="none"/>' % " ".join(ticks),
        '<g fill="#000" font-size="2.6">', "\n".join(numbers), "</g>",
        '<g fill="none" stroke="#000" stroke-width="0.2">', "\n".join(holes), "</g>",
        '<g fill="none" stroke="#000" stroke-width="0.5" font-size="3.2" font-weight="bold">',
        "\n".join(r if r.startswith("<circle") else r.replace("<text ", '<text fill="#000" stroke="none" ') for r in rings),
        "</g>"])
    return inner, refs, count


def build(area=AREA):
    """The guide as one SVG at actual size. Returns (the SVG as text, the reference holes, the number of lights)."""
    w, h = area[2] - area[0], area[3] - area[1]
    inner, refs, count = sheet(area)
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="0 0 %g %g" %s>\n%s\n</svg>\n' % (
        w, h, w, h, FONT, inner)
    return svg, refs, count


def page_starts(length, page):
    """Where each page begins along one side of the sheet: as few pages as cover it, spread evenly,
    the first and last flush with the sheet's edges."""
    n = 1
    while page + (n - 1) * (page - MIN_OVERLAP) < length:
        n += 1
    if n == 1:
        return [0.0]
    return [k * (length - page) / (n - 1) for k in range(n)]


def pages(area=AREA):
    """The guide cut into Letter pages. Returns (the HTML as text, columns, rows)."""
    w, h = area[2] - area[0], area[3] - area[1]
    inner, refs, count = sheet(area)
    xs, ys = page_starts(w, PAGE_W), page_starts(h, PAGE_H)
    out = ["""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Drill guide, back view: pages</title>
<style>
  @page { size: letter portrait; margin: 10mm; }
  body { margin: 0; font: 3mm Arial, Helvetica, sans-serif; }
  .page { width: %gmm; page-break-after: always; break-after: page; }
  .page svg { display: block; }
  .page p { margin: 1mm 0 0; height: 4mm; overflow: hidden; white-space: nowrap; }
</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute"><defs><g id="sheet" %s>
%s
</g></defs></svg>""" % (PAGE_W, FONT, inner)]
    for r, py in enumerate(ys):
        for c, px in enumerate(xs):
            pw, ph = min(PAGE_W, w - px), min(PAGE_H, h - py)
            out.append('<div class="page"><svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" '
                       'viewBox="%.2f %.2f %g %g"><use href="#sheet"/></svg>'
                       '<p><b>Row %d of %d, column %d of %d</b>, seen from behind. Print at 100%%. '
                       'Join pages on the blue lines.</p></div>'
                       % (pw, ph, px, py, pw, ph, r + 1, len(ys), c + 1, len(xs)))
    out.append("</body></html>\n")
    return "\n".join(out), len(xs), len(ys)


def main():
    args = sys.argv[1:]
    area = tuple(float(v) for v in args[:4]) if len(args) >= 4 else AREA
    svg, refs, count = build(area)
    path = os.path.join(DATA, "drill_guide_back.svg")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print("wrote data/drill_guide_back.svg: %.1f x %.1f mm, %d holes, the panel seen from behind"
          % (area[2] - area[0], area[3] - area[1], count))
    html, cols, rows = pages(area)
    with open(os.path.join(DATA, "drill_guide_back_pages.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("wrote data/drill_guide_back_pages.html: the same on %d Letter pages (%d across, %d down), %g x %g mm of "
          "the guide on each" % (cols * rows, cols, rows, PAGE_W, PAGE_H))
    print("reference holes (light A), measured on the FRONT of the panel:")
    for n, (name, x, y) in enumerate(refs):
        print("  REF %d  %-18s %6.1f mm from the left edge, %6.1f mm from the top" % (n + 1, name, x, y))


if __name__ == "__main__":
    main()
