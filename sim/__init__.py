"""PC-only helpers for the simulator and tools.

Importing this package puts firmware/ on sys.path, so `import app`, `import leds` etc.
load the same files that go on the board - the simulator never has its own copy.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRMWARE = os.path.join(ROOT, "firmware")



def cache_path(name):
    # The lookup tables fetched from the MBTA on the first start. MBTA_CACHE_DIR is for the tests, which point
    # it at tests/fixtures/lookup so they run offline whatever is in cache/.
    return os.path.join(os.environ.get("MBTA_CACHE_DIR") or os.path.join(ROOT, "cache"), name)


# At the end of the path, so nothing in firmware/ can hide a standard module
# (firmware/code.py has the same name as Python's own `code`).
if FIRMWARE not in sys.path:
    sys.path.append(FIRMWARE)
