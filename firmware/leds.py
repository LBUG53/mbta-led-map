"""Vehicles in, a color for every pixel out. Runs on the board and in the simulator.

Each station has two lights: light number = station index * 2 (A), + 1 (B).

The data it works with:
  stations     [{"line", "stop_id", "a_dir"}]; a_dir = {route: direction_id that lights A},
               worked out from the API's stop order by sim/directions.py
  wiring       {output: [light number, or -1 for a SKIP pixel]} in wiring order
  vehicles     [{"id", "route", "stop", "status", "direction_id"}] from /vehicles; stop is a
               platform ID or a place- ID; status STOPPED_AT / INCOMING_AT / IN_TRANSIT_TO
  parents      platform stop ID -> place- ID
  riding       {vehicle id: True} for the trains someone at home is on (rides.py)

A frame:
  states = light_states(vehicles, stations, index, parents, riding)
  chains = render(states, stations, wiring, settings, colors)
"""

ROUTE_LINE = {
    "Red": "RL", "Mattapan": "M", "Orange": "OL", "Blue": "BL",
    "Green-B": "GL", "Green-C": "GL", "Green-D": "GL", "Green-E": "GL",
}

# Default LED colors per line (the print's ink colors). Override with
# map.colors in config.yaml once you've seen the real pixels.
LINE_COLORS = {
    "RL": (218, 41, 28),
    "M": (218, 41, 28),
    "OL": (237, 139, 0),
    "BL": (0, 61, 165),
    "GL": (0, 132, 61),
}
# A train one of us is on: purple, which no line uses (leans magenta so it can't be
# mistaken for a dim Blue Line). Override with map.colors.RIDER.
RIDER_COLOR = (190, 0, 255)

# LED states, in priority order.
IDLE = 0
STOPPED = 1
RIDING = 2


# --- lookups
def build_index(stations):
    """Map "LINE|place-id" -> station position."""
    index = {}
    for i in range(len(stations)):
        index[stations[i]["line"] + "|" + stations[i]["stop_id"]] = i
    return index


# --- vehicles
def lights_for_vehicle(v, stations, index, parents):
    """Return the light numbers a vehicle lights: the light for its direction at
    the station it reports (both lights if it gives no direction), or [].

    STOPPED_AT reports the stop it's at; INCOMING_AT and IN_TRANSIT_TO report
    the stop they're heading to. Only a ridden train lights that one (light_states).
    """
    line = ROUTE_LINE.get(v["route"])
    stop = v.get("stop")
    if line is None or stop is None:
        return []
    i = index.get(line + "|" + parents.get(stop, stop), -1)
    if i < 0:
        return []
    a_dir = stations[i]["a_dir"]
    a = a_dir.get(v["route"])
    if a is None:                   # a train off its usual route: the line's other routes agree
        for route in a_dir:
            a = a_dir[route]
            break
    d = v.get("direction_id")
    if d is None or a is None:
        return [2 * i, 2 * i + 1]
    return [2 * i if d == a else 2 * i + 1]


def light_states(vehicles, stations, index, parents, riding=None):
    """IDLE, STOPPED or RIDING for each light (two per station). A train between
    stations lights nothing, unless someone is riding it: that one is followed all the way."""
    states = [IDLE] * (2 * len(stations))
    for v in vehicles:
        if riding and v.get("id") in riding:
            level = RIDING
        elif v["status"] == "STOPPED_AT":
            level = STOPPED
        else:
            continue
        for n in lights_for_vehicle(v, stations, index, parents):
            if level > states[n]:
                states[n] = level
    return states


# --- colors
def scale(color, level):
    return (int(color[0] * level + 0.5), int(color[1] * level + 0.5), int(color[2] * level + 0.5))


def render(states, stations, wiring, settings, colors=None):
    """Return {output: [(r, g, b), ...]} in wiring order. Lights with no train
    are off, and so are SKIP pixels."""
    if colors is None:
        colors = LINE_COLORS
    rider = tuple(colors.get("RIDER") or RIDER_COLOR)
    off = (0, 0, 0)
    chains = {}
    for output in wiring:
        out = []
        for n in wiring[output]:
            s = states[n] if n >= 0 else IDLE
            if s == STOPPED:
                out.append(tuple(colors[stations[n // 2]["line"]]))
            elif s == RIDING:
                out.append(rider)
            else:
                out.append(off)
        chains[output] = out
    return chains


def combined(chains, counts):
    """The single array WLED gets: each output in order, padded with black to
    the LED count WLED has for it. counts: [LEDs per output], lowest output first."""
    out = []
    k = 0
    for output in sorted(chains):
        row = chains[output]
        out.extend(row)
        for _ in range(counts[k] - len(row)):
            out.append((0, 0, 0))
        k += 1
    return out
