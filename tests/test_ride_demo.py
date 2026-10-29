"""Rides on the sample scenes and on the phone remote: start one, change trains, have two people riding, end it.

The board's own ride code runs against the simulator's made-up timetable (sim/sample_feeds.py), so a ride can be
tried without live data. The tests drive the board the way its loop does: a request whenever one is due, a few
seconds apart.

  python -m unittest tests.test_ride_demo -v
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

from sim import live, sample, sample_feeds  # noqa: E402

try:
    import build_firmware
    DATA = build_firmware.build()
    import app
    import leds
    import remote
    import rides
except (SystemExit, FileNotFoundError, ImportError):   # no PyYAML
    DATA = None

START = 1790947600      # 2026-10-02 13:26:40 UTC, 9:26 am in Boston


@unittest.skipIf(DATA is None, "firmware can't be built here")
class Rides(unittest.TestCase):
    def setUp(self):
        self.st = app.setup(json.loads(json.dumps(DATA)), use_map=False)     # the sample board
        self.now = START
        self.route_stops = live.route_stops(DATA["routes"])
        self.run_for(60)                    # the usual sources load first, as at start-up

    def fetch(self, url):
        return sample_feeds.answer(url, self.now, 0), 0, 0

    def run_for(self, seconds):
        for _ in range(seconds // 5):
            self.now += 5
            app.fetch_one(self.st, self.now * 1000, self.now, self.fetch)

    def say(self, text):
        remote.apply(self.st, {"cmd": "ride", "text": text}, self.now * 1000, self.now)
        self.run_for(60)

    def vehicles(self, dt=0):
        return sample.ride_vehicles(self.st["rides"], self.route_stops, self.now + dt)

    # ---- the picker

    def test_the_phone_remote_offers_every_line_and_stop_and_each_choice_is_understood(self):
        status, ctype, out = remote.handle(self.st, "GET", "/api/rides", "", {"x-remote": "1"}, 1000, START)
        self.assertEqual(status, 200)
        choices = json.loads(out)
        self.assertEqual(choices["lines"], ["Red", "Orange", "Blue", "Green", "Mattapan", "77"])
        self.assertEqual({k: len(v) for k, v in choices["stops"].items()},
                         {"Red": 22, "Orange": 20, "Blue": 12, "Green": 70, "Mattapan": 8, "77": 3})
        for line in choices["lines"]:
            names = choices["stops"][line]
            for name in names:
                other = names[1] if name == names[0] else names[0]
                self.assertIsNotNone(rides.parse(self.st, ";".join(["Alex", line, name, other]), START), (line, name))

    def test_the_picker_needs_the_x_remote_header_like_every_api_call(self):
        self.assertEqual(remote.handle(self.st, "GET", "/api/rides", "", {}, 1000, START)[0], 403)

    # ---- one rider

    def test_a_ride_finds_its_train_and_the_ticker_and_the_map_follow_it(self):
        self.say("Alex;Red;Harvard;Alewife")
        ride = self.st["rides"]["ALEX"]
        self.assertTrue(ride["vehicle"].startswith("sample-ride-vehicle-Red"))
        self.assertEqual(list(self.st["riding"]), [ride["vehicle"]])
        item = rides.items(self.st)[0]
        self.assertEqual(item["key"], "ride-ALEX")
        self.assertIn("RED", "".join(seg[0] for seg in item["more"]))      # the line and the time it arrives
        v = self.vehicles()[0]
        self.assertEqual((v["id"], v["route"], v["direction_id"]), (ride["vehicle"], "Red", 1))   # towards Alewife

    def test_the_train_runs_from_the_first_stop_to_the_last_and_arrives_when_the_ride_says(self):
        self.say("Alex;Orange;Oak Grove;Forest Hills")
        stops = self.route_stops["Orange"]
        ride = self.st["rides"]["ALEX"]
        places = []
        for dt in range(0, ride["eta"] - self.now + 1, 10):
            v = self.vehicles(dt)[0]
            places.append(stops.index(v["stop"]))
        self.assertEqual(places, sorted(places), "it never goes backwards")
        self.assertGreater(len(set(places)), 5, "it moves along the line")
        self.assertEqual(self.vehicles(ride["eta"] - self.now)[0]["stop"], "place-forhl")
        self.assertEqual(self.vehicles(ride["eta"] - self.now)[0]["status"], "STOPPED_AT")

    def test_a_ride_on_the_red_line_branch_stays_on_the_branch(self):
        self.say("Alex;Red;Alewife;Braintree")
        path = [stops for route, stops in remote.line_paths(self.route_stops) if "place-brntn" in stops][0]
        ride = self.st["rides"]["ALEX"]
        for dt in range(0, ride["eta"] - self.now + 1, 15):
            self.assertIn(self.vehicles(dt)[0]["stop"], path)

    def test_a_train_is_found_whenever_a_ride_starts_and_has_minutes_left(self):
        for offset in range(0, sample_feeds.RIDE_CYCLE, 25):
            st = app.setup(json.loads(json.dumps(DATA)), use_map=False)
            now = [START + offset]

            def fetch(url):
                return sample_feeds.answer(url, now[0], 0), 0, 0
            for _ in range(14):
                now[0] += 5
                app.fetch_one(st, now[0] * 1000, now[0], fetch)
            rides.apply(st, "Alex;Red;Harvard;Alewife", now[0], now[0] * 1000)
            for _ in range(14):
                now[0] += 5
                app.fetch_one(st, now[0] * 1000, now[0], fetch)
            ride = st["rides"].get("ALEX")
            self.assertIsNotNone(ride and ride["eta"], "start %d s into the cycle" % offset)
            self.assertGreaterEqual(ride["eta"] - now[0], 120, "start %d s into the cycle" % offset)

    # ---- changing trains, and more than one person

    def test_starting_again_changes_trains_and_the_old_one_stops_being_purple(self):
        self.say("Alex;Red;Harvard;Alewife")
        first = self.st["rides"]["ALEX"]["vehicle"]
        self.say("Alex;Orange;Oak Grove;Ruggles")
        self.assertEqual(sorted(self.st["rides"]), ["ALEX"])
        second = self.st["rides"]["ALEX"]["vehicle"]
        self.assertNotEqual(first, second)
        self.assertEqual(list(self.st["riding"]), [second])
        self.assertEqual([v["route"] for v in self.vehicles()], ["Orange"])

    def test_two_people_each_get_their_own_purple_train_and_ticker_item(self):
        self.say("Alex;Red;Harvard;Alewife")
        self.say("Sam;Blue;Bowdoin;Wonderland")
        self.assertEqual(sorted(self.st["rides"]), ["ALEX", "SAM"])
        self.assertEqual(len(self.st["riding"]), 2)
        self.assertEqual(sorted(v["route"] for v in self.vehicles()), ["Blue", "Red"])
        self.assertEqual([i["key"] for i in rides.items(self.st)], ["ride-ALEX", "ride-SAM"])

    def test_ending_one_ride_leaves_the_other(self):
        self.say("Alex;Red;Harvard;Alewife")
        self.say("Sam;Blue;Bowdoin;Wonderland")
        self.say("Alex;DONE")
        self.assertEqual(sorted(self.st["rides"]), ["SAM"])
        self.assertEqual(len(self.st["riding"]), 1)
        self.say("Sam;done")
        self.assertEqual((self.st["rides"], self.st["riding"]), ({}, {}))

    def test_a_bus_ride_is_on_the_sign_but_not_on_the_map(self):
        self.say("Alex;77;Harvard;Porter")
        self.assertIsNotNone(self.st["rides"]["ALEX"]["eta"])
        self.assertEqual(len(rides.items(self.st)), 1)
        self.assertEqual(self.vehicles(), [])

    def test_a_ride_ends_by_itself_after_the_train_arrives(self):
        self.say("Alex;Red;Harvard;Alewife")
        self.run_for(sample_feeds.RIDE_LENGTH + 60)
        self.assertEqual(self.st["rides"], {})
        self.assertEqual(self.st["riding"], {})


@unittest.skipIf(DATA is None, "firmware can't be built here")
class InTheSimulator(unittest.TestCase):
    """The simulator's sample board and its map, which is what a person trying rides in the browser sees."""

    @classmethod
    def setUpClass(cls):
        import server
        cls.server = server
        cls.sim = server.Simulator()

    def say(self, text):
        status, _, out = self.sim.remote("POST", "/api/cmd", json.dumps({"cmd": "ride", "text": text}),
                                         {"x-remote": "1"}, "sample")
        self.assertEqual(status, 200, out)
        board = self.sim.board("sample:typical", False)
        with board.lock:                    # the board's loop would do this at its next hold
            for source in board.st["sources"]:
                source["due"] = 0
            while self.server.firmware.fetch_one(board.st, self.server.now_ms(), self.server.epoch(), board.fetch):
                pass
        return board

    def purple_lights(self):
        frame = self.sim.frame({"source": "sample:typical"})
        return sum(1 for chain in frame["chains"].values() for pixel in chain if tuple(pixel) == leds.RIDER_COLOR)

    def test_a_ride_on_a_sample_scene_lights_a_purple_train(self):
        self.say("Alex;DONE")
        base = self.purple_lights()
        self.say("Alex;Orange;Oak Grove;Forest Hills")
        self.assertGreater(self.purple_lights(), base)
        self.say("Alex;DONE")
        self.assertEqual(self.purple_lights(), base)


if __name__ == "__main__":
    unittest.main()
