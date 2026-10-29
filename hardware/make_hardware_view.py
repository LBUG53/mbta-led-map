r"""The back of the panel with the hardware on it: which tile is which, where the tiles join, and where
the boards, power parts and zip ties go. Not the pixel numbering; that is data/wiring_back_view.html.

  python make_hardware_view.py     writes data/hardware_back_view.html

Drawn from the same data as the tiles (make_tile.py), so the tiles, joints, glue tabs and locating collars
are exactly where they print. The boards and power parts are a PROPOSED arrangement: change PLACES below.
Everything is mirrored left to right, because that is how the panel looks from behind.
"""
import math
import os

import yaml

import make_tile as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "build.yaml"), encoding="utf-8") as f:
    BUILD = yaml.safe_load(f)               # the measured sizes of this build
FACE = BUILD["panel"]["size"]
WALL = BUILD["panel"]["frame_wall"]          # the frame's side walls (the map was drawn for up to 38.1)
SIGN = (259.9, 419.3, 577.9, 577.3)          # the LED panel (318 x 158), front view x0, y0, x1, y1
COLORS = {"lower_left": ("#0f766e", "#ccebe7"), "upper_left": ("#1d4ed8", "#d4e0fb"), "upper_right": ("#7e22ce", "#ead9f8")}
NAMES = {"lower_left": "LOWER-LEFT TILE", "upper_left": "UPPER-LEFT TILE", "upper_right": "UPPER-RIGHT TILE"}
TIE = "#ea580c"

# Places, front view: center x, center y, width, height (mm), as the part lies on the wood. The Sparkle Motion
# is in the bottom lane because that gave the shortest leads to the three chain starts.
PLACES = {
    "portal": (227.0, 485.0, 63.5, 44.5),    # Matrix Portal S3 on its peg cradle, turned so its ribbon header faces the sign
    "sparkle": (201.0, 563.0, 82.8, 37.0),   # Sparkle Motion on its tray, outputs facing up
    "nut5": (193.0, 519.5, 30.0, 12.0),      # lever nut, +5 V, on a zip-tie anchor
    "nutg": (193.0, 534.5, 30.0, 12.0),      # lever nut, ground
    "jack": (225.0, 534.5, 30.0, 12.0),      # barrel-jack adapter on a zip-tie anchor
}
PORTAL_TURN = 1                              # quarter turns from the part's own plan (header up, USB-C down)
SPARKLE_TURN = 2
TERMINALS = [(-41.0 + 12.0 * k, 18.5) for k in (1, 2, 3)]   # the Sparkle Motion's three outputs: (along, across) from its centre
HEADER = (0.0, -26.0)                        # the Matrix Portal's ribbon header, from its centre
USB = (15.0, 31.7)                           # and its USB-C port
CRADLE_OUT = 3.3                             # the sign's cradle stands this far outside the panel (0.3 mm slack, 3 mm wall)
HUB = (SIGN[0] + 12.0, 486.0)                # the sign's data socket, on the edge beside the boards
SIGN_POWER = (SIGN[0] + 150.0, 486.0)        # where the sign's power cable comes out


def cable_lane():
    """The lane between the Sparkle Motion's end and the sign's cradle: (x of its pigtail, x of the supply cable, width)."""
    end = PLACES["sparkle"][0] + PLACES["sparkle"][2] / 2
    gap = SIGN[0] - CRADLE_OUT - end
    return end + gap * 0.2, end + gap * 0.6, gap


def turn(local, center, quarter):
    """A point given relative to a part's centre, with the part turned by `quarter` quarter-turns."""
    u, v = local
    c, s = [(1, 0), (0, 1), (-1, 0), (0, -1)][quarter % 4]
    return (center[0] + u * c - v * s, center[1] + u * s + v * c)


def X(x):
    """Front-view x to back-view x."""
    return FACE - x


def front(p):
    """A point in the tile's coordinates to front-view mm."""
    return (-p[0], -p[1])


def rect(x0, y0, x1, y1, extra):
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" %s/>' % (X(x1), y0, x1 - x0, y1 - y0, extra)


def box(place):
    """(x0, y0, x1, y1) of a part placed by its centre, width and height."""
    cx, cy, w, h = place
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def text(x, y, s, size=3.2, extra=""):
    return '<text x="%.1f" y="%.1f" font-size="%g" text-anchor="middle" %s>%s</text>' % (X(x), y, size, extra, s)


def line(points, extra):
    return '<polyline points="%s" fill="none" %s/>' % (" ".join("%.1f,%.1f" % (X(x), y) for x, y in points), extra)


def obstacles(plans, joints):
    """What is in the way of a board or a block on the wood, for finding room for the small parts: the
    collars, ribs and joints of the tiles, as (a, b, radius) segments in front-view mm, each with a margin."""
    solid = []
    for me in plans.values():
        solid += [(front(s["a"]), front(s["b"]), T.RADIUS + 3.0) for s in me["stations"]]
        solid += [(front(a), front(b), T.RIB_WIDTH / 2 + 1.0) for a, b in me["ribs"]]
    solid += [(front(f["a"]), front(f["b"]), T.SOCKET + 1.0) for f in joints]
    return solid


def tabs_and_marks(plans, joints, credit):
    """Each tile's glue tabs and its locating collars."""
    tabs, marks = {}, {}
    for tile, me in plans.items():
        mark = credit[1] if credit and credit[0] == tile else None
        tabs[tile] = T.pick_tabs(me["stations"], me["edges"], me["plates"] + ([{"rect": mark}] if mark else []),
                                 [plans[t] for t in plans if t != tile], joints)
        marks[tile] = T.locating(me["stations"])
    return tabs, marks


def nearest_room_finder(solid, boxes):
    """nearest_room(x, y, r): the closest spot to (x, y) where a circle of radius r clears the frame, the boxes
    (a list that may grow afterwards) and the tiles."""
    def room(x, y, r):
        if not (WALL + r <= x <= FACE - WALL - r and WALL + r <= y <= FACE - WALL - r):
            return False
        if any(b[0] - r < x < b[2] + r and b[1] - r < y < b[3] + r for b in boxes):
            return False
        return all(T.point_to_segment((x, y), a, b) >= rad + r for a, b, rad in solid)

    def nearest_room(x, y, r):
        for d in range(0, 80, 2):
            for k in range(24):
                px, py = x + d * math.cos(k * math.pi / 12), y + d * math.sin(k * math.pi / 12)
                if room(px, py, r):
                    return px, py
        return x, y
    return nearest_room


def frame_svg():
    return ['<rect x="0" y="0" width="%.1f" height="%.1f" fill="#f3efe6" stroke="#333" stroke-width="0.8"/>' % (FACE, FACE),
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#fffdf8" stroke="#8a7f70" stroke-width="0.5" '
            'stroke-dasharray="4 2"/>' % (WALL, WALL, FACE - 2 * WALL, FACE - 2 * WALL),
            text(FACE / 2, WALL / 2 + 2, "WOOD FRAME (%.0f mm wide, measured)" % WALL, 6.5, 'fill="#6b6257"')]


def tiles_svg(plans, tabs, marks, credit, joints):
    """The three tiles: ribs, glue tabs, collars, locating rings, the credit plate and the joints."""
    o = []
    for tile, me in plans.items():
        dark, light = COLORS[tile]
        for a, b in me["ribs"]:
            o.append(line([front(a), front(b)], 'stroke="%s" stroke-width="%g" stroke-opacity="0.45"' % (dark, T.RIB_WIDTH)))
        for t in tabs[tile]:
            x, y = front(t)
            o.append('<circle cx="%.1f" cy="%.1f" r="%g" fill="#fff" stroke="%s" stroke-width="0.7"/>'
                     '<circle cx="%.1f" cy="%.1f" r="1.4" fill="%s"/>' % (X(x), y, T.TAB_RADIUS, dark, X(x), y, dark))
        for s in me["stations"]:
            o.append(line([front(s["a"]), front(s["b"])],
                          'stroke="%s" stroke-width="%g" stroke-linecap="round"' % (dark, 2 * T.RADIUS)))
            for p in (s["a"], s["b"]):
                x, y = front(p)
                o.append('<circle cx="%.1f" cy="%.1f" r="%g" fill="%s"/>' % (X(x), y, T.BORE / 2, light))
        for s in marks[tile]:
            x, y = front(s["a"])
            o.append('<circle cx="%.1f" cy="%.1f" r="9.5" fill="none" stroke="#111" stroke-width="1.1"/>' % (X(x), y))
            o.append('<path d="M%.1f %.1f h9 M%.1f %.1f v9" stroke="#111" stroke-width="0.9"/>'
                     % (X(x) - 4.5, y, X(x), y - 4.5))
    if credit:
        r = [-credit[1][2], -credit[1][3], -credit[1][0], -credit[1][1]]
        o.append(rect(r[0], r[1], r[2], r[3], 'fill="#fff" stroke="%s" stroke-width="0.5"' % COLORS[credit[0]][0]))
        o.append(text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2 + 1.3, T.CREDIT, 4.4, 'fill="%s" font-weight="bold"' % COLORS[credit[0]][0]))
    for i, f in enumerate(joints):
        jx, jy = front(f["j"])
        o.append(line([front(f["a"]), (jx, jy)], 'stroke="%s" stroke-width="%g"' % (COLORS[f["knob"]][0], T.RIB_WIDTH)))
        o.append(line([front(f["b"]), (jx, jy)], 'stroke="%s" stroke-width="%g"' % (COLORS[f["socket"]][0], T.RIB_WIDTH)))
        o.append('<circle cx="%.1f" cy="%.1f" r="%g" fill="#fff" stroke="%s" stroke-width="2.6"/>'
                 % (X(jx), jy, T.SOCKET - 1.3, COLORS[f["socket"]][0]))
        o.append('<circle cx="%.1f" cy="%.1f" r="%g" fill="%s"/>' % (X(jx), jy, T.KNOB, COLORS[f["knob"]][0]))
        o.append('<circle cx="%.1f" cy="%.1f" r="12" fill="none" stroke="#dc2626" stroke-width="0.9" stroke-dasharray="2.5 1.5"/>'
                 % (X(jx), jy))
        o.append(text(jx, jy - 14, "JOINT %s" % "ABCD"[i], 6.5, 'fill="#dc2626" font-weight="bold"'))
    return o


def sign_svg():
    return [rect(SIGN[0], SIGN[1], SIGN[2], SIGN[3], 'fill="#2b2b2b" stroke="#000" stroke-width="0.6"'),
            text((SIGN[0] + SIGN[2]) / 2, SIGN[1] + 60, "SIGN: back of the 64 x 32 LED panel", 9, 'fill="#eee" font-weight="bold"'),
            text((SIGN[0] + SIGN[2]) / 2, SIGN[1] + 72, "%g x %g x %g mm, face against the wood" % (
                BUILD["sign"]["width"], BUILD["sign"]["height"], BUILD["sign"]["thickness"]), 5.5, 'fill="#ccc"')]


def tie(x0, y0, x1, y1):
    return line([(x0, y0), (x1, y1)], 'stroke="%s" stroke-width="2.2" stroke-linecap="round"' % TIE)


def part(key, label, sub, fill, size=5.0):
    """A board or block as SVG elements, and its box."""
    b = box(PLACES[key])
    o = [rect(b[0], b[1], b[2], b[3], 'fill="%s" stroke="#111" stroke-width="0.6"' % fill),
         text(PLACES[key][0], PLACES[key][1] - (2.5 if sub else -1.6), label, size, 'font-weight="bold"')]
    if sub:
        o.append(text(PLACES[key][0], PLACES[key][1] + 4.5, sub, size, 'font-weight="bold"'))
    return o, b


def boards_svg():
    """The wires first (ribbon, power, the pigtail, the supply cable, the USB-C lead), then the boards and blocks."""
    o = []
    px, py = PLACES["portal"][:2]
    sx, sy = PLACES["sparkle"][:2]
    header = turn(HEADER, (px, py), PORTAL_TURN)
    usb = turn(USB, (px, py), PORTAL_TURN)
    o.append(line([header, HUB], 'stroke="#9ca3af" stroke-width="9" stroke-opacity="0.85" stroke-linejoin="round"'))
    o.append(text(HUB[0] + 28, HUB[1] + 2, "ribbon to the sign", 5, 'fill="#ddd" font-weight="bold"'))
    n5, ng, jk = PLACES["nut5"], PLACES["nutg"], PLACES["jack"]
    o.append(line([(n5[0] + 15, n5[1]), (SIGN_POWER[0], n5[1]), SIGN_POWER], 'stroke="#dc2626" stroke-width="1.4"'))
    o.append(line([(ng[0] + 15, ng[1]), (SIGN_POWER[0] + 4, ng[1]), (SIGN_POWER[0] + 4, SIGN_POWER[1])], 'stroke="#111" stroke-width="1.4"'))
    o.append(text(SIGN_POWER[0] + 2, 512, "sign power", 5.5, 'fill="#eee"'))
    lane, out_x, _ = cable_lane()                                 # the Sparkle Motion's pigtail, and the supply cable coming in through the frame
    o.append(line([(ng[0] + 15, ng[1] + 6), (ng[0] + 15, ng[1] + 8), (lane, ng[1] + 8), (lane, sy)], 'stroke="#dc2626" stroke-width="1.2" stroke-dasharray="4 2"'))
    o.append(line([(out_x, FACE - 4), (out_x, jk[1]), (jk[0] + 15, jk[1])], 'stroke="#111" stroke-width="2.4"'))
    o.append(text(out_x + 14, FACE - 22, "POWER CABLE IN (5 V, 10 A supply)", 5, 'font-weight="bold"'))
    o.append(line([usb, (usb[0], n5[1] - 6)], 'stroke="#2563eb" stroke-width="1.6"'))
    o.append(text(usb[0] - 3, usb[1] + 8, "USB-C lead", 4.2, 'fill="#2563eb" font-weight="bold"'))

    o += part("portal", "MATRIX", "PORTAL", "#e5e7eb")[0]
    o.append(tie(px, py - 25, px, py + 25))
    o += part("sparkle", "SPARKLE MOTION", "(light controller)", "#e5e7eb", 4.4)[0]
    o.append(tie(sx, sy - 21, sx, sy + 21))
    for key, label in (("nut5", "+5 V"), ("nutg", "GND"), ("jack", "JACK")):
        elements, b = part(key, label, "", "#fde68a", 4.2)
        o += elements
        o.append(tie(PLACES[key][0], b[1] - 1.5, PLACES[key][0], b[3] + 1.5))
    o.append(rect(out_x - 6, 571, out_x + 6, 588, 'fill="#fde68a" stroke="#111" stroke-width="0.5"'))    # just inside the frame
    o.append(tie(out_x - 7.5, 579.5, out_x + 7.5, 579.5))
    return o


def starts_svg(plans):
    """Where each output's chain begins, and the lead to it from the Sparkle Motion."""
    sx, sy = PLACES["sparkle"][:2]
    starts = {}
    for me in plans.values():
        for s in me["stations"]:
            for key in ("wa", "wb"):
                if s[key][1] == 0:
                    starts[s[key][0]] = (front(s["a" if key == "wa" else "b"]), s["name"])
    o = []
    for out, ((x, y), name) in sorted(starts.items()):
        o.append(line([turn(TERMINALS[out - 1], (sx, sy), SPARKLE_TURN), (x, y)], 'stroke="#059669" stroke-width="1.1" stroke-dasharray="1.5 2"'))
        o.append('<circle cx="%.1f" cy="%.1f" r="5.5" fill="#059669"/>' % (X(x), y))
        o.append(text(x, y + 2.0, str(out), 5.5, 'fill="#fff" font-weight="bold"'))
    return o


def cups_svg(plans, boxes, nearest_room):
    """The spacer pixels' cups, each near the hop it hangs in. Returns the elements and the cups' centres."""
    hops = [("RL Downtown Crossing", "RL Park Street"), ("BL Gov't Center", "BL State"), ("OL Green St", "GL Brigham Circle")]
    by_name = dict((s["name"], front(s["c"])) for me in plans.values() for s in me["stations"])
    cups, o = [], []
    for (a, b), count in zip(hops, (2, 2, 1)):
        mid = ((by_name[a][0] + by_name[b][0]) / 2, (by_name[a][1] + by_name[b][1]) / 2)
        for k in range(count):
            c = nearest_room(mid[0] + 24 * k, mid[1], 9.5)
            boxes.append((c[0] - 9, c[1] - 9, c[0] + 9, c[1] + 9))
            cups.append(c)
            o.append('<circle cx="%.1f" cy="%.1f" r="8" fill="#fff" stroke="#111" stroke-width="0.6"/>' % (X(c[0]), c[1]))
            o.append(text(c[0], c[1] + 1.5, "cup", 4.4, ""))
    return o, cups


def tile_names_svg(plans, tabs):
    o = []
    for tile, (x, y) in (("lower_left", (110, 583)), ("upper_left", (150, 100)), ("upper_right", (470, 70))):
        o.append(text(x, y, NAMES[tile], 9, 'fill="%s" font-weight="bold"' % COLORS[tile][0]))
        o.append(text(x, y + 9, "%d stations, %d glue tabs" % (len(plans[tile]["stations"]), len(tabs[tile])), 5.5,
                      'fill="%s"' % COLORS[tile][0]))
    return o


def legend_items(tabs):
    return [
        "<b>Tiles</b>: three printed black tiles, coloured here by tile. Each double collar holds one station's two pixels.",
        "<b>Joints A to D</b> (red dashed rings): a solid knob on one tile drops into a C-shaped socket on the next. "
        "A and B join the lower-left tile to the upper-left; C and D join the upper-left to the upper-right.",
        "<b>Locating collars</b> (black ring and cross): two per tile. They match the ringed reference holes on the drill guide.",
        "<b>Glue tabs</b> (white discs with a dot): %d in all." % sum(len(t) for t in tabs.values()),
        "<b>Yellow blocks</b>: zip-tie anchors. Below the Matrix Portal they hold the two lever nuts (+5 V and GND) "
        "and the barrel-jack adapter the power supply plugs into; the one against the frame holds the supply cable where it comes in.",
        "<b>Zip ties</b> (orange): one over the Matrix Portal, one over the Sparkle Motion, one on each of the four "
        "anchors: 6, plus any used to bundle wire.",
        "<b>Wires</b>: grey band = ribbon cable from the Matrix Portal to the sign; red and black = power to the sign; "
        "red dashes = 5 V and ground to the Sparkle Motion; blue = the Matrix Portal's USB-C lead, from the lever nuts. "
        "The supply cable and the Sparkle Motion's pigtail share the narrow gap between the Sparkle Motion and the sign.",
        "<b>Green dots 1, 2, 3</b>: where each output's chain of pixels begins. The dotted green lines are the leads "
        "from the Sparkle Motion; route them between collars and hold them with the printed wire clips.",
        "<b>Cups</b>: the five always-dark spacer pixels park in these, next to the hop they hang in.",
        "<b>Proposed, not final</b>: the positions of the two boards, lever nuts, jack adapter and cups "
        "(the Sparkle Motion is in the bottom lane so its three leads are short). "
        "The tiles, joints, tabs and locating collars are exact.",
    ]


def page_html(elements, legend):
    page = ['<!doctype html><html><head><meta charset="utf-8"><title>Hardware back view</title><style>',
            'body{font-family:Arial,Helvetica,sans-serif;margin:16px;color:#111;background:#fff}',
            'h1{font-size:20px;margin:0 0 4px}p{margin:4px 0;font-size:13px;line-height:1.4}',
            'svg{width:100%;max-width:980px;height:auto;display:block;margin:10px 0}svg text{font-family:Arial,Helvetica,sans-serif}',
            'ul{padding-left:18px;max-width:980px}li{font-size:13px;line-height:1.45;margin:3px 0}',
            '@media print{body{margin:6mm}svg{max-width:190mm}}</style></head><body>',
            '<h1>MBTA map: hardware on the back of the panel</h1>',
            '<p>Seen from behind, so left and right are swapped compared with the map. The sign is at the lower left here.</p>',
            '<svg viewBox="0 0 %.1f %.1f" xmlns="http://www.w3.org/2000/svg">' % (FACE, FACE), "\n".join(elements), '</svg><ul>']
    page += ["<li>%s</li>" % t for t in legend]
    page.append("</ul></body></html>")
    return "\n".join(page)


def report(joints, cups, tabs, solid):
    """What was made, and whether each board and block clears the tiles."""
    print("cups: %d; joints: %d; glue tabs: %s" % (
        len(cups), len(joints), ", ".join("%s %d" % (t, len(v)) for t, v in sorted(tabs.items()))))
    for key in ("portal", "sparkle", "nut5", "nutg", "jack"):
        b = box(PLACES[key])
        clear = all(T.point_to_segment(((b[0] + b[2]) / 2 + dx * (b[2] - b[0]) / 2, (b[1] + b[3]) / 2 + dy * (b[3] - b[1]) / 2), a, c) >= r - 2.0
                    for a, c, r in solid for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        hit = [t for tile in tabs for t in tabs[tile]
               if b[0] - 6 < -t[0] < b[2] + 6 and b[1] - 6 < -t[1] < b[3] + 6]
        print("  %-8s clear of collars and ribs: %s; glue tabs under it: %d" % (key, clear, len(hit)))


def main():
    plans = T.make_plans()
    joints = T.all_joints(plans)
    credit = T.place_credit(plans, joints)
    tabs, marks = tabs_and_marks(plans, joints, credit)
    solid = obstacles(plans, joints)
    boxes = [SIGN] + [box(p) for p in PLACES.values()]
    cups_elements, cups = cups_svg(plans, boxes, nearest_room_finder(solid, boxes))

    elements = (frame_svg() + tiles_svg(plans, tabs, marks, credit, joints) + sign_svg() + boards_svg()
                + starts_svg(plans) + cups_elements + tile_names_svg(plans, tabs))
    path = os.path.join(T.MAP_DATA, "hardware_back_view.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page_html(elements, legend_items(tabs)))
    print("wrote", path)
    report(joints, cups, tabs, solid)


if __name__ == "__main__":
    main()
