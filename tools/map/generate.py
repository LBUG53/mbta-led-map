r"""Generate the map: every output from the one layout in layout.py.

  python tools/map/generate.py

Writes
  data/print_no_outline.svg, data/print_with_outline.svg   the print, 610 x 610 mm
  data/stations.csv                                          every station and its two lights
  data/validation_report.md                                     every constraint and every label

Stage 3: the whole print: geometry, markers, labels, water, the T, branch
tags, sign caption and credit, without and with the outline around the sign.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import furniture        # noqa: E402
import labels as lab    # noqa: E402
import layout           # noqa: E402
import overrides        # noqa: E402
import render           # noqa: E402
import validate         # noqa: E402
import water            # noqa: E402

DATA = os.path.join(ROOT, "data")
EXPECTED = {"RL": 22, "M": 8, "OL": 20, "BL": 12, "GL": 70}


def build():
    runs, stations, transfers = layout.build()
    placed = lab.place_all(runs, stations, transfers)
    return runs, stations, transfers, placed


def label_check(placed, stations):
    """Hard constraint 8, in the same shape as validate's checks."""
    bad = ["%s: touches %s" % (l["text"].replace("\n", " / "), ", ".join(sorted(set(l["problems"]))))
           for l in placed if l["problems"]]
    named = set()
    for l in placed:
        named.add(l["name"])
    want = {s["transfer"] or s["name"] for s in stations}
    missing = sorted(want - named)
    if missing:
        bad.append("no label for: " + ", ".join(missing))
    return {"name": "8. Labels never overlap a label, a line, a light's glow (%.0f mm), the sign window, "
                    "the T, the sign caption or the credit" % 5,
            "ok": not bad, "worst": "%d labels for %d stations (%d interchanges share one)"
                                    % (len(placed), len(stations), len(stations) - len(placed)),
            "detail": bad}


def print_svg(runs, stations, transfers, placed, outline):
    """One whole print as SVG text, with or without the thin outline round the sign window."""
    rivers, areas = water.build(stations)
    layers = {"labels-halo": lab.svg_lines(placed), "labels": lab.svg_lines(placed),
              "water": water.svg_lines(rivers, areas), "title": furniture.title(),
              "branch-tags": [t[2] for t in furniture.tags(stations)],
              "sign-caption": furniture.caption(), "credit": furniture.credit()}
    attrs = {"labels-halo": lab.HALO_ATTRS, "labels": lab.LAYER_ATTRS, "water": ' fill="%s"' % water.COLOR,
             "title": furniture.FAMILY,
             "branch-tags": furniture.TAG_ATTRS, "sign-caption": furniture.FAMILY,
             "credit": furniture.FAMILY}
    return render.svg(runs, stations, transfers, outline, layers, attrs)


def water_check(placed, stations):
    """Labels avoid water; light holes stay off it too."""
    rivers, areas = water.build(stations)
    bad, worst = [], None
    for l in placed:
        gap = water.box_gap(l["box"], rivers, areas)
        if worst is None or gap < worst[0]:
            worst = (gap, l["text"])
        if gap < water.LABEL_GAP - 1e-6:
            bad.append("%s: %.1f mm from water" % (l["text"], gap))
    return {"name": "8b. Labels avoid water (at least %.0f mm clear)" % water.LABEL_GAP, "ok": not bad,
            "worst": "%.1f mm: %s" % worst, "detail": bad}


def furniture_checks(runs, stations, transfers, placed):
    """The branch tags must not touch anything either; lights should not sit under water."""
    out = []
    bad = []
    for text, box, _ in furniture.tags(stations):
        hits = lab.problems(box, [], runs, stations, transfers, placed)
        if hits:
            bad.append("%s: touches %s" % (text, ", ".join(sorted(set(hits)))))
    out.append({"name": "Extra: the four branch tags touch nothing", "ok": not bad,
                "worst": "none" if not bad else bad[0], "detail": bad})
    rivers, areas = water.build(stations)
    bad, worst = [], None
    for s in stations:
        for which in ("A", "B"):
            gap = water.point_gap(s[which], rivers, areas)
            if worst is None or gap < worst[0]:
                worst = (gap, "%s %s light %s" % (s["line"], s["name"], which))
            if gap < water.HOLE - 1e-6:
                bad.append("%s %s light %s: %.1f mm from water" % (s["line"], s["name"], which, gap))
    out.append({"name": "Extra: no light's 8 mm hole under water", "ok": not bad,
                "worst": "%.1f mm from the center of %s" % worst, "detail": bad})
    return out


def main():
    runs, stations, transfers, placed = build()

    counts = {}
    for s in stations:
        counts[s["line"]] = counts.get(s["line"], 0) + 1
    checks = validate.check_all(runs, stations) + [label_check(placed, stations), water_check(placed, stations)]
    extra = validate.extra_checks(runs, stations) + furniture_checks(runs, stations, transfers, placed)
    ok = all(c["ok"] for c in checks) and counts == EXPECTED

    report = ["# Map validation report", "",
              "Generated by `tools/map/generate.py`. Stage 3: the whole print.", "",
              "## Network", "",
              "- %d stations (expected 132): %s%s" % (len(stations), ", ".join("%s %d" % (k, counts.get(k, 0))
                                                                               for k in EXPECTED),
                                                      "" if counts == EXPECTED else "  **MISMATCH**"),
              "- %d lights, two per station" % (2 * len(stations)),
              "- %d interchanges: %s" % (len(transfers), ", ".join(sorted(transfers))), "",
              "## Hard constraints", ""]
    report += validate.report_lines(checks)
    report += ["", "## Extra checks", ""]
    report += validate.report_lines(extra)

    report += ["", "## Overrides", ""]
    if overrides.GEOMETRY or overrides.LABELS:
        for key, v in overrides.GEOMETRY.items():
            report.append("- **%s %s** moved (%+.1f, %+.1f) mm: %s" % (key[0], key[1], v[0], v[1], v[2]))
        for key, v in overrides.LABELS.items():
            report.append("- **%s**: %s" % (key, v.get("reason", "(no reason given)")))
    else:
        report.append("None.")

    short = [l for l in placed if l["short"]]
    two = [l for l in placed if len(l["lines"]) > 1]
    report += ["", "## Abbreviations and two-line labels", "",
               "Short forms used (%d): %s" % (len(short), "; ".join("%s for %s" % (l["text"], l["name"])
                                                                    for l in short) or "none"), "",
               "Two-line labels (%d): %s" % (len(two), "; ".join(l["name"] for l in two) or "none"),
               "", "## Every label", "",
               "| Station | Label | Line | Side | Distance mm | Follows its rule |", "|---|---|---|---|---|---|"]
    for l in sorted(placed, key=lambda l: (l["anchor"]["branch"], l["name"])):
        follows = "yes" if not (l["override"] or l["moved"]) else "override: " + (l["override"] or "")
        if l["problems"]:
            follows += " **(overlaps: %s)**" % ", ".join(sorted(set(l["problems"])))
        report.append("| %s | %s | %s | %s | %.1f | %s |" % (
            l["name"], l["text"].replace("\n", " / "), l["anchor"]["branch"], lab.SIDE_WORDS[l["side"]], l["dist"],
            follows))
    text = "\n".join(report) + "\n"
    summary = text.split("## Every label")[0]
    if not ok:
        print(summary)
        print("Nothing was written: the checks above failed, so the files in data/ are still the last good ones.")
        return 1

    for name, outline in (("print_no_outline.svg", False), ("print_with_outline.svg", True)):
        with open(os.path.join(DATA, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(print_svg(runs, stations, transfers, placed, outline))

    with open(os.path.join(DATA, "stations.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["line", "station", "x_mm", "y_mm", "light_A_x", "light_A_y", "light_B_x", "light_B_y",
                    "light_A_lights_for_trains_heading_toward", "branch"])
        for s in stations:
            w.writerow([s["line"], s["name"]] + ["%.2f" % v for v in (s["x"], s["y"], s["A"][0], s["A"][1],
                                                                       s["B"][0], s["B"][1])]
                       + [s["toward"], s["branch"]])

    with open(os.path.join(DATA, "validation_report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
