"""The display logic: polling, the ticker, the sign picture and the map packet.

Runs on the board (called from code.py) and unchanged in the simulator, so no
hardware access in here. The caller passes in fetch(url), which returns
(parsed JSON, bytes, ms).

A network request freezes the board until it returns, so requests only go
out while the ticker is holding still, one per hold.

Times: now_ms is a monotonic ms clock, epoch is UTC seconds, t is seconds for
the map animation (code.py wraps it every hour - CircuitPython floats lose
precision on big numbers).
"""
import gc
import json

import feeds
import leds as ledlib
import remote
import rides
import sign as signlib

API = "https://api-v3.mbta.com"
AIO = "https://io.adafruit.com/api/v2/"
VEHICLE_FIELDS = "current_status,direction_id,stop"
ALERT_FIELDS = "header,short_header,effect,severity,informed_entity"
PRED_FIELDS = "departure_time,schedule_relationship,direction_id"
ALERT_SECONDS = 120
MAILBOX_SECONDS = 15        # how soon a ride message from a phone is noticed (Adafruit IO allows far more)
RIDE_SECONDS = 20           # each ride's train is looked up this often, the rides taking turns
MAIL_FRESH_S = 1800         # at start-up, act on ride messages up to this old (the board restarted mid-ride)
WEATHER_SECONDS = 1800
FIND_SECONDS = 1800         # look for the day's game this often, and just after midnight
SCORE_SECONDS = 900
LIVE_SCORE_SECONDS = 60
RETRY_MS = 30000           # first retry after a failure: the source's own interval, but no longer than this
BACKOFF_MAX_MS = 120000    # each failure in a row doubles the wait, up to this
WLED_RETRY_MS = 2000       # a setting WLED did not take is sent again after this, then twice as long...
WLED_RETRY_MAX_MS = 60000  # ...up to this
STOP_LOOKUP_MS = 5000      # at most one "which station is this platform?" lookup this often
PRED_STALE_MS = 120000     # a row shows "--" when its predictions are older than this
WEATHER_STALE_MS = 2 * 3600 * 1000
DDP_PORT = 4048
DDP_HEADER = 10
DAYS = ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")

ROWS_REDRAW_MS = 500       # the two route rows are drawn again this often, for their countdowns
SLIDE_MS = 500             # a static item slides up into place
PAUSE_MS = 2000            # the gap that stands in for a static item when there are none
FLASH_MS = 3000            # a SCORE! flash
BLINK_MS = 300
PAGE_EXTRA_MS = 1500       # a two-text item holds this much longer, turning over halfway
SCROLL_SPEED = 32          # pixels a second, for alerts
SCROLL_SPAN = signlib.RIGHT + 2 - signlib.BAND_ALERT_LEFT   # width of the alert's window


def load_data(path="data.json"):
    with open(path) as f:
        return json.load(f)


# No urllib on CircuitPython, so URLs are built by hand. params is a list of (key, value).
def url(path, params):
    out = API + path.replace(" ", "%20")
    sep = "?"
    for k, v in params:
        out += sep + k.replace("[", "%5B").replace("]", "%5D") + "=" + str(v).replace(" ", "%20")
        sep = "&"
    return out


def request_headers(url, mbta_key, aio_key):
    # Each key goes only to its own service. API has no trailing slash, so the check adds one:
    # otherwise a host that merely starts with the MBTA's name would be sent the key.
    headers = {"Accept": "application/json"}
    if url.startswith(API + "/"):
        headers["Accept"] = "application/vnd.api+json"
        if mbta_key:
            headers["x-api-key"] = mbta_key
    elif url.startswith(AIO) and aio_key:
        headers["X-AIO-Key"] = aio_key
    return headers


# --- setup
# A source is something polled on a schedule. handler(st, src, data, now_ms, epoch) gets the
# parsed answer. ms/bytes/ok/errors are only for the status report; fails is failures in a row.
def add_source(st, name, seconds, source_url, handler, arg=None):
    st["sources"].append({"name": name, "every": int(seconds * 1000), "due": 0, "url": source_url,
                          "handler": handler, "arg": arg, "ms": 0, "max_ms": 0, "bytes": 0,
                          "max_bytes": 0, "ok": 0, "errors": 0, "fails": 0})


def setup(data, use_map=True):
    """All state lives in this one dict (no classes on the board). use_map=False skips vehicle
    polling - the simulator uses that for its sign-only sample board."""
    st = {}
    setup_map(st, data)
    setup_sign(st, data)
    setup_night(st, data)
    setup_sources(st, data, use_map)
    rides.setup(st, st["stations"], data.get("ride"))
    add_source(st, "ride", RIDE_SECONDS, None, got_ride)      # no url until someone starts a ride
    st["sources"][-1]["make_url"] = ride_url
    st["mail_at"] = None                # created_at of the newest ride message acted on

    # What has been fetched so far.
    st["vehicles"] = [[], None]         # [vehicles, time fetched or None]
    st["preds"] = [[[], None] for _ in st["rows"]]
    st["alerts"] = []
    st["sign_alerts"] = []              # [[alert id, text], ...] that qualify for the sign
    st["seen_alerts"] = None            # ids already shown; None until the first fetch
    st["weather"] = None
    st["weather_at"] = None
    st["games"] = {}                    # team name -> game dict (feeds.parse_game)
    st["unknown"] = {}                  # platform stop IDs missing from the parents table
    st["next_lookup"] = 0
    st["failures"] = 0                  # fetches failed in a row
    st["wled_fails"] = 0                # sends to WLED that failed in a row
    st["wled_next"] = 0                 # ms on the steady clock: no send to WLED before this
    st["last_error"] = ""

    # The map: one state per light (station n owns lights 2n and 2n + 1).
    st["states"] = [ledlib.IDLE] * (2 * len(st["stations"]))
    st["map_dirty"] = True              # new data arrived: work the states out again
    st["map_checked"] = 0

    # The ticker: the item showing, the one before it, and where in its life it is.
    st["tk"] = {"item": None, "prev": None, "phase": "hold", "start": 0, "fetched": False,
                "queue": [], "pos": 0}
    # The sign's picture is kept and reused until what it shows changes.
    st["base"] = None                   # the two route rows
    st["base_key"] = None
    st["base_at"] = -100000
    st["band_key"] = None               # the ticker row drawn over them
    st["frame"] = None

    st["ui"] = remote.new_ui()          # the phone remote's state: mode, life totals, timer...
    return st


def setup_map(st, data):
    st["settings"] = data["map"]
    st["stations"] = data["stations"]
    st["routes"] = data["routes"]
    st["colors"] = data["colors"]
    st["parents"] = data["parents"]             # platform stop ID -> station ID
    st["route_stops"] = data["route_stops"]     # route -> its stations in order
    st["index"] = ledlib.build_index(st["stations"])
    st["wiring"] = {}                   # output -> [light number, or -1 for a SKIP pixel]
    for output in data["wiring"]:       # (JSON turned the output numbers into text)
        st["wiring"][int(output)] = data["wiring"][output]
    st["outputs"] = sorted(st["wiring"])
    st["counts"] = data["output_leds"]  # LEDs per output, as set up in WLED
    st["music"] = data.get("music") or []   # [name, WLED effect number, one effect per line?] for music mode
    st["poll_ms"] = int(max(5, data["poll_seconds"]) * 1000)


def setup_sign(st, data):
    sign = data["sign"]
    st["rows"] = sign["rows"][:2]
    st["min_severity"] = sign.get("alert_min_severity", 3)
    st["sign_brightness"] = sign.get("brightness", 0.6)
    st["my_stops"] = {}
    st["sign_routes"] = {}
    for r in st["rows"]:
        st["my_stops"][r["stop_id"]] = True
        st["sign_routes"][r["route"]] = True
    st["ticker"] = data.get("ticker") or {}
    st["hold_ms"] = int(st["ticker"].get("hold_seconds", 5) * 1000)


def setup_night(st, data):
    night = data.get("night") or {}
    st["night"] = night
    st["night_on"] = night.get("enabled", True)
    st["night_start"] = minutes(night.get("start", "23:00"))
    st["night_end"] = minutes(night.get("end", "7:00"))
    st["night_hold_ms"] = int(night.get("hold_seconds", 10) * 1000)
    st["night_poll_ms"] = int(night.get("poll_seconds", 60) * 1000)
    st["force_night"] = False           # the simulator's preview switch
    st["night_colors"] = night_colors(data["colors"], night.get("map_level", 0.5))


def setup_sources(st, data, use_map):
    # Order matters: fetch_one() breaks ties by list order, so put the important ones first.
    routes = st["routes"]
    tcfg = st["ticker"]
    poll = st["poll_ms"] / 1000
    st["sources"] = []
    if st["rows"]:
        # One request covers every sign row.
        params = [("filter[stop]", ",".join(st["my_stops"])), ("filter[route]", ",".join(st["sign_routes"])),
                  ("fields[prediction]", PRED_FIELDS)]
        for r in st["rows"]:
            if r.get("branch_letter"):
                params += [("include", "trip"), ("fields[trip]", "headsign")]
                break
        add_source(st, "predictions", poll, url("/predictions", params), got_predictions)
    if use_map:
        add_source(st, "vehicles", poll, url("/vehicles", [("filter[route]", ",".join(routes)),
                                                          ("fields[vehicle]", VEHICLE_FIELDS)]), got_vehicles)
    if tcfg.get("alerts", True) and st["sign_routes"]:
        add_source(st, "alerts", ALERT_SECONDS,
                   url("/alerts", [("filter[route]", ",".join(st["sign_routes"])), ("filter[datetime]", "NOW"),
                                   ("fields[alert]", ALERT_FIELDS)]), got_alerts)
    if tcfg.get("weather", True) or tcfg.get("rain", True):
        add_source(st, "weather", WEATHER_SECONDS,
                   feeds.weather_url(tcfg.get("latitude"), tcfg.get("longitude")), got_weather)
    st["teams"] = []
    for name in ("sox", "bruins", "patriots"):
        if tcfg.get(name, True):
            st["teams"].append(name)
            # Which game (yesterday's or today's): its url changes with the date.
            add_source(st, name + "-find", FIND_SECONDS, "", got_find, name)
            st["sources"][-1]["make_url"] = find_team_url
            # That game, live; no url until the find says which game.
            add_source(st, name, SCORE_SECONDS, None, got_game, name)


def night_colors(colors, level):
    out = {}
    for line in colors:
        out[line] = ledlib.scale(colors[line], level)
    return out


def setup_mailbox(st, user, feed):
    # Ride messages from our phones (rides.py). code.py calls this when settings.toml has an Adafruit IO account.
    add_source(st, "mailbox", MAILBOX_SECONDS,
               AIO + user + "/feeds/" + feed + "/data?limit=5&include=id,value,created_at", got_mail)


def minutes(text):
    # "23:00" -> 1380
    h, m = str(text).split(":")
    return int(h) * 60 + int(m)


def is_night(st, epoch):
    if st["force_night"]:
        return True
    if not st["night_on"]:
        return False
    m = feeds.local(epoch) % 86400 // 60
    start, end = st["night_start"], st["night_end"]
    if start <= end:                    # otherwise the window wraps past midnight
        return start <= m < end
    return m >= start or m < end


# --- data handlers
# data.json maps platform IDs to stations, but the MBTA adds platforms now and then (and
# shuttles use odd ones). Unknown ones get looked up one at a time by lookup_stop().
def note_stop(st, stop):
    if stop and stop not in st["parents"] and not stop.startswith("place-"):
        st["unknown"][stop] = True


def got_vehicles(st, src, d, now_ms, epoch):
    vehicles = []
    for v in d["data"]:
        rel = v.get("relationships", {})
        stop = feeds.rel_id(rel, "stop")
        route = feeds.rel_id(rel, "route")
        a = v["attributes"]
        vehicles.append({"id": v["id"], "route": route, "stop": stop,
                         "status": a.get("current_status"), "direction_id": a.get("direction_id")})
        note_stop(st, stop)
    st["vehicles"] = [vehicles, now_ms]
    st["map_dirty"] = True


def departure(p):
    return p["departure_time"]


def got_predictions(st, src, d, now_ms, epoch):
    # one request covers both sign rows, so split the answer up by route, stop and direction
    heads = {}
    for trip in d.get("included") or []:
        heads[trip["id"]] = trip["attributes"].get("headsign")
    found = [[] for _ in st["rows"]]
    for p in d["data"]:
        a = p["attributes"]
        if not a.get("departure_time"):
            continue                    # arrival only: a trip that ends here
        rel = p.get("relationships", {})
        route = feeds.rel_id(rel, "route")
        stop = feeds.rel_id(rel, "stop")
        trip = feeds.rel_id(rel, "trip")
        if stop not in st["my_stops"]:
            note_stop(st, stop)         # a platform of one of the sign's stations
        for n in range(len(st["rows"])):
            r = st["rows"][n]
            if (route == r["route"] and a.get("direction_id") == r["direction_id"]
                    and (stop == r["stop_id"] or st["parents"].get(stop) == r["stop_id"])):
                found[n].append({"departure_time": a["departure_time"],
                                 "schedule_relationship": a.get("schedule_relationship"),
                                 "headsign": heads.get(trip)})
    for n in range(len(found)):
        found[n].sort(key=departure)    # same UTC offset throughout, so text order is time order
        st["preds"][n] = [found[n][:12], now_ms]  # enough to skip the ones too soon to catch
    st["base_at"] = -100000             # redraw the countdowns now


def got_alerts(st, src, d, now_ms, epoch):
    alerts = []
    for a in d["data"]:
        at = a["attributes"]
        entities = []
        for e in at.get("informed_entity") or []:
            entities.append({"route": e.get("route"), "stop": e.get("stop"),
                             "activities": e.get("activities") or []})
        alerts.append({"id": a["id"], "effect": at.get("effect"), "severity": at.get("severity"),
                       "header": at.get("header"), "short_header": at.get("short_header"),
                       "entities": entities})
    st["alerts"] = alerts
    shown = []
    for a in alerts:
        on_sign = False
        for e in a["entities"]:
            if e["route"] in st["sign_routes"]:
                on_sign = True
                break
        if on_sign:
            text = signlib.alert_text([a], st["my_stops"], st["parents"], st["min_severity"])
            if text:
                shown.append([a["id"], text])
    st["sign_alerts"] = shown
    if not st["ticker"].get("alerts", True):
        return
    first = st["seen_alerts"] is None
    seen = {}
    for aid, text in shown:
        seen[aid] = True
        if not first and aid not in st["seen_alerts"] and not is_night(st, epoch):
            st["tk"]["queue"].append(alert_item(aid, text))     # new: show it right away, once
    st["seen_alerts"] = seen


def got_weather(st, src, d, now_ms, epoch):
    st["weather"] = feeds.parse_weather(d)
    st["weather_at"] = now_ms


def got_mail(st, src, d, now_ms, epoch):
    # The feed's newest messages, newest first. Each is acted on once, oldest first.
    if st["mail_at"] is None:
        st["mail_at"] = epoch - MAIL_FRESH_S
    new = []
    for m in d:
        at = signlib.parse_iso(m["created_at"])
        if at > st["mail_at"]:
            new.append([at, m.get("value") or ""])
    new.sort()
    for at, text in new:
        rides.apply(st, text, at, now_ms)
        st["mail_at"] = at


def ride_url(st, src, epoch):
    src["arg"] = rides.next_ride(st)
    path, params = rides.request(st["rides"][src["arg"]])
    return url(path, params)


def got_ride(st, src, d, now_ms, epoch):
    if rides.got(st, src["arg"], d, epoch) and not is_night(st, epoch):
        for it in rides.items(st):
            if it["key"] == "ride-" + src["arg"]:
                st["tk"]["queue"].append(it)        # the train is found: show it right away


def find_team_url(st, src, epoch):       # rebuilt every time: it has today's date in it
    return feeds.find_url(feeds.TEAMS[src["arg"]], epoch)


def source(st, name):
    for s in st["sources"]:
        if s["name"] == name:
            return s
    return None


def got_find(st, src, d, now_ms, epoch):
    # Scores take two requests: this small one (~300 bytes) finds today's or last night's game,
    # then the team's own source polls just that game (~20 KB).
    name = src["arg"]
    game = source(st, name)
    event_id = feeds.parse_find(d)
    if event_id is None:
        game["url"] = None
        st["games"][name] = None
    else:
        new_url = feeds.game_url(feeds.TEAMS[name], event_id)
        if new_url != game["url"]:
            game["url"] = new_url
            game["due"] = now_ms            # fetch the game at the next hold
            st["games"][name] = None
    # Look again in 30 minutes, or just after midnight if that's sooner.
    to_midnight = (86400 - feeds.local(epoch) % 86400 + 60) * 1000
    src["due"] = now_ms + min(src["every"], to_midnight)


def got_game(st, src, d, now_ms, epoch):
    name = src["arg"]
    old = st["games"].get(name)
    g = feeds.parse_game(d, feeds.TEAMS[name])
    st["games"][name] = g
    # same game, already under way, and our score went up -> celebrate
    if g and old and old["start"] == g["start"] and old["state"] != "pre" and g["us"] > old["us"]:
        if name == "bruins" and st["ui"]["mode"] == "bruins":
            remote.goal(st, now_ms)         # GOAL! on the sign and a sweep across the map
        elif not is_night(st, epoch):
            st["tk"]["queue"].append(feeds.score_item(name))
            item = feeds.game_item(name, g, epoch)
            if item:
                st["tk"]["queue"].append(item)
    live = feeds.game_live(g, epoch)
    src["every"] = (remote.game_every(st, name, live) or (LIVE_SCORE_SECONDS if live else SCORE_SECONDS)) * 1000
    src["due"] = now_ms + src["every"]


def lookup_stop(st, fetch):
    for sid in st["unknown"]:
        break
    del st["unknown"][sid]
    d = fetch(url("/stops/" + sid, [("fields[stop]", "parent_station")]))[0]
    p = (d["data"]["relationships"].get("parent_station") or {}).get("data")
    st["parents"][sid] = p["id"] if p else sid
    st["map_dirty"] = True


def retry_delay(src):
    # Double the wait for every failure in a row so an outage isn't hammered.
    # The shift is capped so a long outage can't overflow it.
    return min(min(src["every"], RETRY_MS) << min(src["fails"] - 1, 8), BACKOFF_MAX_MS)


def fetch_one(st, now_ms, epoch, fetch):
    """Make at most one request (the most overdue source). Returns True if it tried one."""
    best = None
    for s in st["sources"]:
        if (s["due"] <= now_ms and s["url"] is not None and (best is None or s["due"] < best["due"])
                and remote.wants(st, s["name"])):
            best = s
    if best is None and not (st["unknown"] and now_ms >= st["next_lookup"]):
        return False
    try:
        if best is None:
            st["next_lookup"] = now_ms + STOP_LOOKUP_MS
            lookup_stop(st, fetch)
        else:
            every = best["every"]
            if best["name"] in ("predictions", "vehicles") and is_night(st, epoch):
                every = max(every, st["night_poll_ms"])
            best["due"] = now_ms + every
            if best.get("make_url"):
                best["url"] = best["make_url"](st, best, epoch)
            d, size, ms = fetch(best["url"])
    except Exception as e:      # the request failed: keep showing the old data and try again later
        st["failures"] += 1
        st["last_error"] = (best["name"] if best else "stop") + ": " + str(e)
        if best:
            best["errors"] += 1
            best["fails"] += 1
            best["due"] = now_ms + retry_delay(best)
        return True
    st["failures"] = 0          # the network is fine, whatever happens to the answer
    if best is not None:
        best["ms"] = ms
        best["bytes"] = size
        best["max_ms"] = max(best["max_ms"], ms)
        best["max_bytes"] = max(best["max_bytes"], size)
        try:
            best["handler"](st, best, d, now_ms, epoch)
        except Exception as e:  # a bug in reading the answer: no NO DATA banner, but back off and say what it was
            st["last_error"] = best["name"] + ": reading the answer failed, " + type(e).__name__ + " " + str(e)
            best["errors"] += 1
            best["fails"] += 1
            best["due"] = now_ms + retry_delay(best)
        else:
            best["ok"] += 1
            best["fails"] = 0
    return True


# --- ticker
def alert_item(aid, text):
    segs = [[text, signlib.ALERT]]
    return feeds.item("alert-" + aid, segs, scroll=signlib.segs_width(segs) > SCROLL_SPAN, icon=True)


PAUSE = feeds.item("pause", [])


def rotation(st, now_ms, epoch):
    # Static items and scrolling alerts alternate. Requests only happen during a static hold,
    # so two alerts back to back would starve the network - a blank PAUSE goes between them.
    if st["failures"] >= 3:
        return [feeds.item("nodata", [["NO DATA", signlib.ALERT]])]
    cfg = st["ticker"]
    night = is_night(st, epoch)
    statics = []
    if cfg.get("clock", True) or night:
        days = feeds.local(epoch) // 86400
        statics.append(feeds.item("clock", [[DAYS[(days + 4) % 7] + " " + feeds.clock_text(epoch),
                                             signlib.WHITE]]))
    if st["weather"] and now_ms - st["weather_at"] < WEATHER_STALE_MS:
        statics += feeds.weather_items(st["weather"], cfg)
    if night:
        return statics[:2] + rides.items(st)    # just the time and the weather, and anyone on their way home
    statics += rides.items(st)
    for name in st["teams"]:
        it = feeds.game_item(name, st["games"].get(name), epoch)
        if it:
            statics.append(it)
    alerts = []
    if st["ui"]["message"]:
        alerts.append(remote.message_item(st["ui"]["message"]))     # from the phone remote, every time round
    if cfg.get("alerts", True):
        for aid, text in st["sign_alerts"]:
            alerts.append(alert_item(aid, text))
    out = []
    for k in range(max(len(statics), len(alerts))):
        if k < len(statics):
            out.append(statics[k])
        elif alerts[k]["scroll"]:
            out.append(PAUSE)
        if k < len(alerts):
            out.append(alerts[k])
    if not out:
        out.append(PAUSE)
    return out


def advance(st, now_ms, epoch):
    tk = st["tk"]
    prev = tk["item"]
    if tk["queue"]:
        item = tk["queue"].pop(0)
    else:
        items = rotation(st, now_ms, epoch)
        item = items[tk["pos"] % len(items)]
        tk["pos"] = (tk["pos"] + 1) % 1000000
    tk["prev"] = prev
    tk["item"] = item
    tk["start"] = now_ms
    tk["fetched"] = False
    if item["scroll"]:
        tk["phase"] = "scroll"
    elif (prev is not None and prev["key"] == item["key"] and prev["segs"] == item["segs"]
          and not item.get("more")):
        tk["phase"] = "hold"            # the only item: just keep it up
    elif is_night(st, epoch):
        tk["phase"] = "hold"            # night: swap without sliding
    else:
        tk["phase"] = "slide"


def tick(st, now_ms, epoch, fetch):
    # Called every frame. The one request per hold happens at the start of the hold; it blocks,
    # so a slow request just makes that hold longer instead of stuttering a scroll.
    remote.update(st, now_ms, epoch)
    if st["ui"]["mode"] != "transit":
        # No ticker in the other modes: one request a second at most, never during a flash or a spin.
        ui = st["ui"]
        if now_ms - ui["fetched"] >= 1000 and not remote.busy(st, now_ms, epoch):
            ui["fetched"] = now_ms
            if fetch_one(st, now_ms, epoch, fetch):
                gc.collect()
        return
    tk = st["tk"]
    item = tk["item"]
    elapsed = now_ms - tk["start"]
    if tk["phase"] == "slide":
        if elapsed >= SLIDE_MS:
            tk["phase"] = "hold"
            tk["start"] = now_ms
            tk["fetched"] = False
        return
    if tk["phase"] == "scroll":
        if elapsed * SCROLL_SPEED // 1000 < item["w"] + SCROLL_SPAN:
            return
    else:
        flash = item is not None and item["flash"]
        if not tk["fetched"]:
            tk["fetched"] = True
            if not flash:
                fetch_one(st, now_ms, epoch, fetch)
                gc.collect()
                return                  # the clock has moved; look again next frame
        if flash:
            hold = FLASH_MS
        elif item is None or item["key"] == "pause":
            hold = PAUSE_MS
        else:
            hold = st["night_hold_ms"] if is_night(st, epoch) else st["hold_ms"]
            if item.get("more"):
                hold += PAGE_EXTRA_MS   # two texts share the hold
        if elapsed < hold and not (tk["queue"] and not flash):
            return
    advance(st, now_ms, epoch)


# --- sign
def clock_and_date(epoch):
    days = feeds.local(epoch) // 86400
    y, m, d = feeds.civil_from_days(days)
    return feeds.clock_text(epoch), DAYS[(days + 4) % 7] + " " + str(m) + "/" + str(d)


def sign_rows(st, now_ms, epoch):
    rows = []
    for n in range(len(st["rows"])):
        r = st["rows"][n]
        preds, when = st["preds"][n]
        if when is None or now_ms - when > PRED_STALE_MS:
            preds = []
        if st["ui"]["costume"]:
            times = remote.costume_times(n, epoch)
        else:
            times = signlib.row_times(preds, epoch, bool(r.get("branch_letter")), 2, r.get("walk_minutes", 0))
        rows.append({"badge": r["badge"], "note": r["note"], "times": times})
    return rows


def sign_frame(st, now_ms, epoch):
    # Returns the same bitmap object when nothing changed, so code.py can skip the copy.
    if st["ui"]["align"]:
        return remote.align_frame(st)
    if st["ui"]["korok"] is not None:
        return remote.korok_frame(st, now_ms)
    over = remote.band(st, now_ms, epoch)       # the timer, turn picker or goal flash, over the ticker
    if st["ui"]["mode"] != "transit":
        return remote.sign_frame(st, now_ms, epoch, over)
    if st["ui"]["costume"] and over is None:
        frame = remote.costume_frame(st, now_ms)
        if frame is not None:
            return frame
    if st["base"] is None or now_ms - st["base_at"] >= ROWS_REDRAW_MS:
        st["base_at"] = now_ms
        rows = sign_rows(st, now_ms, epoch)
        key = str(rows)
        if key != st["base_key"]:
            st["base_key"] = key
            st["base"] = signlib.render_ticker_base(rows)
            st["band_key"] = None
    if over is not None:
        key = ("over", str(over))
        if key != st["band_key"] or st["frame"] is None:
            st["band_key"] = key
            st["frame"] = signlib.ticker_band(st["base"], [[over, signlib.LEFT, 0, 0]], False)
        return st["frame"]
    tk = st["tk"]
    item = tk["item"]
    elapsed = now_ms - tk["start"]
    layers = []
    icon = False
    if item is None:
        key = "empty"
    else:
        icon = item["icon"]
        left = signlib.BAND_ALERT_LEFT if icon else 0
        x = left if icon else signlib.LEFT
        if tk["phase"] == "scroll":
            offset = elapsed * SCROLL_SPEED // 1000
            key = (item["key"], offset)
            layers.append([item["segs"], signlib.RIGHT + 2 - offset, 0, left])
        elif tk["phase"] == "slide":
            step = min(signlib.BAND_H + 1, elapsed * (signlib.BAND_H + 1) // SLIDE_MS)
            key = (item["key"], "slide", step)
            prev = tk["prev"]
            if prev is not None and not prev["scroll"]:
                layers.append([prev.get("more") or prev["segs"],
                               signlib.BAND_ALERT_LEFT if prev["icon"] else signlib.LEFT, -step, left])
            layers.append([item["segs"], x, signlib.BAND_H + 1 - step, left])
        elif item.get("more"):
            # Turn over to the second text halfway through, sliding up like a new item.
            half = (st["hold_ms"] + PAGE_EXTRA_MS) // 2
            step = 0 if elapsed < half else min(signlib.BAND_H + 1, (elapsed - half) * (signlib.BAND_H + 1) // SLIDE_MS)
            key = (item["key"], "page", step)
            layers.append([item["segs"], x, -step, left])
            if step:
                layers.append([item["more"], x, signlib.BAND_H + 1 - step, left])
        else:
            on = not item["flash"] or elapsed // BLINK_MS % 2 == 0
            key = (item["key"], "hold", on)
            if on:
                layers.append([item["segs"], x, 0, left])
    if key != st["band_key"] or st["frame"] is None:
        st["band_key"] = key
        st["frame"] = signlib.ticker_band(st["base"], layers, icon)
    return st["frame"]


def sign_palette(st, data, night=False, brightness=None):
    # The panel has no brightness control, so dimming = darkening the palette.
    sign = data["sign"]
    colors = [r["rgb"] for r in st["rows"]]
    if brightness is None:
        brightness = sign.get("brightness", 0.6)
    if night:
        brightness = st["night"].get("sign_brightness", 0.03)
    if st["ui"]["sign_bri"] is not None:
        brightness = st["ui"]["sign_bri"]       # the remote's slider wins, day or night, until set back to auto
    depth = sign.get("bit_depth", 5)
    return remote.palette(st, signlib.palette(colors, brightness, depth), brightness, depth)


# --- map
def map_vehicles(st, now_ms):
    # The trains the map shows: the sample ones in costume mode, otherwise the MBTA's while they're fresh.
    if st["ui"]["costume"]:
        return remote.costume_trains(st["route_stops"], now_ms)
    if st["vehicles"][1] is not None and now_ms - st["vehicles"][1] < 3 * st["poll_ms"]:
        return st["vehicles"][0]
    return []


def update_map(st, now_ms):
    # Also runs once a second with no new data, so vehicles go dark when they get stale.
    if not st["map_dirty"] and now_ms - st["map_checked"] < 1000:
        return
    st["map_dirty"] = False
    st["map_checked"] = now_ms
    vehicles = map_vehicles(st, now_ms)
    st["states"] = ledlib.light_states(vehicles, st["stations"], st["index"], st["parents"], st["riding"])


def map_live(st):
    # In music mode the board stops sending, and WLED runs its own effects once its realtime timeout passes.
    return st["ui"]["mode"] != "music"


def is_animated(st, now_ms):
    return remote.animating(st, now_ms)


def ddp_buffer(st):
    # One DDP packet for all outputs (max 480 LEDs; build_firmware checks). Allocated once.
    n = 0
    for count in st["counts"]:
        n += count * 3
    buf = bytearray(DDP_HEADER + n)
    buf[0] = 0x41           # DDP version 1, push
    buf[2] = 0x01           # RGB, 8 bits per channel
    buf[3] = 0x01           # default output device
    buf[8] = n >> 8         # data length (the offset in bytes 4-7 stays 0)
    buf[9] = n & 255
    return buf


def map_chains(st, night=False):
    return ledlib.render(st["states"], st["stations"], st["wiring"], st["settings"],
                         st["night_colors"] if night else st["colors"])


def ddp_packet(st, t, buf, night=False, now_ms=0):
    # Each output is padded with black up to its LED count in WLED, so output 2 starts where
    # WLED expects it even if output 1 has spare pixels at the end.
    chains = remote.map_overlay(st, map_chains(st, night), now_ms, t)
    n = DDP_HEADER
    k = 0
    for output in st["outputs"]:
        end = n + st["counts"][k] * 3
        k += 1
        for c in chains[output]:
            buf[n] = c[0]
            buf[n + 1] = c[1]
            buf[n + 2] = c[2]
            n += 3
        while n < end:
            buf[n] = 0
            n += 1
    return buf


def wled_due(st, now_ms):
    if st["ui"]["posts"] and now_ms >= st["wled_next"]:
        return st["ui"]["posts"][0]
    return None


def wled_result(st, now_ms, ok):
    # Posting to WLED blocks the board for up to WLED_TIMEOUT. If WLED is off, back off so the
    # display only stutters now and then instead of every loop.
    if ok:
        st["ui"]["posts"].pop(0)
        st["wled_fails"] = 0
        st["wled_next"] = 0
    else:
        st["wled_fails"] += 1
        st["wled_next"] = now_ms + min(WLED_RETRY_MS << min(st["wled_fails"] - 1, 8), WLED_RETRY_MAX_MS)


def report(st):
    out = []
    for s in st["sources"]:
        out.append("%s %d ms (max %d) %d B (max %d) ok %d err %d" % (
            s["name"], s["ms"], s["max_ms"], s["bytes"], s["max_bytes"], s["ok"], s["errors"]))
    if st["wled_fails"]:
        out.append("wled not answering: %d failures in a row" % st["wled_fails"])
    return out
