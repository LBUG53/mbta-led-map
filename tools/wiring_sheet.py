"""Full-size printable wiring sheet (the back of the panel, mirrored), with every pixel's number.

  python tools/wiring_sheet.py      writes data/wiring_back_view.html

Print at 100% on Letter: an overview, then 12 overlapping pages that tile the
panel. Re-run after editing data/wiring_plan.csv.
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim import layout  # noqa: E402

BUILD = layout.load_build()
FACE = BUILD["panel"]["size"]
WALL = BUILD["panel"]["frame_wall"]
SIGN_W, SIGN_H, SIGN_EDGE = BUILD["sign"]["width"], BUILD["sign"]["height"], BUILD["sign"]["edge"]
PAGE_W, PAGE_H = 190.0, 255.0       # printable area of a Letter page with 10 mm margins... and a bit
OVERLAP = 10.0
COLORS = {1: "#1d4ed8", 2: "#c2410c", 3: "#00763a"}   # blue, orange, green: red and orange looked alike printed


def mx(x):
    """Front-view x to back-view x."""
    return FACE - x


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;")


def drawing(stations, wiring):
    """The whole back view as SVG elements, in mm."""
    out = ['<rect x="0" y="0" width="%g" height="%g" fill="#fff" stroke="#000" stroke-width="0.6"/>' % (FACE, FACE)]
    # the opening behind the face (inside the frame walls) and the sign
    out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="none" stroke="#999" stroke-width="0.3" '
               'stroke-dasharray="3 2"/>' % (WALL, WALL, FACE - 2 * WALL, FACE - 2 * WALL))
    sx0, sy0 = FACE - SIGN_EDGE - SIGN_W, FACE - SIGN_EDGE - SIGN_H
    out.append('<rect x="%.2f" y="%.2f" width="%g" height="%g" fill="#eee" stroke="#666" stroke-width="0.4"/>'
               % (mx(sx0 + SIGN_W), sy0, SIGN_W, SIGN_H))
    out.append('<text x="%.1f" y="%.1f" font-size="7" text-anchor="middle" fill="#666">SIGN (back of the LED panel)</text>'
               % (mx(sx0 + SIGN_W / 2), sy0 + SIGN_H / 2 + 3))

    def at(light):
        s = stations[light // 2]
        p = s["B" if light % 2 else "A"]
        return mx(p[0]), p[1]

    # the pairs, with their names
    for s in stations:
        ax, ay = mx(s["A"][0]), s["A"][1]
        bx, by = mx(s["B"][0]), s["B"][1]
        out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#bbb" stroke-width="13.5" '
                   'stroke-linecap="round"/>' % (ax, ay, bx, by))
    for s in stations:
        ax, ay = mx(s["A"][0]), s["A"][1]
        bx, by = mx(s["B"][0]), s["B"][1]
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        if dx < -0.01 or (abs(dx) <= 0.01 and dy < 0):
            ax, ay, bx, by, dx, dy = bx, by, ax, ay, -dx, -dy       # label beyond the right-hand or lower light
        lx, ly = bx + dx * 8.5, by + dy * 8.5
        if abs(dx) > 0.5:
            anchor, ly = "start", ly + 1.0
        else:
            anchor, ly = "middle", ly + 3.0
        out.append('<text x="%.2f" y="%.2f" font-size="2.6" text-anchor="%s" fill="#444">%s %s</text>'
                   % (lx, ly, anchor, s["line"], esc(s["station"])))
    # the wires, then the lights on top
    for output in sorted(wiring):
        color = COLORS.get(output, "#333")
        chain = wiring[output]
        real = [(n, light) for n, light in enumerate(chain) if light >= 0]
        pts = " ".join("%.2f,%.2f" % at(light) for n, light in real)
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="0.7" stroke-opacity="0.8"/>' % (pts, color))
        for k in range(len(real) - 1):              # SKIP pixels: marks along the jump they hang in
            (n0, l0), (n1, l1) = real[k], real[k + 1]
            for j in range(n0 + 1, n1):
                f = (j - n0) / float(n1 - n0)
                x = at(l0)[0] + (at(l1)[0] - at(l0)[0]) * f
                y = at(l0)[1] + (at(l1)[1] - at(l0)[1]) * f
                out.append('<rect x="%.2f" y="%.2f" width="9" height="5" rx="1" fill="#fff" stroke="%s" stroke-width="0.5"/>'
                           % (x - 4.5, y - 2.5, color))
                out.append('<text x="%.2f" y="%.2f" font-size="2.6" text-anchor="middle" fill="%s">skip %d</text>'
                           % (x, y + 0.95, color, j))
        for n, light in real:
            x, y = at(light)
            out.append('<circle cx="%.2f" cy="%.2f" r="6" fill="#fff" stroke="%s" stroke-width="0.6"/>' % (x, y, color))
            out.append('<text x="%.2f" y="%.2f" font-size="4.6" font-weight="bold" text-anchor="middle" fill="%s">%d</text>'
                       % (x, y + 1.65, color, n))
        x, y = at(real[0][1])
        out.append('<text x="%.2f" y="%.2f" font-size="3.4" font-weight="bold" text-anchor="middle" fill="%s">'
                   'OUTPUT %d STARTS</text>' % (x, y + 10.5, color, output))
    out.append('<text x="305" y="20" font-size="9" font-weight="bold" text-anchor="middle">BACK VIEW (mirrored)</text>')
    out.append('<text x="305" y="29" font-size="4.5" text-anchor="middle">number = pixel on its output, counting from 0 '
               'at the controller; output 1 red, 2 orange, 3 green</text>')
    return "\n".join(out)


def html(stations, wiring):
    """The whole sheet as one HTML page: an overview, then the panel cut into full-size pages that overlap."""
    cols = int(math.ceil((FACE - OVERLAP) / (PAGE_W - OVERLAP)))
    rows = int(math.ceil((FACE - OVERLAP) / (PAGE_H - OVERLAP)))
    x0 = (FACE - (PAGE_W + (cols - 1) * (PAGE_W - OVERLAP))) / 2
    y0 = (FACE - (PAGE_H + (rows - 1) * (PAGE_H - OVERLAP))) / 2
    parts = ["""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>MBTA map: wiring, back view</title>
<style>
  @page { size: letter portrait; margin: 10mm; }
  body { margin: 0; font-family: Arial, sans-serif; }
  svg text { font-family: Arial, sans-serif; }
  .page { width: %gmm; height: %gmm; page-break-after: always; break-after: page; position: relative; overflow: hidden; }
  .tag { position: absolute; left: 2mm; top: 1mm; font-size: 9pt; background: #fff; padding: 0 1mm; }
  @media screen { .page { margin: 6mm auto; outline: 1px solid #aaa; } body { background: #ddd; } }
</style></head><body>
<svg width="0" height="0" style="position:absolute"><defs><g id="all">
%s
</g></defs></svg>
""" % (PAGE_W, PAGE_H, drawing(stations, wiring))]
    counts = ", ".join("output %d: %d pixels" % (o, len(wiring[o])) for o in sorted(wiring))
    scale = PAGE_W / FACE
    parts.append('<div class="page"><div class="tag">Overview (not to scale). %s. Pages follow in rows, left to right, '
                 '%d across and %d down.</div><svg width="%gmm" height="%gmm" viewBox="0 -40 %g %g">'
                 '<use href="#all"/></svg></div>' % (counts, cols, rows, PAGE_W, PAGE_H, FACE, PAGE_H / scale))
    for r in range(rows):
        for c in range(cols):
            vx, vy = x0 + c * (PAGE_W - OVERLAP), y0 + r * (PAGE_H - OVERLAP)
            ruler = ('<g transform="translate(%g %g)"><rect x="-2" y="-6" width="104" height="9" fill="#fff"/>'
                     '<line x1="0" y1="0" x2="100" y2="0" stroke="#000" stroke-width="0.4"/>'
                     '<line x1="0" y1="-2" x2="0" y2="2" stroke="#000" stroke-width="0.4"/>'
                     '<line x1="100" y1="-2" x2="100" y2="2" stroke="#000" stroke-width="0.4"/>'
                     '<text x="50" y="-1.5" font-size="3" text-anchor="middle">this line is 100 mm</text></g>'
                     % (vx + 45, vy + PAGE_H - 4))
            parts.append('<div class="page"><div class="tag">Row %d of %d, column %d of %d (back view)</div>'
                         '<svg width="%gmm" height="%gmm" viewBox="%g %g %g %g"><use href="#all"/>%s</svg></div>'
                         % (r + 1, rows, c + 1, cols, PAGE_W, PAGE_H, vx, vy, PAGE_W, PAGE_H, ruler))
    parts.append("</body></html>\n")
    return "\n".join(parts), cols * rows


def main():
    stations = layout.load_stations()
    wiring = layout.load_wiring(stations)
    text, pages = html(stations, wiring)
    path = os.path.join(layout.DATA, "wiring_back_view.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote data/wiring_back_view.html: an overview and %d full-size pages" % pages)


if __name__ == "__main__":
    main()
