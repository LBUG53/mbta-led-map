"""Local simulator: python server.py, then http://127.0.0.1:8000

/ is the whole display, /remote the phone remote, /map the print by itself.

It runs the board's own code (firmware/app.py) in a thread with a PC fetch()
in place of the board's, so the requests, schedule and ticker are the real ones.
This file only serves the pages and turns the board's state into JSON.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sim import FIRMWARE, ROOT, layout, live, mbta_api, sample, sample_feeds

# The board's own modules, from firmware/ (see sim/__init__.py).
import app as firmware
import leds as ledlib
import remote
import sign as signlib

sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_firmware  # noqa: E402

STATIC = os.path.join(ROOT, "static")
MAP_FILES = ("print_no_outline.svg", "print_with_outline.svg", "stations.csv", "validation_report.md")
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
         ".svg": "image/svg+xml", ".json": "application/json", ".csv": "text/plain; charset=utf-8",
         ".md": "text/plain; charset=utf-8"}


def fetch_live(url):
    """The fetch(url) the board's code is handed, on the PC: (parsed JSON, bytes, milliseconds)."""
    began = time.time()
    headers = firmware.request_headers(url, mbta_api.api_key(), None)
    headers["User-Agent"] = "mbta-led-map"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError("HTTP %d" % e.code) from None    # don't let the request headers (the key) into the message
    return json.loads(raw), len(raw), int((time.time() - began) * 1000)


def now_ms():
    return int(time.monotonic() * 1000)


def epoch():
    return int(time.time())


class Board:
    """One copy of the board's code, running in a thread.

    There are up to two: "live" (real data: vehicles, sign, ticker) and "sample"
    (the sign and ticker from made-up feeds). A board pauses when no page has
    asked for it for a minute, so an idle simulator makes no requests.
    """

    IDLE_AFTER = 60     # seconds

    def __init__(self, data, use_sample):
        self.fetch = sample_feeds.Fetcher() if use_sample else fetch_live
        # A copy of the data, because the board's code adds to some of it as it runs.
        self.st = firmware.setup(json.loads(json.dumps(data)), use_map=not use_sample)
        self.lock = threading.Lock()    # held while the board's state is read or changed
        self.frame = None               # the sign's latest bitmap
        self.wled_log = []              # what the board would have sent to WLED's settings
        self.last_wanted = time.time()
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        """The board's main loop (firmware/code.py), minus the hardware."""
        loaded = False
        while True:
            if time.time() - self.last_wanted > self.IDLE_AFTER:
                time.sleep(0.5)
                continue
            with self.lock:
                if not loaded:          # like the board at start-up: fetch everything once
                    while firmware.fetch_one(self.st, now_ms(), epoch(), self.fetch):
                        pass
                    loaded = True
                firmware.tick(self.st, now_ms(), epoch(), self.fetch)
                firmware.update_map(self.st, now_ms())   # the lights' states, as the board keeps them
                self.frame = firmware.sign_frame(self.st, now_ms(), epoch())
                ui = self.st["ui"]
                if ui["posts"]:         # nothing is sent to WLED from here; it is only noted
                    self.wled_log = (self.wled_log + ui["posts"])[-5:]
                    ui["posts"] = []
                ui["dirty"] = False
            time.sleep(0.05)

    def want(self, night):
        """A page is looking: keep running, with the page's night-mode preview switch."""
        self.last_wanted = time.time()
        self.st["force_night"] = night


class Simulator:
    """Everything the pages ask for."""

    def __init__(self):
        self.cfg = layout.load_config()
        self.colors = layout.line_colors(self.cfg)
        self.parents = live.stop_parents()            # fetched into cache/ on the first run
        self.route_stops = live.route_stops(self.cfg["map"]["routes"])
        self.stations = layout.load_stations(self.route_stops)
        self.index = ledlib.build_index(self.stations)
        self.wiring = layout.load_wiring(self.stations)     # data/wiring_plan.csv
        self.counts = layout.output_counts(self.cfg, self.wiring)
        self.lights = self.light_list()
        self.board_data = build_firmware.build()    # firmware/data.json: what the board is told
        self.boards = {}                            # "live" / "sample", started on first use
        self.t0 = time.time()
        # Changes whenever the server starts with a different layout, so open pages know to reload.
        self.layout_id = hashlib.md5(json.dumps(self.lights, sort_keys=True).encode()).hexdigest()[:12]

    # --- layout
    def light_list(self):
        """Every light, in light-number order, with where it is on the print and in the wiring."""
        wired = {}
        for output in self.wiring:
            for n, light in enumerate(self.wiring[output]):
                if light >= 0:
                    wired[light] = (output, n)
        names = live.route_directions(self.cfg["map"]["routes"])
        out = []
        for i, s in enumerate(self.stations):
            for k, side in enumerate("AB"):
                route = sorted(s["a_dir"])[0]
                d = s["a_dir"][route] if side == "A" else 1 - s["a_dir"][route]
                out.append({"line": s["line"], "station": s["station"], "stop_id": s["stop_id"], "side": side,
                            "x": s[side][0], "y": s[side][1], "output": wired[2 * i + k][0],
                            "index": wired[2 * i + k][1],
                            "toward": "%s to %s" % (names[route][d][0], names[route][d][1])})
        return out

    def sign_window(self):
        """The sign-window-cut rectangle of the print, in mm."""
        with open(layout.PRINTS[False], encoding="utf-8") as f:
            m = re.search(r'<g id="sign-window-cut">\s*<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" '
                          r'height="([\d.]+)"', f.read())
        return {"x": float(m.group(1)), "y": float(m.group(2)), "w": float(m.group(3)), "h": float(m.group(4))}

    def layout_json(self):
        return {"layout_id": self.layout_id, "lights": self.lights, "map": self.cfg.get("map", {}),
                "sign_window": self.sign_window(), "output_leds": self.counts}

    # --- the boards
    def board(self, source, night):
        """The running Board for a page's data source ("live", or "sample:<scene>")."""
        kind = "live" if source == "live" else "sample"
        if kind not in self.boards:
            self.boards[kind] = Board(self.board_data, kind == "sample")
        b = self.boards[kind]
        b.want(night)
        return b

    def remote(self, method, path, body, headers, kind="live"):
        # the phone remote talks to the live board, the simulator's mode switches to the one it shows,
        # through the board's own handler
        b = self.boards.get(kind) or self.board(kind if kind == "live" else "sample:", False)
        b.last_wanted = time.time()
        with b.lock:
            return remote.handle(b.st, method, path, body, headers, now_ms(), epoch())

    # --- the map
    def map_settings(self, query):
        """The map's settings and line colors for one frame: config.yaml, the page's sliders, night mode."""
        settings = dict(self.cfg["map"])
        colors = self.colors
        if query.get("night") == "1":
            colors = firmware.night_colors(colors, (self.cfg.get("night") or {}).get("map_level", 0.5))
        return settings, colors

    def live_inputs(self, b):
        """What the live board knows right now: (vehicles, the trains we're riding, platform table, poll status)."""
        with b.lock:
            st = b.st
            fetched = st["vehicles"][1]
            fresh = fetched is not None and now_ms() - fetched < 3 * st["poll_ms"]
            poll = {"age": None if fetched is None else round((now_ms() - fetched) / 1000),
                    "stale": not fresh, "error": st["last_error"] or None, "report": firmware.report(st)}
            return list(firmware.map_vehicles(st, now_ms())), dict(st["riding"]), dict(st["parents"]), poll

    def explain(self, vehicles, parents):
        """For the page's debug view: which vehicles light each light, and which light nothing."""
        per_light = [[] for _ in self.lights]
        unmapped = []
        for v in vehicles:
            lit = ledlib.lights_for_vehicle(v, self.stations, self.index, parents)
            info = {"id": v.get("id", "sample"), "route": v["route"], "status": v["status"], "stop": v.get("stop"),
                    "direction_id": v.get("direction_id")}
            if not lit:
                unmapped.append(info)
            for n in lit:
                per_light[n].append(info)
        return per_light, unmapped

    def frame(self, query):
        """The map right now: the color of every pixel on every output, exactly as the board would
        send it to WLED, plus what the page's debug view shows."""
        settings, colors = self.map_settings(query)
        t = time.time() - self.t0
        source = query.get("source", "live")
        poll = None
        b = self.board(source, query.get("night") == "1")
        if source == "live":
            vehicles, riding, parents, poll = self.live_inputs(b)
        else:
            scene = source.split(":", 1)[-1]
            with b.lock:
                riding = dict(b.st["riding"])
                rides = dict(b.st["rides"])
                if b.st["ui"]["costume"]:           # the mode switches' costume mode replaces the scene
                    scene = "moving"
            vehicles = sample.vehicles(scene, self.stations, self.route_stops, t)
            vehicles += sample.ride_vehicles(rides, self.route_stops, time.time())
            parents = self.parents

        # The same two steps as the board (firmware/app.py: update_map, map_chains).
        states = ledlib.light_states(vehicles, self.stations, self.index, parents, riding)
        chains = ledlib.render(states, self.stations, self.wiring, settings, colors)
        extras = False
        if b is not None:                   # the remote's extras: find a station, the goal sweep, off
            with b.lock:
                chains = remote.map_overlay(b.st, chains, now_ms(), t)
                extras = remote.animating(b.st, now_ms())

        per_light, unmapped = self.explain(vehicles, parents)
        return {"source": source, "states": states, "chains": chains, "vehicles": per_light,
                "unmapped": unmapped, "poll": poll, "ddp_leds": len(ledlib.combined(chains, self.counts)),
                "animated": extras, "layout_id": self.layout_id}

    # --- the sign
    def sign(self, query):
        """The sign, drawn by the board's code (live, or from the sample feeds), plus debug details."""
        b = self.board(query.get("source", "live"), query.get("night") == "1")
        with b.lock:
            st = b.st
            bitmap = b.frame or signlib.blank()
            rows = firmware.sign_rows(st, now_ms(), epoch())
            item = st["tk"]["item"]
            rotation = firmware.rotation(st, now_ms(), epoch())
            debug = {
                "rows": [{"label": r["badge"], "stop": r["stop_id"], "times": rows[n]["times"],
                          "walk": r.get("walk_minutes", 0), "count": len(st["preds"][n][0])}
                         for n, r in enumerate(st["rows"])],
                "showing": "".join(seg[0] for seg in item["segs"]) if item else "(starting)",
                "rotation": [("".join(seg[0] for seg in it["segs"]) or "(pause)")[:40] for it in rotation],
                "sources": firmware.report(st), "error": st["last_error"] or None,
            }
            palette = firmware.sign_palette(st, self.board_data, firmware.is_night(st, epoch()))
        # Each pixel is a palette index 0-15, sent as one hex digit.
        return {"w": signlib.W, "h": signlib.H, "palette": palette,
                "rows": ["".join("%x" % v for v in row) for row in bitmap], "debug": debug}


SIM = None      # the one Simulator, made in main() (or by the tests)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # the page polls often; keep the console quiet

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj, code=200):
        self.send(code, json.dumps(obj).encode("utf-8"), TYPES[".json"])

    def send_file(self, path):
        if not os.path.isfile(path):
            return self.send(404, b"not found", "text/plain")
        with open(path, "rb") as f:
            self.send(200, f.read(), TYPES.get(os.path.splitext(path)[1], "application/octet-stream"))

    def send_remote(self, method, path, body):
        headers = dict((k.lower(), v) for k, v in self.headers.items())
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        code, ctype, out = SIM.remote(method, path, body, headers, "sample" if query.get("board") == "sample" else "live")
        if ctype == "file":             # the board's way of saying "send this file of mine"
            return self.send_file(os.path.join(FIRMWARE, out))
        self.send(code, out.encode("utf-8"), ctype)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        query = dict(urllib.parse.parse_qsl(url.query))
        p = url.path
        try:
            if p == "/":
                return self.send_file(os.path.join(STATIC, "index.html"))
            if p == "/print.svg":
                return self.send_file(layout.PRINTS[query.get("outline") == "1"])
            if p.startswith("/static/"):
                return self.send_file(os.path.join(STATIC, os.path.basename(p)))   # no subpaths
            if p == "/map":
                return self.send_file(os.path.join(STATIC, "map.html"))
            if p.startswith("/map/") and os.path.basename(p) in MAP_FILES:
                return self.send_file(os.path.join(layout.DATA, os.path.basename(p)))
            if p in ("/remote", "/remote/") or p.startswith("/remote/api/"):
                return self.send_remote("GET", p, "")
            if p == "/api/layout":
                return self.send_json(SIM.layout_json())
            if p == "/api/frame":
                return self.send_json(SIM.frame(query))
            if p == "/api/sign":
                return self.send_json(SIM.sign(query))
            self.send(404, b"not found", "text/plain")
        except Exception as e:  # show errors in the page, not a dropped connection
            self.send_json({"error": "%s: %s" % (type(e).__name__, e)}, 500)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        try:
            if p.startswith("/remote/api/"):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8")
                return self.send_remote("POST", p, body)
            self.send(404, b"not found", "text/plain")
        except Exception as e:
            self.send_json({"error": "%s: %s" % (type(e).__name__, e)}, 500)


def main():
    global SIM
    ap = argparse.ArgumentParser(description="MBTA LED map simulator")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    try:
        SIM = Simulator()
    except mbta_api.ApiError as e:
        # Even the sample scenes need the lookup tables, which are fetched once and then kept in cache/.
        raise SystemExit("The simulator needs the internet the first time it starts, to fetch the lookup tables "
                         "from the MBTA API (%s). Connect and run it again; afterwards it works offline "
                         "on its sample data." % e)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)     # this computer only
    print("MBTA LED map simulator on http://127.0.0.1:%d  (Ctrl+C to stop)" % args.port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
