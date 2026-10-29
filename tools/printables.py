"""Make every page you print or open while building, in one go.

  python tools/printables.py

Runs the scripts that write them (each can also be run on its own) and lists them in the order the
build uses them. Print the paper ones at 100% ("Actual size") and measure the 100 mm bar or the
50 mm grid before you drill or cut by them.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (script, what it writes, when it's used), in build order
PAGES = [
    ("tools/test_page.py", "data/test_page.html", "Step 5: print one Letter page to check label sizes and how light shows through, before ordering the print."),
    ("tools/drill_guide.py", "data/drill_guide_back_pages.html", "Step 7: nine Letter pages taped together inside the frame; drill through every cross. (data/drill_guide_back.svg is the same as one sheet for a print shop.)"),
    ("tools/sign_template.py", "data/sign_window_template.html", "Step 7: two Letter pages, landscape, taped into the panel's corner; jigsaw along the red line."),
    ("tools/wiring_sheet.py", "data/wiring_back_view.html", "Step 8: the back of the panel at full size, with every pixel's number."),
    ("tools/pixel_placer.py", "data/pixel_placer.html", "Step 8: open on a phone or laptop; it shows each pixel's hole, one at a time."),
    ("tools/power_guide.py", "data/power_guide.html", "Step 9: open beside the panel; the power wiring step by step, with the checks before switching on."),
]


def main():
    for script, out, when in PAGES:
        subprocess.run([sys.executable, os.path.join(ROOT, script)], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    print("Made, in the order you'll use them:\n")
    for script, out, when in PAGES:
        print("  %s\n      %s\n" % (out, when))


if __name__ == "__main__":
    main()
