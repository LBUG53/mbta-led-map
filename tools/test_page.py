"""A test page of the print: downtown at full size on one Letter page.

  python tools/test_page.py      writes data/test_page.html

Print it at 100% ("Actual size") and check the 100 mm bar, then judge the label sizes, the colors
and how the lights glow through paper, before paying for the full print. Hold it over a few holes
with the map running.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRINT = os.path.join(ROOT, "data", "print_no_outline.svg")
OUT = os.path.join(ROOT, "data", "test_page.html")
FONT = "font-family:Arial,Helvetica,sans-serif"
AREA = (305.0, 172.0, 195.9, 250.0)     # x, y, width, height on the print: downtown, the Orange Line's labels, Mattapan, DEPARTURES


def scale_bar(x, y):
    """A 100 mm bar with cm ticks, to check the page printed at 100%."""
    out = ['<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#000" stroke-width="0.3"/>' % (x, y, x + 100, y)]
    for k in range(11):
        h = 3 if k % 5 == 0 else 1.5
        out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#000" stroke-width="0.3"/>' % (x + 10 * k, y, x + 10 * k, y - h))
    out.append('<text x="%g" y="%g" font-size="3" style="%s">100 mm: measure this bar. If it isn\'t 100 mm, print '
               'again at 100%% / Actual size.</text>' % (x, y + 4.5, FONT))
    return "\n".join(out)


def build():
    with open(PRINT, encoding="utf-8") as f:
        svg = f.read()
    inner = svg.split(">", 1)[1].rsplit("</svg>", 1)[0]
    x0, y0, w, h = AREA
    page = ['<svg xmlns="http://www.w3.org/2000/svg" width="215.9mm" height="279.4mm" viewBox="0 0 215.9 279.4">',
            '<text x="10" y="9" font-size="4" font-weight="700" style="%s">MBTA map: test page, actual size</text>' % FONT,
            '<svg x="10" y="12" width="%g" height="%g" viewBox="%g %g %g %g">%s</svg>' % (w, h, x0, y0, w, h, inner),
            '<rect x="10" y="12" width="%g" height="%g" fill="none" stroke="#999" stroke-width="0.2"/>' % (w, h),
            scale_bar(10, 268), "</svg>"]
    html = ('<!doctype html><html><head><meta charset="utf-8"><title>Print test page</title>'
            '<style>@page{size:215.9mm 279.4mm;margin:0}html,body{margin:0;padding:0}svg{display:block}</style>'
            '</head><body>%s</body></html>' % "\n".join(page))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)


if __name__ == "__main__":
    build()
    print("wrote data/test_page.html")
