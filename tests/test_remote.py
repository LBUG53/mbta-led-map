"""Tests for the phone remote (firmware/remote.py and its hooks in app.py), run on the PC.

  python -m unittest tests.test_remote -v
"""
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

from sim import sample_feeds  # noqa: E402

try:
    import build_firmware
    DATA = build_firmware.build()
    import app
    import remote
    import sign as signlib
except (SystemExit, FileNotFoundError, ImportError) as e:   # no cache yet, or no PyYAML
    DATA = None

PAGE = {"x-remote": "1"}     # the header remote.html sends
EPOCH = 1790947600      # 2026-10-02 13:26:40 UTC = 9:26 am in Boston, a Friday


@unittest.skipIf(DATA is None, "firmware can't be built here")
class Remote(unittest.TestCase):
    def setUp(self):
        self.st = app.setup(json.loads(json.dumps(DATA)))
        self.now = 100000
        self.urls = []

    def fetch(self, url):
        self.urls.append(url)
        return sample_feeds.answer(url, EPOCH, 0), 1000, 50

    def cmd(self, **c):
        code, ctype, out = remote.handle(self.st, "POST", "/api/cmd", json.dumps(c), PAGE, self.now, EPOCH)
        self.assertEqual(code, 200)
        return json.loads(out)

    def run_for(self, ms, step=50):
        for _ in range(ms // step):
            self.now += step
            app.tick(self.st, self.now, EPOCH, self.fetch)
            frame = app.sign_frame(self.st, self.now, EPOCH)
        return frame

    def test_state_and_page(self):
        code, ctype, out = remote.handle(self.st, "GET", "/api/state", "", PAGE, self.now, EPOCH)
        s = json.loads(out)
        self.assertEqual((code, s["mode"], s["life"], s["timer"]), (200, "transit", [40, 40, 40, 40], 0))
        self.assertEqual(remote.handle(self.st, "GET", "/", "", PAGE, self.now, EPOCH), (200, "file", "remote.html"))
        self.assertEqual(remote.handle(self.st, "GET", "/remote/api/state?x=1", "", PAGE, self.now, EPOCH)[0], 200)
        stations = json.loads(remote.handle(self.st, "GET", "/api/stations", "", PAGE, self.now, EPOCH)[2])
        self.assertEqual(len(stations), 132)
        self.assertIn(["RL", "Alewife"], stations)
        self.assertEqual(remote.handle(self.st, "GET", "/nothing", "", PAGE, self.now, EPOCH)[0], 404)
        self.assertEqual(remote.handle(self.st, "POST", "/api/cmd", "not json", PAGE, self.now, EPOCH)[0], 400)
        # another website can't add the header; the code is checked when one is set
        self.assertEqual(remote.handle(self.st, "POST", "/api/cmd", "{}", {}, self.now, EPOCH)[0], 403)
        self.st["remote_token"] = "1234"
        self.assertEqual(remote.handle(self.st, "GET", "/api/state", "", PAGE, self.now, EPOCH)[0], 401)
        ok = {"x-remote": "1", "x-remote-token": "1234"}
        self.assertEqual(remote.handle(self.st, "GET", "/api/state", "", ok, self.now, EPOCH)[0], 200)

    def test_the_page_only_asks_for_addresses_the_board_serves(self):
        with open(os.path.join(ROOT, "firmware", "remote.html"), encoding="utf-8") as f:
            asked = set(re.findall(r"api\('(api/\w+)'", f.read()))
        self.assertTrue(asked)
        for path in asked:
            self.assertIn("/" + path, remote.PATHS)
        for path in remote.PATHS:
            self.assertNotEqual(remote.handle(self.st, "POST", path, "{}", PAGE, self.now, EPOCH)[0], 404, path)

    def test_costume(self):
        # Sample trains, sample departures and HAPPY HALLOWEEN, with nothing fetched.
        self.assertTrue(self.cmd(cmd="costume", on=True)["costume"])
        self.urls = []
        self.run_for(30000)
        app.update_map(self.st, self.now - self.now % remote.HOP_MS)         # while the trains stand at their stations
        self.assertGreater(sum(1 for s in self.st["states"] if s), 40)       # lit by a sample train
        self.assertEqual(self.urls, [])
        times = [r["times"] for r in app.sign_rows(self.st, self.now, EPOCH)]
        self.assertTrue(all(len(t) == 2 and t[0][0] for t in times))
        # Within a minute the sign shows both the departures and the message going by.
        shown = [remote.costume_frame(self.st, ms) for ms in range(0, 60000, 250)]
        self.assertIn(None, shown)
        frame = [list(row) for row in [f for f in shown if f is not None][20]]
        self.assertTrue(any(any(row) for row in frame))
        self.assertFalse(any(frame[1]) or any(frame[-1]))   # the big letters sit in the middle rows
        self.assertFalse(self.cmd(cmd="costume", on=False)["costume"])

    def test_music_mode(self):
        # The board hands the map to WLED: one segment per output running the chosen effect, and no more frames.
        self.assertTrue(app.map_live(self.st))
        s = self.cmd(cmd="mode", mode="music")
        self.assertEqual(s["music"][0], self.st["music"][0][0])
        self.assertFalse(app.map_live(self.st))
        # The default, Lines: each stretch of a line is a segment in its line's color, covering that line's lights.
        self.assertTrue(self.st["music"][0][2])
        segs = [g for g in self.st["ui"]["posts"][-1]["seg"] if g["stop"]]
        base, where = 0, {}
        for k, output in enumerate(self.st["outputs"]):
            for n, light in enumerate(self.st["wiring"][output]):
                if light >= 0:
                    where[base + n] = self.st["stations"][light // 2]["line"]
            base += self.st["counts"][k]
        covered = set()
        for g in segs:
            lines = {where[i] for i in range(g["start"], g["stop"]) if i in where}
            self.assertEqual(len(lines), 1)
            self.assertEqual(g["col"][0], self.st["colors"][lines.pop()])
            covered |= set(range(g["start"], g["stop"]))
        self.assertEqual(set(where) - covered, set())
        self.assertIn(signlib.RIDER, {v for row in app.sign_frame(self.st, self.now, EPOCH) for v in row})
        # Another effect: one segment per output, and the Lines segments left over are deleted.
        self.cmd(cmd="music_fx", i=1)
        posts = [p for p in self.st["ui"]["posts"] if "seg" in p]
        self.assertEqual(len(posts), 1)                                 # the first effect never goes out now
        counts = self.st["counts"]
        live = [g for g in posts[0]["seg"] if g["stop"]]
        self.assertEqual([(g["start"], g["stop"]) for g in live],
                         [(sum(counts[:k]), sum(counts[:k + 1])) for k in range(len(counts))])
        self.assertEqual({g["fx"] for g in live}, {self.st["music"][1][1]})
        self.assertGreaterEqual(len(posts[0]["seg"]), len(segs))
        self.cmd(cmd="mode", mode="transit")
        self.assertTrue(app.map_live(self.st))

    def test_korok(self):
        # It rises into view, says YAHAHA!, then YOU FOUND ME!, in its own leaf and wood colors; then it's gone.
        before = app.sign_palette(self.st, DATA)
        self.cmd(cmd="korok")
        lit = lambda f: {v for row in f for v in row} - {0}
        green = signlib.FIRST_ROW_COLOR
        self.assertEqual(lit(app.sign_frame(self.st, self.now, EPOCH)), {green})       # only the leaf's tip yet
        yahaha = [list(r) for r in self.run_for(1000)]
        self.assertEqual(lit(yahaha), {green, green + 1, signlib.WHITE})
        pal = app.sign_palette(self.st, DATA)
        self.assertGreater(pal[green][1], pal[green][0])                               # the leaf is green
        found = [list(r) for r in self.run_for(remote.KOROK_YAHAHA_MS)]
        self.assertNotEqual(found, yahaha)
        self.assertIn(signlib.WHITE, found[1] + found[21])                             # three lines of text
        self.run_for(remote.KOROK_MS)
        self.assertIsNone(self.st["ui"]["korok"])
        self.assertEqual(app.sign_palette(self.st, DATA), before)                       # the route colors are back

    def test_alignment_rings(self):
        # The outermost ring white and the next yellow, nothing inside; then back to the usual sign.
        self.assertTrue(self.cmd(cmd="align", on=True)["align"])
        frame = [list(row) for row in app.sign_frame(self.st, self.now, EPOCH)]
        w, h = signlib.W, signlib.H
        self.assertEqual(set(frame[0]) | set(frame[h - 1]) | {frame[y][0] for y in range(h)}, {signlib.WHITE})
        self.assertEqual(set(frame[1][1:w - 1]) | {frame[y][w - 2] for y in range(1, h - 1)}, {signlib.ALERT})
        self.assertEqual({v for row in frame[2:h - 2] for v in row[2:w - 2]}, {0})
        self.assertFalse(self.cmd(cmd="align", on=False)["align"])
        frame = [list(row) for row in app.sign_frame(self.st, self.now, EPOCH)]
        self.assertNotEqual(set(frame[0]), {signlib.WHITE})

    def test_life_totals(self):
        self.cmd(cmd="mode", mode="game")
        s = self.cmd(cmd="life", p=1, d=-7)
        self.assertEqual(s["life"], [40, 33, 40, 40])
        self.assertEqual(self.cmd(cmd="life", p=99, d=-1)["life"][3], 39)      # out of range: the last player
        self.assertEqual(self.cmd(cmd="players", n=3, start=20)["life"], [20, 20, 20])
        self.assertEqual(self.cmd(cmd="players", n=9, start=20)["life"], [20] * 6)
        self.assertEqual(self.cmd(cmd="set", p=0, v=5)["life"][0], 5)
        self.assertEqual(self.cmd(cmd="reset")["life"], [20] * 6)
        frame = self.run_for(200)
        self.assertEqual(len(frame), signlib.H)
        self.assertTrue(any(frame[5]))                  # life totals in the first row
        self.assertIs(app.sign_frame(self.st, self.now, EPOCH), frame)     # unchanged: the same object

    def test_timer(self):
        self.assertEqual(self.cmd(cmd="timer", seconds=90)["timer"], 90)
        self.assertEqual(remote.band(self.st, self.now + 1000, EPOCH), [["TMR 1:29", signlib.WHITE]])
        frame = self.run_for(1000)
        self.assertTrue(any(frame[25]))                 # drawn over the ticker's row, in transit mode
        self.now += 90000
        remote.update(self.st, self.now, EPOCH)
        self.assertIsNone(self.st["ui"]["timer"])
        self.assertIn(remote.band(self.st, self.now, EPOCH), ([["TIME!", signlib.ALERT]], []))
        self.now += remote.TIMER_DONE_MS
        remote.update(self.st, self.now, EPOCH)
        self.assertIsNone(remote.band(self.st, self.now, EPOCH))
        self.cmd(cmd="timer", seconds=5000)
        self.assertEqual(remote.timer_text(5000), "TMR 83M")
        self.assertEqual(self.cmd(cmd="timer_stop")["timer"], 0)

    def test_message(self):
        s = self.cmd(cmd="message", text="  hello   there, <b>Alex</b> ~ 5pm  ")
        self.assertEqual(s["message"], "HELLO THERE, BALEX/B 5PM")       # only what the font can draw
        self.assertEqual(self.st["tk"]["queue"][-1]["key"], "message")
        self.assertIn("message", [it["key"] for it in app.rotation(self.st, self.now, EPOCH)])
        long = self.cmd(cmd="message", text="x" * 500)["message"]
        self.assertEqual(len(long), remote.MESSAGE_MAX)
        self.assertTrue(self.st["tk"]["queue"][-1]["scroll"])
        self.assertEqual(self.cmd(cmd="message", text="")["message"], "")
        self.assertNotIn("message", [it["key"] for it in app.rotation(self.st, self.now, EPOCH)])

    def test_off_and_wake(self):
        s = self.cmd(cmd="off", wake="7:00")
        self.assertEqual((s["mode"], s["wake"]), ("off", "7:00"))
        self.assertEqual(self.st["ui"]["wake"] - EPOCH, 21 * 3600 + 33 * 60 + 20)  # 9:26:40 am until 7 the next morning
        frame = self.run_for(3000)
        self.assertFalse(any(any(row) for row in frame))
        self.assertEqual(self.urls, [])                 # nothing is fetched while off
        chains = remote.map_overlay(self.st, app.map_chains(self.st, 0), self.now, 0)
        self.assertFalse(any(any(c) for row in chains.values() for c in row))
        app.tick(self.st, self.now, self.st["ui"]["wake"] + 1, self.fetch)
        self.assertEqual(self.st["ui"]["mode"], "transit")
        self.cmd(cmd="mode", mode="game")
        self.cmd(cmd="off")
        self.assertEqual(self.cmd(cmd="on")["mode"], "game")       # back to where it was

    def test_bruins_mode(self):
        self.cmd(cmd="mode", mode="bruins")
        frame = self.run_for(6000)
        self.assertTrue([u for u in self.urls if "hockey" in u])
        self.assertFalse([u for u in self.urls if "baseball" in u or "/predictions" in u])
        self.assertTrue(any(frame[5]))
        game = {"start": EPOCH - 3600, "state": "in", "us": 2, "them": 1, "opp": "TOR", "home": True,
                "period": 2, "clock": "12:34"}
        self.st["games"]["bruins"] = game
        self.assertEqual(remote.period_text(game), "P2 12:34")
        self.assertEqual(remote.period_text(dict(game, period=4, clock="0:00")), "END OT")
        self.assertEqual(remote.game_every(self.st, "bruins", True), remote.BRUINS_LIVE_SECONDS)
        self.assertIsNone(remote.game_every(self.st, "sox", True))
        src = app.source(self.st, "bruins")
        d = {"date": "2026-10-02T12:26Z", "competitions": [{"status": {"type": {"state": "in"}, "period": 2,
                                                                         "displayClock": "9:10"},
             "competitors": [{"team": {"abbreviation": "BOS"}, "score": "3", "homeAway": "home"},
                             {"team": {"abbreviation": "TOR"}, "score": "1", "homeAway": "away"}]}]}
        self.st["games"]["bruins"] = dict(game, start=1790943960)
        app.got_game(self.st, src, d, self.now, EPOCH)
        self.assertEqual(self.st["ui"]["goal"], self.now)          # a goal: the flash and the sweep
        self.assertEqual(src["every"], remote.BRUINS_LIVE_SECONDS * 1000)
        self.assertEqual(self.st["games"]["bruins"]["clock"], "9:10")
        chains = remote.map_overlay(self.st, app.map_chains(self.st, 0), self.now, 0)
        self.assertTrue(any(c == remote.GOLD for row in chains.values() for c in row))
        self.assertIn(remote.band(self.st, self.now, EPOCH), ([["GOAL!", signlib.BRUINS]], []))
        self.now += remote.GOAL_MS
        remote.update(self.st, self.now, EPOCH)
        self.assertIsNone(self.st["ui"]["goal"])


if __name__ == "__main__":
    unittest.main()
