"""Text widths from a TrueType file (stdlib only), so labels can be placed
and checked without drawing them. Arial by default; set PRINT_FONT_REGULAR
and PRINT_FONT_BOLD to other .ttf files on systems without it."""
import os
import struct

# Where Arial usually is: Windows, macOS, then Linux with Microsoft's core fonts installed. Liberation Sans, which
# most Linux systems have, is made to match Arial's character widths, so it stands in for it.
FOLDERS = (r"C:\Windows\Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts",
           "/usr/share/fonts/truetype/msttcorefonts", "/usr/share/fonts/truetype/liberation",
           "/usr/share/fonts/liberation-sans", "/usr/share/fonts/liberation")


def find(names):
    """The first of these file names found in a font folder (the Windows path if none is)."""
    for folder in FOLDERS:
        for name in names:
            path = os.path.join(folder, name)
            if os.path.exists(path):
                return path
    return os.path.join(FOLDERS[0], names[0])


REGULAR = os.environ.get("PRINT_FONT_REGULAR") or find(("arial.ttf", "Arial.ttf", "LiberationSans-Regular.ttf"))
BOLD = os.environ.get("PRINT_FONT_BOLD") or find(("arialbd.ttf", "Arial Bold.ttf", "Arial_Bold.ttf", "LiberationSans-Bold.ttf"))
CAP = 0.716         # Arial's cap height, in ems


class Font:
    """The character widths of one TrueType file, read straight from its tables."""
    def __init__(self, path):
        """Read the three things needed to measure text: units per em (head), each glyph's
        advance width (hmtx), and which glyph draws which character (cmap).
        """
        self.cmap, self.adv, self.upm = {}, [], 1000
        try:
            with open(path, "rb") as f:
                d = f.read()
        except OSError:
            return                              # widths fall back to an average
        n = struct.unpack(">H", d[4:6])[0]
        t = {}
        for i in range(n):
            o = 12 + 16 * i
            t[d[o:o + 4].decode("latin1")] = struct.unpack(">II", d[o + 8:o + 16])
        head, hhea, hmtx, cmap = (t[k][0] for k in ("head", "hhea", "hmtx", "cmap"))
        self.upm = struct.unpack(">H", d[head + 18:head + 20])[0]
        nh = struct.unpack(">H", d[hhea + 34:hhea + 36])[0]
        self.adv = [struct.unpack(">H", d[hmtx + 4 * i:hmtx + 4 * i + 2])[0] for i in range(nh)]
        nt = struct.unpack(">H", d[cmap + 2:cmap + 4])[0]
        for i in range(nt):
            pid, eid, off = struct.unpack(">HHI", d[cmap + 4 + 8 * i:cmap + 12 + 8 * i])
            sub = cmap + off
            if pid == 3 and eid == 1 and struct.unpack(">H", d[sub:sub + 2])[0] == 4:
                self._format4(d, sub)
                break

    def _format4(self, d, s):
        """Read a format 4 character map (the usual one for Windows Unicode fonts) into self.cmap."""
        seg = struct.unpack(">H", d[s + 6:s + 8])[0] // 2
        ends = s + 14
        starts = ends + 2 * seg + 2
        deltas = starts + 2 * seg
        ranges = deltas + 2 * seg
        for i in range(seg):
            end = struct.unpack(">H", d[ends + 2 * i:ends + 2 * i + 2])[0]
            start = struct.unpack(">H", d[starts + 2 * i:starts + 2 * i + 2])[0]
            delta = struct.unpack(">h", d[deltas + 2 * i:deltas + 2 * i + 2])[0]
            ro = struct.unpack(">H", d[ranges + 2 * i:ranges + 2 * i + 2])[0]
            for c in range(start, min(end, 0x2FF) + 1):
                if ro == 0:
                    g = (c + delta) & 0xFFFF
                else:
                    a = ranges + 2 * i + ro + 2 * (c - start)
                    g = struct.unpack(">H", d[a:a + 2])[0]
                    g = (g + delta) & 0xFFFF if g else 0
                self.cmap[c] = g

    def width(self, text, size, tracking=0.0):
        """Width of a text at a font size, in the size's units; `tracking` is added after each character."""
        if not self.adv:
            return len(text) * size * 0.54 + tracking * len(text)
        total = 0
        for ch in text:
            g = self.cmap.get(ord(ch), 0)
            total += self.adv[min(g, len(self.adv) - 1)]
        return total / self.upm * size + tracking * len(text)


_fonts = {}


def width(text, size, bold=False, tracking=0.0):
    """Width of a text in the print's regular or bold font."""
    path = BOLD if bold else REGULAR
    if path not in _fonts:
        _fonts[path] = Font(path)
    return _fonts[path].width(text, size, tracking)
