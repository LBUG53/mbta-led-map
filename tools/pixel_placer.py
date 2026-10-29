"""The pixel placer: a page that shows where each pixel goes, one at a time, on the back of the panel.

  python tools/pixel_placer.py      writes data/pixel_placer.html

Open it in a browser on a phone or laptop beside the panel and step through each output in string
order: the pixel's number, its station, and its hole on a close-up of the back. Easier than reading
the numbers on black tiles. Made from data/stations.csv and data/wiring_plan.csv; run it again after
editing the plan. The page remembers where you stopped, in that browser.
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACE = 610.0        # the same mirror as tools/wiring_sheet.py: back-view x = FACE - front x
TEMPLATE = os.path.join(ROOT, "tools", "pixel_placer.html")
OUT = os.path.join(ROOT, "data", "pixel_placer.html")


def back(x):
    return round(FACE - float(x), 1)


def build():
    with open(os.path.join(ROOT, "data", "stations.csv"), encoding="utf-8") as f:
        stations = {(r["line"], r["station"]): r for r in csv.DictReader(f)}
    rows = []
    with open(os.path.join(ROOT, "data", "wiring_plan.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["light"] == "SKIP":
                rows.append([int(r["output"]), int(r["index"]), None, None, "SKIP", None, None])
                continue
            s = stations[(r["line"], r["station"])]
            light = r["light"]
            rows.append([int(r["output"]), int(r["index"]), r["station"], r["line"], light,
                         back(s["light_%s_x" % light]), round(float(s["light_%s_y" % light]), 1)])
    holes = []
    names = []
    for s in stations.values():
        for light in "AB":
            holes.append([back(s["light_%s_x" % light]), round(float(s["light_%s_y" % light]), 1)])
        names.append([s["station"], back(s["x_mm"]), round(float(s["y_mm"]), 1)])
    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(page.replace("__DATA__", json.dumps({"rows": rows, "holes": holes, "names": names})))
    return rows


if __name__ == "__main__":
    rows = build()
    print("wrote data/pixel_placer.html: %d pixels on %d outputs" % (len(rows), len({r[0] for r in rows})))
