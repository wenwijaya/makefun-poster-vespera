#!/usr/bin/env python3
"""VESPERA - a travel poster for a place that isn't there.

A pure-stdlib Python program (no third-party libraries, no network) that
paints a vintage travel poster for Vespera, an invented island where the
evening never ends, and writes it to /output/entry.png (1024x1024 PNG).

The poster's one landmark is the Glass Lighthouse: a cream tower on a dark
rock islet, its lamp sweeping a beam of gold across a violet dusk sea toward
a low sun. The place name VESPERA is set large across the sky, with the
tagline "WHERE THE EVENING NEVER ENDS" beneath it.

Deterministic: every star, bird and shimmer comes from a fixed-seed
generator, so two runs produce byte-identical output.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024
OUT = "/output/entry.png"

# ---------------------------------------------------------------- palette
SKY_TOP = (23, 17, 56)
SKY_MID = (88, 40, 104)
SKY_LOW = (198, 88, 106)
HORIZON = (244, 164, 96)
SUN_CORE = (255, 236, 182)
SUN_RIM = (255, 196, 118)
SEA_TOP = (76, 53, 112)
SEA_BOT = (15, 12, 40)
ROCK = (32, 19, 54)
CLIFF = (21, 12, 38)
HEADLAND = (52, 30, 84)
CREAM = (250, 238, 214)
GOLD = (232, 183, 110)
LAMP = (255, 214, 130)
DARK = (18, 11, 36)

HORIZON_Y = 560


# ------------------------------------------------------- deterministic rng
class LCG:
    """Tiny fixed-seed generator; identical on every run and platform."""

    def __init__(self, seed=20261121):
        self.s = seed

    def next(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s

    def frac(self):
        return self.next() / 0x7FFFFFFF

    def range(self, lo, hi):
        return lo + self.frac() * (hi - lo)


rng = LCG()


# ------------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def _idx(x, y):
    return (y * W + x) * 3


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = _idx(x, y)
        buf[i], buf[i + 1], buf[i + 2] = c


def blend(x, y, c, a):
    """Blend colour c over the pixel at (x, y) with opacity a (0..1)."""
    if 0 <= x < W and 0 <= y < H and a > 0:
        if a >= 1:
            put(x, y, c)
            return
        i = _idx(x, y)
        buf[i] = int(buf[i] + (c[0] - buf[i]) * a)
        buf[i + 1] = int(buf[i + 1] + (c[1] - buf[i + 1]) * a)
        buf[i + 2] = int(buf[i + 2] + (c[2] - buf[i + 2]) * a)


def lerp(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def fill_row(y, c):
    i = y * W * 3
    buf[i:i + W * 3] = bytes(c) * W


def fill_rect(x0, y0, x1, y1, c):
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    for y in range(y0, y1):
        i = _idx(x0, y)
        buf[i:i + len(row)] = row


def vgrad(y0, y1, stops):
    """Vertical gradient; stops is a list of (pos 0..1, colour)."""
    for y in range(max(0, y0), min(H, y1)):
        t = (y - y0) / max(1, y1 - y0 - 1)
        for k in range(len(stops) - 1):
            p0, c0 = stops[k]
            p1, c1 = stops[k + 1]
            if p0 <= t <= p1:
                f = 0 if p1 == p0 else (t - p0) / (p1 - p0)
                fill_row(y, lerp(c0, c1, f))
                break
        else:
            fill_row(y, stops[-1][1])


def disc(cx, cy, r, c, alpha=1.0):
    """Filled disc with a 1px antialiased edge."""
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        if y < 0 or y >= H:
            continue
        dy = y - cy
        dx = math.sqrt(max(0.0, r * r - dy * dy)) if abs(dy) < r else 0.0
        if dx <= 0:
            continue
        x0 = int(math.ceil(cx - dx))
        x1 = int(math.floor(cx + dx))
        for x in range(x0, x1 + 1):
            d = math.hypot(x - cx, y - cy)
            a = alpha * max(0.0, min(1.0, r + 0.5 - d))
            blend(x, y, c, a)


def glow(cx, cy, r, c, peak):
    """Soft radial glow fading to nothing at radius r."""
    for y in range(int(cy - r), int(cy + r + 1)):
        if y < 0 or y >= H:
            continue
        for x in range(int(cx - r), int(cx + r + 1)):
            if x < 0 or x >= W:
                continue
            d = math.hypot(x - cx, y - cy)
            if d < r:
                a = peak * (1 - d / r) ** 2
                blend(x, y, c, a)


def poly(points, c):
    """Scanline fill of a simple polygon."""
    ys = [p[1] for p in points]
    for y in range(max(0, int(min(ys))), min(H, int(max(ys)) + 1)):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            x0 = int(math.ceil(xs[k]))
            x1 = int(math.floor(xs[k + 1]))
            if x1 >= x0:
                i = _idx(max(0, x0), y)
                npx = min(W, x1 + 1) - max(0, x0)
                if npx > 0:
                    buf[i:i + npx * 3] = bytes(c) * npx


def ellipse(cx, cy, rx, ry, c, alpha=1.0):
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        if y < 0 or y >= H:
            continue
        t = (y - cy) / ry
        if abs(t) >= 1:
            continue
        dx = rx * math.sqrt(1 - t * t)
        for x in range(int(cx - dx), int(cx + dx) + 1):
            d = math.hypot((x - cx) / rx, (y - cy) / ry)
            a = alpha * max(0.0, min(1.0, 1.2 - d))
            blend(x, y, c, a)


def beam(x0, y0, x1, y1, half, c, peak):
    """A soft wedge of light from (x0,y0) to (x1,y1), widening to half."""
    steps = 90
    for s in range(steps + 1):
        t = s / steps
        cx = x0 + (x1 - x0) * t
        cy = y0 + (y1 - y0) * t
        r = 4 + half * t
        a = peak * (1 - t * 0.75)
        disc(cx, cy, r, c, a * 0.16)


# --------------------------------------------------------------------- font
# 5x7 pixel capitals, digits and punctuation. One string per row, '#' = on.
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "-": ["00000", "00000", "00000", "01110", "00000", "00000", "00000"],
    "'": ["00100", "00100", "01000", "00000", "00000", "00000", "00000"],
    "·": ["00000", "00000", "01100", "01100", "00000", "00000", "00000"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(s, cx, y, scale, colour, shadow=None):
    """Draw centred text; shadow is an (dx, dy, colour) tuple or None."""
    w = text_width(s, scale)
    x = cx - w // 2
    if shadow is not None:
        dx, dy, sc = shadow
        _draw_text_at(s, x + dx, y + dy, scale, sc)
    _draw_text_at(s, x, y, scale, colour)


def _draw_text_at(s, x0, y0, scale, colour):
    x = x0
    for ch in s:
        glyph = FONT.get(ch.upper(), FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(
                        x + col * scale,
                        y0 + row * scale,
                        x + (col + 1) * scale,
                        y0 + (row + 1) * scale,
                        colour,
                    )
        x += 6 * scale


# -------------------------------------------------------------------- scene
def paint_sky():
    vgrad(0, HORIZON_Y + 1, [
        (0.00, SKY_TOP),
        (0.42, SKY_MID),
        (0.72, SKY_LOW),
        (1.00, HORIZON),
    ])
    # stars, only high in the sky where it is dark
    for _ in range(110):
        sx = int(rng.range(30, W - 30))
        sy = int(rng.range(30, 300))
        r = rng.range(0.6, 1.7)
        a = rng.range(0.25, 0.9)
        disc(sx, sy, r, CREAM, a)
    # a few soft dusk clouds
    for (cx, cy, rx, ry, a) in [
        (180, 300, 150, 16, 0.10),
        (420, 250, 190, 13, 0.08),
        (830, 320, 170, 15, 0.10),
        (640, 210, 120, 11, 0.07),
    ]:
        ellipse(cx, cy, rx, ry, (255, 170, 150), a)


def paint_sun():
    glow(712, 468, 300, (255, 170, 110), 0.34)
    glow(712, 468, 150, (255, 205, 130), 0.5)
    disc(712, 468, 76, SUN_RIM)
    disc(712, 468, 68, SUN_CORE)
    # thin bright rim on the sea side
    disc(712, 470, 70, (255, 244, 205), 0.35)


def paint_sea():
    vgrad(HORIZON_Y, H, [(0.0, SEA_TOP), (1.0, SEA_BOT)])
    # sun path: shimmering gold dashes under the sun, fading with depth
    for row in range(HORIZON_Y + 6, 940, 7):
        depth = (row - HORIZON_Y) / (940 - HORIZON_Y)
        spread = 20 + depth * 70
        cx = 712 + int(rng.range(-spread, spread) * 0.18)
        half = int(16 + rng.range(0, 40) * (1 - depth * 0.55))
        a = 0.6 * (1 - depth * 0.85)
        for x in range(cx - half, cx + half):
            blend(x, row, GOLD, a)
            blend(x, row + 1, GOLD, a * 0.7)
    # faint horizontal swell lines
    for row in range(HORIZON_Y + 40, H - 60, 46):
        a = 0.05
        for x in range(0, W, 3):
            if rng.frac() < 0.5:
                blend(x, row, (150, 130, 200), a)


def paint_headlands():
    # distant silhouettes framing the horizon, left and right
    poly([(0, HORIZON_Y), (60, 528), (120, 545), (190, 522),
          (250, 548), (310, 536), (330, HORIZON_Y), (0, HORIZON_Y)], HEADLAND)
    poly([(1024, HORIZON_Y), (960, 530), (900, 548), (845, 526),
          (800, 550), (770, HORIZON_Y), (1024, HORIZON_Y)], HEADLAND)


def paint_lighthouse():
    # rocky islet
    poly([(238, 760), (268, 690), (300, 668), (352, 662), (392, 690),
          (418, 760), (430, 830), (240, 830)], ROCK)
    poly([(268, 690), (300, 668), (352, 662), (392, 690), (380, 716),
          (288, 716)], (44, 27, 72))
    # tower: cream, tapering, with dark bands
    poly([(306, 700), (318, 516), (344, 516), (356, 700)], CREAM)
    poly([(310, 640), (352, 640), (350, 662), (312, 662)], (96, 44, 84))
    poly([(314, 576), (348, 576), (346, 596), (316, 596)], (96, 44, 84))
    # gallery platform + lamp room
    fill_rect(310, 506, 352, 516, DARK)
    glow(331, 494, 60, LAMP, 0.85)
    fill_rect(320, 478, 342, 506, (52, 28, 60))
    fill_rect(323, 482, 339, 502, LAMP)
    # dome cap
    poly([(318, 478), (344, 478), (338, 464), (324, 464)], DARK)
    disc(331, 464, 3, GOLD)
    # beam sweeping right toward the sun
    beam(331, 492, 1000, 400, 30, (255, 220, 150), 0.75)
    # small warm windows on the rock cottage
    fill_rect(262, 700, 272, 710, LAMP)
    fill_rect(386, 706, 396, 716, LAMP)
    # warm rim light along the islet's top edge
    for x in range(268, 393, 3):
        y = 690 - int(22 * math.sin((x - 268) / 125 * math.pi))
        blend(x, y, GOLD, 0.35)
        blend(x, y + 1, GOLD, 0.2)


def paint_boat():
    # one tiny sailboat crossing the sun path, for scale and life
    bx, by = 770, 648
    poly([(bx - 16, by), (bx + 16, by), (bx, by + 6)], DARK)
    poly([(bx, by - 2), (bx, by - 34), (bx + 20, by - 2)], CREAM)
    poly([(bx - 2, by - 2), (bx - 2, by - 26), (bx - 15, by - 2)], (232, 183, 110))
    fill_rect(bx - 1, by - 36, bx + 1, by, DARK)


def paint_birds():
    for (bx, by, s) in [(560, 240, 9), (600, 215, 7), (520, 285, 6),
                        (850, 200, 8), (890, 235, 6)]:
        for dx in range(-s, s + 1):
            dy = int(abs(dx) * 0.45)
            put(bx + dx, by + dy, DARK)
            put(bx + dx, by + dy + 1, DARK)


def paint_foreground():
    # dark cliffs framing the bottom corners
    poly([(0, 1024), (0, 930), (70, 884), (150, 908), (210, 950),
          (180, 1024)], CLIFF)
    poly([(1024, 1024), (1024, 940), (950, 896), (880, 918), (830, 962),
          (860, 1024)], CLIFF)
    # a spray of warm light on the cliff edges
    for x in range(0, 210, 4):
        y = 930 - int(46 * math.sin(x / 210 * math.pi) * 0.9)
        blend(x, y, GOLD, 0.12)


def paint_type():
    # place name, large across the dusk sky
    draw_text("VESPERA", W // 2, 74, 12, CREAM, shadow=(4, 4, (40, 16, 60)))
    # gold rule with a diamond, under the name
    fill_rect(W // 2 - 190, 176, W // 2 - 16, 179, GOLD)
    fill_rect(W // 2 + 16, 176, W // 2 + 190, 179, GOLD)
    poly([(W // 2, 168), (W // 2 + 9, 177), (W // 2, 186), (W // 2 - 9, 177)],
         GOLD)
    draw_text("WHERE THE EVENING NEVER ENDS", W // 2, 198, 3, CREAM,
              shadow=(2, 2, (40, 16, 60)))
    # footer line, small, inside the frame
    draw_text("THE GLASS LIGHTHOUSE · SAIL BEYOND THE LAST LIGHT",
              W // 2, 946, 2, (238, 214, 178), shadow=(1, 1, DARK))


def paint_frame():
    c = (250, 238, 214)
    for (d, t) in [(24, 2), (34, 1)]:
        fill_rect(d, d, W - d, d + t, c)
        fill_rect(d, H - d - t, W - d, H - d, c)
        fill_rect(d, d, d + t, H - d, c)
        fill_rect(W - d - t, d, W - d, H - d, c)


def paint():
    paint_sky()
    paint_sun()
    paint_sea()
    paint_headlands()
    paint_lighthouse()
    paint_boat()
    paint_birds()
    paint_foreground()
    paint_type()
    paint_frame()


# ---------------------------------------------------------------------- png
def _filter_row(kind, row, prev):
    if kind == 0:
        return b"\x00" + row
    out = bytearray()
    if kind == 1:  # Sub
        for i, b in enumerate(row):
            left = row[i - 3] if i >= 3 else 0
            out.append((b - left) & 0xFF)
    elif kind == 2:  # Up
        for i, b in enumerate(row):
            up = prev[i] if prev else 0
            out.append((b - up) & 0xFF)
    elif kind == 3:  # Average
        for i, b in enumerate(row):
            left = row[i - 3] if i >= 3 else 0
            up = prev[i] if prev else 0
            out.append((b - ((left + up) // 2)) & 0xFF)
    else:  # Paeth
        for i, b in enumerate(row):
            left = row[i - 3] if i >= 3 else 0
            up = prev[i] if prev else 0
            up_left = prev[i - 3] if (prev and i >= 3) else 0
            p = left + up - up_left
            pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
            pr = left if (pa <= pb and pa <= pc) else (up if pb <= pc else up_left)
            out.append((b - pr) & 0xFF)
    return bytes([kind]) + bytes(out)


def _score_filtered(data):
    return sum(abs(b if b < 128 else b - 256) for b in data[1:])


def write_png(path):
    raw = bytearray()
    prev = None
    for y in range(H):
        row = bytes(buf[y * W * 3:(y + 1) * W * 3])
        best = None
        for kind in range(5):
            cand = _filter_row(kind, row, prev)
            sc = _score_filtered(cand)
            if best is None or sc < best[0]:
                best = (sc, cand)
        raw += best[1]
        prev = row
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    paint()
    try:
        os.makedirs("/output", exist_ok=True)
        size = write_png(OUT)
        path = OUT
    except OSError:
        size = write_png("entry.png")
        path = "entry.png"
    print(f"wrote {path} ({W}x{H}, {size} bytes)")
    if size > 1048576:
        print("WARNING: over the 1 MiB gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
