"""Tests for rides (firmware/rides.py and its hooks in app.py): a phone says which train someone is on.

  python -m unittest tests.test_rides -v
"""
import json
import os
import sys
import time
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
    import rides
except (SystemExit, FileNotFoundError, ImportError):     # no cache yet, or no PyYAML
    DATA = None

EPOCH = 1790947600      # 2026-10-02 13:26:40 UTC = 9:26 am in Boston, a Friday
PAGE = {"x-remote": "1"}


def pred(trip, stop, seq, direction, vehicle=None, arr=None, dep=None):
    """One prediction as the MBTA sends it; arr and dep are seconds after EPOCH."""
    return {"attributes": {"arrival_time": None if arr is None else sample_feeds.iso(EPOCH + arr),
                           "departure_time": None if dep is None else sample_feeds.iso(EPOCH + dep),
                           "stop_sequence": seq, "direction_id": direction, "schedule_relationship": None},
            "relationships": {"trip": {"data": {"id": trip}}, "stop": {"data": {"id": stop}},
                              "vehicle": {"data": {"id": vehicle} if vehicle else None}}}


# Orange Line, Ruggles to Downtown Crossing (northbound, direction 1):
# A left Ruggles before the message, B is at Ruggles, C runs the other way.
FIND = {"data": [pred("A", "place-dwnxg", 13, 1, "O-1", arr=300),
                 pred("B", "place-rugg", 8, 1, "O-2", arr=40, dep=60),
                 pred("B", "place-dwnxg", 13, 1, "O-2", arr=600),
                 pred("C", "place-dwnxg", 7, 0, "O-3", dep=100),
                 pred("C", "place-rugg", 12, 0, "O-3", arr=500)]}


@unittest.skipIf(DATA is None, "firmware can't be built here")
class Rides(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(json.dumps(DATA))
        self.data["ride"] = {"buses": {"77": {"Harvard": ["place-harsq"], "Arlington Heights": ["7922"]}}}
        self.st = app.setup(self.data)

    def start(self, text, at=EPOCH):
        self.assertTrue(rides.apply(self.st, text, at, 0))
        return self.st["rides"]

    def test_messages(self):
        ride = rides.parse(self.st, "alex ; orange ; RUGGLES ; downtown crossing", EPOCH)[1]
        self.assertEqual((ride["name"], ride["routes"], ride["from"], ride["to"]),
                         ("ALEX", ["Orange"], ["place-rugg"], ["place-dwnxg"]))
        self.assertEqual(rides.parse(self.st, "Alex;Green;Kenmore;Park Street", EPOCH)[1]["routes"],
                         ["Green-B", "Green-C", "Green-D", "Green-E"])
        self.assertEqual(rides.parse(self.st, "Alex;77;Harvard;Arlington Heights", EPOCH)[1]["to"], ["7922"])
        self.assertEqual(rides.parse(self.st, "Alex;done", EPOCH), ["done", "ALEX"])
        for bad in ("", "Alex", "Alex;Purple;Ruggles;Alewife", "Alex;Red;Ruggles;Alewife",
                    "Alex;Red;Alewife;Alewife", "Alex;77;Harvard;Porter"):
            self.assertIsNone(rides.parse(self.st, bad, EPOCH), bad)

    def test_finds_the_train_being_boarded(self):
        found = rides.trips(FIND, self.start("Alex;Orange;Ruggles;Downtown Crossing")["ALEX"], self.st)
        self.assertEqual(rides.choose(found, EPOCH)[0], "B")          # at the platform when the message was sent
        self.assertEqual(rides.choose(found, EPOCH - 200)[0], "A")    # the message came after the train left
        del found["A"]
        self.assertEqual(rides.choose(found, EPOCH - 200)[0], "B")    # nothing has left: the next one

    def test_follows_the_train_then_ends(self):
        self.start("Alex;Orange;Ruggles;Downtown Crossing")
        src = app.source(self.st, "ride")
        self.assertEqual((src["url"], src["due"]), ("", 0))           # asked for at the next hold
        url = app.ride_url(self.st, src, EPOCH)
        self.assertIn("filter%5Bstop%5D=place-rugg,place-dwnxg", url)
        app.got_ride(self.st, src, FIND, 0, EPOCH)
        ride = self.st["rides"]["ALEX"]
        self.assertEqual((ride["trip"], ride["vehicle"], ride["eta"]), ("B", "O-2", EPOCH + 600))
        self.assertEqual(self.st["riding"], {"O-2": True})
        self.assertEqual(self.st["tk"]["queue"][-1]["key"], "ride-ALEX")    # on the sign right away
        self.assertIn("filter%5Btrip%5D=B", app.ride_url(self.st, src, EPOCH))
        app.got_ride(self.st, src, {"data": [pred("B", "70020", 13, 1, "O-2", arr=660)]}, 0, EPOCH + 60)
        self.assertEqual(ride["eta"], EPOCH + 660)                    # a platform ID counts as the station
        # The map: that train is purple.
        self.st["vehicles"] = [[{"id": "O-2", "route": "Orange", "stop": "place-bbsta", "status": "STOPPED_AT",
                                 "direction_id": 1}], 0]
        app.update_map(self.st, 1)
        self.assertEqual(sorted(set(self.st["states"])), [app.ledlib.IDLE, app.ledlib.RIDING])
        # Past Downtown Crossing its prediction there is gone: the ride is over.
        app.got_ride(self.st, src, {"data": []}, 0, EPOCH + 700)
        self.assertEqual((self.st["rides"], self.st["riding"], src["url"]), ({}, {}, None))

    def test_waits_for_an_unknown_stop(self):
        # A bus berth at Harvard is a stop ID of its own: look it up before choosing.
        ride = self.start("Alex;77;Harvard;Arlington Heights")["ALEX"]
        d = {"data": [pred("T", "76121", 1, 0, "y1", dep=60), pred("T", "7922", 13, 0, "y1", arr=900)]}
        self.assertIsNone(rides.trips(d, ride, self.st))
        self.assertIn("76121", self.st["unknown"])
        self.st["parents"]["76121"] = "place-harsq"                   # what app.lookup_stop() finds
        self.assertEqual(rides.choose(rides.trips(d, ride, self.st), EPOCH)[0], "T")

    def test_gives_up_when_no_train_turns_up(self):
        self.start("Alex;Orange;Ruggles;Downtown Crossing")
        src = app.source(self.st, "ride")
        for _ in range(rides.FIND_TRIES):
            app.ride_url(self.st, src, EPOCH)
            app.got_ride(self.st, src, {"data": []}, 0, EPOCH)
        self.assertEqual(self.st["rides"], {})

    def test_on_the_sign(self):
        self.start("Alex;Orange;Ruggles;Downtown Crossing")
        self.assertEqual(rides.items(self.st), [])                    # not until the train is found
        self.st["rides"]["ALEX"]["eta"] = EPOCH + 600                # 9:36
        item = rides.items(self.st)[0]
        self.assertEqual(item["segs"], [["ALEX", app.signlib.RIDER]])    # the name, then the line and the time
        self.assertEqual(item["more"], [["OL 9:36", app.signlib.WHITE]])   # ORANGE 9:36 doesn't fit
        self.assertIn("ride-ALEX", [i["key"] for i in app.rotation(self.st, 0, EPOCH)])
        self.st["force_night"] = True
        self.assertIn("ride-ALEX", [i["key"] for i in app.rotation(self.st, 0, EPOCH)])

    def test_mailbox(self):
        app.setup_mailbox(self.st, "someone", "mbta-ride")
        self.assertIn("io.adafruit.com/api/v2/someone/feeds/mbta-ride/data", app.source(self.st, "mailbox")["url"])

        def msg(text, ago):
            return {"id": str(ago), "value": text,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(EPOCH - ago))}   # UTC, as Adafruit IO writes it
        # Newest first, as Adafruit IO sends them. Too old to act on at start-up: the one an hour ago.
        app.got_mail(self.st, None, [msg("Sam;Red;Alewife;Park Street", 30), msg("Alex;done", 60),
                                     msg("Alex;Orange;Ruggles;Downtown Crossing", 90),
                                     msg("Old;Red;Alewife;Park Street", 3600)], 0, EPOCH)
        self.assertEqual(sorted(self.st["rides"]), ["SAM"])          # Alex started and then ended his
        app.got_mail(self.st, None, [msg("Sam;Red;Alewife;Park Street", 30)], 0, EPOCH)
        self.assertEqual(self.st["rides"]["SAM"]["at"], EPOCH - 30)  # each message only once

    def test_phone_remote(self):
        code, _, out = remote.handle(self.st, "POST", "/api/cmd",
                                     json.dumps({"cmd": "ride", "text": "Alex;Red;Downtown Crossing;Alewife"}),
                                     PAGE, 0, EPOCH)
        self.assertEqual((code, json.loads(out)["rides"]), (200, [["ALEX", "Red", None]]))
