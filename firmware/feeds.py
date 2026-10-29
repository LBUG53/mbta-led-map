"""Weather and sports for the sign's ticker: URLs, parsing and the short texts.

Portable like leds.py and sign.py (plain dicts, lists, ints). A ticker item is
  {"key": name, "segs": [[text, color index], ...], "w": width in pixels,
   "scroll": bool, "flash": bool, "icon": bool}
Static items must fit the ticker's width, so each text has shorter fallbacks.
"""
import sign as signlib

FIT = 61            # widest a static item can be (columns 2-62)
DEGREE = "°"

# WMO weather codes (Open-Meteo) -> a word short enough for the big font.
WMO = {0: "CLEAR", 1: "CLEAR", 2: "PT SUN", 3: "CLOUDY", 45: "FOG", 48: "FOG",
       51: "RAIN", 53: "RAIN", 55: "RAIN", 56: "SLEET", 57: "SLEET",
       61: "RAIN", 63: "RAIN", 65: "RAIN", 66: "SLEET", 67: "SLEET",
       71: "SNOW", 73: "SNOW", 75: "SNOW", 77: "SNOW", 80: "RAIN", 81: "RAIN",
       82: "RAIN", 85: "SNOW", 86: "SNOW", 95: "STORM", 96: "STORM", 99: "STORM"}

# ESPN team ids: Red Sox 2 (MLB), Bruins 1 (NHL), Patriots 17 (NFL).
TEAMS = {
    "sox": {"label": "SOX", "short": "BOS", "abbr": "BOS", "color": signlib.SOX,
            "sport": "baseball", "league": "mlb", "id": 2},
    "bruins": {"label": "B'S", "short": "BOS", "abbr": "BOS", "color": signlib.BRUINS,
               "sport": "hockey", "league": "nhl", "id": 1},
    "patriots": {"label": "PATS", "short": "NE", "abbr": "NE", "color": signlib.PATS,
                 "sport": "football", "league": "nfl", "id": 17},
}


def rel_id(rel, name):
    """The id of one related resource in an MBTA (JSON:API) answer: {"stop": {"data": {"id": "70061"}}} -> "70061"."""
    return ((rel.get(name) or {}).get("data") or {}).get("id")


def item(key, segs, scroll=False, flash=False, icon=False, more=None):
    """more: a second text that slides in halfway through the hold."""
    return {"key": key, "segs": segs, "w": signlib.segs_width(segs),
            "scroll": scroll, "flash": flash, "icon": icon, "more": more}


def fit(texts):
    """The first text that fits the ticker (the last one if none does)."""
    for text in texts:
        if signlib.text_width(text, signlib.LARGE) <= FIT:
            return text
    return texts[-1]


# --- clock
def civil_from_days(z):
    """Days since 1970-01-01 -> (year, month, day)."""
    z += 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    return yoe + era * 400 + (1 if m <= 2 else 0), m, d


def nth_sunday(year, month, n):
    """Days since 1970-01-01 of the nth Sunday of a month."""
    first = signlib.days_from_civil(year, month, 1)
    return first + (7 - (first + 4) % 7) % 7 + 7 * (n - 1)


def eastern_offset(epoch):
    """Boston's offset from UTC in seconds: daylight time runs from 2 am on the
    second Sunday of March to 2 am on the first Sunday of November."""
    year = civil_from_days(epoch // 86400)[0]
    start = nth_sunday(year, 3, 2) * 86400 + 7 * 3600
    end = nth_sunday(year, 11, 1) * 86400 + 6 * 3600
    return -4 * 3600 if start <= epoch < end else -5 * 3600


def local(epoch):
    """Boston local time as seconds, for splitting into days and hours."""
    return epoch + eastern_offset(epoch)


def clock_text(epoch):
    """'9:26': Boston time, 12-hour, no leading zero."""
    secs = local(epoch) % 86400
    hour = secs // 3600 % 12
    return "%d:%02d" % (hour if hour else 12, secs % 3600 // 60)


# --- weather
def weather_url(lat, lon):
    """Open-Meteo: now, today's high and low, and the chance of rain hour by hour. No key needed."""
    return ("https://api.open-meteo.com/v1/forecast?latitude=" + str(lat) + "&longitude=" + str(lon)
            + "&current=temperature_2m,weather_code,is_day"
            + "&daily=temperature_2m_max,temperature_2m_min"
            + "&hourly=precipitation_probability&temperature_unit=fahrenheit"
            + "&timezone=America%2FNew_York&forecast_days=1")


def parse_weather(d):
    """Keep only what the ticker shows from Open-Meteo's answer."""
    cur = d["current"]
    daily = d["daily"]
    return {"temp": int(cur["temperature_2m"] + 0.5), "code": cur["weather_code"],
            "is_day": cur.get("is_day", 1),
            "hi": int(daily["temperature_2m_max"][0] + 0.5),
            "lo": int(daily["temperature_2m_min"][0] + 0.5),
            "rain": d["hourly"]["precipitation_probability"],    # one value per hour, midnight first
            "hour": int(cur["time"][11:13])}


def hour_text(h):
    """15 -> '3PM'."""
    return str(h % 12 if h % 12 else 12) + ("PM" if h >= 12 else "AM")


def weather_items(w, cfg):
    """Current weather, today's high and low, and rain when it's likely."""
    out = []
    if cfg.get("weather", True):
        word = WMO.get(w["code"], "")
        if word == "CLEAR" and w["is_day"]:
            word = "SUNNY"
        if word == "PT SUN" and not w["is_day"]:
            word = "CLOUDY"
        temp = str(w["temp"]) + DEGREE
        out.append(item("weather", [[fit([temp + " " + word, temp + word, temp]), signlib.WHITE]]))
        out.append(item("hilo", [["H" + str(w["hi"]) + " L" + str(w["lo"]), signlib.WHITE]]))
    if cfg.get("rain", True):
        threshold = cfg.get("rain_threshold", 50)
        rest = w["rain"][w["hour"]:]
        for n in range(len(rest)):
            if rest[n] is not None and rest[n] >= threshold:
                peak = max([p for p in rest[n:] if p is not None])
                when = "NOW" if n == 0 else hour_text(w["hour"] + n)
                head = "RAIN " + str(peak) + "%"
                # RAIN 60% 3PM is too wide for the big font, so the time wins over the chance.
                out.append(item("rain", [[fit([head + " " + when, "RAIN " + when, head]), signlib.WHITE]]))
                break
    return out


# --- sports
def ymd(day):
    """Days since 1970 -> '20261003', the way ESPN writes dates."""
    y, m, d = civil_from_days(day)
    return "%04d%02d%02d" % (y, m, d)


def find_url(team, epoch):
    """The team's games yesterday and today (Boston dates), as a list of links.
    ESPN's core API, about 300 bytes."""
    today = local(epoch) // 86400
    return ("https://sports.core.api.espn.com/v2/sports/" + team["sport"] + "/leagues/" + team["league"]
            + "/teams/" + str(team["id"]) + "/events?dates=" + ymd(today - 1) + "-" + ymd(today))


def parse_find(d):
    """The id of the latest game in a find_url answer, or None."""
    items = d.get("items") or []
    if not items:
        return None
    return items[-1]["$ref"].split("/events/")[1].split("?")[0]


def game_url(team, event_id):
    """One game, live: date, teams, score, status (about 20 KB)."""
    return ("https://site.api.espn.com/apis/site/v2/sports/" + team["sport"] + "/" + team["league"]
            + "/scoreboard/" + event_id)


def parse_utc(s):
    """'2026-10-03T00:00Z' (ESPN leaves out the seconds) -> epoch seconds."""
    days = signlib.days_from_civil(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    return days * 86400 + int(s[11:13]) * 3600 + int(s[14:16]) * 60


def score(competitor):
    """A team's score from ESPN, which sends it as text or inside a dict depending on the feed."""
    s = competitor.get("score")
    if isinstance(s, dict):
        s = s.get("displayValue")
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


def parse_game(d, team):
    """A game from game_url's answer, or None."""
    comp = d["competitions"][0]
    us = them = None
    for c in comp["competitors"]:
        if c["team"]["abbreviation"] == team["abbr"]:
            us = c
        else:
            them = c
    if us is None or them is None:
        return None
    return {"start": parse_utc(d["date"]), "state": comp["status"]["type"]["state"],
            "us": score(us), "them": score(them), "opp": them["team"]["abbreviation"],
            "home": us.get("homeAway") == "home",
            "period": comp["status"].get("period"), "clock": comp["status"].get("displayClock")}


def game_live(g, epoch):
    """True from ten minutes before the start until the game is final."""
    return g is not None and g["state"] != "post" and g["start"] - 600 <= epoch < g["start"] + 8 * 3600


def game_item(name, g, epoch):
    """The ticker item for a team, or None on days without a game.

    Before: SOX 7:10. During: SOX 4-2. After, until 10 the next morning:
    SOX W 5-3. When the opponent doesn't fit, the item turns over halfway to
    a second text: SOX V NYY (home) or SOX @ NYY (away).
    """
    if g is None:
        return None
    team = TEAMS[name]
    label = team["label"]
    today = local(epoch) // 86400
    game_day = local(g["start"]) // 86400
    both = str(g["us"]) + "-" + str(g["them"])
    if g["state"] == "pre":
        if game_day != today:
            return None
        when = clock_text(g["start"])
        texts = [label + " " + when + " " + g["opp"], label + " " + when, team["short"] + " " + when]
    elif g["state"] == "in":
        if epoch > g["start"] + 12 * 3600:
            return None                 # a stale feed, not a twelve-hour game
        texts = [label + " " + str(g["us"]) + " " + g["opp"] + " " + str(g["them"]),
                 label + " " + both, team["short"] + " " + both]
    else:
        if local(epoch) >= (game_day + 1) * 86400 + 10 * 3600:
            return None
        result = "W" if g["us"] > g["them"] else "L" if g["us"] < g["them"] else "T"
        texts = [label + " " + result + " " + both, team["short"] + " " + result + " " + both,
                 team["short"] + " " + result + both]
    text = fit(texts)
    more = None
    if g["opp"] not in text:
        vs = ("V " if g.get("home") else "@ ") + g["opp"]
        more = team_segs(team, fit([label + " " + vs, team["short"] + " " + vs, vs]))
    return item(name, team_segs(team, text), more=more)


def team_segs(team, text):
    for label in (team["label"], team["short"]):
        if text.startswith(label + " "):
            return [[label, team["color"]], [text[len(label):], signlib.WHITE]]
    return [[text, signlib.WHITE]]


def score_item(name):
    team = TEAMS[name]
    text = fit([team["label"] + " SCORE!", team["label"] + " SCORE", team["short"] + " SCORE"])
    return item(name + "-score", [[text, team["color"]]], flash=True)
