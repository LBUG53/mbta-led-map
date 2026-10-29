"""Made-up answers for every feed the firmware reads, so the simulator's
sample mode (and the tests) can show each kind of ticker item without waiting
for a game day or a rainy one."""
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

EASTERN = timezone(timedelta(hours=-4))


def iso(epoch):
    """An epoch as the MBTA writes times: ISO 8601 with Boston's offset."""
    return datetime.fromtimestamp(epoch, EASTERN).isoformat(timespec="seconds")


def espn(abbr, opp, start, state, us, them, home=False):
    """One game as ESPN's single-game scoreboard returns it."""
    def side(a, score, where):
        return {"team": {"abbreviation": a}, "homeAway": where, "score": str(score)}
    stamp = datetime.fromtimestamp(start, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    return {"date": stamp, "competitions": [{"status": {"type": {"state": state}},
            "competitors": [side(opp, them, "away" if home else "home"),
                            side(abbr, us, "home" if home else "away")]}]}


# The made-up timetable for rides on the sample scenes: a train leaves the first stop RIDE_LEAVES seconds into every
# RIDE_CYCLE and reaches the last RIDE_LENGTH seconds later. Trains overlap, so someone who starts a ride always
# finds one with at least RIDE_LENGTH - RIDE_CYCLE seconds left, or one about to leave.
RIDE_CYCLE, RIDE_LEAVES, RIDE_LENGTH = 300, 60, 420


def ride_answer(url, now):
    """The predictions a ride asks for (rides.request): its trains between FROM and TO on the made-up timetable.
    rides.request lists FROM's stops and then TO's, so the first stop in the request is FROM and the last is TO.
    A trip still to leave FROM has a prediction there; the ones under way only have the arrival at TO."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    stops = q["filter[stop]"][0].split(",")
    route = q["filter[route]"][0].split(",")[0]
    only = q["filter[trip]"][0] if "filter[trip]" in q else None
    out = []
    for k in (int(now // RIDE_CYCLE) + d for d in (-2, -1, 0, 1)):
        trip = "sample-ride-%s-%d" % (route, k)
        leave = k * RIDE_CYCLE + RIDE_LEAVES
        arrive = leave + RIDE_LENGTH
        if arrive <= now or (only and trip != only):
            continue

        def pred(stop, arr, dep, seq):
            return {"attributes": {"arrival_time": arr and iso(arr), "departure_time": dep and iso(dep),
                                   "stop_sequence": seq, "direction_id": 0, "schedule_relationship": None},
                    "relationships": {"route": {"data": {"id": route}}, "stop": {"data": {"id": stop}},
                                      "trip": {"data": {"id": trip}},
                                      "vehicle": {"data": {"id": "sample-ride-vehicle-%s-%d" % (route, k)}}}}
        if leave > now and not only:
            out.append(pred(stops[0], None, leave, 5))
        out.append(pred(stops[-1], arrive, None, 15))
    return {"data": out}


def answer(url, now, elapsed=0):
    """The JSON a feed would return. `elapsed` (seconds since the sample began)
    drives the things that change: the Sox score, and a second alert."""
    if "/vehicles" in url:
        return {"data": [{"id": "R-1", "attributes": {"current_status": "STOPPED_AT", "direction_id": 0},
                          "relationships": {"stop": {"data": {"id": "place-asmnl"}},
                                            "route": {"data": {"id": "Red"}}}}]}
    if "/predictions" in url and "stop_sequence" in url:        # a ride's request, not the sign's
        return ride_answer(url, now)
    if "/predictions" in url:
        def pred(route, stop, direction, seconds):
            return {"attributes": {"departure_time": iso(now + seconds) if seconds else None,
                                   "schedule_relationship": None, "direction_id": direction},
                    "relationships": {"route": {"data": {"id": route}}, "stop": {"data": {"id": stop}},
                                      "trip": {"data": {"id": "t"}}}}
        return {"data": [pred("Red", "70061", 1, 0), pred("Red", "70061", 0, 390), pred("77", "23151", 0, 690),
                         pred("77", "23151", 0, 270), pred("Red", "Alewife-01", 0, 40),
                         pred("Red", "70061", 0, 960), pred("Red", "70061", 0, 1320)]}
    if "/alerts" in url:
        def alert(aid, route, text):
            return {"id": aid, "attributes": {"effect": "SHUTTLE", "severity": 7, "header": text,
                                              "short_header": text,
                                              "informed_entity": [{"route": route, "stop": None, "activities": []}]}}
        data = [alert("sample-1", "Red", "Red Line: shuttle buses replace service between JFK/UMass and Ashmont")]
        if elapsed >= 150:
            data.append(alert("sample-2", "77", "Route 77: detour at Porter Square"))
        return {"data": data}
    if "/stops/" in url:
        return {"data": {"relationships": {"parent_station": {"data": None}}}}
    if "open-meteo" in url:
        hour = datetime.fromtimestamp(now, EASTERN).hour
        rain = [10] * 24
        for h in range(min(23, hour + 2), 24):
            rain[h] = 60
        return {"current": {"time": iso(now)[:16], "temperature_2m": 57.6, "weather_code": 2, "is_day": 1},
                "daily": {"temperature_2m_max": [64.2], "temperature_2m_min": [48.7]},
                "hourly": {"precipitation_probability": rain}}
    if "sports.core.api.espn.com" in url:          # which game: one per league
        league = url.split("/leagues/")[1].split("/")[0]
        return {"items": [{"$ref": "http://sports.core.api.espn.com/v2/sports/x/leagues/" + league
                                   + "/events/sample-" + league + "?lang=en"}]}
    if "/scoreboard/sample-mlb" in url:
        return espn("BOS", "NYY", now - 7200, "in", 4 + int(elapsed // 90), 2, home=True)
    if "/scoreboard/sample-nhl" in url:
        return espn("BOS", "MIN", now + 3 * 3600, "pre", 0, 0)
    if "/scoreboard/sample-nfl" in url:
        return espn("NE", "BUF", now - 4 * 3600, "post", 24, 17)
    raise ValueError("no sample for " + url)


class Fetcher:
    """fetch(url) for firmware/app.py, answering from the samples."""

    def __init__(self):
        self.began = time.time()

    def __call__(self, url):
        now = time.time()
        return answer(url, int(now), now - self.began), 0, 0
