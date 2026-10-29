"""The small mounting parts, all on one plate (any color), and the sign's brackets and bezel.

  python make_parts.py      writes parts_plate.stl, portal_cradle.stl, sign_parts.stl and sign_mounts.stl

A tray for the Sparkle Motion, a peg cradle for the Matrix Portal, cups for the
unused SKIP pixels, wire clips and zip-tie anchors. Each has a 3.6 mm screw hole
but glue works too. The six sign brackets screw into the LED panel's M3 inserts and
push into bases glued to the wood, so the sign pulls out with its brackets; the bezel is glued round the sign
window on the front. The two feet stand the finished map on a table, leaning back. All of those are in
sign_parts.stl, one plate for the 400 mm bed: the brackets and their bases inside the bezel, the feet
beside it. sign_mounts.stl is the brackets and bases on their own.
"""
import math
import os

import yaml
from manifold3d import CrossSection, Manifold

from make_tile import bed_turn
from stl import write_stl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "build.yaml"), encoding="utf-8") as f:
    BUILD = yaml.safe_load(f)               # the measured sizes of this build

SEG = 48
HOLE = 3.6

BORE = 13.0             # the pixel bore from the collar test

# The sign's brackets. The panel lies face down on the back of the wood, over its window, so a bracket's
# tab sits at the panel's thickness. Adafruit's drawing puts the six M3 inserts 7.85 mm in from the edges.
PANEL_T = BUILD["sign"]["thickness"]   # panel thickness at its edge, face to back
CLAMP = 0.3             # the tab sits this much lower, so tightening the screw pulls the panel onto the wood
SLOT = (5.0, 13.0)      # the screw can land anywhere this far in from the panel's edge
M3 = 4.2                # slot width: at 3.4 the slot's edges covered part of the panel's threaded hole
BRACKET_W = 14.0        # along the panel's edge
TAB_T, LEG_T, FOOT_T = 3.0, 3.0, 2.5
LEG_GAP = 0.5           # between the panel's edge and the leg
FOOT_OUT = 9.0          # from the panel's edge to the foot's outer end
FOOT_W = 26.0           # the foot runs on along the edge past the tab, on one side, for a wider stance
# Each bracket's foot pushes into a base glued to the wood. The tabs overlap the sign by at least 12 mm (the
# inserts are 7.85 mm in), so with the brackets glued down the sign could never come out; this way it pulls out
# with its brackets on. Two prongs under the foot go down a slot in the base and grip by friction: on the Kobra
# Max the drawn 0.15 mm side gap prints as a tight fit. Barbs of 0.1 mm and more under the slot's lip held so
# hard they wouldn't pull out. The prongs start at the foot's end (y = 0), so printed on its side they stand on
# the bed.
BASE_H = 8.0
SNAP_L = 10.0           # the prongs' length along the panel's edge
PRONG_T = 1.2
PRONG_HALF = 1.95       # from the slot's middle to a prong's outside face
SLOT_HALF = 2.1
LIP0 = 2.5              # the slot grips the prongs from here up; the hollow below it is as tested, from the barbs
CAVITY_HALF = 2.9


# The bezel: a thin frame glued round the window on the front of the print.
WINDOW = (BUILD["sign"]["width"] - 2 * BUILD["sign"]["window_inset"],      # the print's window opening
          BUILD["sign"]["height"] - 2 * BUILD["sign"]["window_inset"])
BEZEL_W = 3.0           # outside the window; any wider and it reaches DEPARTURES, whose baseline is 4.3 mm above it
BEZEL_OVER = 1.25       # inside the window, over the sign's outermost LEDs (about half of one), to hide the cut wood
BEZEL_T = 3.0           # at 1.6 mm it bent coming off the bed

# The feet: the bottom edge of the frame sits in a channel that leans back. They touch only the outside of the
# frame: the front lip stays below the credit line, the back wall below the top of the frame's 20 mm rim.
FRAME_D = BUILD["panel"]["depth"]  # the panel's depth, front of the print to the back of the frame
FIT = 0.8               # room in the channel
LEAN = 10.0             # degrees back from upright
LIP_H, BACK_H = 8.0, 15.0
WALL = 5.0
REACH_FRONT, REACH_BACK = 35.0, 120.0   # the base, from the channel's front: the map's weight sits about 55 mm back
FOOT_WIDTH = 30.0
BASE_T = 5.0


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def hole_z(x, y, z0, z1, d=HOLE):
    """A vertical hole at (x, y), a little longer than z0 to z1 so it cuts cleanly through."""
    return Manifold.cylinder(z1 - z0 + 2, d / 2, d / 2, SEG).translate((x, y, z0 - 1))


def hole_y(x, z, y0, y1, d=HOLE):
    """A hole running along y (through a part that is printed lying on its side)."""
    return Manifold.cylinder(y1 - y0 + 2, d / 2, d / 2, SEG).rotate((-90.0, 0.0, 0.0)).translate((x, y0 - 1, z))


def controller_tray():
    """A tray for the Sparkle Motion: four pegs for its mounting holes, two screw ears, slots for a zip tie."""
    w, h = 50.8, 33.0
    dx, dy = 45.7 / 2, 27.9 / 2
    part = box(-w / 2 - 2, -h / 2 - 2, 0, w / 2 + 2, h / 2 + 2, 2)
    part += box(-w / 2 - 14, -6, 0, -w / 2 - 2, 6, 2) + box(w / 2 + 2, -6, 0, w / 2 + 14, 6, 2)     # screw ears
    for sx in (-1, 1):
        for sy in (-1, 1):
            at = (sx * dx, sy * dy, 0)
            part += Manifold.cylinder(6, 3, 3, SEG).translate(at)                   # standoff: board 4 mm up
            part += Manifold.cylinder(8.5, 1.1, 1.0, SEG).translate(at)             # peg through the board's hole
    cut = hole_z(-w / 2 - 8, 0, 0, 2) + hole_z(w / 2 + 8, 0, 0, 2)
    for sy in (-1, 1):                                                              # zip-tie slots across the middle
        cut += box(-2.5, sy * (h / 2 - 1.0) - 1.0, -1, 2.5, sy * (h / 2 - 1.0) + 1.0, 3)
    return part - cut


def portal_cradle():
    """Four pegs through the board's mounting holes (Adafruit's drawing: 1.60 x 0.78 in apart), so the board
    can't slide any way and nothing touches its edges: the buttons, USB-C, power screws and side sockets stay
    clear. The posts hold it 12 mm up so the socket on its underside hangs free. A zip tie through the block
    in the middle and over the board holds it down."""
    dx, dy, up = 40.64 / 2, 19.81 / 2, 12.0
    part = box(-32, -17, 0, 32, 17, 2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            at = (sx * dx, sy * dy, 0)
            part += Manifold.cylinder(up, 3.5, 2.5, SEG).translate(at)              # post
            part += Manifold.cylinder(up + 4.0, 1.1, 1.0, SEG).translate(at)        # peg through the 2.5 mm hole
    part += box(-7, -6, 0, 7, 6, 6.2) - box(-2.8, -7, 2.4, 2.8, 7, 4.8)             # block with a tunnel for the zip tie
    return part - hole_z(-27.5, 0, 0, 2) - hole_z(27.5, 0, 0, 2)



def skip_cup():
    """A cup that holds one unused (SKIP) pixel out of the way, with a screw ear."""
    part = Manifold.cylinder(2, 9, 9, SEG) + box(0, -5, 0, 17, 5, 2)                # base and screw ear
    part += Manifold.cylinder(9, BORE / 2 + 1.4, BORE / 2 + 1.4, SEG)
    return part - Manifold.cylinder(9, BORE / 2, BORE / 2, SEG).translate((0, 0, 2)) - hole_z(12.5, 0, 0, 2)


def wire_clip(width=8.0):
    """Lying on its side: a base, a post, and a roof that is open on one side."""
    part = box(-10, 0, 0, 6, 2, width)
    part += box(4, 0, 0, 6, 9, width)
    part += box(-4, 7, 0, 6, 9, width)
    part += box(-4, 5.8, 0, -2.8, 7, width)                     # a small lip so the wire doesn't slide back out
    return part - hole_y(-7, width / 2, 0, 2)


def tie_anchor():
    """A base with a block on it and a tunnel through the block; the part sits on the block, the tie goes round both."""
    part = box(-15, -6, 0, 15, 6, 2.4) + box(-7, -6, 0, 7, 6, 6.2)
    part -= box(-2.8, -7, 2.4, 2.8, 7, 4.8)                     # tunnel for a zip tie up to 5 mm wide
    return part - hole_z(-11.5, 0, 0, 2.4) - hole_z(11.5, 0, 0, 2.4)


def snap_x():
    return (LEG_GAP + FOOT_OUT) / 2


def snap_prongs():
    cx = snap_x()
    a, b = PRONG_HALF - PRONG_T, PRONG_HALF
    return (box(cx - b, 0, 0.5, cx - a, SNAP_L, BASE_H + 0.5) +
            box(cx + a, 0, 0.5, cx + b, SNAP_L, BASE_H + 0.5))


def sign_bracket():
    """One bracket, made as it is used (x outward from the panel's edge at x = 0, z up from the wood, standing on
    its base), then laid on its side for printing so the layers run round the bend instead of across it."""
    top = PANEL_T - CLAMP
    leg0, leg1 = LEG_GAP, LEG_GAP + LEG_T
    w = BRACKET_W
    part = box(-SLOT[1] - 4.0, 0, top, leg1, w, top + TAB_T)                        # tab, over the panel's back
    part += box(leg0, 0, BASE_H, leg1, w, top + TAB_T)                              # leg, beside the panel's edge
    # The foot's extra length is all on one side: printed on its side, that side is on top, so nothing overhangs.
    part += box(leg0, 0, BASE_H, FOOT_OUT, FOOT_W, BASE_H + FOOT_T)                 # foot, on its base
    brace = CrossSection([[(leg1, BASE_H + FOOT_T), (FOOT_OUT, BASE_H + FOOT_T),
                           (leg1, BASE_H + FOOT_T + FOOT_OUT - leg1)]])
    part += Manifold.extrude(brace, w).rotate((90.0, 0.0, 0.0)).translate((0, w, 0))  # fillet where leg meets foot
    part += snap_prongs()
    a, b = -SLOT[1], -SLOT[0]
    slot = box(a, w / 2 - M3 / 2, top - 1, b, w / 2 + M3 / 2, top + TAB_T + 1)
    slot += Manifold.cylinder(TAB_T + 2, M3 / 2, M3 / 2, SEG).translate((a, w / 2, top - 1))
    slot += Manifold.cylinder(TAB_T + 2, M3 / 2, M3 / 2, SEG).translate((b, w / 2, top - 1))
    return (part - slot).rotate((90.0, 0.0, 0.0))


def sign_base(length=FOOT_W):
    """What a bracket pushes into, glued to the wood. Printed as it lies; it starts 2 mm before the foot's end so
    the slot has a wall there."""
    cx, y1 = snap_x(), SNAP_L + 0.2
    part = box(LEG_GAP, -2.0, 0, FOOT_OUT, length, BASE_H)
    part -= box(cx - SLOT_HALF, -0.2, LIP0, cx + SLOT_HALF, y1, BASE_H + 1)
    return part - box(cx - CAVITY_HALF, -0.2, -1, cx + CAVITY_HALF, y1, LIP0)


def sign_bezel():
    """A flat frame, printed face down. Its outer edge is chamfered so it reads as a thin line, not a step."""
    iw, ih = WINDOW[0] - 2 * BEZEL_OVER, WINDOW[1] - 2 * BEZEL_OVER
    ow, oh = WINDOW[0] + 2 * BEZEL_W, WINDOW[1] + 2 * BEZEL_W
    c = 0.8
    outer = Manifold.extrude(CrossSection.square((ow - 2 * c, oh - 2 * c), True), BEZEL_T)     # z = 0 is the front
    outer = Manifold.batch_hull([outer, Manifold.extrude(CrossSection.square((ow, oh), True), BEZEL_T - c).translate((0, 0, c))])
    return outer - Manifold.extrude(CrossSection.square((iw, ih), True), BEZEL_T + 2).translate((0, 0, -1))


def frame_foot():
    """One foot, drawn as a side profile (x toward the back, y up) and printed lying on that profile, so the layers
    run round the channel's corners instead of across them."""
    d = FRAME_D + FIT
    a = math.radians(LEAN)

    def tilt(pts):
        # Lean the channel back: its top moves toward +x.
        return [(u * math.cos(a) + v * math.sin(a), -u * math.sin(a) + v * math.cos(a)) for u, v in pts]

    floor = tilt([(-WALL, -WALL), (d + WALL, -WALL), (d + WALL, 0), (-WALL, 0)])
    lip = tilt([(-WALL, -WALL), (0, -WALL), (0, LIP_H), (-WALL, LIP_H)])
    back = tilt([(d, -WALL), (d + WALL, -WALL), (d + WALL, BACK_H), (d, BACK_H)])
    low = min(y for _, y in floor) - BASE_T
    base = [(-REACH_FRONT, low), (REACH_BACK, low), (REACH_BACK, low + BASE_T), (-REACH_FRONT, low + BASE_T)]
    rear = [(back[0][0], low), (REACH_BACK, low), (REACH_BACK, low + BASE_T), (back[0][0], low + BASE_T)]
    shape = (CrossSection([floor + base]).hull() + CrossSection([lip]) +
             CrossSection([back + rear]).hull())
    return Manifold.extrude(shape, FOOT_WIDTH).translate((0, -low, 0))


def main():
    parts = []
    names = []

    def row(make, count, x0, y0, step, label):
        for i in range(count):
            parts.append(make().translate((x0 + i * step, y0, 0)))
        names.append("%d x %s" % (count, label))

    row(wire_clip, 6, 130, 26, 19, "wire clip")
    row(wire_clip, 10, 10, 48, 19, "wire clip")
    row(controller_tray, 1, 41, 86, 0, "Sparkle Motion tray")
    row(skip_cup, 3, 112, 74, 32, "SKIP pixel cup")
    row(skip_cup, 3, 112, 98, 32, "SKIP pixel cup")
    row(tie_anchor, 6, 16, 122, 34, "zip-tie anchor")
    row(tie_anchor, 2, 16, 138, 34, "zip-tie anchor")
    row(portal_cradle, 1, 150, 162, 0, "Matrix Portal cradle")
    whole = Manifold.compose(parts)
    bb = whole.bounding_box()
    here = os.path.dirname(os.path.abspath(__file__))
    write_stl(portal_cradle(), os.path.join(here, "portal_cradle.stl"), "portal_cradle")
    brackets = [sign_bracket().translate((-75.0 + 30.0 * (i % 3), 30.0 * (i // 3) - 10.0, 0)) for i in range(6)]
    brackets += [sign_base().translate((10.0 + 14.0 * i, -45.0, 0)) for i in range(6)]
    feet = [frame_foot().translate((-60.0, y, 0)) for y in (100.0, -130.0)]     # above and below the bezel
    sign = Manifold.compose([sign_bezel()] + brackets + feet)
    write_stl(sign, os.path.join(here, "sign_parts.stl"), "sign_parts")
    write_stl(Manifold.compose(brackets), os.path.join(here, "sign_mounts.stl"), "sign_mounts")
    for name, part in (("parts_plate", whole), ("sign_parts", sign)):
        if bed_turn(part) is None:
            print("  %s.stl is bigger than the printer's bed in build.yaml: print its parts in two goes" % name)
    path = os.path.join(here, "parts_plate.stl")
    write_stl(whole, path, "parts_plate")
    for n in names:
        print(" ", n)
    print("plate %.0f x %.0f x %.0f mm, %.1f cm3, %d pieces" % (
        bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2], whole.volume() / 1000, len(whole.decompose())))
    print("wrote", path, "portal_cradle.stl, sign_parts.stl (the bezel, the six sign brackets and their bases inside it, "
          "the two feet) and sign_mounts.stl (the brackets and bases alone)")


if __name__ == "__main__":
    main()
