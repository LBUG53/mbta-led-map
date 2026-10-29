"""Write firmware/data.json, and with --deploy copy everything to the board.

  python tools/build_firmware.py --deploy D:            D: = the CIRCUITPY drive
  python tools/build_firmware.py --deploy D: --secrets  first time: also writes settings.toml
                                                        (asks for Wi-Fi, copies the key from .env)

The board can't parse YAML or CSV, so config.yaml, the stations, the wiring plan
and the cached MBTA lookup tables get packed into one JSON file for it.
Re-run after changing any of those.
"""
import argparse
import getpass
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sim import FIRMWARE, cache_path, layout, mbta_api  # noqa: E402
import leds as ledlib                         # noqa: E402  (firmware/leds.py)

DDP_MAX_LEDS = 480          # one DDP packet carries 1440 bytes of color
DATA_FILE = os.path.join(FIRMWARE, "data.json")
# What goes on the board, in copying order. code.py is last: the board restarts when it changes.
BOARD_FILES = ("data.json", "leds.py", "sign.py", "feeds.py", "rides.py", "remote.py", "remote.html", "app.py", "code.py")


def hex_rgb(text):
    """'#FFB020' -> [255, 176, 32]."""
    h = str(text).lstrip("#")
    return [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)]


def read_cache(name):
    """One of the lookup tables the simulator fetches from the MBTA API on its first start."""
    path = cache_path(name)
    if not os.path.exists(path):
        raise SystemExit("cache/%s is missing: start the simulator once (python server.py) to fetch it" % name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sign_rows(sign):
    """The sign's rows from config.yaml, in the form the board uses. Rows without a stop are left out."""
    rows = []
    for r in (sign.get("rows") or [])[:3]:
        if str(r.get("stop_id")) in ("", "TODO"):
            continue
        # "77 OUT" -> a badge ("77") drawn in the row's color and a note ("OUT") beside it.
        parts = str(r["label"]).split(None, 1)
        rows.append({"badge": parts[0] if parts else "", "note": parts[1] if len(parts) > 1 else "",
                     "route": str(r["route"]), "stop_id": str(r["stop_id"]),
                     "direction_id": int(r["direction_id"]), "rgb": hex_rgb(r.get("color", "#FFFFFF")),
                     "branch_letter": bool(r.get("branch_letter")),
                     "walk_minutes": float(r.get("walk_minutes") or 0)})
    return rows


def build_data():
    """Everything the board needs to know, as one dict (the contents of data.json)."""
    cfg = layout.load_config()
    routes = cfg["map"].get("routes", list(ledlib.ROUTE_LINE))

    parents = read_cache("stop_parents.json")
    route_stops = read_cache("route_stops.json")
    missing = [r for r in routes if r not in route_stops]
    if missing:
        raise SystemExit("start the simulator once first; no cached stops for " + ", ".join(missing))
    stations = layout.load_stations(route_stops)    # with which direction lights light A
    wiring = layout.load_wiring(stations)           # data/wiring_plan.csv, as edited after wiring
    counts = layout.output_counts(cfg, wiring)
    if sum(counts) > DDP_MAX_LEDS:
        raise SystemExit("%d LEDs don't fit one DDP packet (%d)" % (sum(counts), DDP_MAX_LEDS))

    sign = dict(cfg.get("sign") or {})
    sign["rows"] = sign_rows(sign)
    hw = cfg.get("hardware") or {}
    return {
        "poll_seconds": cfg.get("poll_seconds", 10),
        "routes": routes,
        "map": cfg["map"],
        "colors": {k: list(v) for k, v in layout.line_colors(cfg).items()},
        "stations": [{"line": s["line"], "stop_id": s["stop_id"], "a_dir": s["a_dir"], "name": s["station"]}
                     for s in stations],
        "wiring": wiring,
        "output_leds": counts,
        "parents": parents,
        "route_stops": {r: route_stops[r] for r in routes},
        "sign": sign,
        "ticker": cfg.get("ticker") or {},
        "night": cfg.get("night") or {},
        "ride": cfg.get("ride") or {},
        "music": [[str(e[0]), int(e[1]), e[2:] == ["lines"]] for e in (cfg.get("music") or {}).get("effects") or []],
        "wled_ip": str(hw.get("wled_ip", "TODO")),
        "ddp_resend_seconds": hw.get("ddp_resend_seconds", 1),
    }


def build():
    data = build_data()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    return data


def toml_string(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_secrets(drive):
    """Write settings.toml on the board: the Wi-Fi details (asked for here) and the MBTA key (from .env)."""
    ssid = input("Wi-Fi network name (2.4 GHz): ").strip()
    password = getpass.getpass("Wi-Fi password (hidden as you type): ")
    token = getpass.getpass("Code the phone remote asks for (hidden; Enter for none): ").strip()
    key = mbta_api.api_key()
    if not key:
        raise SystemExit("MBTA_API_KEY isn't set in .env")
    with open(os.path.join(drive, "settings.toml"), "w", encoding="utf-8") as f:
        f.write("CIRCUITPY_WIFI_SSID = " + toml_string(ssid) + "\n")
        f.write("CIRCUITPY_WIFI_PASSWORD = " + toml_string(password) + "\n")
        f.write("MBTA_API_KEY = " + toml_string(key) + "\n")
        if token:
            f.write("REMOTE_TOKEN = " + toml_string(token) + "\n")
    print("wrote settings.toml on the board")


def deploy(drive, secrets):
    """Copy the firmware to the board's CIRCUITPY drive."""
    drive = drive.rstrip("\\/") + os.sep
    if not os.path.exists(os.path.join(drive, "boot_out.txt")):
        raise SystemExit(drive + " doesn't look like a CIRCUITPY drive (no boot_out.txt)")
    if secrets:
        write_secrets(drive)
    for name in BOARD_FILES:
        shutil.copy(os.path.join(FIRMWARE, name), drive)
        print("copied", name)
    if not os.path.exists(os.path.join(drive, "settings.toml")):
        print("settings.toml is missing on the board: run again with --secrets")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--deploy", metavar="DRIVE", help="the board's CIRCUITPY drive, e.g. D: or /Volumes/CIRCUITPY")
    ap.add_argument("--secrets", action="store_true", help="write settings.toml on the drive")
    args = ap.parse_args()
    data = build()
    print("wrote firmware/data.json: %d lights on %d LEDs, %d sign rows, WLED at %s" % (
        2 * len(data["stations"]), sum(data["output_leds"]), len(data["sign"]["rows"]), data["wled_ip"]))
    if args.deploy:
        deploy(args.deploy, args.secrets)


if __name__ == "__main__":
    main()
