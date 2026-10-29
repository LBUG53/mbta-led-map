"""The power wiring guide: a step-by-step page with the circuit drawn for each step.

  python tools/power_guide.py      writes data/power_guide.html

Open it in a browser beside the panel: lever nuts, the trunk from the supply, the sign, the Matrix
Portal, the Sparkle Motion and (if needed) the far ends of the light chains, then the checks with a
multimeter before power goes on. The back-view map shows every light, colored by output, from
data/stations.csv and data/wiring_plan.csv. The page remembers what you have ticked, in that browser.
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim import layout  # noqa: E402

FACE = layout.load_build()["panel"]["size"]     # the back view is the front mirrored: x -> FACE - x
TEMPLATE = os.path.join(ROOT, "tools", "power_guide.html")
OUT = os.path.join(ROOT, "data", "power_guide.html")


def build():
    with open(os.path.join(ROOT, "data", "stations.csv"), encoding="utf-8") as f:
        stations = {(r["line"], r["station"]): r for r in csv.DictReader(f)}
    lights = {}
    with open(os.path.join(ROOT, "data", "wiring_plan.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["light"] == "SKIP":
                continue
            s = stations[(r["line"], r["station"])]
            lights.setdefault(r["output"], []).append(
                [round(FACE - float(s["light_%s_x" % r["light"]]), 1), round(float(s["light_%s_y" % r["light"]]), 1)])
    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(page.replace("__PTS__", json.dumps(lights)))
    return lights


if __name__ == "__main__":
    lights = build()
    print("wrote data/power_guide.html: %d lights on %d outputs" % (sum(len(v) for v in lights.values()), len(lights)))
