"""Tests for the map generator (tools/map): the physical rules listed in
docs/HOW_IT_WORKS.md.

  python -m unittest tests.test_map -v
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "map"))

import furniture   # noqa: E402
import generate    # noqa: E402
import labels as lab  # noqa: E402
import layout      # noqa: E402
import overrides   # noqa: E402
import params as P  # noqa: E402
import render      # noqa: E402
import validate    # noqa: E402


class MapGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs, cls.stations, cls.transfers, cls.labels = generate.build()

    def test_hard_constraints(self):
        for check in validate.check_all(self.runs, self.stations):
            self.assertTrue(check["ok"], check["name"] + ": " + "; ".join(check["detail"][:5]))

    def test_extra_checks(self):
        for check in validate.extra_checks(self.runs, self.stations):
            self.assertTrue(check["ok"], check["name"] + ": " + "; ".join(check["detail"][:5]))

    def test_light_a_is_on_the_right_of_travel(self):
        by = {(s["line"], s["name"]): s for s in self.stations}
        oak = by[("OL", "Oak Grove")]            # heading south: right-hand side is west
        self.assertLess(oak["A"][0], oak["x"])
        bowdoin = by[("BL", "Bowdoin")]          # heading east: right-hand side is south
        self.assertGreater(bowdoin["A"][1], bowdoin["y"])
        mattapan = by[("M", "Mattapan")]         # heading west: right-hand side is north
        self.assertLess(mattapan["A"][1], mattapan["y"])

    def test_svg(self):
        for outline in (False, True):
            svg = generate.print_svg(self.runs, self.stations, self.transfers, self.labels, outline)
            self.assertIn('width="610mm" height="610mm" viewBox="0 0 610 610"', svg)
            for name in ("background", "water", "lines", "stations", "interchanges", "labels", "branch-tags",
                         "sign-caption", "credit", "sign-window-cut", "labels-halo", "termini"):
                self.assertIn('<g id="%s"' % name, svg)
                self.assertNotIn('<g id="%s">\n</g>' % name, svg)       # nothing left empty
            self.assertEqual(svg.count("<circle"), 132)    # a dot or circle for every station
            self.assertEqual(svg.count("<text"), 2 * 130 + 4 + 1 + 1)   # 130 label lines, twice (halo and text), tags, caption, credit
            self.assertEqual("stroke-width=\"0.5\"" in svg, outline)
            for text in ("B BRANCH", "C BRANCH", "D BRANCH", "E BRANCH", "DEPARTURES",
                         "#D9E2F2", "#F4F0E6", "#212322"):
                self.assertIn(text, svg)
            self.assertNotIn(">T<", svg)            # the logo is the MBTA's artwork, never a typed letter
            self.assertIn(furniture.T_LETTER, svg)
            for old in ("#1A1A1A", "#282828", "#5F7868"):       # the colors from before the brand guidelines
                self.assertNotIn(old, svg)
            # The print names the MBTA only to say it isn't them, as the MBTA's guidance for its logo asks.
            self.assertEqual(svg.count("MBTA"), 1)
            self.assertIn("Not affiliated with the MBTA", svg)

    # ---- labels (hard constraint 8 and the label rules)

    def test_every_station_has_exactly_one_label(self):
        self.assertEqual(len(self.labels), 132 - 7)             # each interchange shares one
        names = [l["name"] for l in self.labels]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), {s["transfer"] or s["name"] for s in self.stations})

    def test_no_label_touches_anything(self):
        check = generate.label_check(self.labels, self.stations)
        self.assertTrue(check["ok"], "; ".join(check["detail"][:6]))

    def test_the_files_it_writes_use_unix_line_endings(self):
        """Written in text mode on Windows they would come out with CRLF, and git would then show them as changed."""
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            generate.main()
        for name in ("print_no_outline.svg", "print_with_outline.svg", "validation_report.md"):
            with open(os.path.join(generate.DATA, name), "rb") as f:
                self.assertNotIn(b"\r\n", f.read(), name)


    def test_a_failed_check_writes_nothing(self):
        """The print is what gets ordered and stations.csv feeds everything else: a run that breaks a rule must
        leave the last good files alone. (Their content would be the same either way here, so this looks at
        whether they were written at all, by stamping them with an old time first.)"""
        import contextlib
        import io
        from unittest import mock
        paths = [os.path.join(generate.DATA, n) for n in
                 ("print_no_outline.svg", "print_with_outline.svg", "stations.csv", "validation_report.md")]
        old = 1000000000
        for path in paths:
            os.utime(path, (old, old))
        failing = {"name": "forced by the test", "ok": False, "worst": "", "detail": ["a label on a line"]}
        out = io.StringIO()
        try:
            with mock.patch.object(generate, "label_check", return_value=failing), contextlib.redirect_stdout(out):
                self.assertEqual(generate.main(), 1)
            self.assertEqual([int(os.stat(p).st_mtime) for p in paths], [old] * len(paths), "something was written")
            self.assertIn("Nothing was written", out.getvalue())
        finally:
            for path in paths:                  # leave them looking as if they had just been made
                os.utime(path, None)

if __name__ == "__main__":
    unittest.main()
