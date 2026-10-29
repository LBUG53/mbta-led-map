"""Checks on the files that go on the board: what CircuitPython can run, what the board serves, where the
API keys go.

  python -m unittest tests.test_board_files -v

firmware/code.py needs the board's hardware modules, so it can't run on a PC; the two checks that concern
it read its syntax tree instead of its text.
"""
import ast
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sim  # noqa: E402,F401  (puts firmware/ on the path)
import app  # noqa: E402

FIRMWARE = os.path.join(ROOT, "firmware")
SHARED = ("app", "feeds", "leds", "rides", "remote", "sign")     # these also run on the PC; code.py is the board's alone
NOT_ON_THE_BOARD = ("os", "time", "typing", "dataclasses", "enum")


def tree(name):
    with open(os.path.join(FIRMWARE, name + ".py"), encoding="utf-8") as f:
        return ast.parse(f.read())


class Plain(unittest.TestCase):
    def test_shared_files_use_only_what_circuitpython_has(self):
        """About 2 MB of memory and a smaller Python: lists, dicts, ints and strings, no classes."""
        for name in SHARED:
            for node in ast.walk(tree(name)):
                where = "%s.py:%d" % (name, getattr(node, "lineno", 0))
                self.assertNotIsInstance(node, (ast.ClassDef, ast.JoinedStr, ast.NamedExpr, ast.AnnAssign), where)
                if isinstance(node, ast.FunctionDef):
                    self.assertFalse(node.returns or any(a.annotation for a in node.args.args), where)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name.split(".")[0], NOT_ON_THE_BOARD, where)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or "").split(".")[0], NOT_ON_THE_BOARD, where)

    def test_the_remote_page_fits_in_what_the_board_can_hold(self):
        self.assertLess(os.path.getsize(os.path.join(FIRMWARE, "remote.html")), 16000)


class Exposure(unittest.TestCase):
    def test_the_board_serves_no_files_of_its_own(self):
        """A Server given a root directory answers any GET that matches no route with the file of that name
        from the drive, so /settings.toml would hand out the Wi-Fi password and the API keys. The remote page
        is sent with an explicit root for that one file instead."""
        servers = [n for n in ast.walk(tree("code")) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "Server"]
        self.assertTrue(servers, "code.py no longer makes a Server: update this test")
        for call in servers:
            self.assertEqual(len(call.args), 1, "Server(pool) only: no root directory")
            self.assertNotIn("root_path", [k.arg for k in call.keywords])

    def test_each_key_goes_only_to_its_own_service(self):
        mbta, aio = "mbta-secret", "aio-secret"
        for url in (app.API + "/vehicles", app.url("/predictions", [("filter[stop]", "place-alfcl")])):
            h = app.request_headers(url, mbta, aio)
            self.assertEqual(h["x-api-key"], mbta)
            self.assertNotIn("X-AIO-Key", h)
        h = app.request_headers(app.AIO + "someone/feeds/mbta-ride/data", mbta, aio)
        self.assertEqual(h["X-AIO-Key"], aio)
        self.assertNotIn("x-api-key", h)
        for url in ("https://api.open-meteo.com/v1/forecast", "https://site.api.espn.com/apis/site/v2/x",
                    "https://api-v3.mbta.com.example.org/vehicles", "https://api-v3.mbta.comfoo/x"):
            h = app.request_headers(url, mbta, aio)
            self.assertEqual(h, {"Accept": "application/json"}, url)

    def test_no_key_means_no_key_header(self):
        self.assertNotIn("x-api-key", app.request_headers(app.API + "/vehicles", "", None))
        self.assertNotIn("X-AIO-Key", app.request_headers(app.AIO + "x", "k", None))


if __name__ == "__main__":
    unittest.main()
