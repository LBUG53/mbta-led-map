"""Which MBTA direction_id lights light A at each station.

Light A is on the right-hand side of a train moving in the direction the
line is drawn (data/stations.csv, column light_A_lights_for_trains_heading_toward).
Nothing here hardcodes a direction_id: for each route, the API's stop list
for direction 0 says which way direction 0 runs, and that is compared with
the drawing order of each branch.
"""
import math

ROUTES = {"RL": ["Red"], "M": ["Mattapan"], "OL": ["Orange"], "BL": ["Blue"],
          "GL": ["Green-B", "Green-C", "Green-D", "Green-E"]}


def drawing_direction(s):
    """The unit vector a station's branch is drawn along (light A is on its right)."""
    rx, ry = s["A"][0] - s["x"], s["A"][1] - s["y"]
    n = math.hypot(rx, ry)
    return (ry / n, -rx / n)


def light_a_directions(stations, route_stops):
    """Sets s["a_dir"] = {route: direction_id that lights light A} on every station.

    stations     in drawing order, each with line, branch, stop_id, x, y, A
    route_stops  {route: [place-ids in the order direction 0 runs]} from the API
    Returns a list of problems (empty when every station got its routes).
    """
    problems = []
    by_branch = {}
    for s in stations:
        s["a_dir"] = {}
        by_branch.setdefault(s["branch"], []).append(s)
    place = {}
    for s in stations:
        place[(s["line"], s["stop_id"])] = s
    for branch, group in by_branch.items():
        for route in ROUTES[group[0]["line"]]:
            order = route_stops.get(route) or []
            on = [s for s in group if s["stop_id"] in order]
            if not on:
                continue
            if len(on) >= 2:
                # Drawn first-to-last; direction 0 runs the same way if it reaches them in that order.
                same = order.index(on[0]["stop_id"]) < order.index(on[-1]["stop_id"])
            else:
                # One station on this route in the branch (Union Sq): compare the way
                # the branch is drawn with where direction 0 goes next from it.
                s = on[0]
                i = order.index(s["stop_id"])
                j = i + 1 if i + 1 < len(order) else i - 1
                other = place.get((s["line"], order[j]))
                if other is None:
                    problems.append("%s: no neighbor on %s to tell the direction from" % (s["station"], route))
                    continue
                dx, dy = drawing_direction(s)
                ahead = (other["x"] - s["x"]) * dx + (other["y"] - s["y"]) * dy > 0
                same = ahead if j > i else not ahead
            for s in on:
                s["a_dir"][route] = 0 if same else 1
    for s in stations:
        if not s["a_dir"]:
            problems.append("%s %s is on no route the API lists" % (s["line"], s["station"]))
    return problems
