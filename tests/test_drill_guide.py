"""Tests for the drilling guide (tools/drill_guide.py): a wrong hole here is a hole in the wrong place in the wood.

  python -m unittest tests.test_drill_guide -v
"""
import csv
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import drill_guide as G  # noqa: E402


def lights():
    """Every light's centre on the front of the panel, from the stations file."""
    with open(os.path.join(G.DATA, "stations.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [(r["line"], r["station"], k, float(r["light_%s_x" % k]), float(r["light_%s_y" % k]))
            for r in rows for k in ("A", "B")]


def holes_on(svg):
    """The (x, y) of every hole circle on the sheet: the circles drawn at the finished hole's size."""
    found = re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"/><path', svg)
    return sorted((float(x), float(y)) for x, y, r in found if abs(float(r) - G.HOLE / 2) < 1e-3)


class DrillGuide(unittest.TestCase):
    def test_every_light_gets_a_cross_where_the_back_view_puts_it(self):
        """Seen from behind, left and right swap: a light at x on the front is at (right edge - x) on the sheet."""
        svg, refs, count = G.build()
        x0, y0, x1, y1 = G.AREA
        expected = sorted((round(x1 - x, 2), round(y - y0, 2)) for _, _, _, x, y in lights())
        self.assertEqual(count, len(expected))
        self.assertEqual(count, 264)
        self.assertEqual(holes_on(svg), expected)

    def test_the_sheet_is_the_size_of_the_opening_in_the_frame(self):
        svg, _, _ = G.build()
        side = G.PANEL - 2 * G.FRAME
        self.assertIn('width="%gmm" height="%gmm" viewBox="0 0 %g %g"' % (side, side, side, side), svg)

    def test_the_grid_lines_are_50_mm_apart_so_the_scale_can_be_checked(self):
        """The guide says to measure 500 mm from the line marked 50 to the one marked 550."""
        svg, _, _ = G.build()
        across = sorted(float(x) for x in re.findall(r"M([\d.]+) 0 V", svg))
        self.assertGreaterEqual(len(across), 10)
        for a, b in zip(across, across[1:]):
            self.assertAlmostEqual(b - a, 50.0, places=2)
        x1 = G.AREA[2]
        self.assertEqual(sorted(round(x1 - x, 2) for x in across), sorted(round(float(v), 2) for v in range(50, 600, 50) if G.AREA[0] < v < x1))

    def test_the_six_reference_holes_are_the_tiles_locating_collars(self):
        _, refs, _ = G.build()
        self.assertEqual({name for name, _, _ in refs}, {name for _, name in G.LOCATING})
        front = {(line, station): (x, y) for line, station, k, x, y in lights() if k == "A"}
        for name, x, y in refs:
            line = [l for l, n in G.LOCATING if n == name][0]
            self.assertEqual((x, y), front[(line, name)], "measured on the FRONT of the panel, as the sheet says")

    def test_a_light_too_near_the_edge_of_the_sheet_stops_the_guide(self):
        line, station, k, x, y = lights()[0]
        with self.assertRaises(SystemExit):
            G.build((x - 1.0, y - 1.0, x + 200.0, y + 200.0))

    def test_an_area_with_no_lights_in_it_is_still_drawn_to_size(self):
        svg, refs, count = G.build((0.0, 0.0, 30.0, 30.0))
        self.assertEqual((count, refs), (0, []))
        self.assertIn('width="30mm" height="30mm"', svg)

    def test_pages_cover_the_whole_sheet_and_overlap_enough_to_join(self):
        for length, page in ((569.6, G.PAGE_W), (569.6, G.PAGE_H), (195.0, G.PAGE_W), (195.1, G.PAGE_W), (100.0, G.PAGE_H)):
            starts = G.page_starts(length, page)
            self.assertEqual(starts[0], 0.0)
            self.assertAlmostEqual(starts[-1] + min(page, length), length, places=6, msg="the last page is flush with the edge")
            for a, b in zip(starts, starts[1:]):
                self.assertGreaterEqual(a + page - b, G.MIN_OVERLAP - 1e-6, "neighbouring pages share a strip to join on")

    def test_the_pages_hold_every_cross_once(self):
        html, cols, rows = G.pages()
        self.assertEqual(cols * rows, html.count('<div class="page">'))
        self.assertEqual(html.count('<use href="#sheet"/>'), cols * rows)
        self.assertEqual(len(holes_on(html)), 264, "the sheet is defined once and each page is a window onto it")


if __name__ == "__main__":
    unittest.main()
