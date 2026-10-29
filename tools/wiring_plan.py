r"""Plan the wiring of the 264 map lights on the Sparkle Motion's three outputs.

  python tools/wiring_plan.py            check, report, and write the plan if there is none
  python tools/wiring_plan.py --force    replace data/wiring_plan.csv (loses hand edits)

Writes data/wiring_plan.csv (output, index, station, line, light: A, B or SKIP)
and data/wled_settings.md (LED count and start index per output, and every
jump). The simulator and the firmware read the mapping from the CSV, so edit
the CSV after wiring if the real order differs; this tool never overwrites it
without --force, and without --force it checks and reports the file as it is.

Each output is one chain of 50-pixel strings plugged end to end. The chain
runs out along a line on one side (one light per station) and comes back on
the other, turning into each branch it passes, so the wire never has to cross
itself. Where two pixels in a row are further apart than the wire between
them reaches, SKIP pixels (always off) take up the distance.
"""
import argparse
import csv
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim import layout  # noqa: E402

SLACK = 8               # mm of each wire lost to bends and to seating the pixels
STRING = layout.STRING

# What each output carries: (branch, first station, last station) stretches,
# and the station its chain starts from (the end nearest the controller).
OUTPUTS = [
    {"output": 1, "root": ("M", "Mattapan"),
     "parts": [("Mattapan", None, None), ("Red", None, None), ("Red Braintree", None, None),
               ("Red Ashmont", None, None), ("Blue", None, None)]},
    {"output": 2, "root": ("OL", "Forest Hills"),
     "parts": [("Orange", None, None), ("Green trunk", "Medford/Tufts", "Park Street"),
               ("Green Union Sq", None, None), ("Green E", None, None)]},
    {"output": 3, "root": ("GL", "Riverside"),
     "parts": [("Green trunk", "Boylston", "Kenmore"), ("Green B", None, None), ("Green C", None, None),
               ("Green D", None, None)]},
]

# Where the lines really join; the chain turns here rather than at a shorter hop nearby.
JUNCTIONS = [(("RL", "JFK/UMass"), ("RL", "Savin Hill")), (("RL", "JFK/UMass"), ("RL", "North Quincy")),
             (("RL", "Ashmont"), ("M", "Ashmont")), (("GL", "Lechmere"), ("GL", "Union Sq")),
             (("GL", "Kenmore"), ("GL", "Blandford St")), (("GL", "Kenmore"), ("GL", "St. Mary's St")),
             (("GL", "Kenmore"), ("GL", "Fenway")), (("GL", "Copley"), ("GL", "Prudential"))]


def reach(cfg):
    """How far apart two neighboring pixels can be, in a straight line (the wire's length less some slack)."""
    return float(layout.load_build()["pixels"]["wire_spacing"]) - SLACK


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def members(stations, parts):
    """(station indexes of an output, the edges between neighbors on a line)."""
    nodes, edges = [], []
    for branch, first, last in parts:
        run = [i for i, s in enumerate(stations) if s["branch"] == branch]
        names = [stations[i]["station"] for i in run]
        a = names.index(first) if first else 0
        b = names.index(last) if last else len(run) - 1
        run = run[a:b + 1]
        nodes += run
        edges += [(run[k], run[k + 1]) for k in range(len(run) - 1)]
    return nodes, edges


def tree(stations, nodes, edges):
    """The lines themselves, joined into one tree by the shortest hops between them.
    Returns ({station: [neighbors]}, [the hops added])."""
    group = {i: i for i in nodes}

    def find(i):
        while group[i] != i:
            i = group[i]
        return i

    adj = {i: [] for i in nodes}

    def join(a, b):
        group[find(a)] = find(b)
        adj[a].append(b)
        adj[b].append(a)

    for a, b in edges:
        join(a, b)
    at = {i: (stations[i]["x"], stations[i]["y"]) for i in nodes}
    hops = sorted((dist(at[a], at[b]), a, b) for a in nodes for b in nodes if a < b)
    added = []
    for d, a, b in hops:
        if find(a) != find(b):
            join(a, b)
            added.append((a, b, d))
    return adj, added


def walk(stations, adj, root):
    """The lights in wiring order: [(station index, "A" or "B")]. Walks around the
    tree keeping it on the left, taking the light on the walker's right at each
    station on the way out and the other one on the way back."""
    at = {i: (stations[i]["x"], stations[i]["y"]) for i in adj}
    out = []

    def visit(node, parent, heading):
        kids = [k for k in adj[node] if k != parent]
        hx, hy = heading
        back = math.atan2(-hy, -hx)

        def turn(k):        # how far round from the way we came, sweeping through our right-hand side
            a = math.atan2(at[k][1] - at[node][1], at[k][0] - at[node][0])
            return (back - a) % (2 * math.pi)
        kids.sort(key=turn)
        if parent is None and kids:
            hx, hy = at[kids[0]][0] - at[node][0], at[kids[0]][1] - at[node][1]
        s = stations[node]
        right = (-hy, hx)                                       # screen coordinates, y down
        side_a = (s["A"][0] - s["x"]) * right[0] + (s["A"][1] - s["y"]) * right[1]
        first = "A" if side_a >= 0 else "B"
        out.append((node, first))
        for k in kids:
            visit(k, node, (at[k][0] - at[node][0], at[k][1] - at[node][1]))
        out.append((node, "B" if first == "A" else "A"))

    sys.setrecursionlimit(2000)
    visit(root, None, (0, -1))
    return out


def with_skips(stations, order, reach_mm):
    """[(station index or None for SKIP, light, mm from the previous real light)]."""
    rows, prev = [], None
    for node, light in order:
        p = stations[node][light]
        d = dist(prev, p) if prev else 0.0
        for _ in range(int(math.ceil(d / reach_mm)) - 1 if d > reach_mm else 0):
            rows.append((None, "SKIP", 0.0))
        rows.append((node, light, d))
        prev = p
    return rows


def plan(stations, cfg):
    """[{"output", "rows", "hops"}] for the three outputs."""
    by = {(s["line"], s["station"]): i for i, s in enumerate(stations)}
    out = []
    for o in OUTPUTS:
        nodes, edges = members(stations, o["parts"])
        edges += [(by[a], by[b]) for a, b in JUNCTIONS if by[a] in nodes and by[b] in nodes]
        adj, hops = tree(stations, nodes, edges)
        rows = with_skips(stations, walk(stations, adj, by[o["root"]]), reach(cfg))
        out.append({"output": o["output"], "rows": rows, "hops": hops})
    return out


def write_csv(stations, outputs, path):
    """Write the plan as data/wiring_plan.csv: one row per pixel, in wiring order."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["output", "index", "station", "line", "light"])
        for o in outputs:
            for n, (node, light, d) in enumerate(o["rows"]):
                if node is None:
                    w.writerow([o["output"], n, "", "", "SKIP"])
                else:
                    w.writerow([o["output"], n, stations[node]["station"], stations[node]["line"], light])


def measure(stations, wiring):
    """Per output: pixels, lights, SKIPs, and the wire runs between pixels in a row
    (a run across SKIPs is shared out evenly between its wires)."""
    out = []
    for output in sorted(wiring):
        chain = wiring[output]
        runs, prev, wires = [], None, 1
        for n, light in enumerate(chain):
            if light < 0:
                wires += 1
                continue
            s = stations[light // 2]
            p = s["B" if light % 2 else "A"]
            if prev is not None:
                runs.append((dist(prev[0], p) / wires, dist(prev[0], p), wires - 1, prev[1], n))
            prev, wires = (p, n), 1
        out.append({"output": output, "pixels": len(chain), "lights": sum(1 for c in chain if c >= 0),
                    "skips": sum(1 for c in chain if c < 0), "runs": runs})
    return out


def name(stations, light):
    """'RL Alewife A' for a light number."""
    s = stations[light // 2]
    return "%s %s %s" % (s["line"], s["station"], "B" if light % 2 else "A")


def settings_md(stations, wiring, counts, cfg, hops):
    """The text of data/wled_settings.md: what to enter in WLED, every hop between lines and every SKIP pixel."""
    r = reach(cfg)
    m = measure(stations, wiring)
    total = sum(counts)
    lines = ["# WLED settings and wiring notes", "",
             "Made by `tools/wiring_plan.py` from `data/wiring_plan.csv`; run it again after editing the CSV.", "",
             "## WLED: Config > LED Preferences", "",
             "| Output | Sparkle Motion GPIO | Start index | LED count | Strings of %d | Lights | SKIP pixels | Spare at the end |" % STRING,
             "|---|---|---|---|---|---|---|---|"]
    gpio = (cfg.get("hardware") or {}).get("output_gpios") or [21, 22, 19]
    start = 0
    for n, o in enumerate(m):
        lines.append("| %d | %s | %d | %d | %d | %d | %d | %d |" % (
            o["output"], gpio[n] if n < len(gpio) else "?", start, counts[n], counts[n] // STRING, o["lights"],
            o["skips"], counts[n] - o["pixels"]))
        start += counts[n]
    lines += ["", "Total: %d LEDs on %d strings, %d lights. Type WS281x, color order to suit the strings (test with one)."
              % (total, total // STRING, sum(o["lights"] for o in m)),
              "The board sends one DDP packet of %d x 3 bytes covering all three outputs in this order." % total, "",
              "## Wire runs", "",
              "Each wire between two pixels is %d mm; the plan allows %d mm in a straight line (%d mm slack)."
              % (r + SLACK, r, SLACK), ""]
    for o in m:
        worst = max(o["runs"]) if o["runs"] else (0, 0, 0, 0, 0)
        over = [x for x in o["runs"] if x[0] > r + 0.05]
        lines.append("- Output %d: %d pixels; longest wire run %.1f mm (pixel %d to %d)%s." % (
            o["output"], o["pixels"], worst[0], worst[3], worst[4],
            "; **%d runs over reach**" % len(over) if over else ""))
    lines += ["", "## Where each chain leaves a line", "",
              "The generated plan follows the lines; these are the hops it makes from one line to another.", ""]
    for output, a, b, d in hops:
        lines.append("- Output %d: %s %s to %s %s (stations %.0f mm apart)" % (
            output, stations[a]["line"], stations[a]["station"], stations[b]["line"], stations[b]["station"], d))
    lines += ["", "## SKIP pixels (always off; tuck them behind the panel)", "",
              "| Output | Pixel | Between | Straight-line jump |", "|---|---|---|---|"]
    for o in m:
        chain = wiring[o["output"]]
        for per, d, skips, a, b in o["runs"]:
            if skips:
                lines.append("| %d | %s | %s and %s | %.0f mm |" % (
                    o["output"], ", ".join(str(i) for i in range(a + 1, b)), name(stations, chain[a]),
                    name(stations, chain[b]), d))
    return "\n".join(lines) + "\n", m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="replace data/wiring_plan.csv with a fresh plan")
    args = ap.parse_args()
    cfg = layout.load_config()
    stations = layout.load_stations()
    hops = []
    if args.force or not os.path.exists(layout.WIRING):
        outputs = plan(stations, cfg)
        write_csv(stations, outputs, layout.WIRING)
        print("wrote data\\wiring_plan.csv")
    else:
        print("data\\wiring_plan.csv exists: checking it as it is (--force writes a fresh plan)")
    for o in plan(stations, cfg):
        hops += [(o["output"], a, b, d) for a, b, d in o["hops"]]
    wiring = layout.load_wiring(stations)           # raises if a light is missing or wired twice
    counts = layout.output_counts(cfg, wiring)
    text, m = settings_md(stations, wiring, counts, cfg, hops)
    with open(os.path.join(layout.DATA, "wled_settings.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    r = reach(cfg)
    bad = 0
    for n, o in enumerate(m):
        over = [x for x in o["runs"] if x[0] > r + 0.05]
        bad += len(over)
        print("output %d: %3d pixels = %3d lights + %2d SKIP; %d strings (%d LEDs, %d spare); longest run %.1f mm%s" % (
            o["output"], o["pixels"], o["lights"], o["skips"], counts[n] // STRING, counts[n],
            counts[n] - o["pixels"], max(o["runs"])[0], "; %d OVER REACH" % len(over) if over else ""))
    print("total: %d LEDs on %d strings; wrote data/wled_settings.md" % (sum(counts), sum(counts) // STRING))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
