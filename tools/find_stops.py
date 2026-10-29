"""Look up stop IDs for config.yaml sign rows.

  python tools/find_stops.py 77            # every stop, both directions
  python tools/find_stops.py 77 linnaean   # only names containing "linnaean"
  python tools/find_stops.py Red porter    # platforms at a rail station
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import mbta_api  # noqa: E402


def main(route, text=""):
    """Print every stop on a route, both directions, optionally only those whose name contains `text`."""
    text = text.lower()
    r, _ = mbta_api.get(f"/routes/{route}", {"fields[route]": "long_name,direction_names,direction_destinations"})
    a = r["data"]["attributes"]
    print(f"Route {route}: {a['long_name']}")
    for d in (0, 1):
        print(f"\ndirection_id {d}: {a['direction_names'][d]} toward {a['direction_destinations'][d]}")
        s, _ = mbta_api.get("/stops", {"filter[route]": route, "filter[direction_id]": d,
                                       "fields[stop]": "name,platform_name", "include": "child_stops"})
        children = {c["id"]: c for c in s.get("included", [])}
        for stop in s["data"]:
            name = stop["attributes"]["name"]
            if text and text not in name.lower():
                continue
            print(f"  {stop['id']:14} {name}")
            # For rail, list the platforms too (direction-specific IDs).
            for rel in stop.get("relationships", {}).get("child_stops", {}).get("data", []) or []:
                c = children.get(rel["id"])
                if c and c["attributes"].get("platform_name"):
                    print(f"      platform {c['id']:10} {c['attributes']['platform_name']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], " ".join(sys.argv[2:]))
