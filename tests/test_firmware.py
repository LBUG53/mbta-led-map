"""Tests for the Matrix Portal firmware's logic (firmware/app.py, feeds.py), run on the PC.

  python -m unittest tests.test_firmware -v
Set RUN_NETWORK_TESTS=1 to also run it against the live feeds.
"""
import json
import os
import sys
import time
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usefixtures  # noqa: E402,F401  (first: the tests use the committed lookup tables, not cache/)

from sim import sample_feeds  # noqa: E402

try:
    import build_firmware
    DATA = build_firmware.build()       # writes firmware/data.json
    import app                          # the board's own files, from firmware/ (see sim/__init__.py)
    import feeds
except (SystemExit, FileNotFoundError, ImportError) as e:   # no cache yet, or no PyYAML
    DATA = None
    SKIP = str(e)

EPOCH = 1790947600      # 2026-10-02 13:26:40 UTC = 9:26 am in Boston, a Friday
BOARD_FILES = ("data.json", "code.py", "app.py", "feeds.py", "leds.py", "sign.py", "rides.py", "remote.py")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Net:
    """A fake network: answers from the samples, 800 ms a request, and keeps a log."""

    def __init__(self, test, broken=False):
        self.test = test
        self.broken = broken
        self.elapsed = 0
        self.log = []           # (time of request, ticker phase, url)

    def __call__(self, url):
        self.log.append((self.test.now, self.test.st["tk"]["phase"], url))
        self.test.now += 800
        if self.broken:
            raise OSError("no network")
        return sample_feeds.answer(url, EPOCH, self.elapsed), 1000, 800


@unittest.skipIf(DATA is None, "firmware can't be built here")
class Firmware(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(json.dumps(DATA))    # what the board reads back from data.json
        self.data["ticker"].update({"weather": True, "rain": True, "sox": True, "bruins": True,
                                    "patriots": True, "alerts": True, "hold_seconds": 5})
        self.st = app.setup(self.data)
        self.now = 0
        self.net = Net(self)

    def load(self):
        while app.fetch_one(self.st, self.now, EPOCH, self.net):
            pass

    def run_for(self, seconds, each=None):
        """Run the main loop at 20 frames a second. Returns the ticker keys shown, in order."""
        shown = []
        end = self.now + seconds * 1000
        while self.now < end:
            app.tick(self.st, self.now, EPOCH, self.net)
            app.sign_frame(self.st, self.now, EPOCH)
            item = self.st["tk"]["item"]
            key = item["key"] if item else None
            if not shown or shown[-1] != key:
                shown.append(key)
            if each:
                each()
            self.now += 50
        return shown

    # ---- requests

    def test_fetches_only_while_holding(self):
        self.load()
        loaded = len(self.net.log)
        self.assertEqual(loaded, len([s for s in self.st["sources"] if s["url"] is not None]))   # not "ride": no one is riding
        self.run_for(300)
        later = self.net.log[loaded:]
        self.assertGreater(len(later), 15)
        self.assertEqual({phase for _, phase, _ in later}, {"hold"})
        # One request per hold: never two within a hold's length of each other.
        times = [t for t, _, _ in later]
        self.assertGreaterEqual(min(b - a for a, b in zip(times, times[1:])), 2000)

    def test_failures_are_survived(self):
        self.net.broken = True
        self.load()
        self.assertGreaterEqual(self.st["failures"], 5)
        self.assertEqual(self.run_for(12)[-1], "nodata")
        self.net.broken = False
        self.run_for(60)
        self.assertEqual(self.st["failures"], 0)
        self.assertNotIn("nodata", self.run_for(30)[1:])

    # ---- ticker

    def test_rotation_order(self):
        self.load()
        shown = self.run_for(90)
        self.assertEqual(shown[:9], [None, "clock", "alert-sample-1", "weather", "hilo", "rain", "sox", "bruins",
                                     "patriots"])
        self.assertEqual(shown[9], "clock")             # round again

    # ---- sign picture

    def test_sign_picture(self):
        self.load()
        self.assertEqual(app.clock_and_date(EPOCH), ("9:26", "FRI 10/2"))
        walk = self.st["rows"][1].get("walk_minutes", 0)
        self.st["rows"][1]["walk_minutes"] = 0
        self.assertEqual([r["times"] for r in app.sign_rows(self.st, self.now, EPOCH)],
                         [[["4", ""], ["11", ""]], [["NOW", ""], ["6", ""]]])
        self.st["rows"][1]["walk_minutes"] = 5                  # a 5-minute walk: NOW is too soon
        self.assertEqual(app.sign_rows(self.st, self.now, EPOCH)[1]["times"], [["6", ""], ["16", ""]])
        self.st["rows"][1]["walk_minutes"] = 14                 # the real walk to Alewife
        self.assertEqual(app.sign_rows(self.st, self.now, EPOCH)[1]["times"], [["16", ""], ["22", ""]])
        self.st["rows"][1]["walk_minutes"] = walk
        frames = []
        self.run_for(60, lambda: frames.append(self.st["frame"]))
        frames = [f for f in frames if f is not None]
        for bm in frames[::7]:
            self.assertEqual((len(bm), len(bm[0])), (32, 64))
            self.assertFalse(any(bm[0]) or any(bm[31]))                     # edges half hidden: unused
            self.assertFalse(any(row[0] or row[63] for row in bm))
            for y in list(range(1, 21)) + [30]:                             # only the ticker moves
                self.assertEqual(bm[y], frames[0][y])
        self.assertGreater(len({bytes(bm[25]) for bm in frames}), 10)
        self.assertEqual(max(max(row) for bm in frames for row in bm), app.signlib.PATS)
        self.assertEqual(len(app.sign_palette(self.st, self.data)), 16)     # 13, and the remote's three spare player colors

    # ---- map

    def test_packet_shape_and_stopped_train(self):
        self.load()
        app.update_map(self.st, self.now)
        buf = app.ddp_packet(self.st, 0.0, app.ddp_buffer(self.st))
        self.assertEqual(DATA["output_leds"], [100, 100, 100])
        self.assertEqual(len(buf), 10 + 300 * 3)
        self.assertEqual((buf[0], buf[2], buf[3]), (0x41, 1, 1))
        self.assertEqual((buf[8] << 8) | buf[9], 900)
        rgb = [tuple(buf[10 + 3 * i:13 + 3 * i]) for i in range(300)]
        # The sample train (Red, heading south, stopped at Ashmont) lights that one light, full red.
        ashmont = self.ashmont_south()
        self.assertEqual(self.st["states"][ashmont], app.ledlib.STOPPED)
        wiring = {int(k): v for k, v in DATA["wiring"].items()}
        at = self.pixel(wiring, ashmont)
        self.assertEqual(rgb[at], tuple(DATA["colors"]["RL"]))
        for output in (1, 2, 3):
            base = (output - 1) * 100
            for n, light in enumerate(wiring[output]):
                if light != ashmont:
                    self.assertEqual(rgb[base + n], (0, 0, 0), (output, n))     # SKIP pixels and dark lights
            self.assertEqual(set(rgb[base + len(wiring[output]):base + 100]), {(0, 0, 0)})   # unused pixels
        self.assertEqual(sum(1 for w in wiring.values() for n in w if n < 0), 5)
        app.update_map(self.st, self.now + 100000)          # stale vehicles are dropped
        self.assertEqual(self.st["states"][ashmont], app.ledlib.IDLE)

    def ashmont_south(self):
        """The light a southbound Red Line train lights at Ashmont."""
        for i, s in enumerate(DATA["stations"]):
            if s["line"] == "RL" and s["stop_id"] == "place-asmnl":
                return 2 * i + (0 if s["a_dir"]["Red"] == 0 else 1)

    def pixel(self, wiring, light):
        """Where a light is in the DDP packet's 300 pixels (outputs of 100, in order)."""
        for output in sorted(wiring):
            if light in wiring[output]:
                return (int(output) - 1) * 100 + wiring[output].index(light)

    # ---- clock, files

    def test_night_mode(self):
        st = self.st
        at = lambda h, m=0: EPOCH - (9 * 3600 + 26 * 60 + 40) + h * 3600 + m * 60   # Boston time today
        self.assertFalse(app.is_night(st, at(22, 59)))
        self.assertTrue(app.is_night(st, at(23, 0)))
        self.assertTrue(app.is_night(st, at(3)))
        self.assertTrue(app.is_night(st, at(6, 59)))
        self.assertFalse(app.is_night(st, at(7, 0)))
        self.load()
        # The ticker: just the time and the weather, swapping without sliding, held longer.
        texts = ["".join(s[0] for s in it["segs"]) for it in app.rotation(st, self.now, at(23, 30))]
        self.assertEqual(texts, ["FRI 11:30", "58\u00b0 PT SUN"])
        st["force_night"] = True
        shown = self.run_for(60)
        self.assertEqual(set(shown[1:]), {"clock", "weather"})
        self.assertNotIn("slide", [st["tk"]["phase"]])
        self.assertLessEqual(len(shown), 8)                     # 10 s holds
        # Fewer requests, no flashes or alert interruptions.
        before = len(self.net.log)
        self.net.elapsed = 400                                  # a new alert and a Sox run
        self.run_for(300)
        per_min = sum(1 for _, _, u in self.net.log[before:] if "/predictions" in u) / 5
        self.assertLessEqual(per_min, 1.1)
        self.assertEqual(st["tk"]["queue"], [])
        # Dimmer sign; still map.
        day = app.sign_palette(st, self.data)
        night = app.sign_palette(st, self.data, True)
        self.assertLess(sum(night[1]), sum(day[1]))
        self.assertGreater(min(night[1]), 0)                    # warm white keeps all three channels
        app.update_map(st, self.now)
        self.assertFalse(app.is_animated(st, 0))
        at = 10 + 3 * self.pixel(st["wiring"], self.ashmont_south())
        lit = app.ddp_packet(st, 0.0, app.ddp_buffer(st))[at:at + 3]
        dim = app.ddp_packet(st, 0.0, app.ddp_buffer(st), True)[at:at + 3]
        for a, b in zip(dim, lit):
            self.assertLessEqual(abs(a - b * 0.5), 1)           # half, give or take rounding

    def test_eastern_time(self):
        cases = [(1772953199, -5), (1772953200, -4),     # 2026-03-08, 2 am: clocks go forward
                 (1793512799, -4), (1793512800, -5),     # 2026-11-01, 2 am: clocks go back
                 (1767243600, -5), (1782878400, -4)]     # New Year, 1 July
        for epoch, hours in cases:
            self.assertEqual(feeds.eastern_offset(epoch), hours * 3600, epoch)
        self.assertEqual(feeds.civil_from_days(0), (1970, 1, 1))
        self.assertEqual(feeds.civil_from_days(app.signlib.days_from_civil(2028, 2, 29)), (2028, 2, 29))
        self.assertEqual(app.clock_and_date(1767243600), ("12:00", "THU 1/1"))
        self.assertEqual(feeds.parse_utc("2026-10-03T00:00Z"), 1790985600)

    def test_the_key_is_in_no_board_file_and_data_json_stays_small(self):
        self.assertLess(len(read(os.path.join(build_firmware.FIRMWARE, "data.json"))), 60000)
        key = build_firmware.mbta_api.api_key()
        for name in BOARD_FILES:
            if key:
                self.assertNotIn(key, read(os.path.join(build_firmware.FIRMWARE, name)), name)

    @unittest.skipUnless(os.environ.get("RUN_NETWORK_TESTS"), "set RUN_NETWORK_TESTS=1")
    def test_live_feeds(self):
        key = build_firmware.mbta_api.api_key()

        def fetch(url):
            began = time.time()
            headers = {"User-Agent": "mbta-led-map"}
            if url.startswith(app.API) and key:
                headers["x-api-key"] = key
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
                body = r.read()
            return json.loads(body), len(body), int((time.time() - began) * 1000)
        now = int(time.time())
        while app.fetch_one(self.st, self.now, now, fetch):
            pass
        self.assertEqual(self.st["failures"], 0, self.st["last_error"])
        for s in self.st["sources"]:
            if s["url"] is None:
                continue                                # a team with no game yesterday or today
            self.assertEqual((s["ok"], s["errors"]), (1, 0), s["name"])
            self.assertLess(s["bytes"], 60000, s["name"])
        self.assertIsNotNone(self.st["weather"])
        bm = app.sign_frame(self.st, self.now, now)
        self.assertEqual((len(bm), len(bm[0])), (32, 64))
        print()
        for line in app.report(self.st):
            print("  live:", line)
        print("  live ticker:", ["".join(seg[0] for seg in it["segs"])[:40]
                                 for it in app.rotation(self.st, self.now, now)])


if __name__ == "__main__":
    unittest.main()
