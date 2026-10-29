"""Tests for the MBTA LED map simulator (standard library only).

  python -m unittest discover -s tests -v

Offline by default. Tests that call the MBTA API run only when asked:

  set RUN_NETWORK_TESTS=1      (PowerShell: $env:RUN_NETWORK_TESTS = "1")

They read the key from .env like the server does; the key is never printed.
"""
import csv
import math
import os
import json
import subprocess
import sys
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usefixtures  # noqa: E402,F401  (first: the tests use the committed lookup tables, not cache/)

from sim import cache_path, directions  # noqa: E402
from sim import layout  # noqa: E402
from sim import sample  # noqa: E402
import leds as L  # noqa: E402    the board's own files, from firmware/ (see sim/__init__.py)
import sign as S  # noqa: E402

DATA = os.path.join(ROOT, "data")
NETWORK = os.environ.get("RUN_NETWORK_TESTS") == "1"
SETTINGS = {"brightness": 0.3}


def read_text(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def read_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


ROUTES = ["Red", "Mattapan", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"]


def route_stops():
    """The API's stop order per route (direction 0), from the tests' lookup tables."""
    with open(cache_path("route_stops.json"), encoding="utf-8") as f:
        return json.load(f)


def route_names():
    with open(cache_path("route_directions.json"), encoding="utf-8") as f:
        return json.load(f)


def load_map():
    stations = layout.load_stations(route_stops())
    return stations, L.build_index(stations), layout.load_wiring(stations)


def named(stations, line, station):
    return [i for i, s in enumerate(stations) if s["line"] == line and s["station"] == station][0]


def rgb_of(chains, wiring, light):
    for output in wiring:
        if light in wiring[output]:
            return chains[output][wiring[output].index(light)]


# --- data files
class DataFiles(unittest.TestCase):
    def test_stations(self):
        rows = read_csv("stations.csv")
        self.assertEqual(len(rows), 132)
        counts = {}
        for r in rows:
            counts[r["line"]] = counts.get(r["line"], 0) + 1
        self.assertEqual(counts, {"RL": 22, "M": 8, "OL": 20, "BL": 12, "GL": 70})
        ids = {(r["line"], r["station"]): r for r in read_csv("station_ids.csv")}
        self.assertEqual(len(ids), 132)
        for r in rows:
            self.assertTrue(ids[(r["line"], r["station"])]["stop_id"].startswith("place-"), r)
            for side in ("A", "B"):                             # each light 7 mm from the station
                d = math.hypot(float(r["light_%s_x" % side]) - float(r["x_mm"]),
                               float(r["light_%s_y" % side]) - float(r["y_mm"]))
                self.assertAlmostEqual(d, 7.0, delta=0.02)
        per_line = [(r["line"], r["stop_id"]) for r in ids.values()]
        self.assertEqual(len(per_line), len(set(per_line)))     # no station matched twice on a line
        unsure = [r["station"] for r in ids.values() if r["match"].startswith("uncertain")]
        self.assertEqual(unsure, ["Northeastern"])              # checked by hand: Northeastern University

    def test_wiring_plan(self):
        rows = read_csv("wiring_plan.csv")
        self.assertEqual(list(rows[0]), ["output", "index", "station", "line", "light"])
        stations = layout.load_stations()
        wiring = layout.load_wiring(stations)                   # raises on a missing or doubled light
        self.assertEqual(sorted(wiring), [1, 2, 3])
        lights = sorted(n for chain in wiring.values() for n in chain if n >= 0)
        self.assertEqual(lights, list(range(264)))
        cfg = layout.load_config()
        counts = layout.output_counts(cfg, wiring)
        self.assertEqual(counts, [100, 100, 100])               # two strings of 50 on each output
        for n, output in enumerate(sorted(wiring)):
            self.assertLessEqual(len(wiring[output]), counts[n])
        # No wire has to stretch: straight-line runs, shared across SKIP pixels, within reach.
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import wiring_plan
        reach = wiring_plan.reach(cfg)
        self.assertLessEqual(reach, 85)                         # the spec's limit; these strings give 72
        for o in wiring_plan.measure(stations, wiring):
            for per_wire, total, skips, a, b in o["runs"]:
                self.assertLessEqual(per_wire, reach + 0.05, (o["output"], a, b))
        self.assertLessEqual(sum(o["skips"] for o in wiring_plan.measure(stations, wiring)), 8)

    def test_wiring_tool_keeps_an_edited_plan(self):
        before = read_text(os.path.join(DATA, "wiring_plan.csv"))
        out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "wiring_plan.py")],
                             capture_output=True, text=True, cwd=ROOT, timeout=120)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("--force", out.stdout)
        self.assertEqual(read_text(os.path.join(DATA, "wiring_plan.csv")), before)
        md = read_text(os.path.join(DATA, "wled_settings.md"))
        for line in ("| 1 | 21 | 0 | 100 |", "| 2 | 22 | 100 | 100 |", "| 3 | 19 | 200 | 100 |"):
            self.assertIn(line, md)

    def test_api_key_is_not_in_any_file(self):
        env = os.path.join(ROOT, ".env")
        if not os.path.exists(env):
            self.skipTest("no .env")
        key = ""
        for line in read_text(env).lstrip("\ufeff").splitlines():
            if line.startswith("MBTA_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
        self.assertTrue(key)
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".venv", ".git", "__pycache__")]
            for name in files:
                path = os.path.join(base, name)
                if os.path.abspath(path) == os.path.abspath(env) or name.endswith(".zip"):
                    continue
                try:
                    text = read_text(path)
                except OSError:
                    continue
                self.assertNotIn(key, text, f"API key found in {path}")

    def test_env_is_gitignored(self):
        lines = read_text(os.path.join(ROOT, ".gitignore")).split()
        self.assertIn(".env", lines)


# --- lighting module
class Directions(unittest.TestCase):
    """Which direction_id lights light A, worked out from the API's stop order."""

    @classmethod
    def setUpClass(cls):
        cls.stations = layout.load_stations(route_stops())
        cls.names = route_names()
        cls.by_branch = {}
        for s in cls.stations:
            cls.by_branch.setdefault(s["branch"], []).append(s)

    def test_every_line_and_branch(self):
        """Light A's direction, by the API's own destination for it, matches the
        direction the stations file gives in plain words."""
        want = {  # branch: (the routes that run on it, where light A's direction ends up, a word from the file)
            "Red": (["Red"], "Ashmont/Braintree", "southbound"),
            "Red Ashmont": (["Red"], "Ashmont/Braintree", "southbound"),
            "Red Braintree": (["Red"], "Ashmont/Braintree", "southbound"),
            "Mattapan": (["Mattapan"], "Mattapan", "outbound"),
            "Orange": (["Orange"], "Forest Hills", "southbound"),
            "Blue": (["Blue"], "Wonderland", "eastbound"),
            "Green trunk": (["Green-B", "Green-C", "Green-D", "Green-E"], None, "westbound"),
            "Green Union Sq": (["Green-D"], "Riverside", "westbound"),
            "Green B": (["Green-B"], "Boston College", "westbound"),
            "Green C": (["Green-C"], "Cleveland Circle", "westbound"),
            "Green D": (["Green-D"], "Riverside", "westbound"),
            "Green E": (["Green-E"], "Heath Street", "westbound"),
        }
        self.assertEqual(set(self.by_branch), set(want))
        ends = {"Green-B": "Boston College", "Green-C": "Cleveland Circle", "Green-D": "Riverside",
                "Green-E": "Heath Street"}
        for branch, (routes, destination, word) in want.items():
            seen = set()
            for s in self.by_branch[branch]:
                self.assertIn(word, s["toward"], (branch, s["station"]))
                self.assertTrue(s["a_dir"], (branch, s["station"]))
                for route, d in s["a_dir"].items():
                    seen.add(route)
                    self.assertIn(route, routes, (branch, s["station"]))
                    self.assertEqual(self.names[route][d][1], destination or ends[route], (branch, s["station"], route))
            self.assertEqual(seen, set(routes), branch)

    def test_a_train_lights_the_light_on_its_right(self):
        """Along every route, both ways, the light a train lights is on its right-hand side."""
        index = L.build_index(self.stations)
        table = route_stops()
        checked = set()
        for route in ROUTES:
            stops = table[route]
            for k in range(len(stops) - 1):
                if (stops[k], stops[k + 1]) == ("place-asmnl", "place-nqncy"):
                    continue                    # the list runs on from one Red branch to the other
                line = L.ROUTE_LINE[route]
                a, b = self.stations[index[line + "|" + stops[k]]], self.stations[index[line + "|" + stops[k + 1]]]
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                for d, sign in ((0, 1), (1, -1)):           # direction 1 runs the other way
                    for s in (a, b):
                        v = {"route": route, "stop": s["stop_id"], "status": "STOPPED_AT", "direction_id": d}
                        (n,) = L.lights_for_vehicle(v, self.stations, index, {})
                        p = s["B" if n % 2 else "A"]
                        right = (-dy * sign, dx * sign)     # screen coordinates, y down
                        side = (p[0] - s["x"]) * right[0] + (p[1] - s["y"]) * right[1]
                        if abs(side) < 0.7 * 7 * math.hypot(dx, dy):
                            continue                # the line turns between the two: this hop isn't the track here
                        self.assertGreater(side, 0, (route, d, s["station"]))
                        checked.add((route, d, s["stop_id"]))
        self.assertEqual(len(checked), 2 * sum(len(table[r]) for r in ROUTES))  # every stop of every route, both ways

    def test_not_hardcoded(self):
        """Turn the API's stop order round and every answer flips."""
        table = route_stops()
        flipped = {r: table[r][::-1] for r in table}
        flipped["Red"] = table["Red"][::-1]
        other = layout.load_stations(flipped)
        for s, o in zip(self.stations, other):
            self.assertEqual(set(s["a_dir"]), set(o["a_dir"]))
            for route in s["a_dir"]:
                self.assertEqual(o["a_dir"][route], 1 - s["a_dir"][route], (s["station"], route))

class Lighting(unittest.TestCase):
    def setUp(self):
        self.stations, self.index, self.wiring = load_map()
        self.parents = {"70061": "place-alfcl", "70094": "place-asmnl"}

    def states(self, vehicles, riding=None):
        return L.light_states(vehicles, self.stations, self.index, self.parents, riding)

    def light(self, line, station, direction_id, route):
        """The light a train of `route` heading `direction_id` lights at a station."""
        i = named(self.stations, line, station)
        return 2 * i if self.stations[i]["a_dir"][route] == direction_id else 2 * i + 1

    def at(self, chains, line, station, direction_id, route):
        return rgb_of(chains, self.wiring, self.light(line, station, direction_id, route))

    def test_output_is_one_rgb_array_per_output_in_wiring_order(self):
        chains = L.render(self.states([]), self.stations, self.wiring, SETTINGS)
        self.assertEqual({c: len(v) for c, v in chains.items()}, {c: len(v) for c, v in self.wiring.items()})
        self.assertEqual(sum(len(v) for v in chains.values()), 264 + 5)     # the lights and the SKIP pixels
        for chain in chains.values():
            for rgb in chain:
                self.assertEqual(len(rgb), 3)
                for v in rgb:
                    self.assertIsInstance(v, int)
                    self.assertTrue(0 <= v <= 255)
        self.assertEqual(chains[1][0], (0, 0, 0))            # no train: off

    def test_only_a_stopped_train_lights_its_station(self):
        v = [{"route": "Red", "stop": "70061", "status": "STOPPED_AT", "direction_id": 0},
             {"route": "Red", "stop": "place-harsq", "status": "INCOMING_AT", "direction_id": 0},
             {"route": "Red", "stop": "place-portr", "status": "IN_TRANSIT_TO", "direction_id": 1}]
        chains = L.render(self.states(v), self.stations, self.wiring, SETTINGS)
        red = L.LINE_COLORS["RL"]
        self.assertEqual(self.at(chains, "RL", "Alewife", 0, "Red"), red)                   # platform ID -> parent
        for station, d in (("Alewife", 1), ("Harvard", 0), ("Harvard", 1), ("Porter", 0), ("Porter", 1), ("Davis", 0)):
            self.assertEqual(self.at(chains, "RL", station, d, "Red"), (0, 0, 0), station)   # trains on their way light nothing
        self.assertEqual(sum(1 for s in self.states(v) if s), 1)

    def test_both_lights_of_a_station_at_once(self):
        v = [{"route": "Orange", "stop": "place-rugg", "status": "STOPPED_AT", "direction_id": 0},
             {"route": "Orange", "stop": "place-rugg", "status": "STOPPED_AT", "direction_id": 1}]
        chains = L.render(self.states(v), self.stations, self.wiring, SETTINGS)
        orange = L.LINE_COLORS["OL"]
        self.assertEqual(self.at(chains, "OL", "Ruggles", 0, "Orange"), orange)
        self.assertEqual(self.at(chains, "OL", "Ruggles", 1, "Orange"), orange)

    def test_a_train_someone_is_riding_is_purple(self):
        v = [{"id": "R-1", "route": "Red", "stop": "place-harsq", "status": "STOPPED_AT", "direction_id": 0},
             {"id": "R-2", "route": "Red", "stop": "place-portr", "status": "IN_TRANSIT_TO", "direction_id": 0}]
        chains = L.render(self.states(v, {"R-2": True}), self.stations, self.wiring, SETTINGS)
        self.assertEqual(self.at(chains, "RL", "Harvard", 0, "Red"), L.LINE_COLORS["RL"])
        self.assertEqual(self.at(chains, "RL", "Porter", 0, "Red"), L.RIDER_COLOR)     # full purple, moving or not

# --- sign module
class Sign(unittest.TestCase):
    def test_countdown_rules(self):
        now = S.parse_iso("2026-09-28T17:00:00-04:00")

        def at(sec, **kw):
            t = datetime.fromtimestamp(now + sec).astimezone().isoformat(timespec="seconds")
            return dict({"departure_time": t}, **kw)
        self.assertEqual(S.countdown(at(30), now), "NOW")
        self.assertEqual(S.countdown(at(-20), now), "NOW")
        self.assertIsNone(S.countdown(at(-40), now))
        self.assertEqual(S.countdown(at(125), now), "2")
        self.assertEqual(S.countdown(at(3700), now), "60+")
        self.assertIsNone(S.countdown({"departure_time": None}, now))               # arrival-only: not boardable
        self.assertIsNone(S.countdown(at(300, schedule_relationship="CANCELLED"), now))
        preds = [at(300, headsign="Braintree"), at(-100), at(600, headsign="Ashmont"), at(900)]
        self.assertEqual(S.row_times(preds, now), [["5", ""], ["10", ""]])
        self.assertEqual(S.row_times(preds, now, branch_letter=True), [["5", "B"], ["10", "A"]])
        self.assertEqual(S.row_times(preds, now, walk_minutes=6), [["10", ""], ["15", ""]])     # skips the 5

    def test_alert_filter(self):
        alerts = [{"header": "Red Line delays", "effect": "DELAY", "severity": 5, "entities": []},
                  {"header": "minor", "effect": "STATION_ISSUE", "severity": 1, "entities": [{"stop": "70001"}]},
                  {"header": "my stop moved", "effect": "STOP_MOVE", "severity": 1, "entities": [{"stop": "23151"}]},
                  {"header": "elevator", "effect": "ELEVATOR_CLOSURE", "severity": 7, "entities": [{"stop": "23151"}]},
                  {"header": "at Alewife", "effect": "STATION_ISSUE", "severity": 1, "entities": [{"stop": "70061"}]}]
        text = S.alert_text(alerts, {"23151": True, "place-alfcl": True}, {"70061": "place-alfcl"})
        self.assertIn("RED LINE DELAYS", text)
        self.assertIn("MY STOP MOVED", text)
        self.assertIn("AT ALEWIFE", text)                      # names my stop via its platform
        self.assertNotIn("MINOR", text)
        self.assertNotIn("ELEVATOR", text)

# --- the print
# --- the first start
class FirstStart(unittest.TestCase):
    def test_without_the_internet_it_says_why_and_stops_cleanly(self):
        import server
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as empty:        # no lookup tables yet
            with mock.patch.dict(os.environ, {"MBTA_CACHE_DIR": empty}),                     mock.patch.object(server.mbta_api, "get", side_effect=server.mbta_api.ApiError("Network error for /stops")),                     mock.patch.object(sys, "argv", ["server.py"]):
                with self.assertRaises(SystemExit) as caught:
                    server.main()
        self.assertIn("internet", str(caught.exception))
        self.assertIn("Network error for /stops", str(caught.exception))


# --- server (in process)
class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.server = server
        cls.app = server.Simulator()
        server.SIM = cls.app

    def test_layout(self):
        j = self.app.layout_json()
        self.assertEqual(len(j["lights"]), 264)
        self.assertEqual(len(self.app.layout_id), 12)
        self.assertEqual(j["output_leds"], [100, 100, 100])
        w = j["sign_window"]                                # the print's sign-window-cut rectangle
        self.assertAlmostEqual(w["x"] + w["w"], 610 - 32.35 - 1, places=2)
        self.assertAlmostEqual(w["y"] + w["h"], 610 - 32.35 - 1, places=2)
        self.assertAlmostEqual(w["w"], 315.5, places=2)
        where = sorted((l["output"], l["index"]) for l in j["lights"])
        self.assertEqual(len(set(where)), 264)
        alewife = [l for l in j["lights"] if l["station"] == "Alewife"]
        self.assertEqual([l["toward"] for l in alewife], ["South to Ashmont/Braintree", "North to Alewife"])
        for outline, mark in (("0", False), ("1", True)):   # both prints are served
            svg = read_text(layout.PRINTS[outline == "1"])
            self.assertEqual('stroke-width="0.5"' in svg, mark)

    def test_sign_runs_the_board_code(self):
        s = self.app.sign({"source": "sample:typical"})
        self.assertEqual((s["w"], s["h"]), (64, 32))
        self.assertEqual(len(s["rows"]), 32)
        self.assertTrue(all(len(r) == 64 for r in s["rows"]))
        self.assertEqual(len(s["palette"]), 16)
        self.assertEqual([r["label"] for r in s["debug"]["rows"]], ["77", "RL"])


# --- MBTA API (opt-in)
@unittest.skipUnless(NETWORK, "set RUN_NETWORK_TESTS=1 to call the MBTA API")
class Network(unittest.TestCase):
    def test_key_is_used(self):
        from sim import mbta_api
        _, remaining = mbta_api.get("/routes/Red", {"fields[route]": "long_name"})
        self.assertGreater(int(remaining), 20, "rate limit looks anonymous; is the key loaded?")

    def test_every_live_vehicle_maps_or_has_no_stop(self):
        from sim import live, mbta_api
        stations, index, wiring = load_map()
        parents = live.stop_parents()
        d, _ = mbta_api.get("/vehicles", {"filter[route]": ",".join(ROUTES),
                                          "fields[vehicle]": "current_status,direction_id,stop"})
        for v in d["data"]:
            rel = v["relationships"]
            self.assertIn("stop", rel)
            self.assertEqual(set(v["attributes"]), {"current_status", "direction_id"})
            stop = (rel["stop"].get("data") or {}).get("id")
            if stop is None:
                continue
            vehicle = {"route": rel["route"]["data"]["id"], "stop": stop,
                       "direction_id": v["attributes"]["direction_id"]}
            if stop not in parents and not stop.startswith("place-"):
                continue                                     # a platform the board looks up on demand
            self.assertEqual(len(L.lights_for_vehicle(vehicle, stations, index, parents)), 1, vehicle)

    def test_direction_table_matches_the_api_today(self):
        from sim import live
        fresh = {}
        from sim import mbta_api
        for route in ROUTES:
            d, _ = mbta_api.get("/stops", {"filter[route]": route, "filter[direction_id]": 0, "fields[stop]": "name"})
            fresh[route] = [s["id"] for s in d["data"]]
        self.assertEqual(fresh, {r: live.route_stops(ROUTES)[r] for r in ROUTES})


if __name__ == "__main__":
    unittest.main()
