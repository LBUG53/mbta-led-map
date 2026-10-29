"""Lookup tables built once from the MBTA API and cached in cache/.

The firmware gets both tables in data.json (tools/build_firmware.py); the
simulator builds them on its first start.
"""
import json
import os

from . import cache_path, mbta_api


def stop_parents():
    """{platform stop ID: parent place-id} for the subway, cached on disk."""
    path = cache_path("stop_parents.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            table = json.load(f)
        if table:
            return table
    d, _ = mbta_api.get("/stops", {"filter[route_type]": "0,1", "fields[stop]": "parent_station"})
    table = {}
    for s in d["data"]:
        p = (s["relationships"].get("parent_station") or {}).get("data")
        if p:
            table[s["id"]] = p["id"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(table, f, indent=0, sort_keys=True)
    return table


def route_stops(routes):
    """{route: [parent place-ids in route order]}, cached. Gives which routes
    serve each station and where each route ends."""
    path = cache_path("route_stops.json")
    table = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            table = json.load(f)
    missing = [r for r in routes if r not in table]
    for r in missing:
        d, _ = mbta_api.get("/stops", {"filter[route]": r, "filter[direction_id]": 0, "fields[stop]": "name"})
        table[r] = [s["id"] for s in d["data"]]
    if missing:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(table, f, indent=1)
    return table


def route_directions(routes):
    """{route: [[name, destination] for direction 0, the same for direction 1]}, cached."""
    path = cache_path("route_directions.json")
    table = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            table = json.load(f)
    if any(r not in table for r in routes):
        d, _ = mbta_api.get("/routes", {"filter[id]": ",".join(routes),
                                        "fields[route]": "direction_names,direction_destinations"})
        for r in d["data"]:
            a = r["attributes"]
            table[r["id"]] = [[a["direction_names"][i], a["direction_destinations"][i]] for i in (0, 1)]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(table, f, indent=1)
    return table
