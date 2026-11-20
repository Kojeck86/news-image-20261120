#!/usr/bin/env python3
"""THE WORLD - front page of Friday 20 November 2026.

Draws a 1024x1024 newspaper front page as a PNG using only the Python
standard library: a hand-built 5x7 bitmap font, flat vector shapes, and a
small PNG encoder (zlib + struct). Deterministic: no clock, no randomness,
no dict-order dependence in the output bytes.

Run:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
Writes <output>/entry.png (1024x1024, under 1 MiB).
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---- palette ---------------------------------------------------------
INK = (0, 0, 0)
PAPER = (255, 255, 255)
RED = (176, 30, 30)
DARKBLUE = (24, 58, 104)
MIDBLUE = (52, 92, 140)
NIGHT = (16, 28, 52)
LIGHT = (232, 232, 232)
GRAY = (120, 120, 120)
DARK = (40, 40, 40)
GOLD = (198, 158, 60)
GREEN = (28, 112, 58)
ORANGE = (222, 108, 20)
SKY = (210, 220, 230)
WATER = (60, 110, 160)
FLAGBLUE = (40, 90, 170)


# ---- canvas ----------------------------------------------------------
def new_canvas():
    px = bytearray(W * H * 3)
    for i in range(0, len(px), 3):
        px[i] = 255
        px[i + 1] = 255
        px[i + 2] = 255
    return px


def set_px(px, x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i] = color[0]
        px[i + 1] = color[1]
        px[i + 2] = color[2]


def fill_rect(px, x, y, w, h, color):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            px[i] = color[0]
            px[i + 1] = color[1]
            px[i + 2] = color[2]


def hline(px, x, y, w, color, t=1):
    fill_rect(px, x, y, w, t, color)


def vline(px, x, y, h, color, t=1):
    fill_rect(px, x, y, t, h, color)


def line(px, x0, y0, x1, y1, color):
    """Bresenham line, 1px wide."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        set_px(px, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def thick_line(px, x0, y0, x1, y1, color, t=2):
    for a in range(t):
        line(px, x0, y0 + a, x1, y1 + a, color)


def fill_circle(px, cx, cy, r, color):
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(r * r - dy * dy))
        fill_rect(px, cx - dx, cy + dy, 2 * dx + 1, 1, color)


def circle_outline(px, cx, cy, r, color):
    for deg in range(0, 360, 2):
        a = math.radians(deg)
        set_px(px, cx + int(r * math.cos(a)), cy + int(r * math.sin(a)), color)


# ---- 5x7 bitmap font (uppercase, digits, punctuation) ----------------
# Each glyph is 7 rows of 5 cells; '#' is ink, '.' is blank.
FONT = {
    "A": (" .###. ".replace(" ", "."), "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..#.", "#...#"),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "&": (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "—": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
}

BLANK = (".....", ".....", ".....", ".....", ".....", ".....", ".....")


def _norm(text):
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .upper()
    )


def text_width(text, scale):
    n = len(_norm(text))
    return n * 6 * scale - scale if n else 0


def draw_text(px, x, y, text, scale, color):
    """Draw text at (x, y); returns the pixel width drawn."""
    cx = x
    for ch in _norm(text):
        glyph = FONT.get(ch, BLANK)
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit == "#":
                    fill_rect(px, cx + c * scale, y + r * scale, scale, scale, color)
        cx += 6 * scale
    return cx - x - scale if cx > x else 0


def draw_text_centered(px, cx, y, text, scale, color):
    w = text_width(text, scale)
    return draw_text(px, cx - w // 2, y, text, scale, color)


def draw_text_right(px, x, y, text, scale, color):
    w = text_width(text, scale)
    return draw_text(px, x - w, y, text, scale, color)


def wrap_text(text, scale, max_w):
    lines = []
    cur = ""
    for word in _norm(text).split(" "):
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_lines(px, x, y, lines, scale, color, leading=5):
    for i, ln in enumerate(lines):
        draw_text(px, x, y + i * (7 * scale + leading), ln, scale, color)


# ---- PNG encoder -----------------------------------------------------
def _chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path, px):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += px[y * W * 3 : (y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


# ---- illustrations ---------------------------------------------------
def draw_lead_art(px, x, y, w, h):
    """Shenzhen skyline at dusk, three flags for the trilateral summit."""
    fill_rect(px, x, y, w, h, DARKBLUE)
    fill_rect(px, x, y + h - 62, w, 62, MIDBLUE)
    # sun
    fill_circle(px, x + w - 110, y + 46, 26, GOLD)
    fill_circle(px, x + w - 110, y + 46, 18, (226, 190, 110))
    # skyline silhouettes (offset, width, height from panel bottom)
    towers = [
        (0, 62, 72), (70, 42, 112), (120, 56, 86), (186, 46, 132),
        (242, 70, 96), (322, 50, 122), (382, 66, 76), (458, 42, 106),
        (510, 62, 142), (582, 46, 92), (638, 70, 116), (718, 50, 82),
        (778, 56, 126), (844, 46, 96), (900, 62, 112), (962, 6, 70),
    ]
    for off, tw, th in towers:
        fill_rect(px, x + off, y + h - th, tw, th, (12, 20, 34))
        # lit windows, deterministic pattern
        for wy in range(y + h - th + 8, y + h - 8, 12):
            for wx in range(x + off + 7, x + off + tw - 4, 11):
                if (wx // 11 + wy // 12) % 3 != 0:
                    fill_rect(px, wx, wy, 3, 4, GOLD)
    # three flags on poles, centre-left
    for i, col in enumerate((RED, FLAGBLUE, PAPER)):
        fx = x + 420 + i * 52
        vline(px, fx, y + h - 96, 96, DARK, 3)
        fill_rect(px, fx + 3, y + h - 94, 34, 20, col)
        if col is PAPER:
            fill_rect(px, fx + 3, y + h - 94, 34, 2, INK)
            fill_rect(px, fx + 3, y + h - 76, 34, 2, INK)
    # ground band
    fill_rect(px, x, y + h - 10, w, 10, (10, 16, 28))


def draw_houthi_art(px, x, y, w, h):
    """Drone over a city target, explosion burst."""
    fill_rect(px, x, y, w, h, LIGHT)
    # buildings
    for off, bw, bh in ((0, 90, 22), (100, 60, 30), (170, 80, 18), (260, 70, 26), (340, 60, 20), (410, 62, 28)):
        fill_rect(px, x + off, y + h - bh, bw, bh, DARK)
    # explosion burst
    ex, ey = x + 130, y + 26
    for k in range(8):
        a = math.radians(k * 45)
        line(px, ex, ey, ex + int(20 * math.cos(a)), ey + int(20 * math.sin(a)), ORANGE)
    fill_circle(px, ex, ey, 10, ORANGE)
    fill_circle(px, ex, ey, 5, GOLD)
    # quadcopter drone
    dx, dy = x + 330, y + 16
    fill_rect(px, dx - 8, dy - 3, 16, 6, INK)
    for sx, sy in ((-14, -8), (14, -8), (-14, 8), (14, 8)):
        line(px, dx, dy, dx + sx, dy + sy, INK)
        fill_circle(px, dx + sx, dy + sy, 4, INK)
    fill_circle(px, dx, dy, 2, RED)


def draw_anthropic_art(px, x, y, w, h):
    """Rising stock chart with a green arrow."""
    fill_rect(px, x, y, w, h, PAPER)
    # grid
    for gx in range(x + 40, x + w, 47):
        vline(px, gx, y + 6, h - 12, LIGHT, 1)
    for gy in range(y + 12, y + h - 6, 15):
        hline(px, x + 6, gy, w - 12, LIGHT, 1)
    # axes
    hline(px, x + 6, y + h - 8, w - 12, INK, 2)
    vline(px, x + 6, y + 6, h - 14, INK, 2)
    # rising line
    pts = [
        (x + 14, y + h - 16), (x + 80, y + h - 26), (x + 150, y + h - 22),
        (x + 220, y + h - 38), (x + 290, y + h - 30), (x + 360, y + h - 48),
        (x + 430, y + h - 56),
    ]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        thick_line(px, ax, ay, bx, by, GREEN, 3)
    # arrow head
    ax, ay = pts[-1]
    line(px, ax, ay, ax - 12, ay + 2, GREEN)
    line(px, ax, ay, ax - 4, ay + 12, GREEN)
    line(px, ax, ay, ax - 12, ay + 2, GREEN)
    # label
    draw_text(px, x + w - 150, y + 4, "$97  +17%", 2, GREEN)


def draw_kyiv_art(px, x, y, w, h):
    """Broken bridge: deck split, towers, smoke over the gap."""
    fill_rect(px, x, y, w, h, SKY)
    fill_rect(px, x, y + h - 12, w, 12, WATER)
    for wx in range(x + 20, x + w - 20, 46):
        hline(px, wx, y + h - 6, 22, (140, 180, 210), 2)
    # towers
    fill_rect(px, x + 118, y + 8, 6, 34, DARK)
    fill_rect(px, x + 348, y + 8, 6, 34, DARK)
    # cables
    line(px, x + 121, y + 10, x + 30, y + 36, DARK)
    line(px, x + 121, y + 10, x + 205, y + 36, DARK)
    line(px, x + 351, y + 10, x + 268, y + 36, DARK)
    line(px, x + 351, y + 10, x + 440, y + 36, DARK)
    # deck, broken in the middle
    fill_rect(px, x + 8, y + 36, 196, 6, DARK)
    fill_rect(px, x + 268, y + 36, 196, 6, DARK)
    line(px, x + 204, y + 36, x + 216, y + 48, DARK)
    line(px, x + 268, y + 36, x + 256, y + 48, DARK)
    # smoke over the gap
    fill_circle(px, x + 232, y + 20, 9, GRAY)
    fill_circle(px, x + 246, y + 13, 7, GRAY)
    fill_circle(px, x + 222, y + 12, 6, (150, 150, 150))


def draw_genoa_art(px, x, y, w, h):
    """Night airport: runway lights, two drones overhead."""
    fill_rect(px, x, y, w, h, NIGHT)
    # moon
    fill_circle(px, x + w - 46, y + 16, 10, (224, 224, 200))
    # stars
    for sx, sy in ((30, 12), (90, 20), (180, 10), (260, 16), (330, 8), (400, 22)):
        fill_rect(px, x + sx, y + sy, 2, 2, PAPER)
    # runway
    fill_rect(px, x, y + h - 18, w, 8, (90, 90, 90))
    for rx in range(x + 10, x + w - 10, 34):
        fill_rect(px, rx, y + h - 15, 16, 2, PAPER)
    # drones
    for dx, dy in ((x + 120, y + 22), (x + 300, y + 30)):
        hline(px, dx - 12, dy, 24, INK, 2)
        vline(px, dx, dy - 6, 12, INK, 2)
        fill_circle(px, dx, dy, 2, RED)


# ---- layout ----------------------------------------------------------
M = 28            # side margin
CW = W - 2 * M    # content width = 968
COLW = 472        # story column width
GAPX = 524        # right column x


def draw_substory(px, x, y, headline, body, art):
    draw_lines(px, x, y, wrap_text(headline, 3, COLW), 3, INK, 5)
    art(px, x, y + 58, COLW, 62)
    draw_lines(px, x, y + 128, wrap_text(body, 2, COLW)[:2], 2, INK, 5)


def build_page():
    px = new_canvas()

    # masthead
    draw_text_centered(px, W // 2, 22, "THE WORLD", 13, INK)
    hline(px, M, 118, CW, INK, 2)
    draw_text(px, M, 126, "FRIDAY, 20 NOVEMBER 2026", 2, INK)
    draw_text_right(px, W - M, 126, "PRICE: FREE", 2, INK)
    hline(px, M, 146, CW, INK, 4)

    # lead headline, centred
    lead_lines = wrap_text("TRUMP, XI AND PUTIN MEET IN SHENZHEN", 5, CW)
    for i, ln in enumerate(lead_lines):
        draw_text_centered(px, W // 2, 158 + i * 41, ln, 5, INK)

    # lead illustration
    draw_lead_art(px, M, 244, CW, 210)

    # lead body
    lead_body = (
        "THE THREE LEADERS HELD A HISTORIC TRILATERAL SUMMIT ON THE APEC "
        "SIDELINES. UKRAINE WAS THE PRIORITY, AND THEY ADOPTED A JOINT "
        "DECLARATION ON PEACE. THE NYT AND CNN CALL XI AND PUTIN THE "
        "WINNERS OF THE SUMMIT."
    )
    draw_lines(px, M, 464, wrap_text(lead_body, 2, CW)[:3], 2, INK, 5)

    hline(px, M, 524, CW, INK, 2)

    # sub-stories, row 1
    draw_substory(
        px, M, 534,
        "HOUTHI STRIKES HIT SAUDI ARABIA",
        "DRONES AND MISSILES HIT FOUR TARGETS, INCLUDING THE SADAF PLANT IN JUBAIL.",
        draw_houthi_art,
    )
    draw_substory(
        px, GAPX, 534,
        "ANTHROPIC SOARS ON NASDAQ DEBUT",
        "SHARES ROSE 17% ON DAY ONE TO ABOUT $97. THE LARGEST IPO EVER AT $81.3BN.",
        draw_anthropic_art,
    )
    vline(px, 510, 534, 158, GRAY, 1)

    hline(px, M, 699, CW, INK, 2)

    # sub-stories, row 2
    draw_substory(
        px, M, 709,
        "KYIV HIT BY FOUR BALLISTIC MISSILES",
        "STRIKES DISABLED THE KERCH BRIDGE AFTER NIGHT ATTACKS, HALTING TRAFFIC.",
        draw_kyiv_art,
    )
    draw_substory(
        px, GAPX, 709,
        "GENOA AIRPORT HALTED BY DRONES",
        "UNIDENTIFIED DRONES SHUT THE AIRPORT FOR FOUR HOURS OVERNIGHT.",
        draw_genoa_art,
    )
    vline(px, 510, 709, 158, GRAY, 1)

    hline(px, M, 874, CW, INK, 2)

    # ALSO TODAY strip
    draw_text(px, M, 884, "ALSO TODAY", 2, RED)
    today = [
        "EISENKOT TAPPED TO FORM ISRAEL'S NEXT GOVERNMENT, BYPASSING NETANYAHU",
        "AUSTRALIA, CANADA, ITALY AND THE UK URGE ISRAEL TO LET AID REACH FLOODED GAZA",
        "INDIA EVACUATES OVER 80,000 PEOPLE AS TROPICAL STORM DANA APPROACHES",
        "COP31 CLIMATE TALKS IN ANTALYA STRUGGLE AS THE FINAL DEADLINE NEARS",
        "US DETAILS $12BN IN VENEZUELAN OIL AND MINERAL REVENUE",
    ]
    for i, item in enumerate(today):
        yy = 906 + i * 17
        fill_rect(px, M, yy + 4, 6, 6, RED)
        draw_text(px, M + 14, yy, item, 2, INK)

    return px


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    px = build_page()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, px)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
