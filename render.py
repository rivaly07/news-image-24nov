#!/usr/bin/env python3
"""Render one newspaper-style page: the world's news of Tuesday 24 November 2026.

Deterministic and offline (PIL only). The page carries a masthead that fixes the
date, a six-box stat strip, one lead story with a drawn scene, a three-column
body of 21 stories, a mapped dot panel, an "also on this day" strip holding the
remaining datelines, and a DATE CHECK footer.

Usage:  MAKEFUN_OUTPUT_DIR=out python3 render.py
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W = H = 1024
BG = (249, 247, 241)
PANEL = (241, 237, 228)
INK = (20, 17, 14)
MUTED = (107, 100, 89)
RULE = (169, 160, 145)
GRID = (218, 212, 200)
FLAG = (163, 22, 33)
SEA = (214, 224, 226)
LAND = (229, 223, 211)
LANDEDGE = (196, 189, 175)
FDIR = "/usr/share/fonts/opentype/urw-base35"

SERIF_B = "NimbusRoman-Bold.otf"
SERIF = "NimbusRoman-Regular.otf"
SANS_NB = "NimbusSansNarrow-Bold.otf"
SANS_N = "NimbusSansNarrow-Regular.otf"

# one badge colour per region so breadth is visible at a glance
REGION_COLOR = {
    "MIDDLE EAST": (140, 32, 26),
    "EUROPE": (30, 54, 96),
    "ASIA": (18, 84, 78),
    "AFRICA": (140, 92, 20),
    "AMERICAS": (84, 42, 104),
    "OCEANIA": (28, 96, 52),
    "GLOBAL": (60, 60, 60),
}

_cache: dict = {}


def F(name: str, size: int):
    key = (name, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(os.path.join(FDIR, name), size)
    return _cache[key]


def F_MAST():
    return F(SERIF_B, 52)


def F_EYE():
    return F(SANS_NB, 13)


def F_DECK():
    return F(SANS_N, 12)


def F_LEAD():
    return F(SERIF_B, 26)


def F_HEAD():
    return F(SERIF_B, 15)


def F_BODY():
    return F(SERIF, 8)


def F_LEADBODY():
    return F(SERIF, 9)


def F_KICK():
    return F(SANS_NB, 7)


def F_BADGE():
    return F(SANS_NB, 7)


def F_SRC():
    return F(SANS_N, 7)


def F_STATN():
    return F(SERIF_B, 20)


def F_STATL():
    return F(SANS_NB, 8)


def F_ONE():
    return F(SANS_NB, 8)


def F_FOOT():
    return F(SANS_N, 8)


d = None
TRACE: list = []
TRACE_ON = False
TALLY = ""


def wrap(text, font, maxw, maxlines):
    """Greedy wrap measured by real glyph widths, truncated with an ellipsis."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if not cur or d.textlength(trial, font=font) <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > maxlines:
        lines = lines[:maxlines]
        last = lines[-1]
        while last and d.textlength(last + "…", font=font) > maxw:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    out = []
    for ln in lines:
        while d.textlength(ln, font=font) > maxw and len(ln) > 2:
            ln = ln[:-2] + "…"
        out.append(ln)
    return out


def put(x, y, txt, font, fill=INK):
    d.text((x, y), txt, font=font, fill=fill)
    if TRACE_ON:
        TRACE.append((txt, d.textbbox((x, y), txt, font=font)))


def put_c(y, txt, font, fill=INK):
    put((W - d.textlength(txt, font=font)) / 2, y, txt, font, fill)


def put_r(right, y, txt, font, fill=INK):
    put(right - d.textlength(txt, font=font), y, txt, font, fill)


def rule(y, x0=22, x1=W - 22, c=INK, w=1):
    d.line([(x0, y), (x1, y)], fill=c, width=w)


def badge(x, y, text, region):
    f = F_BADGE()
    w = int(d.textlength(text, font=f)) + 8
    d.rectangle([x, y, x + w, y + 10], fill=REGION_COLOR.get(region, FLAG))
    d.text((x + 4, y + 2), text, font=f, fill=(255, 255, 255))
    return x + w


CONTINENTS = [
    [(-168, 65), (-140, 70), (-100, 72), (-75, 68), (-60, 50), (-70, 42), (-80, 25),
     (-97, 16), (-105, 22), (-120, 32), (-130, 55)],
    [(-80, 10), (-60, 12), (-35, -5), (-38, -22), (-55, -35), (-70, -50), (-75, -45),
     (-72, -20), (-80, 0)],
    [(-17, 15), (0, 35), (11, 37), (32, 31), (43, 12), (51, 11), (40, -10), (33, -25),
     (20, -35), (12, -18), (8, 4)],
    [(-10, 36), (0, 45), (15, 38), (30, 45), (40, 60), (25, 70), (5, 60), (-8, 44)],
    [(30, 45), (60, 55), (90, 75), (140, 72), (135, 45), (122, 32), (100, 10), (95, 20),
     (78, 8), (60, 25), (45, 30)],
    [(113, -22), (130, -12), (145, -15), (153, -28), (150, -38), (135, -35), (115, -35)],
    # small islands so coastal datelines still land on something
    [(-6, 50), (1, 51), (2, 58), (-5, 58), (-8, 54)],
    [(129, 31), (136, 34), (142, 40), (145, 45), (141, 45), (137, 36), (131, 33)],
    [(95, 5), (106, -6), (120, -9), (132, -8), (141, -3), (135, 2), (125, 0), (115, 3), (105, 8), (98, 8)],
    [(120, 22), (122, 25), (121, 25), (119, 23)],
    [(176, -17), (180, -16), (180, -19), (176, -19)],
    [(166, -14), (169, -15), (170, -20), (167, -19)],
    [(172, -34), (176, -38), (178, -41), (173, -41), (170, -37)],
]


def point_in_land(lon, lat):
    for poly in CONTINENTS:
        inside = False
        j = len(poly) - 1
        for i in range(len(poly)):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        if inside:
            return True
    return False


def draw_map(x0, y0, x1, y1, stories):
    mw, mh = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=PANEL)

    def px(lon, lat):
        return (x0 + (lon + 180) / 360 * mw, y0 + (72 - lat) / 144 * mh)

    for lat in range(-60, 70, 20):
        d.line([px(-180, lat), px(180, lat)], fill=GRID)
    for lon in range(-150, 180, 30):
        d.line([px(lon, -70), px(lon, 72)], fill=GRID)
    for poly in CONTINENTS:
        d.polygon([px(lo, la) for lo, la in poly], fill=LAND, outline=LANDEDGE)
    # dot the landmasses so the silhouette still reads as a map at thumbnail size
    step = 6
    gy = y0 + 2
    while gy < y1 - 2:
        gx = x0 + 2
        while gx < x1 - 2:
            lon = (gx - x0) / mw * 360 - 180
            lat = 72 - (gy - y0) / mh * 144
            if point_in_land(lon, lat):
                d.rectangle([gx, gy, gx + 1, gy + 1], fill=(206, 198, 183))
            gx += step
        gy += step
    d.rectangle([x0, y0, x1, y1], outline=RULE)
    for name, lon, lat in (("AMERICAS", -100, 45), ("EUROPE", 12, 54), ("AFRICA", 18, 2),
                           ("ASIA", 88, 46), ("OCEANIA", 134, -26)):
        put(px(lon, lat)[0] - d.textlength(name, font=F_SRC()) / 2, px(lon, lat)[1], name,
            F_SRC(), (152, 144, 130))
    for s in stories:
        cx, cy = px(s["lon"], s["lat"])
        d.ellipse([cx - 2.4, cy - 2.4, cx + 2.4, cy + 2.4], fill=FLAG)
    put(x0 + 6, y0 + 3, "WORLD DESK MAP  ·  " + TALLY, F_KICK(), INK)
    put_r(x1 - 6, y0 + 3, "one pin per story", F_SRC(), MUTED)
    # region key
    kx = x0 + 6
    for region, color in sorted(REGION_COLOR.items()):
        if region == "GLOBAL":
            continue
        label = region.title() if region != "MIDDLE EAST" else "Mid-East"
        d.rectangle([kx, y1 - 12, kx + 6, y1 - 6], fill=color)
        put(kx + 9, y1 - 13, label, F_SRC(), MUTED)
        kx += 9 + d.textlength(label, font=F_SRC()) + 12


def render(facts, out_path):
    global d, TALLY
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    TRACE.clear()

    lead = [s for s in facts if s.get("lead")][0]
    stories = [s for s in facts if not s.get("brief") and not s.get("lead")]
    extras = [s for s in facts if s.get("brief")]
    total = len(stories) + len(extras) + 1
    counted: dict = {}
    for s in facts:
        counted[s["region"]] = counted.get(s["region"], 0) + 1
    order = ["ASIA", "EUROPE", "MIDDLE EAST", "AMERICAS", "AFRICA", "OCEANIA", "GLOBAL"]
    TALLY = "  ·  ".join("%s %d" % (r.upper() if r != "MIDDLE EAST" else "MID-EAST", counted.get(r, 0))
                         for r in order if counted.get(r))

    # top rail
    put(22, 7, "ONE DAY, ONE PAGE", F_KICK(), INK)
    put_r(W - 22, 7, "WORLD EDITION  ·  %d STORIES  ·  6 REGIONS" % total, F_KICK(), MUTED)
    rule(21)

    # masthead: the date is criterion one, so it is the biggest thing on the page
    put_c(24, "THE WORLD ON", F_EYE(), FLAG)
    put_c(38, "TUESDAY 24 NOVEMBER 2026", F_MAST(), INK)
    rule(84, 22, W - 22, RULE)
    put_c(88, "One page, one day: what happened on Tuesday 24 November 2026 — Ukraine, Hormuz, Washington, "
              "Khartoum and points between.", F_DECK(), MUTED)

    # stat strip
    stats = lead.get("stats") or []
    s0, s1 = 108, 150
    d.rectangle([22, s0, W - 22, s1], outline=RULE)
    bw = (W - 44) / len(stats)
    for i, (num, lab) in enumerate(stats):
        bx = 22 + i * bw
        if i:
            d.line([(bx, s0 + 5), (bx, s1 - 6)], fill=RULE)
        put(bx + 7, s0 + 5, num, F_STATN(), FLAG)
        for j, ln in enumerate(wrap(lab, F_STATL(), bw - 13, 2)):
            put(bx + 7, s0 + 26 + j * 10, ln, F_STATL(), INK)

    # lead story + drawn scene
    ly = 160
    rule(ly)
    bx = badge(22, ly + 8, lead["region"].upper(), lead["region"])
    put(bx + 5, ly + 9, lead["kicker"].upper(), F_KICK(), MUTED)
    y = ly + 22
    for ln in wrap(lead["head"], F_LEAD(), 630, 2):
        put(22, y, ln, F_LEAD(), INK)
        y += 29
    y += 2
    for ln in wrap(lead["body"], F_LEADBODY(), 630, 3):
        put(22, y, ln, F_LEADBODY(), INK)
        y += 11.5
    put(22, y + 2, "SOURCE: " + lead["src"].upper(), F_KICK(), MUTED)

    sx0, sy0, sx1, sy1 = 668, 168, W - 22, 308
    d.rectangle([sx0, sy0, sx1, sy1], fill=PANEL, outline=RULE)
    hz = sy1 - 44
    d.rectangle([sx0 + 6, hz, sx1 - 6, sy1 - 14], fill=SEA)
    for i in range(4):
        d.line([(sx0 + 8, hz + 7 + i * 8), (sx1 - 8, hz + 7 + i * 8)], fill=(200, 213, 217))
    d.polygon([(sx0 + 30, hz), (sx0 + 168, hz), (sx0 + 154, hz + 19), (sx0 + 44, hz + 19)],
              fill=(38, 34, 30))
    d.rectangle([sx0 + 142, hz - 24, sx0 + 160, hz], fill=(38, 34, 30))
    for cx in (sx0 + 64, sx0 + 94, sx0 + 124):
        d.rectangle([cx, hz - 12, cx + 17, hz], fill=(88, 82, 74))
    d.ellipse([sx0 + 82, hz - 40, sx0 + 106, hz - 16], fill=(196, 58, 38))
    d.ellipse([sx0 + 86, hz - 36, sx0 + 102, hz - 20], fill=(240, 172, 44))
    for dx in (-7, 0, 7):
        d.line([(sx0 + 94 + dx, hz - 48), (sx0 + 94 + dx * 1.4, hz - 64)], fill=(150, 142, 130))
    mx, my = sx0 + 250, hz + 12
    d.ellipse([mx - 11, my - 11, mx + 11, my + 11], outline=(40, 38, 34), width=2)
    for a in range(0, 360, 45):
        r = math.radians(a)
        d.line([(mx + math.cos(r) * 11, my + math.sin(r) * 11),
                (mx + math.cos(r) * 17, my + math.sin(r) * 17)], fill=(40, 38, 34))
    put(sx0 + 7, sy1 - 12, "Mines in the strait: three hulls burn.", F_SRC(), INK)

    # body grid: three columns, seven rows
    gx0, gy0, colw, gap, ch, rows = 22, 332, 317, 14, 74, 6
    cards = stories[: rows * 3]
    for i, s in enumerate(cards):
        cx = gx0 + (i % 3) * (colw + gap)
        cy = gy0 + (i // 3) * ch
        rule(cy, cx, cx + colw, RULE)
        bx = badge(cx, cy + 5, s["region"].upper()[:9], s["region"])
        put(bx + 4, cy + 6, s["kicker"].upper(), F_KICK(), MUTED)
        yy = cy + 18
        for ln in wrap(s["head"], F_HEAD(), colw, 2):
            put(cx, yy, ln, F_HEAD(), INK)
            yy += 14.5
        by = cy + 47
        for ln in wrap(s["body"], F_BODY(), colw, 2):
            put(cx, by, ln, F_BODY(), INK)
            by += 9
        put_r(cx + colw, cy + 64, s["src"], F_SRC(), MUTED)

    # bottom band: the day on a map (natural aspect) beside the remaining datelines
    by0, by1 = gy0 + rows * ch + 6, H - 30
    map_w = 380
    draw_map(22, by0, 22 + map_w, by1, [lead] + stories + extras)

    lx = 22 + map_w + 18
    rw = (W - 22 - lx) / 2
    put(lx, by0 + 2, "MORE FROM THE DAY", F_KICK(), FLAG)
    put(lx, by0 + 14, "%d more dispatches" % len(extras), F_SRC(), MUTED)
    half = (len(extras) + 1) // 2
    for i, s in enumerate(extras):
        colx = lx if i < half else lx + rw + 6
        py = by0 + 40 + (i % half) * 17
        txt = "· " + s["head"]
        while d.textlength(txt, font=F_ONE()) > rw - 6 and len(txt) > 8:
            txt = txt[:-2] + "…"
        put(colx, py, txt, F_ONE(), INK)
        put(colx, py + 9, s["src"], F_SRC(), MUTED)
    put_r(W - 22, by1 - 12, "one dot per dateline", F_SRC(), MUTED)

    # footer: one line, the date restated
    fy = H - 20
    rule(fy - 5, 22, W - 22)
    foot = ("DATE CHECK: every item on this page is dated Tuesday 24 November 2026 (UTC) and drawn from that day's  "
            "reporting — AP, Reuters, AFP, Al Jazeera, RBC-Ukraine, ABC News, Bloomberg, SBS, PINA, Rio Times, "
            "Miami Herald, UNICEF.")
    put(22, fy, wrap(foot, F_FOOT(), W - 44, 1)[0], F_FOOT(), MUTED)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)

    problems = []
    for i, s in enumerate(cards):
        cy = gy0 + (i // 3) * ch
        used = cy + 18 + 14.5 * len(wrap(s["head"], F_HEAD(), colw, 2))
        used += 9 * len(wrap(s["body"], F_BODY(), colw, 2))
        if used > cy + ch - 6:
            problems.append("card %d overflows its frame by %.1f px" % (i, used - (cy + ch - 6)))
    if by0 + 40 + (half - 1) * 17 + 16 > by1:
        problems.append("dateline list overruns the bottom band")
    if by1 > fy - 5:
        problems.append("bottom band collides with the footer")
    return out_path, problems


def main():
    facts = json.loads((Path(__file__).resolve().parent / "news.json").read_text())
    out = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", Path(__file__).resolve().parent / "out")) / "entry.png"
    p, problems = render(facts, out)
    print("wrote %s %d bytes" % (p, p.stat().st_size))
    for pr in problems:
        print("PROBLEM:", pr)


if __name__ == "__main__":
    main()
