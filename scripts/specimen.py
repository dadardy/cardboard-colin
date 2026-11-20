#!/usr/bin/env python3
"""Render specimen PNGs with Pillow from the built TTFs."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "specimen")
os.makedirs(OUT, exist_ok=True)
WEIGHTS = [w for w in ["Light", "Regular", "Bold"] if os.path.exists(os.path.join(ROOT, "fonts/ttf", f"CardboardColin-{w}.ttf"))]
INK, PAPER, CARD = (28, 26, 30), (250, 247, 240), (196, 160, 112)

def font(w, size):
    return ImageFont.truetype(os.path.join(ROOT, "fonts/ttf", f"CardboardColin-{w}.ttf"), size)

CHARSET = ["ABCDEFGHIJKLM", "NOPQRSTUVWXYZ", "abcdefghijklm", "nopqrstuvwxyz",
           "0123456789", ".,!?'\":;-–—_()[]{}", "&@#$%/\\|+−=×*<>^~`",
           "‘’“”‚„•·…¡¿©§¢£€¥«»°", "ÀÁÂÃÄÅÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ", "àáâãäåèéêëìíîïñòóôõöùúûüý"]
PANGRAM = "The quick brown fox jumps over the lazy dog."

def lines_img(lines, w, width=2000, pad=60, bg=PAPER):
    rows = []
    for text, size, wt in lines:
        f = font(wt, size)
        rows.append((text, f, int(size * 1.25)))
    H = sum(r[2] for r in rows) + 2 * pad
    im = Image.new("RGB", (width, H), bg)
    d = ImageDraw.Draw(im); y = pad
    for text, f, lh in rows:
        d.text((pad, y), text, font=f, fill=INK); y += lh
    return im

paths = []
for w in WEIGHTS:
    lines = [(f"Cardboard Colin {w}", 90, w)] + [(l, 110, w) for l in CHARSET] + [(PANGRAM, 70, w), (PANGRAM.upper(), 70, w)]
    p = os.path.join(OUT, f"charset-{w}.png"); lines_img(lines, w, width=2100).save(p); paths.append(p)

# CLOSED hero on cardboard
im = Image.new("RGB", (2000, 1300), CARD); d = ImageDraw.Draw(im)
y = 60
for w in WEIGHTS:
    d.text((80, y), "CLOSED", font=font(w, 330), fill=INK); y += 400
p = os.path.join(OUT, "closed.png"); im.save(p); paths.append(p)

# pangram per weight
lines = []
for w in WEIGHTS:
    lines += [(f"{w}: {PANGRAM}", 64, w), ("SORRY, WE'RE CLOSED! BACK AT 3:30 — 100% HANDMADE & PROUD.", 64, w), ("", 30, w)]
p = os.path.join(OUT, "pangram.png"); lines_img(lines, None, width=2200).save(p); paths.append(p)

# README hero
im = Image.new("RGB", (1600, 560), CARD); d = ImageDraw.Draw(im)
d.text((70, 40), "Cardboard Colin", font=font("Bold" if "Bold" in WEIGHTS else WEIGHTS[0], 200), fill=INK)
d.text((75, 300), "Hand-drawn marker type, straight off a CLOSED sign.", font=font("Regular", 66), fill=INK)
d.text((75, 400), "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789 !?&@", font=font("Regular", 66), fill=INK)
p = os.path.join(OUT, "hero.png"); im.save(p); paths.append(p)
print("\n".join(paths))
