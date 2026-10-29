"""The phone remote (remote.html) and the modes it switches between.

Modes: transit (normal), game (Magic life totals + turn picker), bruins (just
the Bruins game, polled every 15 s), music (WLED's sound-reactive effects on the
map instead of trains), off. Costume is a switch, not a mode: the
map shows sample trains, the sign sample departures and HAPPY HALLOWEEN, and
nothing is fetched, so it works without the internet once the clock is set.
Its state is st["ui"].

code.py (or the simulator) passes each web request to handle();
app.py calls band()/sign_frame() for the sign and map_overlay() for the map.
Like app.py this also runs in the simulator, so no hardware access here.
"""
import json
import random

import feeds
import rides
import sign as signlib

MODES = ("transit", "game", "bruins", "music", "off")
# What each mode fetches (None = everything). The map keeps its trains in game and bruins mode.
NEEDS = {"transit": None, "game": ("vehicles", "mailbox", "ride"),
         "bruins": ("vehicles", "mailbox", "ride", "bruins-find", "bruins"), "music": ("mailbox", "ride"), "off": ()}
PLAYER = (6, 7, 8, 13, 14, 15)          # palette indexes: the three route colors' slots, then the spare ones
PLAYER_RGB = ((255, 0, 0), (40, 90, 255), (0, 220, 60), (255, 200, 0), (200, 60, 255), (255, 214, 160))
PLAYER_NAMES = ("RED", "BLUE", "GREEN", "GOLD", "PURPLE", "WHITE")
GOLD = (255, 170, 0)
# Every address handle() answers. The board's server registers each one; a missing one got a 404 there
# while the simulator, which passes everything to handle(), worked.
PATHS = ("/", "/api/state", "/api/rides", "/api/stations", "/api/cmd")
FIND_MS = 20000             # a found station blinks this long
PICK_SPIN_MS = 2600         # the turn picker runs through the players, then stops
PICK_SHOW_MS = 30000        # and shows who goes first this long
GOAL_MS = 8000
TIMER_DONE_MS = 15000
BLINK_MS = 300
BRUINS_LIVE_SECONDS = 15    # how often bruins mode asks for the score during a game
MESSAGE_MAX = 120
MESSAGE_GAP_MS = 6000       # outside transit mode the message takes turns with the clock or the game's period
MESSAGE_STILL_MS = 5000     # how long a message that fits is shown each turn
SCROLL_SPEED = 32           # pixels a second, the same as the ticker's alerts
HOP_MS = 6000               # costume trains: each one waits 4 s at a station, then 2 s on its way to the next
COSTUME_EVERY = (9, 6)      # costume departures: a bus every 9 minutes on the top row, a train every 6 below
COSTUME_TEXT = "HAPPY HALLOWEEN"
COSTUME_SHOW_MS = 20000     # the departures are shown this long, then COSTUME_TEXT crosses the whole sign
KOROK_MS = 8000             # the korok pops up, says YAHAHA!, then YOU FOUND ME!, then the sign goes back
KOROK_YAHAHA_MS = 3500
KOROK_RGB = ((0, 220, 60), (255, 120, 0))   # leaf, wood: borrowed palette slots 6 and 7, like game mode's players
# 14 wide so YAHAHA! (44 px) fits beside it: g = leaf, w = wood.
KOROK = ("......gg......", ".....gggg.....", "....gggggg....", "...gggggggg...", "...gggggggg...",
         "....gggggg....", "......ww......", "...wwwwwwww...", ".wwwwwwwwwwww.", "wwwwwwwwwwwwww",
         "ww..wwwwww..ww", "ww..wwwwww..ww", "wwwwwwwwwwwwww", "wwwwww..wwwwww", ".wwwww..wwwww.",
         "..wwwwwwwwww..", "....wwwwww....", "......ww......", "...w.gwwg.w...", "....wgwwgw....",
         ".....gwwg.....", ".....gggg.....", "....gggggg....", ".....w..w.....", ".....w..w.....",
         "....ww..ww....")


def new_ui():
    return {"mode": "transit", "back": "transit", "life": [40, 40, 40, 40], "start": 40,
            "pick": None,           # [player, ms the spin began]
            "timer": None,          # ms on the steady clock when it ends
            "timer_done": None,     # ms it ended, while TIME! flashes
            "message": "",
            "costume": False,       # sample trains on the map
            "align": False,         # the sign shows its alignment rings instead of anything else
            "korok": None,          # ms the korok popped up
            "music_fx": 0,          # which of st["music"] music mode runs
            "message_at": 0,        # ms it was set: its turns are counted from here
            "sign_bri": None,       # 0.01-1, or None for the configured brightness
            "map_bri": None,        # percent last sent to WLED, or None
            "wake": None,           # epoch to come back on from off, or None
            "find": None,           # [station number, ms the blink ends]
            "goal": None,           # ms of the last Bruins goal
            "posts": [],            # JSON bodies waiting to go to WLED's /json/state
            "dirty": True,          # the palette needs setting again
            "frame": None, "key": None, "fetched": 0, "where": None, "free": None}


def wants(st, name):
    if st["ui"]["costume"]:
        return False
    needs = NEEDS[st["ui"]["mode"]]
    return needs is None or name in needs


def set_mode(st, mode, now_ms):
    ui = st["ui"]
    if mode != "off":
        ui["wake"] = None
    if mode == ui["mode"]:
        return
    if ui["mode"] != "off":
        ui["back"] = ui["mode"]
    ui["mode"] = mode
    if mode == "music":
        music_post(st, now_ms)
    ui["dirty"] = True
    ui["key"] = None
    st["band_key"] = None               # the transit picture is redrawn when it comes back
    st["base_at"] = -100000
    for s in st["sources"]:             # don't make the new mode wait for its first data
        if wants(st, s["name"]) and s["name"] in ("bruins-find", "bruins", "predictions", "vehicles"):
            s["due"] = min(s["due"], now_ms)


def line_runs(st):
    """[line, first LED, LED after the last] for each stretch of one line along the strings, counted the way
    WLED numbers its LEDs. A SKIP pixel or two inside a stretch doesn't split it."""
    runs = []
    base = 0
    for k in range(len(st["outputs"])):
        lights = st["wiring"][st["outputs"][k]]
        first = len(runs)
        for n in range(len(lights)):
            if lights[n] < 0:
                continue
            line = st["stations"][lights[n] // 2]["line"]
            at = base + n
            if len(runs) > first and runs[-1][0] == line and at - runs[-1][2] <= 2:
                runs[-1][2] = at + 1
            else:
                runs.append([line, at, at + 1])
        base += st["counts"][k]
    return runs


def music_post(st, now_ms):
    # WLED runs the effect in segments: one per output, so it runs along each string, or for Lines one per
    # stretch of a line, in the line's color. The trains come back by themselves: WLED switches to the
    # board's DDP frames as soon as they arrive again.
    ui = st["ui"]
    if not st["music"]:
        return
    name, fx, lines = st["music"][ui["music_fx"]]
    segs = []
    if lines:
        for line, a, b in line_runs(st):
            # pal 2 is WLED's "Color 1": the effect in the segment's own color. Speed 100 is what was tried.
            segs.append({"start": a, "stop": b, "fx": fx, "sx": 100, "pal": 2, "col": [st["colors"][line]]})
    else:
        start = 0
        for count in st["counts"]:
            segs.append({"start": start, "stop": start + count, "fx": fx, "sx": 128, "pal": 0, "col": [[255, 160, 0]]})
            start += count
    for i in range(len(segs)):
        # Unfrozen: segment 0 had been left frozen and black by a wiring test.
        segs[i]["id"] = i
        segs[i]["on"] = True
        segs[i]["frz"] = False
    for i in range(len(segs), len(line_runs(st)) + len(st["counts"])):
        segs.append({"id": i, "stop": 0})                   # WLED deletes a segment that stops at 0
    ui["posts"] = [p for p in ui["posts"] if "seg" not in p]          # only the newest effect goes out
    ui["posts"].append({"on": True, "seg": segs})
    st["wled_next"] = min(st["wled_next"], now_ms + 2000)


def update(st, now_ms, epoch):
    # called every frame: expire the timer, blinks, the goal flash, and wake up from off
    ui = st["ui"]
    if ui["timer"] is not None and now_ms >= ui["timer"]:
        ui["timer"] = None
        ui["timer_done"] = now_ms
    if ui["timer_done"] is not None and now_ms - ui["timer_done"] >= TIMER_DONE_MS:
        ui["timer_done"] = None
    if ui["find"] is not None and now_ms >= ui["find"][1]:
        ui["find"] = None
    if ui["korok"] is not None and now_ms - ui["korok"] >= KOROK_MS:
        ui["korok"] = ui["key"] = None
        ui["dirty"] = True              # give slots 6 and 7 back
        st["band_key"] = None           # the usual picture is drawn again
        st["base_at"] = -100000
    if ui["goal"] is not None and now_ms - ui["goal"] >= GOAL_MS:
        ui["goal"] = None
    if ui["pick"] is not None and now_ms - ui["pick"][1] >= PICK_SPIN_MS + PICK_SHOW_MS:
        ui["pick"] = None
    if ui["mode"] == "off" and ui["wake"] is not None and epoch >= ui["wake"]:
        set_mode(st, ui["back"], now_ms)


def goal(st, now_ms):
    st["ui"]["goal"] = now_ms


def game_every(st, name, live):
    if name == "bruins" and live and st["ui"]["mode"] == "bruins":
        return BRUINS_LIVE_SECONDS
    return None


# --- the sign
def timer_text(seconds):
    """'TMR 4:59', or 'TMR 75M' from an hour up."""
    if seconds >= 3600:
        return "TMR %dM" % (seconds // 60)
    return "TMR %d:%02d" % (seconds // 60, seconds % 60)


def band(st, now_ms, epoch):
    # What covers the bottom row right now (timer, goal, turn picker), or None.
    ui = st["ui"]
    on = now_ms // BLINK_MS % 2 == 0
    if ui["goal"] is not None:
        return [["GOAL!", signlib.BRUINS]] if on else []
    if ui["pick"] is not None and ui["mode"] == "game":
        who, began = ui["pick"]
        alive = [i for i in range(len(ui["life"])) if ui["life"][i] > 0] or [who]
        if now_ms - began < PICK_SPIN_MS:
            who = alive[(now_ms - began) // 120 % len(alive)]
            return [[PLAYER_NAMES[who], PLAYER[who]]]
        return [[PLAYER_NAMES[who] + " 1ST", PLAYER[who]]]
    if ui["timer_done"] is not None:
        return [["TIME!", signlib.ALERT]] if on else []
    if ui["timer"] is not None:
        return [[timer_text((ui["timer"] - now_ms + 999) // 1000), signlib.WHITE]]
    return None


def message_layer(st, now_ms):
    # Outside transit mode there's no ticker, so the message alternates with the clock in the
    # bottom row. Returns a ticker_band layer, or None when it's the clock's turn.
    ui = st["ui"]
    if not ui["message"] or ui["mode"] in ("transit", "off"):
        return None
    segs = [[ui["message"], signlib.WHITE]]
    w = signlib.segs_width(segs)
    span = signlib.RIGHT + 2 - signlib.LEFT
    scroll = w > span
    shown = (w + span) * 1000 // SCROLL_SPEED if scroll else MESSAGE_STILL_MS
    at = (now_ms - ui["message_at"]) % (shown + MESSAGE_GAP_MS)
    if at >= shown:
        return None
    if scroll:
        return [segs, signlib.RIGHT + 2 - at * SCROLL_SPEED // 1000, 0, 0]
    return [segs, signlib.LEFT, 0, 0]


def busy(st, now_ms, epoch):
    # Don't start a (blocking) request while something is moving on the sign.
    layer = message_layer(st, now_ms)
    return band(st, now_ms, epoch) is not None or (layer is not None and layer[1] != signlib.LEFT)


def period_text(g):
    """'P2 14:31', 'OT 3:10' or 'END P1' for a hockey game in progress."""
    p = g.get("period") or 0
    label = ("P" + str(p)) if p <= 3 else ("OT" if p == 4 else "SO")
    clock = g.get("clock") or ""
    return (label + " " + clock) if clock and clock != "0:00" else ("END " + label)


def right_text(bm, y, text, color):
    signlib.draw_text(bm, signlib.RIGHT + 1 - signlib.text_width(text, signlib.LARGE), y, text, color,
                      font=signlib.LARGE)


def sign_frame(st, now_ms, epoch, over):
    ui = st["ui"]
    mode = ui["mode"]
    big = signlib.LARGE
    if mode == "off":
        key = "off"
    elif mode == "game":
        key = ["game", list(ui["life"])]
    elif mode == "music":
        key = ["music", ui["music_fx"]]
    else:
        key = ["bruins", st["games"].get("bruins"), feeds.local(epoch) // 86400]
    if over is None and mode != "off":
        over = [[feeds.clock_text(epoch), signlib.WHITE]]
        if mode == "bruins":
            g = st["games"].get("bruins")
            if g and g["state"] == "in":
                over = [[period_text(g), signlib.WHITE]]
            elif g and g["state"] == "post":
                over = [["FINAL", signlib.WHITE]]
            elif g:
                over = [["AT " + feeds.clock_text(g["start"]), signlib.WHITE]]
    layer = [over, signlib.LEFT, 0, 0]
    if mode != "off" and band(st, now_ms, epoch) is None:
        layer = message_layer(st, now_ms) or layer      # the message's turn
    key = str([key, layer])
    if key == ui["key"] and ui["frame"] is not None:
        return ui["frame"]
    bm = signlib.blank()
    if mode == "game":
        life = ui["life"]
        top = (len(life) + 1) // 2
        for r in range(2):
            row = life[:top] if r == 0 else life[top:]
            for c in range(len(row)):
                who = c if r == 0 else top + c
                text = str(max(row[c], 0))
                color = PLAYER[who] if row[c] > 0 else signlib.DIM
                w = signlib.text_width(text, big)
                if c == 0:
                    x = signlib.LEFT
                elif c == len(row) - 1:
                    x = signlib.RIGHT + 1 - w
                else:
                    x = (signlib.LEFT + signlib.RIGHT + 1 - w) // 2
                signlib.draw_text(bm, x, 1 + r * 10, text, color, font=big)
    elif mode == "music":
        signlib.draw_text(bm, signlib.LEFT, 1, "MUSIC", signlib.RIDER, font=big)
        if st["music"]:
            name = clean(st["music"][ui["music_fx"]][0])
            if signlib.text_width(name, big) <= signlib.RIGHT + 1 - signlib.LEFT:
                signlib.draw_text(bm, signlib.LEFT, 11, name, signlib.DIM, font=big)
    elif mode == "bruins":
        g = st["games"].get("bruins")
        if g is None:
            signlib.draw_text(bm, signlib.LEFT, 1, "BRUINS", signlib.BRUINS, font=big)
            signlib.draw_text(bm, signlib.LEFT, 11, "NO GAME", signlib.DIM, font=big)
        else:
            signlib.draw_text(bm, signlib.LEFT, 1, "BOS", signlib.BRUINS, font=big)
            signlib.draw_text(bm, signlib.LEFT, 11, g["opp"], signlib.WHITE, font=big)
            if g["state"] != "pre":
                right_text(bm, 1, str(g["us"]), signlib.BRUINS)
                right_text(bm, 11, str(g["them"]), signlib.WHITE)
            else:
                right_text(bm, 11, "HOME" if g.get("home") else "AWAY", signlib.DIM)
    if mode != "off":
        bm = signlib.ticker_band(bm, [layer], False)
    ui["key"] = key
    ui["frame"] = bm
    return bm


def quantize(rgb, brightness, bit_depth):
    # Round to what the panel can show at this bit depth, the same way sign.palette() does.
    levels = (1 << bit_depth) - 1
    out = []
    for v in rgb:
        out.append(int(int(v * brightness * levels / 255 + 0.5) * 255 / levels + 0.5))
    return (out[0], out[1], out[2])


def palette(st, pal, brightness, bit_depth):
    # Game mode borrows the route-color slots (6-8) for players 1-3; 4-6 use the spare slots.
    pal = list(pal)
    while len(pal) < 16:
        pal.append((0, 0, 0))
    for k in range(3, 6):
        pal[PLAYER[k]] = quantize(PLAYER_RGB[k], brightness, bit_depth)
    if st["ui"]["mode"] == "game":
        for k in range(3):
            pal[PLAYER[k]] = quantize(PLAYER_RGB[k], brightness, bit_depth)
    if st["ui"]["korok"] is not None:
        for k in range(2):
            pal[signlib.FIRST_ROW_COLOR + k] = quantize(KOROK_RGB[k], brightness, bit_depth)
    return pal


# --- the map
def animating(st, now_ms):
    ui = st["ui"]
    return ui["goal"] is not None or ui["find"] is not None


def map_overlay(st, chains, now_ms, t):
    """Change the map's colors for the current extras. chains: {output: [(r, g, b), ...]}."""
    ui = st["ui"]
    if ui["mode"] in ("off", "music"):              # in music mode WLED draws the map, not the board
        for output in chains:
            chains[output] = [(0, 0, 0)] * len(chains[output])
        return chains
    if ui["goal"] is not None:                      # black and gold run along every line
        step = (now_ms - ui["goal"]) // 60
        for output in chains:
            lights = st["wiring"][output]
            row = chains[output]
            for n in range(len(row)):
                row[n] = GOLD if lights[n] >= 0 and (n + step) % 6 < 3 else (0, 0, 0)
    if ui["find"] is not None:                      # the station's two lights blink white
        if ui["where"] is None:
            ui["where"] = {}
            for output in st["wiring"]:
                lights = st["wiring"][output]
                for n in range(len(lights)):
                    if lights[n] >= 0:
                        ui["where"][lights[n]] = (output, n)
        color = (255, 255, 255) if now_ms // BLINK_MS % 2 == 0 else (0, 0, 0)
        for light in (2 * ui["find"][0], 2 * ui["find"][0] + 1):
            output, n = ui["where"][light]
            chains[output][n] = color
    return chains


# --- the remote page
def clean(text):
    # Only characters the sign's font has; the font is capitals only.
    out = ""
    for ch in str(text).upper():
        if ch in signlib.LARGE:         # only what the sign's font can draw
            out += ch
    return " ".join(out.split())[:MESSAGE_MAX]


def number(value, low, high, fallback):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return fallback


def wake_epoch(text, epoch):
    # "7:00" -> epoch of the next 7:00 Boston time
    h, m = str(text).split(":")
    local = feeds.local(epoch)
    target = local // 86400 * 86400 + int(h) % 24 * 3600 + int(m) % 60 * 60
    if target <= local:
        target += 86400
    return epoch + target - local


def apply(st, c, now_ms, epoch):
    # One command from the page, e.g. {"cmd": "life", "p": 0, "d": -1}.
    ui = st["ui"]
    cmd = c.get("cmd")
    life = ui["life"]
    if cmd == "mode" and c.get("mode") in MODES:
        set_mode(st, c["mode"], now_ms)
    elif cmd == "off":
        set_mode(st, "off", now_ms)
        ui["wake"] = wake_epoch(c["wake"], epoch) if c.get("wake") else None
    elif cmd == "on":
        set_mode(st, ui["back"], now_ms)
    elif cmd == "life":
        p = number(c.get("p"), 0, len(life) - 1, 0)
        life[p] = max(-99, min(999, life[p] + number(c.get("d"), -999, 999, 0)))
    elif cmd == "set":
        life[number(c.get("p"), 0, len(life) - 1, 0)] = number(c.get("v"), -99, 999, ui["start"])
    elif cmd == "players":
        ui["start"] = number(c.get("start"), 1, 999, ui["start"])
        ui["life"] = [ui["start"]] * number(c.get("n"), 2, 6, len(life))
        ui["pick"] = None
    elif cmd == "reset":
        ui["life"] = [ui["start"]] * len(life)
        ui["pick"] = None
    elif cmd == "pick":
        alive = [i for i in range(len(life)) if life[i] > 0]
        if alive:
            ui["pick"] = [alive[random.randint(0, len(alive) - 1)], now_ms]
    elif cmd == "timer":
        ui["timer"] = now_ms + number(c.get("seconds"), 1, 359999, 60) * 1000
        ui["timer_done"] = None
    elif cmd == "timer_stop":
        ui["timer"] = ui["timer_done"] = None
    elif cmd == "message":
        ui["message"] = clean(c.get("text") or "")
        ui["message_at"] = now_ms               # in every mode it shows straight away
        if ui["message"] and ui["mode"] == "transit":
            st["tk"]["queue"].append(message_item(ui["message"]))      # show it right away
    elif cmd == "sign_bri":
        ui["sign_bri"] = None if c.get("pct") is None else number(c.get("pct"), 1, 100, 60) / 100
        ui["dirty"] = True
    elif cmd == "map_bri":
        ui["map_bri"] = number(c.get("pct"), 1, 100, 6)
        ui["posts"] = [p for p in ui["posts"] if "bri" not in p]        # only the newest setting goes out
        ui["posts"].append({"bri": max(1, ui["map_bri"] * 255 // 100)})
        st["wled_next"] = min(st["wled_next"], now_ms + 2000)           # a new setting is tried soon, even if WLED has been silent
    elif cmd == "find":
        ui["find"] = [number(c.get("i"), 0, len(st["stations"]) - 1, 0), now_ms + FIND_MS]
    elif cmd == "find_stop":
        ui["find"] = None
    elif cmd == "costume":
        ui["costume"] = bool(c.get("on"))
        st["map_dirty"] = True
    elif cmd == "align":
        ui["align"] = bool(c.get("on"))
        ui["key"] = None
        st["band_key"] = None           # the usual picture is drawn again when it's switched off
        st["base_at"] = -100000
    elif cmd == "music_fx":
        ui["music_fx"] = number(c.get("i"), 0, max(0, len(st["music"]) - 1), 0)
        ui["key"] = None
        if ui["mode"] == "music":
            music_post(st, now_ms)
    elif cmd == "korok":
        ui["korok"] = now_ms
        ui["key"] = None
        ui["dirty"] = True
    elif cmd == "ride":                         # the same message a phone sends: NAME;ROUTE;FROM;TO or NAME;DONE
        rides.apply(st, c.get("text") or "", epoch, now_ms)


def line_paths(route_stops):
    """(route, stops in order) for every path a train can run, one per branch: the Red Line is two."""
    paths = []
    for route in ("Red", "Mattapan", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"):
        stops = route_stops.get(route) or []
        if route == "Red" and "place-asmnl" in stops and "place-jfk" in stops:
            # The MBTA lists Alewife to Ashmont, then North Quincy to Braintree: run each branch.
            a, j = stops.index("place-asmnl"), stops.index("place-jfk")
            paths.append((route, stops[:a + 1]))
            paths.append((route, stops[:j + 1] + stops[a + 1:]))
        else:
            paths.append((route, stops))
    return paths


def align_frame(st):
    """For squaring the sign up behind its window: the outermost ring of LEDs white, the next ring yellow.
    The bezel covers about half of the outer ring (make_parts.py, BEZEL_OVER), so with the sign square an
    even half-row of white shows on every side; on a side where it's off, either all the white or the
    yellow shows."""
    ui = st["ui"]
    if ui["key"] != "align" or ui["frame"] is None:
        bm = signlib.blank()
        for ring, color in ((0, signlib.WHITE), (1, signlib.ALERT)):
            for x in range(ring, signlib.W - ring):
                bm[ring][x] = bm[signlib.H - 1 - ring][x] = color
            for y in range(ring, signlib.H - ring):
                bm[y][ring] = bm[y][signlib.W - 1 - ring] = color
        ui["key"] = "align"
        ui["frame"] = bm
    return ui["frame"]


def korok_frame(st, now_ms):
    ui = st["ui"]
    t = now_ms - ui["korok"]
    top = 3 + max(0, len(KOROK) - t // 15)      # it rises from the bottom edge, then speaks
    lines = () if top > 3 else ("YAHAHA!",) if t < KOROK_YAHAHA_MS else ("YOU", "FOUND", "ME!")
    key = "korok %d %d" % (top, len(lines))
    if key != ui["key"] or ui["frame"] is None:
        bm = signlib.blank()
        colors = {"g": signlib.FIRST_ROW_COLOR, "w": signlib.FIRST_ROW_COLOR + 1}
        for gy in range(len(KOROK)):
            if top + gy < signlib.H - 1:
                row = KOROK[gy]
                for gx in range(len(row)):
                    if row[gx] in colors:
                        bm[top + gy][signlib.LEFT + gx] = colors[row[gx]]
        x0 = signlib.LEFT + len(KOROK[0]) + 1
        y = 11 if len(lines) == 1 else 1                # the sign's own rows: 1, 11 and 21
        for text in lines:
            w = signlib.text_width(text, signlib.LARGE)
            signlib.draw_text(bm, x0 + (signlib.RIGHT + 1 - x0 - w) // 2, y, text, signlib.WHITE, font=signlib.LARGE)
            y += 10
        ui["key"] = key
        ui["frame"] = bm
    return ui["frame"]


def costume_trains(route_stops, now_ms):
    """Sample trains for costume mode, in the same shape as the MBTA's: three each way on every line and
    branch, stepping one station every HOP_MS. The simulator's "moving trains" scene uses this too."""
    out = []
    step = now_ms // HOP_MS
    moving = now_ms % HOP_MS >= 4000
    for route, stops in line_paths(route_stops):
        n = len(stops)
        if n < 2:
            continue
        for d in (0, 1):
            for k in range(3):
                pos = (k * n // 3 + step) % (n - 1)        # never waits at the last stop
                i = pos if d == 0 else n - 1 - pos
                if moving:
                    stop, status = stops[i + 1 if d == 0 else i - 1], "IN_TRANSIT_TO"
                else:
                    stop, status = stops[i], "STOPPED_AT"
                out.append({"id": "costume", "route": route, "stop": stop, "status": status, "direction_id": d})
    return out


def costume_times(n, epoch):
    """Sample countdowns for sign row n, as row_times() gives them: [["4", ""], ["13", ""]]."""
    every = COSTUME_EVERY[n % len(COSTUME_EVERY)] * 60
    secs = every - (epoch + 180 * n) % every
    out = []
    for s in (secs, secs + every):
        out.append(["NOW" if s < 60 else str(s // 60), ""])
    return out


def costume_frame(st, now_ms):
    """The whole sign while COSTUME_TEXT goes by in big letters, or None while the departures show."""
    ui = st["ui"]
    big = signlib.LARGE
    w = signlib.text_width(COSTUME_TEXT, big)
    span = signlib.RIGHT + 2 - signlib.LEFT
    cross_ms = (w + span) * 1000 // SCROLL_SPEED
    at = now_ms % (COSTUME_SHOW_MS + cross_ms) - COSTUME_SHOW_MS
    if at < 0:
        return None
    x = signlib.RIGHT + 2 - at * SCROLL_SPEED // 1000
    key = "costume %d" % x
    if key != ui["key"] or ui["frame"] is None:
        bm = signlib.blank()
        signlib.draw_text(bm, x, (signlib.H - 9) // 2, COSTUME_TEXT, signlib.BRUINS, signlib.LEFT,
                          signlib.RIGHT, font=big)       # the Bruins' gold reads as Halloween orange
        ui["key"] = key
        ui["frame"] = bm
    st["band_key"] = None               # the departures are drawn again when it has gone by
    return ui["frame"]


def message_item(text):
    segs = [[text, signlib.WHITE]]
    span = signlib.RIGHT + 2 - signlib.LEFT
    return feeds.item("message", segs, scroll=signlib.segs_width(segs) > span)


def state(st, now_ms, epoch):
    ui = st["ui"]
    pick = None
    if ui["pick"] is not None and now_ms - ui["pick"][1] >= PICK_SPIN_MS:
        pick = ui["pick"][0]
    sources = []
    for s in st["sources"]:
        sources.append([s["name"], s["ok"], s["errors"], s["ms"]])
    return {"mode": ui["mode"], "life": ui["life"], "start": ui["start"], "pick": pick,
            "spinning": ui["pick"] is not None and pick is None,
            "timer": 0 if ui["timer"] is None else (ui["timer"] - now_ms + 999) // 1000,
            "message": ui["message"], "costume": ui["costume"], "align": ui["align"],
            "music": [m[0] for m in st["music"]], "music_fx": ui["music_fx"],
            "sign_bri": None if ui["sign_bri"] is None else int(ui["sign_bri"] * 100 + 0.5),
            "sign_default": int(st.get("sign_brightness", 0.6) * 100 + 0.5),
            "map_bri": ui["map_bri"],
            "wake": None if ui["wake"] is None else feeds.clock_text(ui["wake"]),
            "find": None if ui["find"] is None else ui["find"][0],
            "game": st["games"].get("bruins"), "clock": feeds.clock_text(epoch),
            "rides": [[n, st["rides"][n]["routes"][0], st["rides"][n]["eta"] and feeds.clock_text(st["rides"][n]["eta"])]
                      for n in sorted(st["rides"])],
            "players": [PLAYER_NAMES[i] for i in range(len(ui["life"]))],
            "colors": [list(PLAYER_RGB[i]) for i in range(len(ui["life"]))],
            "status": {"failures": st["failures"], "error": st["last_error"], "free": ui["free"],
                       "lit": sum(1 for s in st["states"] if s), "sources": sources}}


def refused(st, path, headers):
    # The page itself is open to anyone on the network. The api/ calls need the X-Remote header:
    # a browser won't let another website add a custom header without asking first (a CORS
    # preflight), and nothing here answers that, so a site you visit can't drive the sign.
    if "api/" not in path:
        return 0
    if headers.get("x-remote") != "1":
        return 403
    token = st.get("remote_token")
    if token and headers.get("x-remote-token") != token:
        return 401                      # the page then asks for the code
    return 0


def handle(st, method, path, body, headers, now_ms, epoch):
    # Returns (status, content type, text). Content type "file" means send the file named in text.
    path = path.split("?")[0]
    status = refused(st, path, headers)
    if status:
        return status, "application/json", json.dumps({"error": status})
    try:
        if path.endswith("api/state"):
            return 200, "application/json", json.dumps(state(st, now_ms, epoch))
        if path.endswith("api/rides"):
            return 200, "application/json", json.dumps(rides.choices(st))
        if path.endswith("api/stations"):
            return 200, "application/json", json.dumps([[s["line"], s.get("name") or s["stop_id"]] for s in st["stations"]])
        if path.endswith("api/cmd") and method == "POST":
            apply(st, json.loads(body or "{}"), now_ms, epoch)
            return 200, "application/json", json.dumps(state(st, now_ms, epoch))
        if path in ("/", "/remote", "/remote/"):
            return 200, "file", "remote.html"
    except (ValueError, KeyError, TypeError, AttributeError) as e:     # not JSON, or not a command
        return 400, "application/json", json.dumps({"error": type(e).__name__})
    return 404, "text/plain", "not found"
