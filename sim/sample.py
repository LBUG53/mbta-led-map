"""Hand-made vehicle lists for the simulated map, without live data.
(The sign's sample data is in sample_feeds.py.)"""
import remote      # firmware/remote.py (see sim/__init__.py)

from . import sample_feeds

# A plausible moment, chosen to light both lights of a station (Harvard, JFK),
# the transfer pairs and both Ashmonts.
TYPICAL = [
    # route, stop, status, direction_id
    ("Red", "place-alfcl", "STOPPED_AT", 0),
    ("Red", "place-harsq", "INCOMING_AT", 1),
    ("Red", "place-harsq", "STOPPED_AT", 0),
    ("Red", "place-pktrm", "STOPPED_AT", 1),
    ("Red", "place-dwnxg", "STOPPED_AT", 0),
    ("Red", "place-jfk", "IN_TRANSIT_TO", 0),
    ("Red", "place-jfk", "INCOMING_AT", 1),
    ("Red", "place-asmnl", "STOPPED_AT", 1),
    ("Red", "place-brntn", "STOPPED_AT", 1),
    ("Red", "place-qnctr", "INCOMING_AT", 0),
    ("Red", "place-portr", "IN_TRANSIT_TO", 1),
    ("Mattapan", "place-asmnl", "STOPPED_AT", 0),
    ("Mattapan", "place-matt", "INCOMING_AT", 0),
    ("Mattapan", "place-miltt", "STOPPED_AT", 1),
    ("Orange", "place-dwnxg", "STOPPED_AT", 1),
    ("Orange", "place-state", "INCOMING_AT", 0),
    ("Orange", "place-forhl", "STOPPED_AT", 1),
    ("Orange", "place-welln", "IN_TRANSIT_TO", 0),
    ("Orange", "place-rugg", "STOPPED_AT", 0),
    ("Blue", "place-state", "STOPPED_AT", 1),
    ("Blue", "place-wondl", "STOPPED_AT", 1),
    ("Blue", "place-aport", "INCOMING_AT", 0),
    ("Green-B", "place-pktrm", "STOPPED_AT", 0),
    ("Green-B", "place-brico", "STOPPED_AT", 1),
    ("Green-C", "place-kencl", "STOPPED_AT", 0),
    ("Green-D", "place-river", "INCOMING_AT", 0),
    ("Green-D", "place-unsqu", "STOPPED_AT", 1),
    ("Green-E", "place-mdftf", "STOPPED_AT", 1),
    ("Green-E", "place-coecl", "IN_TRANSIT_TO", 0),
    ("Green-E", "place-nuniv", "STOPPED_AT", 0),
    ("Green-E", "place-gover", "INCOMING_AT", 1),
]

def moving(route_stops, t):
    """Simulated trains stepping along each line, three per direction: the board's costume mode."""
    return remote.costume_trains(route_stops, int(t * 1000))


def ride_vehicles(rides, route_stops, now):
    """The made-up trains that sample rides follow (sample_feeds.ride_answer), on the map: each runs along its line
    from FROM to TO, one station at a time, so that it reaches TO when the ride's arrival time says. A bus ride
    has no train on the map."""
    out = []
    for name in sorted(rides):
        ride = rides[name]
        vehicle = ride["vehicle"]
        if not vehicle or not vehicle.startswith("sample-ride-") or ride["eta"] is None:
            continue
        for route, stops in remote.line_paths(route_stops):
            a = [i for i, s in enumerate(stops) if s in ride["from"]]
            b = [i for i, s in enumerate(stops) if s in ride["to"]]
            if route in ride["routes"] and a and b:
                break
        else:
            continue
        i, j = a[0], b[0]
        way = 1 if j > i else -1
        done = max(0.0, min(1.0, 1.0 - (ride["eta"] - now) / sample_feeds.RIDE_LENGTH)) * abs(j - i)
        passed = int(done)
        if passed >= abs(j - i):
            stop, status = stops[j], "STOPPED_AT"
        elif done - passed < 0.35:          # a third of each hop is spent standing in the station
            stop, status = stops[i + way * passed], "STOPPED_AT"
        else:
            stop, status = stops[i + way * (passed + 1)], "IN_TRANSIT_TO"
        out.append({"id": vehicle, "route": route, "stop": stop, "status": status,
                    "direction_id": 0 if way > 0 else 1})
    return out


def vehicles(scene, stations, route_stops=None, t=0.0):
    if scene == "moving":
        return moving(route_stops or {}, t)
    if scene == "all_stopped":
        status = "STOPPED_AT"
    elif scene == "idle":
        return []
    else:
        return [{"id": f"sample-{n}", "route": r, "stop": s, "status": st, "direction_id": d}
                for n, (r, s, st, d) in enumerate(TYPICAL)]
    out = []
    for n, s in enumerate(stations):        # one train each way at every station: all 264 lights
        route = sorted(s["a_dir"])[0]
        for d in (0, 1):
            out.append({"id": f"all-{n}-{d}", "route": route, "stop": s["stop_id"], "status": status,
                        "direction_id": d})
    return out
