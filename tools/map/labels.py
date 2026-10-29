"""Station labels for the map: one rule per stretch of line, one distance,
horizontal text. Each label is placed by its rule and then checked against
everything it must not touch; nothing here moves a label to make it fit
(that is done by moving the geometry, or by an entry in overrides.py).
"""
import math

import font
import overrides
from geometry import rect_to_point, rect_to_rect, rect_to_segment
import params as P

SIZE = 3.5                      # mm, about 10 pt
TRANSFER_SIZE = 4.0             # transfer stations a step up, so the system's spine is easy to find
BESIDE, BESIDE_DIAGONAL = 12.5, 11.0
LABEL_GAP = 1.0                 # between two labels
LINE_GAP = 0.6                  # between a label and a line's edge (labels have a cream outline)
PAGE_MARGIN = 6.0
SIDE_WORDS = {"R": "right", "L": "left", "A": "above", "B": "below"}

# Short forms, tried in order when the full name doesn't fit cleanly.
SHORT = {
    "Science Park/West End": ["Science Park"],
    "Hynes Convention Ctr": ["Hynes"],
    "Community College": ["Comm College"],
    "Tufts Medical Ctr": ["Tufts Med Ctr"],
    "Longwood Medical Area": ["Longwood Med Area"],
    "Museum of Fine Arts": ["Mus. of Fine Arts"],
    "St. Mary's St": ["St. Mary's"],
    "Packard's Corner": ["Packard's Cnr"],
    "Coolidge Corner": ["Coolidge Cnr"],
    "Orient Heights": ["Orient Hts"],
    "Newton Centre": ["Newton Ctr"],
    "Quincy Center": ["Quincy Ctr"],
    "Malden Center": ["Malden Ctr"],
    "Gov't Center": ["Gov't Ctr"],
}

# One label per interchange: (line whose circle it sits by, side).
TRANSFER_LABELS = {
    "North Station": ("OL", "R"),
    "Haymarket": ("OL", "R"),
    "State": ("BL", "R"),
    "Downtown Crossing": ("RL", "A"),
    "Gov't Center": ("BL", "A"),
    "Park Street": ("RL", "A"),
    "Ashmont": ("M", "B"),
}


def is_diagonal(s):
    return abs(s["dir"][0]) > 0.1 and abs(s["dir"][1]) > 0.1


def rule_side(s):
    """The side of the line a station's label goes on, by stretch (spec section 6)."""
    diag = is_diagonal(s)
    horizontal = abs(s["dir"][1]) < 0.1
    b = s["branch"]
    if b == "Orange":
        return "R"
    if b == "Green trunk":
        return "R" if diag else ("B" if horizontal else "L")
    if b == "Green C":
        return "B" if horizontal else "L"
    if b in ("Green Union Sq", "Green B", "Green D", "Red Ashmont"):
        return "L"
    if b in ("Green E", "Red Braintree"):
        return "R"
    if b == "Blue":
        return "A" if horizontal else "L"
    if b == "Red":
        if horizontal:
            return "A"
        return "R" if s["name"] in ("Alewife", "Davis", "Porter", "Harvard", "Central") else "L"
    if b == "Mattapan":
        return "A"
    raise ValueError(b)


def box_for(anchor, side, text, dx=0.0, dy=0.0, dist=None, size=SIZE):
    """(x0, y0, x1, y1, text x, baseline y, anchor) for a label by a station."""
    w = font.width(text, size, True)
    cap = size * font.CAP
    if dist is None:
        dist = BESIDE_DIAGONAL if (is_diagonal(anchor) and side in "RL") else BESIDE
    x, y = anchor["x"], anchor["y"]
    if side == "R":
        x0, base, align, tx = x + dist, y + cap / 2, "start", x + dist
    elif side == "L":
        x0, base, align, tx = x - dist - w, y + cap / 2, "end", x - dist
    elif side == "A":
        x0, base, align, tx = x - w / 2, y - dist, "middle", x
    else:
        x0, base, align, tx = x - w / 2, y + dist + cap, "middle", x
    x0, tx, base = x0 + dx, tx + dx, base + dy
    return (x0, base - cap, x0 + w, base + 0.3, tx, base, align)


def reserved():
    """Parts of the print that labels must stay out of (drawn in stage 3)."""
    w, o = P.WINDOW_INSET, 3.0
    return {
        "the sign window": (P.SIGN_X0 + w - o, P.SIGN_Y0 + w - o, P.SIGN_X1 - w + o, P.SIGN_Y1 - w + o),
        "the T logo": (P.TITLE_BOX[0] - P.TITLE_CLEAR, P.TITLE_BOX[1] - P.TITLE_CLEAR,
                       P.TITLE_BOX[2] + P.TITLE_CLEAR, P.TITLE_BOX[3] + P.TITLE_CLEAR),
        "the sign caption": P.CAPTION_BOX,
        "the credit": P.CREDIT_BOX,
    }


def problems(box, me, runs, stations, transfers, placed):
    """Everything a label box touches that it shouldn't. `me` = stations it names."""
    r = box[:4]
    out = []
    if r[0] < PAGE_MARGIN or r[1] < PAGE_MARGIN or r[2] > P.FACE - PAGE_MARGIN or r[3] > P.FACE - PAGE_MARGIN:
        out.append("off the print")
    for name, rect in reserved().items():
        if rect_to_rect(r, rect) < LABEL_GAP:
            out.append(name)
    for run in runs:
        for a, b in zip(run.pts, run.pts[1:]):
            if rect_to_segment(r, a, b) < P.LINE_WIDTH / 2 + LINE_GAP:
                out.append("the %s line" % run.branch)
                break
    for name, group in transfers.items():
        a, b = group
        if rect_to_segment(r, (a["x"], a["y"]), (b["x"], b["y"])) < P.CONNECTOR_W / 2 + LINE_GAP:
            out.append("the %s interchange" % name)
    for s in stations:
        for which in ("A", "B"):
            if rect_to_point(r, s[which]) < P.GLOW_RADIUS:
                out.append("%s %s's light" % (s["line"], s["name"]))
                break
    for other in placed:
        if rect_to_rect(r, other["box"][:4]) < LABEL_GAP:
            out.append("the label %s" % other["text"])
    return out


def place_all(runs, stations, transfers):
    """Returns the list of labels: dicts with text, box, side, rule, problems, notes."""
    jobs = []
    seen = set()
    for s in stations:
        if s["transfer"]:
            if s["transfer"] in seen:
                continue
            seen.add(s["transfer"])
            line, side = TRANSFER_LABELS[s["transfer"]]
            anchor = [t for t in transfers[s["transfer"]] if t["line"] == line][0]
            jobs.append((s["transfer"], anchor, side, transfers[s["transfer"]]))
        else:
            jobs.append((s["name"], s, rule_side(s), [s]))

    labels = []
    for name, anchor, side, group in jobs:
        ov = overrides.LABELS.get(name, {})
        if ov.get("line") and ov["line"] != anchor["line"]:
            ov = {}
        use_side = ov.get("side", side)
        texts = [ov["text"]] if ov.get("text") else [name] + SHORT.get(name, [])
        if any(s["line_end"] for s in group):
            texts = [t.upper() for t in texts]          # as on the MBTA's own map: ALEWIFE, OAK GROVE
        size = TRANSFER_SIZE if len(group) > 1 else SIZE
        best = None
        for text in texts:
            lines = text.split("\n")
            boxes = []
            for k, part in enumerate(lines):
                shift = (k - (len(lines) - 1) / 2) * size * 1.15 if use_side in "RL" else \
                    (k - (len(lines) - 1)) * size * 1.15 if use_side == "A" else k * size * 1.15
                boxes.append(box_for(anchor, use_side, part, ov.get("dx", 0.0), ov.get("dy", 0.0) + shift,
                                     ov.get("dist"), size))
            hull = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes),
                    max(b[3] for b in boxes))
            bad = problems(hull, group, runs, stations, transfers, labels)
            cand = {"name": name, "text": text, "size": size, "lines": lines, "boxes": boxes, "box": hull + boxes[0][4:],
                    "side": use_side, "rule": side, "anchor": anchor, "problems": bad,
                    "override": ov.get("reason"), "short": text.lower() != name.lower() and not ov.get("text"),
                    "dist": ov.get("dist") or (BESIDE_DIAGONAL if (is_diagonal(anchor) and use_side in "RL")
                                               else BESIDE),
                    "moved": bool(ov.get("dx") or ov.get("dy") or ov.get("dist") or ov.get("side"))}
            if best is None or len(bad) < len(best["problems"]):
                best = cand
            if not bad:
                break
        labels.append(best)
    return labels


def svg_lines(labels):
    """The labels' text, once. generate.py writes it twice: a cream copy with a thick outline
    (labels-halo), then the dark text on top. An outline drawn under the text with paint-order would
    be one copy, but some print software ignores paint-order and prints the outline over the text."""
    out = []
    for lab in labels:
        size = '' if lab["size"] == SIZE else ' font-size="%g"' % lab["size"]
        for part, b in zip(lab["lines"], lab["boxes"]):
            out.append('<text x="%.2f" y="%.2f" text-anchor="%s"%s>%s</text>'
                       % (b[4], b[5], b[6], size, part.replace("&", "&amp;")))
    return out


LAYER_ATTRS = ' font-family="Arial, Helvetica, sans-serif" font-size="%g" font-weight="700" fill="#212322"' % SIZE
HALO_ATTRS = (' font-family="Arial, Helvetica, sans-serif" font-size="%g" font-weight="700" fill="%s" stroke="%s" '
              'stroke-width="0.7" stroke-linejoin="round"' % (SIZE, P.BACKGROUND, P.BACKGROUND))
