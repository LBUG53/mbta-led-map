"""Check the layout against the physical rules listed in docs/HOW_IT_WORKS.md ("The map generator").

Each check returns {"name", "ok", "worst", "detail": [lines]}; worst is the
closest any station comes to the limit, in plain words.
"""
import math

import layout
import params as P
from geometry import point_to_segment


def name_of(s):
    return "%s %s" % (s["line"], s["name"])


def lights(stations):
    """[(station number, 'A' or 'B', (x, y))] for every light."""
    out = []
    for i, s in enumerate(stations):
        out.append((i, "A", s["A"]))
        out.append((i, "B", s["B"]))
    return out


def neighbors(runs):
    """Consecutive stations along every line, including across junctions."""
    pairs = []
    for run in runs:
        prev = run.after
        for s in run.stops:
            if prev is not None:
                pairs.append((prev, s))
            prev = s
        joins = getattr(run, "joins", None)
        if joins is not None and run.stops:
            pairs.append((run.stops[-1], joins))
    return pairs


def dist_to_rect(p, x0, y0, x1, y1):
    """Distance from a point to a rectangle's outline (inside or outside it)."""
    x, y = p
    if x0 <= x <= x1 and y0 <= y <= y1:
        return min(x - x0, x1 - x, y - y0, y1 - y)
    return math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))


def check_all(runs, stations):
    """Run every hard constraint. Returns one dict per check: its name, whether it
    passed (`ok`), the closest call (`worst`) and what failed (`detail`).
    """
    out = []
    lit = lights(stations)

    # 1. inside the cradle opening
    bad, worst = [], None
    for i, which, (x, y) in lit:
        margin = min(x - P.LIGHT_MIN, P.LIGHT_MAX - x, y - P.LIGHT_MIN, P.LIGHT_MAX - y)
        if worst is None or margin < worst[0]:
            worst = (margin, "%s light %s at (%.1f, %.1f)" % (name_of(stations[i]), which, x, y))
        if margin < -1e-6:
            bad.append("%s light %s at (%.1f, %.1f)" % (name_of(stations[i]), which, x, y))
    out.append({"name": "1. Every light between %.0f and %.0f mm (cradle walls assumed %.1f mm)"
                        % (P.LIGHT_MIN, P.LIGHT_MAX, P.CRADLE_WALL),
                "ok": not bad, "worst": "%.1f mm inside the limit: %s" % worst, "detail": bad})

    # 2. two lights per station, 14 mm apart, square to the line
    bad, worst = [], 0.0
    for s in stations:
        gap = math.dist(s["A"], s["B"])
        along = abs((s["A"][0] - s["B"][0]) * s["dir"][0] + (s["A"][1] - s["B"][1]) * s["dir"][1])
        off = max(abs(gap - 2 * P.LIGHT_OFFSET), along)
        worst = max(worst, off)
        if off > 0.01:
            bad.append("%s: %.2f mm apart, %.2f mm off square" % (name_of(s), gap, along))
    out.append({"name": "2. Two lights per station, %.0f mm apart, square to the line" % (2 * P.LIGHT_OFFSET),
                "ok": not bad, "worst": "%d stations, %d lights; largest error %.2f mm"
                                        % (len(stations), 2 * len(stations), worst), "detail": bad})

    # 3. lights of different stations
    bad, worst = [], None
    for a in range(len(lit)):
        for b in range(a + 1, len(lit)):
            if lit[a][0] == lit[b][0]:
                continue
            d = math.dist(lit[a][2], lit[b][2])
            text = "%s %s and %s %s" % (name_of(stations[lit[a][0]]), lit[a][1], name_of(stations[lit[b][0]]), lit[b][1])
            if worst is None or d < worst[0]:
                worst = (d, text)
            if d < P.MIN_LIGHT_GAP - 1e-6:
                bad.append("%.1f mm: %s" % (d, text))
    out.append({"name": "3. Lights of different stations at least %.0f mm apart" % P.MIN_LIGHT_GAP,
                "ok": not bad, "worst": "%.1f mm: %s" % worst, "detail": sorted(bad)})

    # 4 and 6. spacing along each line
    pairs = neighbors(runs)
    close = min(pairs, key=lambda p: math.dist((p[0]["x"], p[0]["y"]), (p[1]["x"], p[1]["y"])))
    far = max(pairs, key=lambda p: math.dist((p[0]["x"], p[0]["y"]), (p[1]["x"], p[1]["y"])))

    def gap(p):
        return math.dist((p[0]["x"], p[0]["y"]), (p[1]["x"], p[1]["y"]))
    bad = ["%.1f mm: %s to %s" % (gap(p), name_of(p[0]), name_of(p[1])) for p in pairs
           if gap(p) < P.MIN_STATION_GAP - 1e-6]
    out.append({"name": "4. Stations along a line at least %.0f mm apart" % P.MIN_STATION_GAP, "ok": not bad,
                "worst": "%.1f mm: %s to %s" % (gap(close), name_of(close[0]), name_of(close[1])), "detail": bad})

    # 5. the sign
    bad, worst = [], None
    for i, which, p in lit:
        d = dist_to_rect(p, P.SIGN_X0, P.SIGN_Y0, P.SIGN_X1, P.SIGN_Y1)
        inside = P.SIGN_X0 <= p[0] <= P.SIGN_X1 and P.SIGN_Y0 <= p[1] <= P.SIGN_Y1
        text = "%s light %s at (%.1f, %.1f)" % (name_of(stations[i]), which, p[0], p[1])
        if worst is None or d < worst[0]:
            worst = (d, text)
        if inside or d < P.SIGN_CLEAR - 1e-6:
            bad.append("%.1f mm%s: %s" % (d, " (behind the sign)" if inside else "", text))
    out.append({"name": "5. No light within %.0f mm of the sign panel's outline" % P.SIGN_CLEAR, "ok": not bad,
                "worst": "%.1f mm: %s" % worst, "detail": bad})

    bad = ["%.1f mm: %s to %s" % (gap(p), name_of(p[0]), name_of(p[1])) for p in pairs
           if gap(p) > P.MAX_STATION_GAP + 1e-6]
    out.append({"name": "6. Neighboring stations no more than %.0f mm apart (wire reach)" % P.MAX_STATION_GAP,
                "ok": not bad, "worst": "%.1f mm: %s to %s" % (gap(far), name_of(far[0]), name_of(far[1])),
                "detail": bad})

    # 7. right-angle turns
    bad, worst, count = [], None, 0
    for run in runs:
        for vertex, deg, t in layout.corners(run):
            if abs(deg - 90) > 1:
                continue
            count += 1
            for s in run.stops:
                d = math.dist(vertex, (s["x"], s["y"]))
                if worst is None or d < worst[0]:
                    worst = (d, "%s from the turn at (%.0f, %.0f)" % (name_of(s), vertex[0], vertex[1]))
                if d < P.MIN_FROM_RIGHT_ANGLE - 1e-6:
                    bad.append("%.1f mm: %s" % (d, name_of(s)))
    out.append({"name": "7. No station within %.1f mm of a right-angle turn" % P.MIN_FROM_RIGHT_ANGLE, "ok": not bad,
                "worst": ("%.1f mm: %s" % worst) if worst else "the layout has no right-angle turns",
                "detail": bad})
    return out


def extra_checks(runs, stations):
    """Not in the spec's list, but they'd spoil the build: a light under another
    line's ink, a station on a curve, a line that isn't octilinear."""
    out = []
    bad, worst = [], None
    limit = 4.0 + P.LINE_WIDTH / 2          # 8 mm hole's edge clear of a 4 mm line
    for i, which, p in lights(stations):
        s = stations[i]
        for run in runs:
            if run.line == s["line"] or {run.line, s["line"]} == {"RL", "M"}:
                continue
            for a, b in layout.segments(run):
                d = point_to_segment(p, a, b)
                if worst is None or d < worst[0]:
                    worst = (d, "%s light %s and the %s line" % (name_of(s), which, run.branch))
                if d < limit - 1e-6:
                    bad.append("%.1f mm: %s light %s under the %s line" % (d, name_of(s), which, run.branch))
    out.append({"name": "Extra: every light's hole clear of other lines' ink (%.0f mm from their centers)" % limit,
                "ok": not bad, "worst": "%.1f mm: %s" % worst, "detail": sorted(set(bad))})

    bad = []
    for run in runs:
        for vertex, deg, t in layout.corners(run):
            for s in run.stops:
                d = math.dist(vertex, (s["x"], s["y"]))
                if 0.5 < d < t - 0.2:
                    bad.append("%s is %.1f mm from a %d-degree bend whose curve runs %.1f mm" % (name_of(s), d, deg, t))
    out.append({"name": "Extra: no station on a curve", "ok": not bad,
                "worst": "none" if not bad else bad[0], "detail": bad})

    bad = []
    for run in runs:
        for a, b in layout.segments(run):
            dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
            if min(dx, dy) > 0.01 and abs(dx - dy) > 0.01:
                bad.append("%s: (%.1f, %.1f) to (%.1f, %.1f)" % (run.branch, a[0], a[1], b[0], b[1]))
    out.append({"name": "Extra: every segment horizontal, vertical or at 45 degrees", "ok": not bad,
                "worst": "all %d segments" % sum(len(layout.segments(r)) for r in runs) if not bad else bad[0],
                "detail": bad})
    return out


def report_lines(checks):
    lines = []
    for c in checks:
        lines.append("- **%s** %s. Closest: %s." % ("PASS" if c["ok"] else "FAIL", c["name"], c["worst"]))
        for d in c["detail"][:12]:
            lines.append("  - " + d)
        if len(c["detail"]) > 12:
            lines.append("  - ... and %d more" % (len(c["detail"]) - 12))
    return lines
