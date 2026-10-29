"""The jigsaw template for the sign window: two Letter pages, landscape, that need no trimming.

  python tools/sign_template.py      writes data/sign_window_template.html

Print both pages at 100% ("Actual size"), and check the 100 mm bar. The corner page goes into the
panel's bottom right corner, its paper edges flush with the wood's; the left page lies on top, its
bottom edge on the panel's bottom edge and its right edge on the blue line printed on the corner
page. Cut along the red line from the front. Using it: docs/BUILD.md, step 7.

The window comes from tools/map/params.py, the same numbers the print uses.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "map"))
import params as P  # noqa: E402

OUT = os.path.join(ROOT, "data", "sign_window_template.html")
FONT = "font-family:Arial,Helvetica,sans-serif"
PW, PH = 279.4, 215.9                       # Letter, landscape
EDGE = P.BUILD["panel"]["size"]            # the wood panel (24 in); positions are mm from its top left corner, front view
FRAME = EDGE - P.BUILD["panel"]["frame_wall"]   # the inside of the frame walls
STARTER = 3 / 8 * 25.4                      # the starter holes for the blade: 3/8 in
WIN = (P.SIGN_X0 + P.WINDOW_INSET, P.SIGN_Y0 + P.WINDOW_INSET, P.SIGN_X1 - P.WINDOW_INSET, P.SIGN_Y1 - P.WINDOW_INSET)
TOP = EDGE - PH                             # both pages' top edge, on the panel
CORNER_X0 = EDGE - PW                       # the corner page's left edge
LEFT_X0 = WIN[0] - 21.0                     # the left page's left edge: 21 mm left of the window
LEFT_X1 = LEFT_X0 + PW                      # and its right edge, which lands on the corner page


def scale_bar(x, y):
    """A 100 mm bar with cm ticks, to check the page printed at 100%."""
    out = ['<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#000" stroke-width="0.3"/>' % (x, y, x + 100, y)]
    for k in range(11):
        h = 3 if k % 5 == 0 else 1.5
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#000" stroke-width="0.3"/>' % (x + 10 * k, y, x + 10 * k, y - h))
    out.append('<text x="%g" y="%g" font-size="3" style="%s">100 mm: measure this bar. If it isn\'t 100 mm, print '
               'again at 100%% / Actual size.</text>' % (x, y + 4.5, FONT))
    return "\n".join(out)


def drawing(corner_page):
    out = ['<rect x="%g" y="%g" width="%g" height="%g" fill="#fdecea" stroke="#c00" stroke-width="0.5"/>'
           % (WIN[0], WIN[1], WIN[2] - WIN[0], WIN[3] - WIN[1]),
           '<path d="M%g %g V%g H%g" fill="none" stroke="#888" stroke-width="0.3" stroke-dasharray="2 1.5"/>'
           % (FRAME, TOP, FRAME, LEFT_X0)]
    r = STARTER / 2
    for cx, cy in ((WIN[0] + r + 1, WIN[1] + r + 1), (WIN[2] - r - 1, WIN[1] + r + 1),
                   (WIN[0] + r + 1, WIN[3] - r - 1), (WIN[2] - r - 1, WIN[3] - r - 1)):
        out.append('<circle cx="%g" cy="%g" r="%g" fill="none" stroke="#c00" stroke-width="0.3"/>' % (cx, cy, r))
        out.append('<path d="M%g %g h4 M%g %g v4" stroke="#c00" stroke-width="0.3"/>' % (cx - 2, cy, cx, cy - 2))
    out.append('<text x="%g" y="%g" font-size="3" fill="#666" style="%s">dashed: the inside of the frame walls, '
               'behind the face</text>' % (CORNER_X0 + 12, FRAME - 2, FONT))
    if corner_page:
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#06c" stroke-width="0.5"/>' % (LEFT_X1, TOP + 8, LEFT_X1, EDGE - 8))
        out.append('<text x="%g" y="%g" font-size="3.5" fill="#06c" style="%s" transform="rotate(-90 %g %g)">'
                   'The left page\'s right edge goes on this line</text>'
                   % (LEFT_X1 - 2, WIN[3] - 6, FONT, LEFT_X1 - 2, WIN[3] - 6))
        for k, t in enumerate(("CORNER PAGE", "Push this corner of the paper", "into the panel's bottom right corner.")):
            out.append('<text x="%g" y="%g" font-size="3.5" text-anchor="end" style="%s;font-weight:%d">%s</text>'
                       % (FRAME - 3, EDGE - 16.4 + k * 4.3, FONT, 700 if k == 0 else 400, t))
        out.append('<path d="M%g %g L%g %g L%g %g" fill="none" stroke="#000" stroke-width="0.5"/>'
                   % (EDGE - 7, EDGE - 18, EDGE - 7, EDGE - 7, EDGE - 18, EDGE - 7))
    else:
        lines = ["CUT ALONG THE RED LINE, FROM THE FRONT",
                 "Window %.2f x %.2f mm" % (WIN[2] - WIN[0], WIN[3] - WIN[1]),
                 "Top left corner %.2f mm from the left edge, %.2f mm from the top" % (WIN[0], WIN[1]),
                 "Right and bottom edges %.2f mm from the panel's edges" % (EDGE - WIN[2]),
                 "Drill the four starter holes (3/8 in) inside the corners first.",
                 "Take any pixels near the sign out of their holes before cutting."]
        cy = (WIN[1] + WIN[3]) / 2
        for k, t in enumerate(lines):
            out.append('<text x="%g" y="%g" font-size="%g" style="%s;font-weight:%s" fill="%s">%s</text>'
                       % (WIN[0] + 14, cy - 30 + k * 7, 5 if k == 0 else 3.6, FONT, 700 if k == 0 else 400,
                          "#c00" if k == 0 else "#000", t))
        out.append(scale_bar(WIN[0] + 14, WIN[3] - 14))
        out.append('<text x="%g" y="%g" font-size="3.5" style="%s;font-weight:700">LEFT PAGE: bottom edge of the paper '
                   'on the panel\'s bottom edge</text>' % (LEFT_X0 + 9, EDGE - 9, FONT))
    return "\n".join(out)


def build():
    body = ['<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="%g %g %g %g">%s</svg>'
            % (PW, PH, x0, TOP, PW, PH, drawing(corner)) for x0, corner in ((LEFT_X0, False), (CORNER_X0, True))]
    html = ('<!doctype html><html><head><meta charset="utf-8"><title>Sign window jigsaw template</title>'
            '<style>@page{size:%gmm %gmm;margin:0}html,body{margin:0;padding:0}svg{display:block}</style></head><body>'
            '<div style="page-break-after:always">%s</div>%s</body></html>' % (PW, PH, body[0], body[1]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)


if __name__ == "__main__":
    build()
    print("wrote data/sign_window_template.html: window %.2f x %.2f mm, %.2f mm from the right and bottom edges"
          % (WIN[2] - WIN[0], WIN[3] - WIN[1], EDGE - WIN[2]))
