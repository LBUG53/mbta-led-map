"""Everything on the print that isn't the network: the T, the Green Line
branch tags, the caption under the sign and the credit line."""
import font
import params as P

TEXT = P.INK                # MBTA Gray Dark
GRAY = "#6F7070"            # a 65% tint of it, for secondary text
TAG_COLOR = P.COLORS["GL"]  # the branch tags name Green Line branches
TAG_SIZE = 2.6
TAG_BELOW = 9.0             # tag's cap top below the branch's last stop
CAPTION_SIZE = 8.4         # "DEPARTURES": its capitals are 6 mm tall
CAPTION_RISE = 4.35        # from the word's baseline up to the top of the window
CREDIT_SIZE = 3.4          # capitals 2.4 mm tall: still quiet, but big enough to print cleanly
FAMILY = ' font-family="Arial, Helvetica, sans-serif"'

BRANCH_ENDS = {"B BRANCH": "Boston College", "C BRANCH": "Cleveland Circle", "D BRANCH": "Riverside",
               "E BRANCH": "Heath St"}


# The T logo on a 1000-unit square, from Wikimedia Commons ("MBTA.svg"). Its proportions match the
# brand guide's drawing: ring 4.4% of the diameter, bar 63.2% wide and 15.9% tall. Don't redraw it.
T_DISC = ("M500 44.3c-251.7 0-455.7 204-455.7 455.7s204 455.7 455.7 455.7 455.7-204 455.7-455.7S751.7 44.3 500 44.3z")
T_RING = ("M500 0C223.9 0 0 223.9 0 500s223.9 500 500 500 500-223.9 500-500S776.1 0 500 0zm0 955.7c-251.7 0-455.7-204"
          "-455.7-455.7S248.3 44.3 500 44.3s455.7 204 455.7 455.7-204 455.7-455.7 455.7z")
T_LETTER = "M184.3 435.1h236.6v389.3h158.2V435.1h236.6V276.9H184.3z"


def title():
    """The T logo in TITLE_BOX: the ring and the T in the print's dark ink, white inside the ring."""
    x0, y0, x1, _ = P.TITLE_BOX
    return ['<g transform="translate(%.2f %.2f) scale(%.4f)">' % (x0, y0, (x1 - x0) / 1000),
            '<path d="%s" fill="#FFFFFF"/>' % T_DISC,
            '<path d="%s" fill="%s"/>' % (T_RING, TEXT),
            '<path d="%s" fill="%s"/>' % (T_LETTER, TEXT),
            '</g>']


def tags(stations):
    """[(text, box, svg)] for the four branch tags, just beyond each branch's last stop."""
    out = []
    cap = TAG_SIZE * font.CAP
    for text, last in BRANCH_ENDS.items():
        s = [t for t in stations if t["line"] == "GL" and t["name"] == last][0]
        w = font.width(text, TAG_SIZE, True, 0.25)
        base = s["y"] + TAG_BELOW + cap
        box = (s["x"] - w / 2, base - cap, s["x"] + w / 2, base + 0.2)
        out.append((text, box, '<text x="%.2f" y="%.2f" text-anchor="middle">%s</text>' % (s["x"], base, text)))
    return out


TAG_ATTRS = FAMILY + ' font-size="%g" font-weight="700" letter-spacing="0.25" fill="%s"' % (TAG_SIZE, TAG_COLOR)


def credit():
    """Bottom left: who made it, the license, and where the data comes from, small and gray."""
    text = "  \u00b7  ".join(P.CREDIT)
    assert P.CREDIT_BOX[0] + font.width(text, CREDIT_SIZE, False, 0) <= P.CREDIT_BOX[2], "credit line too long"
    return ['<text x="%.2f" y="%.2f" font-size="%g" fill="%s" xml:space="preserve">%s</text>'
            % (P.CREDIT_BOX[0], P.CREDIT_BOX[3], CREDIT_SIZE, GRAY, text.replace("&", "&amp;"))]


def caption():
    """DEPARTURES, centred just above the sign like the title over a station board, in spaced capitals."""
    base = P.SIGN_Y0 + P.WINDOW_INSET - CAPTION_RISE
    return ['<text x="%.2f" y="%.2f" font-size="%g" font-weight="700" letter-spacing="0.12em" text-anchor="middle" '
            'fill="%s">DEPARTURES</text>' % ((P.SIGN_X0 + P.SIGN_X1) / 2, base, CAPTION_SIZE, TEXT)]
