"""Rides: one of us tells the board which train or bus we're on, and the map and the sign follow it.

A message comes from a phone (an iPhone Shortcut posting to an Adafruit IO feed, or the phone
remote's "ride" command) as
  NAME;ROUTE;FROM;TO    e.g. ALEX;Orange;Ruggles;Downtown Crossing (send it on getting on)
  NAME;DONE             that person's ride is over
ROUTE is Red, Orange, Blue, Green or Mattapan, or a bus route listed under ride.buses in the config.
FROM and TO are station names as the map prints them, or the bus stop names in the config.

The train is found from the MBTA's predictions at FROM and TO: a trip that stops at both, FROM
first. After that only that trip is followed, so its arrival time at TO goes on the sign and its
vehicle lights purple on the map. Portable like leds.py (plain dicts and lists).
"""
import feeds
import sign as signlib

FIELDS = "arrival_time,departure_time,stop_sequence,direction_id,schedule_relationship"
RAIL = {"RED": ["Red"], "MATTAPAN": ["Mattapan"], "ORANGE": ["Orange"], "BLUE": ["Blue"],
        "GREEN": ["Green-B", "Green-C", "Green-D", "Green-E"]}
LINE = {"RED": "RL", "MATTAPAN": "M", "ORANGE": "OL", "BLUE": "BL", "GREEN": "GL"}
# On the sign, longest first: the first that fits goes beside the arrival time.
LABEL = {"RED": ("RED", "RL"), "MATTAPAN": ("MATT", "M"), "ORANGE": ("ORANGE", "OL"),
         "BLUE": ("BLUE", "BL"), "GREEN": ("GREEN", "GL")}
NAME_MAX = 8
BOARDING_S = 120        # a train leaving FROM up to this long after the message is the one being boarded
FIND_TRIES = 9          # about three minutes of looking for the train before giving up
MISSES = 2              # its arrival at TO gone from the predictions this many times in a row: it has arrived
RIDE_MAX_S = 3 * 3600


def key(text):
    # "Gov't Center" and "GOVT CENTER" are the same station
    out = ""
    for ch in str(text).upper():
        if "A" <= ch <= "Z" or "0" <= ch <= "9":
            out += ch
    return out


def setup(st, stations, cfg):
    """cfg: data["ride"] from the config ({"buses": {route: {stop name: [stop ids]}}})."""
    st["rides"] = {}                    # name -> ride
    st["riding"] = {}                   # vehicle id -> True, for the map
    st["ride_turn"] = 0
    names = {}
    for s in stations:
        names[s["line"] + "|" + key(s.get("name") or s["stop_id"])] = s["stop_id"]
    st["ride_names"] = names
    st["ride_buses"] = {}
    st["ride_bus_stops"] = {}           # route -> its stop names as the config spells them, for a picker
    for route in (cfg or {}).get("buses") or {}:
        stops = {}
        table = cfg["buses"][route]
        st["ride_bus_stops"][str(route)] = [str(name) for name in table]
        for name in table:
            ids = table[name]
            stops[key(name)] = [str(i) for i in ids] if isinstance(ids, list) else [str(ids)]
        st["ride_buses"][key(route)] = [str(route), stops]


def choices(st):
    """What a picker can offer: {"lines": [...], "stops": {line: [stop names]}}. The five rail lines come first,
    then the bus routes in the config; the names are spelled the way a message spells them."""
    lines = ["Red", "Orange", "Blue", "Green", "Mattapan"]
    stops = {}
    for name in lines:
        stops[name] = [s.get("name") or s["stop_id"] for s in st["stations"] if s["line"] == LINE[name.upper()]]
    for route in st["ride_bus_stops"]:
        lines.append(route)
        stops[route] = st["ride_bus_stops"][route]
    return {"lines": lines, "stops": stops}


def parse(st, text, at):
    """A message -> ["done", name], ["ride", ride], or None if it makes no sense."""
    parts = [p.strip() for p in str(text).split(";")]
    name = key(parts[0])[:NAME_MAX]
    if not name or len(parts) < 2:
        return None
    route = key(parts[1])
    if route in ("DONE", "HOME", "STOP", "OFF"):
        return ["done", name]
    if len(parts) < 4:
        return None
    if route in RAIL:
        line = LINE[route]
        a = st["ride_names"].get(line + "|" + key(parts[2]))
        b = st["ride_names"].get(line + "|" + key(parts[3]))
        if a is None or b is None or a == b:
            return None
        routes, start, end, label = RAIL[route], [a], [b], LABEL[route]
    elif route in st["ride_buses"]:
        number, stops = st["ride_buses"][route]
        start, end = stops.get(key(parts[2])), stops.get(key(parts[3]))
        if start is None or end is None or start == end:
            return None
        routes, label = [number], (number,)
    else:
        return None
    return ["ride", {"name": name, "routes": routes, "from": start, "to": end, "label": label, "at": at,
                     "trip": None, "vehicle": None, "eta": None, "tries": 0, "misses": 0}]


def apply(st, text, at, now_ms):
    """Start or end a ride from a message. Returns True if it did anything."""
    m = parse(st, text, at)
    if m is None:
        return False
    if m[0] == "done":
        if m[1] in st["rides"]:
            end(st, m[1])
        return True
    st["rides"][m[1]["name"]] = m[1]
    for s in st["sources"]:             # look for the train at the next hold
        if s["name"] == "ride":
            s["url"] = ""
            s["due"] = now_ms
    return True


def end(st, name):
    del st["rides"][name]
    riding(st)
    if not st["rides"]:
        for s in st["sources"]:
            if s["name"] == "ride":
                s["url"] = None


def riding(st):
    out = {}
    for name in st["rides"]:
        v = st["rides"][name]["vehicle"]
        if v:
            out[v] = True
    if out != st["riding"]:
        st["riding"] = out
        st["map_dirty"] = True


def next_ride(st):
    """Whose turn it is for the one ride request: the rides take turns."""
    names = sorted(st["rides"])
    if not names:
        return None
    st["ride_turn"] = (st["ride_turn"] + 1) % len(names)
    return names[st["ride_turn"]]


def request(ride):
    """(path, params) for the ride's next request: find the train, or follow it."""
    params = [("filter[route]", ",".join(ride["routes"])), ("fields[prediction]", FIELDS)]
    if ride["trip"] is None:
        return "/predictions", [("filter[stop]", ",".join(ride["from"] + ride["to"]))] + params
    return "/predictions", [("filter[trip]", ride["trip"]), ("filter[stop]", ",".join(ride["to"]))] + params


def trips(d, ride, st):
    """Trip id -> {"dep", "fseq"} at FROM and {"arr", "tseq"} at TO (epochs, stop sequences), "vehicle", "dir".

    None if the answer has a stop the board can't place yet (a bus berth at Harvard is its own stop ID):
    it is noted for app.lookup_stop(), and choosing waits for the next answer rather than mistake a
    train still to leave FROM for one that has gone."""
    parents = st["parents"]
    out = {}
    unknown = False
    for p in d["data"]:
        a = p["attributes"]
        if a.get("schedule_relationship") in ("SKIPPED", "CANCELLED"):
            continue
        rel = p.get("relationships") or {}
        trip = feeds.rel_id(rel, "trip")
        if trip is None:
            continue
        stop = feeds.rel_id(rel, "stop")
        if stop and stop not in parents and not stop.startswith("place-") and stop not in ride["from"] + ride["to"]:
            st["unknown"][stop] = True
            unknown = True
            continue
        place = parents.get(stop, stop)
        if trip not in out:
            out[trip] = {"dep": None, "fseq": None, "arr": None, "tseq": None, "vehicle": None, "dir": None}
        t = out[trip]
        if place in ride["from"] and a.get("departure_time"):
            t["dep"] = signlib.parse_iso(a["departure_time"])
            t["fseq"] = a.get("stop_sequence")
        if place in ride["to"] and (a.get("arrival_time") or a.get("departure_time")):
            t["arr"] = signlib.parse_iso(a.get("arrival_time") or a["departure_time"])
            t["tseq"] = a.get("stop_sequence")
        t["vehicle"] = feeds.rel_id(rel, "vehicle") or t["vehicle"]
        t["dir"] = a.get("direction_id")
    return None if unknown else out


def by_dep(t):
    return t[1]["dep"]


def by_arr(t):
    return t[1]["arr"]


def choose(found, at):
    """The trip being ridden, as (trip id, trip), or None.

    Ahead: trips still to leave FROM, then reach TO. Passed: trips with only a TO prediction,
    which have already left FROM. A train leaving FROM within BOARDING_S of the message is the
    one at the platform; otherwise the message came after the train left, so it's the passed
    train that left FROM last (the last to reach TO before the next one from FROM)."""
    ahead = []
    passed = []
    for tid in found:
        t = found[tid]
        if t["arr"] is None:
            continue
        if t["dep"] is None:
            passed.append((tid, t))
        elif t["fseq"] is not None and t["tseq"] is not None and t["fseq"] < t["tseq"]:
            ahead.append((tid, t))
    dirs = {}
    for tid, t in ahead:
        dirs[t["dir"]] = True
    if dirs:                            # the same way as the trains from FROM to TO
        passed = [p for p in passed if p[1]["dir"] in dirs]
    ahead.sort(key=by_dep)
    if ahead and ahead[0][1]["dep"] <= at + BOARDING_S:
        return ahead[0]
    if ahead:
        passed = [p for p in passed if p[1]["arr"] < ahead[0][1]["arr"]]
    if passed:
        passed.sort(key=by_arr)
        return passed[-1]
    return ahead[0] if ahead else None


def got(st, name, d, epoch):
    """The answer to request(); keeps the ride up to date or ends it. Returns True when the train was just found."""
    ride = st["rides"].get(name)
    if ride is None:
        return False
    found = trips(d, ride, st)
    if found is None:
        return False                    # asked again in RIDE_SECONDS, by when the stop is known
    new = False
    if ride["trip"] is None:
        pick = choose(found, ride["at"])
        if pick is None:
            ride["tries"] += 1
            if ride["tries"] >= FIND_TRIES:
                end(st, name)
            return False
        ride["trip"] = pick[0]
        new = True
    t = found.get(ride["trip"])
    if t is None or t["arr"] is None:
        ride["misses"] += 1
        if ride["misses"] >= MISSES or (ride["eta"] is not None and epoch >= ride["eta"] - 60):
            end(st, name)
            return False
    else:
        ride["misses"] = 0
        ride["eta"] = t["arr"]
        ride["vehicle"] = t["vehicle"] or ride["vehicle"]
    if epoch - ride["at"] > RIDE_MAX_S:
        end(st, name)
        return False
    riding(st)
    return new


def items(st):
    """A ticker item for each ride whose train has been found: the name, turning over to the line and the
    arrival time at TO (ALEX, then RED 9:42). Both together don't fit the sign's width."""
    out = []
    for name in sorted(st["rides"]):
        ride = st["rides"][name]
        if ride["eta"] is None:
            continue
        when = feeds.clock_text(ride["eta"])
        texts = [label + " " + when for label in ride["label"]] + [when]
        out.append(feeds.item("ride-" + name, [[name, signlib.RIDER]], more=[[feeds.fit(texts), signlib.WHITE]]))
    return out
