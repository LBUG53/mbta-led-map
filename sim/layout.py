"""Load the map (stations, lights, wiring) and the config (simulator side)."""
import csv
import os

import yaml

import leds as ledlib      # firmware/leds.py (see sim/__init__.py)

from . import ROOT, directions

DATA = os.path.join(ROOT, "data")
STATIONS = os.path.join(DATA, "stations.csv")
STATION_IDS = os.path.join(DATA, "station_ids.csv")
WIRING = os.path.join(DATA, "wiring_plan.csv")
PRINTS = {False: os.path.join(DATA, "print_no_outline.svg"), True: os.path.join(DATA, "print_with_outline.svg")}
STRING = 50                 # pixels per string


def load_build():
    """build.yaml: the measured sizes of the physical parts."""
    with open(os.path.join(ROOT, "build.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config():
    """config.yaml, or config.example.yaml when there isn't one yet. MBTA_CONFIG names another file: the tests
    use it to read config.example.yaml, whatever private config.yaml is lying around."""
    path = os.environ.get("MBTA_CONFIG") or os.path.join(ROOT, "config.yaml")
    if not os.path.exists(path):
        path = os.path.join(ROOT, "config.example.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_stations(route_stops=None):
    """One dict per station, in the stations file's (drawing) order, with its
    MBTA stop_id, its two lights, and (given route_stops) which direction lights light A."""
    with open(STATION_IDS, newline="", encoding="utf-8") as f:
        ids = {(r["line"], r["station"]): r["stop_id"] for r in csv.DictReader(f)}
    out = []
    with open(STATIONS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append({
                "line": r["line"], "station": r["station"], "branch": r["branch"],
                "stop_id": ids[(r["line"], r["station"])],
                "x": float(r["x_mm"]), "y": float(r["y_mm"]),
                "A": (float(r["light_A_x"]), float(r["light_A_y"])),
                "B": (float(r["light_B_x"]), float(r["light_B_y"])),
                "toward": r["light_A_lights_for_trains_heading_toward"],
            })
    if route_stops is not None:
        problems = directions.light_a_directions(out, route_stops)
        if problems:
            raise ValueError("direction table: " + "; ".join(problems))
    return out


def load_wiring(stations, path=WIRING):
    """{output number: [light index, or -1 for a SKIP pixel]} in wiring order, from
    the wiring plan (which the owner edits after wiring). Light index = station * 2,
    plus 1 for light B."""
    where = {(s["line"], s["station"]): i for i, s in enumerate(stations)}
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.setdefault(int(r["output"]), []).append((int(r["index"]), r))
    wiring, used = {}, {}
    for output in sorted(rows):
        chain = []
        for n, (index, r) in enumerate(sorted(rows[output], key=lambda t: t[0])):
            if index != n:
                raise ValueError("wiring plan: output %d has no pixel %d" % (output, n))
            if r["light"] == "SKIP":
                chain.append(-1)
                continue
            key = (r["line"], r["station"])
            if key not in where or r["light"] not in ("A", "B"):
                raise ValueError("wiring plan: output %d pixel %d names an unknown light" % (output, index))
            light = where[key] * 2 + (r["light"] == "B")
            if light in used:
                raise ValueError("wiring plan: %s %s light %s is wired twice" % (r["line"], r["station"], r["light"]))
            used[light] = True
            chain.append(light)
        wiring[output] = chain
    missing = [i for i in range(2 * len(stations)) if i not in used]
    if missing:
        s = stations[missing[0] // 2]
        raise ValueError("wiring plan: %d lights are not wired (first: %s %s)" % (len(missing), s["line"], s["station"]))
    return wiring


def output_counts(cfg, wiring):
    """LEDs per output as set up in WLED: config hardware.outputs, else whole strings of 50."""
    counts = (cfg.get("hardware") or {}).get("outputs") or []
    out = []
    for n, output in enumerate(sorted(wiring)):
        need = len(wiring[output])
        count = int(counts[n]) if n < len(counts) and counts[n] else -(-need // STRING) * STRING
        if count < need:
            raise ValueError("config hardware.outputs: output %d needs %d LEDs, set to %d" % (output, need, count))
        out.append(count)
    return out


def line_colors(cfg):
    """LINE_COLORS and the RIDER color, with any map.colors overrides ("#RRGGBB") from config."""
    colors = dict(ledlib.LINE_COLORS)
    colors["RIDER"] = ledlib.RIDER_COLOR
    for line, hexcolor in ((cfg.get("map") or {}).get("colors") or {}).items():
        h = hexcolor.lstrip("#")
        colors[line] = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return colors
