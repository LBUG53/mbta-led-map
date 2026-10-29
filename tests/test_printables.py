"""The pages printed or opened while building (tools/printables.py) can all be made, and agree with the plan.

  python -m unittest tests.test_printables -v
"""
import csv
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usefixtures  # noqa: E402,F401  (first: the tests use the committed lookup tables, not cache/)

from sim import layout  # noqa: E402
import pixel_placer  # noqa: E402
import power_guide  # noqa: E402
import sign_template  # noqa: E402
import test_page  # noqa: E402
import wiring_sheet  # noqa: E402


class Printables(unittest.TestCase):
    def test_pages_follow_the_wiring_plan(self):
        with open(os.path.join(ROOT, "data", "wiring_plan.csv"), encoding="utf-8") as f:
            plan = list(csv.DictReader(f))
        rows = pixel_placer.build()
        self.assertEqual([(r[0], r[1], r[4]) for r in rows],
                         [(int(p["output"]), int(p["index"]), p["light"]) for p in plan])
        lights = power_guide.build()
        self.assertEqual(sum(len(v) for v in lights.values()), sum(1 for p in plan if p["light"] != "SKIP"))
        for out in (pixel_placer.OUT, power_guide.OUT):
            with open(out, encoding="utf-8") as f:
                page = f.read()
            self.assertNotIn("__DATA__", page)
            self.assertNotIn("__PTS__", page)

    def test_templates(self):
        sign_template.build()
        test_page.build()
        w = sign_template.WIN
        self.assertAlmostEqual(sign_template.EDGE - w[2], 32.95, places=2)      # the window's right and bottom edges
        self.assertAlmostEqual(sign_template.EDGE - w[3], 32.95, places=2)
        self.assertAlmostEqual(sign_template.LEFT_X1, sign_template.LEFT_X0 + sign_template.PW)
        self.assertLess(sign_template.CORNER_X0, sign_template.LEFT_X1)         # the pages overlap

    def test_the_wiring_sheet_draws_the_sign_where_build_yaml_puts_it(self):
        build = layout.load_build()
        stations = layout.load_stations()
        svg = wiring_sheet.drawing(stations, layout.load_wiring(stations))
        x, y, w, h = [float(v) for v in re.search(
            r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" fill="#eee"', svg).groups()]
        self.assertEqual((w, h), (build["sign"]["width"], build["sign"]["height"]))
        self.assertAlmostEqual(x, build["sign"]["edge"], places=1)              # the back view is mirrored: its right edge is the left of the sheet
        self.assertAlmostEqual(y + h, build["panel"]["size"] - build["sign"]["edge"], places=1)
        self.assertNotIn("Sparkle Motion", svg, "where the boards go is hardware_back_view.html's job")

    def test_the_pages_it_writes_use_unix_line_endings(self):
        wiring_sheet.main()
        for name in ("wiring_back_view.html", "pixel_placer.html", "power_guide.html", "test_page.html",
                     "sign_window_template.html"):
            with open(os.path.join(ROOT, "data", name), "rb") as f:
                self.assertNotIn(b"\r\n", f.read(), name)

    def test_every_script_that_draws_the_panel_mirrors_about_the_panels_own_size(self):
        size = layout.load_build()["panel"]["size"]
        self.assertEqual(wiring_sheet.FACE, size)
        self.assertEqual(power_guide.FACE, size)


if __name__ == "__main__":
    unittest.main()
