"""Tests for how the board behaves when the network or WLED is not answering (firmware/app.py,
firmware/remote.py), run on the PC with fake feeds.

  python -m unittest tests.test_backoff -v
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usefixtures  # noqa: E402,F401  (first: the tests use the committed lookup tables, not cache/)

from sim import sample_feeds  # noqa: E402

try:
    import build_firmware
    DATA = build_firmware.build()
    import app
    import remote
except (SystemExit, FileNotFoundError, ImportError):   # no cache yet, or no PyYAML
    DATA = None

EPOCH = 1790947600      # 2026-10-02 13:26:40 UTC


class Net:
    """A fake network. `mode` is "ok", or the exception message every request fails with."""
    def __init__(self, test):
        self.test = test
        self.mode = "ok"
        self.log = []           # (time, url)

    def __call__(self, url):
        self.log.append((self.test.now, url))
        self.test.now += 200
        if self.mode != "ok":
            raise RuntimeError(self.mode)
        return sample_feeds.answer(url, EPOCH, 0), 1000, 200


def source(every_s, fails):
    return {"every": every_s * 1000, "fails": fails}


@unittest.skipIf(DATA is None, "firmware can't be built here")
class Delays(unittest.TestCase):
    def test_each_failure_in_a_row_doubles_the_wait_up_to_a_limit(self):
        waits = [app.retry_delay(source(30, n)) for n in range(1, 9)]
        self.assertEqual(waits[:3], [30000, 60000, 120000])
        self.assertEqual(waits[3:], [app.BACKOFF_MAX_MS] * 5)
        small = [app.retry_delay(source(5, n)) for n in range(1, 8)]
        self.assertEqual(small, [5000, 10000, 20000, 40000, 80000, 120000, 120000])

@unittest.skipIf(DATA is None, "firmware can't be built here")
class Outages(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(json.dumps(DATA))
        self.data["ticker"].update({"weather": True, "rain": True, "sox": True, "bruins": True,
                                    "patriots": True, "alerts": True, "hold_seconds": 5})
        self.st = app.setup(self.data)
        self.now = 0
        self.net = Net(self)

    def run_for(self, seconds):
        end = self.now + seconds * 1000
        while self.now < end:
            app.tick(self.st, self.now, EPOCH, self.net)
            app.sign_frame(self.st, self.now, EPOCH)
            self.now += 50

    def times(self, name):
        url = next(s["url"] for s in self.st["sources"] if s["name"] == name)
        return [t for t, u in self.net.log if u == url]

    def test_an_outage_is_not_hammered(self):
        self.net.mode = "no network"
        self.run_for(20 * 60)
        for name in ("predictions", "vehicles"):
            times = self.times(name)
            gaps = [b - a for a, b in zip(times, times[1:])]
            self.assertLess(len(times), 20, "%s: %d requests in 20 minutes" % (name, len(times)))
            self.assertEqual(gaps, sorted(gaps), name + " should wait longer and longer")
            self.assertGreaterEqual(gaps[-1], app.BACKOFF_MAX_MS - 1000)
            self.assertLessEqual(max(gaps), app.BACKOFF_MAX_MS + 10000, "still checks at least every ~2 minutes")

    def source(self, name):
        return next(s for s in self.st["sources"] if s["name"] == name)

    def fetch_only(self, name):
        """Make just this source due, then let fetch_one pick: it takes the most overdue one."""
        for s in self.st["sources"]:
            s["due"] = self.now if s["name"] == name else self.now + 10 ** 9
        return app.fetch_one(self.st, self.now, EPOCH, self.net)

    def test_a_bug_in_reading_an_answer_is_not_a_network_failure(self):
        """The request worked, so no NO DATA banner and no reconnect; but the source backs off and the error says what it was."""
        def broken(st, src, d, now_ms, epoch):
            return d["data"][0]["attributes"]["severity"]       # not in a vehicle's answer
        vehicles = self.source("vehicles")
        vehicles["handler"] = broken
        for _ in range(6):
            self.assertTrue(self.fetch_only("vehicles"))
        self.assertEqual(self.st["failures"], 0)
        self.assertNotEqual([i["key"] for i in app.rotation(self.st, self.now, EPOCH)], ["nodata"])
        self.assertIn("vehicles", self.st["last_error"])
        self.assertIn("KeyError", self.st["last_error"])
        self.assertEqual((vehicles["fails"], vehicles["errors"], vehicles["ok"]), (6, 6, 0))
        self.assertGreater(vehicles["due"], self.now, "it waits before trying again")

    def test_a_failed_request_is_a_network_failure(self):
        self.net.mode = "HTTP 500"
        for name in ("vehicles", "predictions", "alerts"):
            self.fetch_only(name)
        self.assertEqual(self.st["failures"], 3)
        self.assertEqual([i["key"] for i in app.rotation(self.st, self.now, EPOCH)], ["nodata"])
        self.assertIn("HTTP 500", self.st["last_error"])

    def test_a_good_answer_clears_both_kinds_of_trouble(self):
        vehicles = self.source("vehicles")
        vehicles["fails"] = 4
        self.st["failures"] = 2
        self.fetch_only("vehicles")
        self.assertEqual((vehicles["fails"], self.st["failures"], vehicles["ok"]), (0, 0, 1))


@unittest.skipIf(DATA is None, "firmware can't be built here")
class WledQueue(unittest.TestCase):
    def setUp(self):
        self.st = app.setup(json.loads(json.dumps(DATA)))
        self.now = 10000

    def cmd(self, **c):
        remote.apply(self.st, c, self.now, EPOCH)

    def test_a_setting_that_fails_stays_and_waits_longer_each_time(self):
        self.cmd(cmd="map_bri", pct=40)
        waits = []
        for _ in range(9):
            self.assertIsNotNone(app.wled_due(self.st, self.now))
            app.wled_result(self.st, self.now, False)
            waits.append(self.st["wled_next"] - self.now)
            self.assertIsNone(app.wled_due(self.st, self.now + waits[-1] - 1), "too soon to try again")
            self.now += waits[-1]
        self.assertEqual(waits[:5], [2000, 4000, 8000, 16000, 32000])
        self.assertEqual(waits[5:], [app.WLED_RETRY_MAX_MS] * 4)
        self.assertEqual(len(self.st["ui"]["posts"]), 1, "still waiting to be sent")

if __name__ == "__main__":
    unittest.main()
