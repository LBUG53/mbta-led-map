"""Tests for the printed tiles (hardware/make_tile.py): every pixel's hole, and its number, must be right.

  python -m unittest tests.test_tiles -v
Needs manifold3d (pip install -r hardware/requirements.txt); skipped without it.
"""
import contextlib
import csv
import io
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hardware"))

try:
    import make_tile as T
    AVAILABLE = True
except ImportError:         # manifold3d is not installed
    AVAILABLE = False

DATA = os.path.join(ROOT, "data")


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@unittest.skipUnless(AVAILABLE, "needs manifold3d: pip install -r hardware/requirements.txt")
class Tiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plans = T.make_plans()
        cls.stations = [s for p in cls.plans.values() for s in p["stations"]]

    def test_every_station_is_on_exactly_one_tile(self):
        names = [s["name"] for s in self.stations]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(names), len(read("stations.csv")))

    def test_each_collar_sits_over_its_light(self):
        """Tile coordinates are the panel seen from behind, so a light at (x, y) on the front is at (-x, -y)."""
        front = {}
        for r in read("stations.csv"):
            front[r["line"] + " " + r["station"]] = {k: (float(r["light_%s_x" % k]), float(r["light_%s_y" % k])) for k in "AB"}
        for s in self.stations:
            for k in "ab":
                x, y = s[k]
                want = front[s["name"]][k.upper()]
                self.assertAlmostEqual(-x, want[0], places=1, msg=s["name"])
                self.assertAlmostEqual(-y, want[1], places=1, msg=s["name"])

    def test_the_two_collars_of_a_station_are_14_mm_apart(self):
        for s in self.stations:
            self.assertAlmostEqual(T.math.dist(s["a"], s["b"]), 14.0, places=1, msg=s["name"])

    def test_the_numbers_on_the_tiles_follow_the_wiring_plan(self):
        """Each hole's number plate says the pixel's place on its output; that must be where the plan puts it."""
        plan = {(r["line"] + " " + r["station"], r["light"]): (int(r["output"]), int(r["index"]))
                for r in read("wiring_plan.csv") if r["light"] != "SKIP"}
        self.assertEqual(len(plan), 2 * len(self.stations))
        for s in self.stations:
            self.assertEqual(s["wa"], plan[(s["name"], "A")], s["name"])
            self.assertEqual(s["wb"], plan[(s["name"], "B")], s["name"])

    def test_the_tiles_do_not_collide_and_each_fits_the_printer(self):
        """hardware/make_tile.py check: the same test the build guide asks for, run on the real tiles."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(sys, "argv", ["make_tile.py", "check"]):
            code = T.main()
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("fits", out.getvalue())


if __name__ == "__main__":
    unittest.main()
