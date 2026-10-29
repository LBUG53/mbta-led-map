"""Draw the print as an SVG in named layers."""
import params as P
import layout


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg(runs, stations, transfers, outline=False, layers=None, attrs=None):
    """layers: extra layer content by name, e.g. {"labels": [...svg lines...]};
    attrs: attributes for those layers' <g> elements."""
    layers = layers or {}
    attrs = attrs or {}
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="0 0 %g %g">'
           % (P.FACE, P.FACE, P.FACE, P.FACE)]

    def layer(name, content, extra=""):
        out.append('<g id="%s"%s>' % (name, extra))
        out.extend(content)
        out.append("</g>")

    layer("background", ['<rect width="%g" height="%g" fill="%s"/>' % (P.FACE, P.FACE, P.BACKGROUND)])
    layer("water", layers.get("water", []), attrs.get("water", ""))
    layer("lines", ['<path d="%s" stroke="%s"><title>%s</title></path>' % (layout.svg_path(r), P.COLORS[r.line],
                                                                         esc(r.branch)) for r in runs],
          ' fill="none" stroke-width="%g" stroke-linecap="round" stroke-linejoin="round"' % P.LINE_WIDTH)

    # Every other station is a white dot inside the line, as on the MBTA's map. It stays inside the
    # line, so no ink lands over the light holes 7 mm either side.
    dots = ['<circle cx="%.2f" cy="%.2f" r="%g"><title>%s</title></circle>'
            % (s["x"], s["y"], P.STATION_DOT / 2, esc(s["line"] + " " + s["name"]))
            for s in stations if not (s["transfer"] or s["terminus"])]
    layer("stations", dots, ' fill="#FFFFFF"')

    inter = []
    for name, group in transfers.items():
        a, b = group[0], group[1]
        for width, color in ((P.CONNECTOR_W, P.INK), (P.CONNECTOR_CORE, "#FFFFFF")):
            inter.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="%g"/>'
                         % (a["x"], a["y"], b["x"], b["y"], color, width))
    for name, group in transfers.items():
        for s in group:
            inter.append('<circle cx="%.2f" cy="%.2f" r="%g" fill="#FFFFFF" stroke="%s" stroke-width="%g">'
                         '<title>%s</title></circle>'
                         % (s["x"], s["y"], (P.CIRCLE_D - P.CIRCLE_STROKE) / 2, P.INK, P.CIRCLE_STROKE,
                            esc(s["line"] + " " + s["name"])))
    layer("interchanges", inter, ' stroke-linecap="round"')
    # The end of a line, drawn as the MBTA's map draws it: a white circle ringed in the line's color.
    ends = ['<circle cx="%.2f" cy="%.2f" r="%g" stroke="%s"><title>%s</title></circle>'
            % (s["x"], s["y"], (P.CIRCLE_D - P.TERMINUS_STROKE) / 2, P.COLORS[s["line"]], esc(s["line"] + " " + s["name"]))
            for s in stations if s["terminus"]]
    layer("termini", ends, ' fill="#FFFFFF" stroke-width="%g"' % P.TERMINUS_STROKE)

    for name in ("labels-halo", "labels", "title", "branch-tags", "sign-caption", "credit"):
        layer(name, layers.get(name, []), attrs.get(name, ""))

    w = P.WINDOW_INSET
    cut = ['<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#0E0E0E"/>'
           % (P.SIGN_X0 + w, P.SIGN_Y0 + w, P.SIGN_W - 2 * w, P.SIGN_H - 2 * w)]
    if outline:
        o = 3.0
        cut.insert(0, '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="#A6A7A7" '
                      'stroke-width="0.5"/>' % (P.SIGN_X0 + w - o, P.SIGN_Y0 + w - o, P.SIGN_W - 2 * w + 2 * o,
                                                P.SIGN_H - 2 * w + 2 * o))
    layer("sign-window-cut", cut)

    out.append("</svg>")
    return "\n".join(out)
