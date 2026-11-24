#!/usr/bin/env python3
"""Draw one image summing up Monday 23 November 2026 world news.

Pure Python 3.13 standard library. Renders a newspaper front page to
/output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png): masthead with the
date, the lead story (Nvidia reinstates Jensen Huang), six story cards
(COP31, Ukraine, US House, Delta, Megaspeed, GTA VI) and an also-ran
ticker. Deterministic: two runs write identical bytes.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (245, 239, 227)
CARD = (255, 253, 246)
INK = (26, 26, 26)
NAVY = (20, 38, 77)
GOLD = (212, 160, 23)
RED = (192, 57, 43)
GREEN = (118, 185, 0)
DARKGREEN = (30, 90, 40)
BLUE = (37, 99, 235)
TEAL = (14, 116, 144)
PURPLE = (124, 58, 237)
ORANGE = (234, 88, 12)
GREY = (120, 120, 120)
LIGHTGREY = (220, 220, 215)

# 3x5 bitmap font. Each glyph is five rows of three cells, rows joined
# with "/". "#" is ink, "." is empty. Uppercase, digits and punctuation.
FONT = {
    "A": "###/#.#/###/#.#/#.#",
    "B": "##./#.#/##./#.#/##.",
    "C": ".##/#../#../#../.##",
    "D": "##./#.#/#.#/#.#/##.",
    "E": "###/#../##./#../###",
    "F": "###/#../##./#../#..",
    "G": ".##/#../#.#/#.#/.##",
    "H": "#.#/#.#/###/#.#/#.#",
    "I": "###/.#./.#./.#./###",
    "J": "..#/..#/..#/#.#/.#.",
    "K": "#.#/#.#/##./#.#/#.#",
    "L": "#../#../#../#../###",
    "M": "#.#/###/#.#/#.#/#.#",
    "N": "#.#/###/###/#.#/#.#",
    "O": ".#./#.#/#.#/#.#/.#.",
    "P": "##./#.#/##./#../#..",
    "Q": ".#./#.#/#.#/##./..#",
    "R": "##./#.#/##./#.#/#.#",
    "S": ".##/#../.#./..#/##.",
    "T": "###/.#./.#./.#./.#.",
    "U": "#.#/#.#/#.#/#.#/###",
    "V": "#.#/#.#/#.#/#.#/.#.",
    "W": "#.#/#.#/###/###/#.#",
    "X": "#.#/#.#/.#./#.#/#.#",
    "Y": "#.#/#.#/.#./.#./.#.",
    "Z": "###/..#/.#./#../###",
    "0": "###/#.#/#.#/#.#/###",
    "1": ".#./##./.#./.#./###",
    "2": "##./..#/.#./#../###",
    "3": "##./..#/.#./..#/##.",
    "4": "#.#/#.#/###/..#/..#",
    "5": "###/#../##./..#/##.",
    "6": ".##/#../##./#.#/.#.",
    "7": "###/..#/.#./.#./.#.",
    "8": ".#./#.#/.#./#.#/.#.",
    "9": ".#./#.#/.##/..#/##.",
    " ": ".../.../.../.../...",
    ".": ".../.../.../.../.#.",
    ",": ".../.../.../.#./#..",
    "-": ".../.../###/.../...",
    ":": ".../.#./.../.#./...",
    "%": "#.#/..#/.#./#../#.#",
    "$": ".#./###/.#./###/.#.",
    "'": ".#./.#./.../.../...",
    "/": "..#/..#/.#./#../#..",
    "(": "..#/.#./.#./.#./..#",
    ")": "#../.#./.#./.#./#..",
    "|": ".#./.#./.#./.#./.#.",
}


def _chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(
        ">I", zlib.crc32(kind + data) & 0xFFFFFFFF
    )


def png_bytes(width, height, rgb):
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgb[y * width * 3:(y + 1) * width * 3]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    out = bytearray(b"\x89PNG\r\n\x1a\n")
    out += _chunk(b"IHDR", ihdr)
    out += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += _chunk(b"IEND", b"")
    return bytes(out)


class Canvas:
    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.px = bytearray(width * height * 3)
        self.fill_rect(0, 0, width, height, bg)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, color, t=2):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def hline(self, x, y, w, color, t=1):
        self.fill_rect(x, y, w, t, color)

    def vline(self, x, y, h, color, t=1):
        self.fill_rect(x, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.fill_rect(x0, y0, t, t, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            half = math.isqrt(max(0, r * r - dy * dy))
            self.fill_rect(cx - half, cy + dy, 2 * half + 1, 1, color)

    def ring(self, cx, cy, r, color, t=2):
        for dy in range(-r, r + 1):
            half = math.isqrt(max(0, r * r - dy * dy))
            inner = math.isqrt(max(0, (r - t) * (r - t) - dy * dy))
            self.fill_rect(cx - half, cy + dy, half - inner, 1, color)
            self.fill_rect(cx + inner + 1, cy + dy, half - inner, 1, color)

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        ys = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = ys
        if ay == cy:
            return
        def edge(xa, ya, xb, yb, y):
            if yb == ya:
                return xa
            return xa + (xb - xa) * (y - ya) / (yb - ya)
        for y in range(ay, cy + 1):
            if y < by:
                xa = edge(ax, ay, bx, by, y)
                xb = edge(ax, ay, cx, cy, y)
            else:
                xa = edge(bx, by, cx, cy, y)
                xb = edge(ax, ay, cx, cy, y)
            lo, hi = sorted((int(xa), int(xb)))
            self.fill_rect(lo, y, hi - lo + 1, 1, color)


def text_width(text, scale):
    return len(text) * 4 * scale - scale


def draw_text(cv, x, y, text, scale, color):
    text = text.upper()
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        rows = glyph.split("/")
        for ry, row in enumerate(rows):
            for rx, cell in enumerate(row):
                if cell == "#":
                    cv.fill_rect(cx + rx * scale, y + ry * scale,
                                 scale, scale, color)
        cx += 4 * scale
    return cx


def draw_centered(cv, cx, y, text, scale, color):
    draw_text(cv, cx - text_width(text, scale) // 2, y, text, scale, color)


def wrap(text, max_chars):
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= max_chars:
            cur += " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(cv, x, y, text, scale, color, max_chars, max_lines=3):
    lines = wrap(text, max_chars)[:max_lines]
    for i, line in enumerate(lines):
        draw_text(cv, x, y + i * 6 * scale, line, scale, color)
    return y + len(lines) * 6 * scale


# ---- pictograms, each drawn inside a square box (x, y, size) ----

def icon_chip(cv, x, y, s, body, pin):
    cv.fill_rect(x, y, s, s, body)
    cv.rect(x, y, s, s, INK, 2)
    inner = s // 4
    cv.fill_rect(x + inner, y + inner, s - 2 * inner, s - 2 * inner, CARD)
    cv.rect(x + inner, y + inner, s - 2 * inner, s - 2 * inner, INK, 2)
    cv.disc(x + s // 2, y + s // 2, max(2, s // 10), pin)
    for i in range(3):
        off = s // 4 + i * s // 4
        cv.fill_rect(x + off - 1, y - s // 8, 3, s // 8, INK)
        cv.fill_rect(x + off - 1, y + s, 3, s // 8, INK)
        cv.fill_rect(x - s // 8, y + off - 1, s // 8, 3, INK)
        cv.fill_rect(x + s, y + off - 1, s // 8, 3, INK)


def icon_thermometer(cv, x, y, s, color):
    stem_w = s // 4
    cv.fill_rect(x + s // 2 - stem_w // 2, y + s // 8, stem_w,
                 s // 2, (255, 255, 255))
    cv.rect(x + s // 2 - stem_w // 2, y + s // 8, stem_w, s // 2, INK, 2)
    cv.disc(x + s // 2, y + s * 3 // 4, s // 4, color)
    cv.ring(x + s // 2, y + s * 3 // 4, s // 4, INK, 2)
    cv.fill_rect(x + s // 2 - stem_w // 2 + 2, y + s // 3,
                 stem_w - 4, s // 4, color)
    for i in range(3):
        yy = y + s // 6 + i * s // 8
        cv.fill_rect(x + s // 2 + stem_w // 2, yy, s // 6, 2, INK)


def icon_ship(cv, x, y, s, color):
    cv.fill_rect(x + s // 10, y + s * 7 // 10, s * 4 // 5, s // 6, color)
    cv.triangle(x + s // 10, y + s * 7 // 10,
                x + s // 10, y + s * 17 // 20,
                x + s * 3 // 10, y + s * 7 // 10, color)
    cv.triangle(x + s * 9 // 10, y + s * 7 // 10,
                x + s * 9 // 10, y + s * 17 // 20,
                x + s * 7 // 10, y + s * 7 // 10, color)
    cv.vline(x + s // 2, y + s // 6, s // 2, INK, 3)
    cv.triangle(x + s // 2, y + s // 6,
                x + s * 5 // 6, y + s // 4,
                x + s // 2, y + s // 3, RED)
    for i in range(3):
        cv.hline(x + s // 10 + i * s // 8, y + s * 19 // 20, s // 4, BLUE, 2)


def icon_capitol(cv, x, y, s, color):
    cv.disc(x + s // 2, y + s // 3, s // 5, color)
    cv.fill_rect(x + s // 2 - s // 5, y + s // 3, s * 2 // 5, s // 6, color)
    cv.fill_rect(x + s // 6, y + s // 2, s * 2 // 3, s // 8, color)
    for i in range(4):
        cv.vline(x + s // 6 + i * s // 5, y + s * 5 // 8, s // 5, INK, 3)
    cv.fill_rect(x + s // 10, y + s * 13 // 16, s * 4 // 5, s // 10, color)
    cv.vline(x + s // 2, y + s // 12, s // 6, INK, 2)
    cv.triangle(x + s // 2, y + s // 12,
                x + s * 2 // 3, y + s // 6,
                x + s // 2, y + s * 2 // 9, RED)


def icon_plane(cv, x, y, s, color):
    cv.fill_rect(x + s // 6, y + s // 2, s * 2 // 3, s // 8, color)
    cv.triangle(x + s * 5 // 6, y + s // 2,
                x + s, y + s * 9 // 16,
                x + s * 5 // 6, y + s * 5 // 8, color)
    cv.triangle(x + s // 4, y + s // 2,
                x + s // 2, y + s * 3 // 4,
                x + s * 3 // 5, y + s // 2, color)
    cv.triangle(x + s // 6, y + s // 2,
                x + s // 4, y + s // 4,
                x + s // 3, y + s // 2, color)
    cv.disc(x + s * 3 // 4, y + s * 15 // 32, max(2, s // 20), CARD)
    cv.disc(x + s * 5 // 8, y + s * 15 // 32, max(2, s // 20), CARD)


def icon_controller(cv, x, y, s, color):
    cv.fill_rect(x + s // 8, y + s // 4, s * 3 // 4, s // 2, color)
    cv.rect(x + s // 8, y + s // 4, s * 3 // 4, s // 2, INK, 2)
    cv.fill_rect(x + s // 4, y + s * 7 // 16, s // 12, s // 4, CARD)
    cv.fill_rect(x + s * 5 // 24, y + s // 2, s // 4, s // 12, CARD)
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        cv.disc(x + s * 5 // 8 + dx * s // 8,
                y + s * 3 // 8 + dy * s // 8, max(2, s // 18), GOLD)


# ---- page layout ----

LEAD = {
    "kicker": "LEAD STORY",
    "head": ["NVIDIA BRINGS", "BACK HUANG"],
    "deck": "Board reinstates Jensen Huang as chief executive "
            "after a week of turmoil; shares jump about 30%.",
}

CARDS = [
    ("CLIMATE", RED, "thermometer",
     "COP31 COLLAPSES",
     "Climate talks in Antalya end with no deal on fossil fuels."),
    ("WAR", NAVY, "ship",
     "UKRAINE SINKS WARSHIP",
     "Sea drones sink a Russian warship off Libya."),
    ("POLITICS", BLUE, "capitol",
     "DEMOCRATS WIN HOUSE",
     "Biggest House majority since 1992 after a North "
     "Carolina flip."),
    ("TRAVEL", TEAL, "plane",
     "DELTA GROUNDS FLIGHTS",
     "Computer failure delays 1,300 flights before "
     "Thanksgiving."),
    ("TECH", PURPLE, "chip",
     "US BLACKLISTS MEGASPEED",
     "Singapore firm accused of diverting Nvidia AI chips "
     "to China."),
    ("CULTURE", ORANGE, "controller",
     "GTA VI SMASHES RECORDS",
     "$3.79 billion on day one, a record launch."),
]

TICKER = [
    "ALSO: Houthis claim a Saudi refinery strike | Rikers Island "
    "to close by 2032",
    "Seoul minister quits in AI exam scandal | UK to host "
    "2035 Women's World Cup",
]

ICONS = {
    "thermometer": icon_thermometer,
    "ship": icon_ship,
    "capitol": icon_capitol,
    "plane": icon_plane,
    "chip": icon_chip,
    "controller": icon_controller,
}


def draw_card(cv, x, y, w, h, tag, color, icon, head, deck):
    cv.fill_rect(x, y, w, h, CARD)
    cv.rect(x, y, w, h, INK, 2)
    cv.fill_rect(x, y, w, 10, color)
    if icon == "chip":
        icon_chip(cv, x + 14, y + 24, 52, GREEN, DARKGREEN)
    else:
        ICONS[icon](cv, x + 14, y + 24, 52, color)
    draw_text(cv, x + 78, y + 34, tag, 3, color)
    cv.hline(x + 78, y + 56, w - 92, LIGHTGREY, 2)
    lines = wrap(head, 17)
    for i, line in enumerate(lines[:2]):
        draw_text(cv, x + 14, y + 92 + i * 26, line, 4, INK)
    draw_wrapped(cv, x + 14, y + 150, deck, 3, INK, 23, 3)


def build():
    cv = Canvas(W, H, PAPER)
    cv.rect(0, 0, W, H, NAVY, 6)

    # Masthead: the day, named loud.
    cv.fill_rect(12, 12, W - 24, 138, NAVY)
    draw_centered(cv, W // 2, 34, "THE WORLD IN ONE PAGE", 7, CARD)
    cv.hline(72, 92, W - 144, GOLD, 3)
    draw_centered(cv, W // 2, 106, "MONDAY 23 NOVEMBER 2026", 6, GOLD)

    # Lead story.
    cv.fill_rect(24, 164, W - 48, 282, CARD)
    cv.rect(24, 164, W - 48, 282, INK, 3)
    cv.fill_rect(24, 164, W - 48, 8, RED)
    icon_chip(cv, 52, 210, 170, GREEN, DARKGREEN)
    cv.ring(137, 295, 42, CARD, 5)
    cv.disc(137, 295, 16, CARD)
    draw_text(cv, 348, 196, LEAD["kicker"], 4, RED)
    for i, line in enumerate(LEAD["head"]):
        draw_text(cv, 348, 236 + i * 44, line, 8, INK)
    draw_wrapped(cv, 348, 340, LEAD["deck"], 4, INK, 38, 3)
    draw_text(cv, 52, 400, "NVIDIA", 5, DARKGREEN)

    # Section divider.
    draw_text(cv, 24, 462, "THE DAY IN SIX STORIES", 4, NAVY)
    cv.hline(24 + text_width("THE DAY IN SIX STORIES", 4) + 16, 470,
             W - 48 - text_width("THE DAY IN SIX STORIES", 4) - 16,
             NAVY, 3)

    # Six story cards.
    cw, ch, gap = 304, 204, 16
    for i, (tag, color, icon, head, deck) in enumerate(CARDS):
        cx = 24 + (i % 3) * (cw + gap)
        cy = 490 + (i // 3) * (ch + gap)
        draw_card(cv, cx, cy, cw, ch, tag, color, icon, head, deck)

    # Also-ran ticker.
    cv.fill_rect(24, 922, W - 48, 78, NAVY)
    for i, line in enumerate(TICKER):
        draw_text(cv, 40, 936 + i * 26, line, 3, CARD)
    draw_text(cv, 40, 988, "23 NOVEMBER 2026", 2, GOLD)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = build()
    data = png_bytes(W, H, cv.px)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
