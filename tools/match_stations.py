r"""Match the map's 132 station names to MBTA parent station IDs (place-xxxx).

  python tools/match_stations.py

Reads data/stations.csv, asks the MBTA API which stations each route
serves, and writes data/station_ids.csv (line, station, stop_id,
mbta_name, match). Matches that needed more than expanding an abbreviation
are marked "uncertain" and printed, for a person to check.
"""
import csv
import difflib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim import mbta_api  # noqa: E402

DATA = os.path.join(ROOT, "data")
ROUTES = {"RL": ["Red"], "M": ["Mattapan"], "OL": ["Orange"], "BL": ["Blue"],
          "GL": ["Green-B", "Green-C", "Green-D", "Green-E"]}
WORDS = {"sq": "square", "st": "street", "ave": "avenue", "rd": "road", "ctr": "center", "centre": "center",
         "mass": "massachusetts", "govt": "government", "bu": "boston university", "hts": "heights"}


def normal(name):
    """Lower case, no punctuation, abbreviations spelled out ("St." first = Saint)."""
    s = name.lower().replace("'", "").replace("’", "")
    s = re.sub(r"^st\.?\s", "saint ", s)
    words = re.split(r"[^a-z0-9]+", s)
    return " ".join(WORDS.get(w, w) for w in words if w)


def route_stations(route):
    """[(place-id, name)] for every station on a route, from the API."""
    d, _ = mbta_api.get("/stops", {"filter[route]": route, "fields[stop]": "name"})
    return [(s["id"], s["attributes"]["name"]) for s in d["data"]]


def match(name, candidates):
    """(stop id, MBTA name, how) for the best candidate."""
    want = normal(name)
    by_normal = {normal(n): (i, n) for i, n in candidates}
    if want in by_normal:
        i, n = by_normal[want]
        return i, n, "exact" if n.lower() == name.lower() else "abbreviation"
    starts = [(i, n) for i, n in candidates if normal(n).startswith(want + " ") or want.startswith(normal(n) + " ")]
    if len(starts) == 1:
        return starts[0][0], starts[0][1], "uncertain (one name starts with the other)"
    close = difflib.get_close_matches(want, list(by_normal), n=1, cutoff=0.0)
    i, n = by_normal[close[0]]
    return i, n, "uncertain (closest name)"


def main():
    with open(os.path.join(DATA, "stations.csv"), newline="", encoding="utf-8") as f:
        stations = [(r["line"], r["station"]) for r in csv.DictReader(f)]
    served = {}
    for line, routes in ROUTES.items():
        seen = {}
        for route in routes:
            for i, n in route_stations(route):
                seen[i] = n
        served[line] = list(seen.items())
    rows, unsure = [], []
    for line, name in stations:
        stop_id, mbta_name, how = match(name, served[line])
        rows.append([line, name, stop_id, mbta_name, how])
        if how.startswith("uncertain"):
            unsure.append(rows[-1])
    with open(os.path.join(DATA, "station_ids.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["line", "station", "stop_id", "mbta_name", "match"])
        w.writerows(rows)
    ids = [(r[0], r[2]) for r in rows]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    counts = {}
    for r in rows:
        counts[r[4].split(" (")[0]] = counts.get(r[4].split(" (")[0], 0) + 1
    print("matched %d stations: %s" % (len(rows), ", ".join("%d %s" % (v, k) for k, v in sorted(counts.items()))))
    for r in unsure:
        print("  check: %s %-22s -> %s  %s  [%s]" % tuple(r))
    for line, i in dupes:
        print("  DUPLICATE on %s: %s" % (line, i))
    unused = {line: [n for i, n in served[line] if (line, i) not in ids] for line in served}
    for line, names in unused.items():
        if names:
            print("  MBTA stations on %s with no light: %s" % (line, ", ".join(names)))
    return 1 if dupes else 0


if __name__ == "__main__":
    sys.exit(main())
