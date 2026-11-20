"""Produce the final marker-inked raster for every glyph at a given weight.

Every glyph (Colin's six included) goes through the same two steps:
  1. a smooth stroke *shape* (designed skeleton widened to the weight's stroke
     width, or Colin's traced letter with its old texture smoothed away), then
  2. marker.ink(): vertical up-and-down passes of a round nib fill the shape.
Weights change the stroke width and nib size, never the texture recipe.
"""
import os
import numpy as np
from render import (CAP, SMALLCAP, P, YT, YB, seed_for, extract_letters, place_mask,
                    norm_to_px, strokes_mask)
from marker import ink, smooth_shape, offset_shape
from glyphdefs import LETTERS, DIGITS, SYMBOLS, ACCENTS, ACCENTED

EXTRACTED = "CLOSED"
LC_WIDTH = 0.9       # small caps are a touch narrower
LC_STROKE = 0.95

# stroke width px (at 480 px cap height), nib diameter px, offset for Colin's letters
WEIGHTS = {
    "Light":   dict(s=28, nib=14, colin=-8),
    "Regular": dict(s=42, nib=21, colin=1),
    "Bold":    dict(s=60, nib=30, colin=10),
}
HV = (0.86, 1.22)  # stem width factor, horizontal-stroke height factor
# Colin's L was drawn noticeably heavier than his other letters: slim it to match.
COLIN_EXTRA = {"L": -9}


def _unpack(d):
    w, strokes = d[0], d[1]
    opts = d[2] if len(d) > 2 else {}
    return w, strokes, opts


def designed_shape(name, w, strokes, opts, s, h=CAP):
    yoff = opts.get("yoff", 0)
    hh = opts.get("h", h)
    px = norm_to_px(strokes, w, hh, s, yoff)
    dots = []
    side = s * 1.3 * opts.get("dotscale", 1.0)
    for u, v in opts.get("dots", []):
        dots.append((s / 2 + u * (w - s), yoff + side / 2 + v * (hh - s)))
    return strokes_mask(px, w + 2 * P, s, seed_for(name), round_r=opts.get("round", 0),
                        dots=dots, dotside=side, wobble=5.0, hv=HV)


def accent_shape(name, accent, base_w, top, s):
    aw = max(base_w * 0.62, 95)
    x0 = (base_w - aw) / 2
    ah = 70
    y0 = top + 14 + 0.75 * s
    if ACCENTS[accent] == "dots2":
        side = s * 1.15
        half = max(aw * 0.3, side * 0.9)
        dots = [(base_w / 2 - half, y0 + side / 2), (base_w / 2 + half, y0 + side / 2)]
        return strokes_mask([], base_w + 2 * P, s, seed_for(name + accent), dots=dots, dotside=side, wobble=2)
    sa = s * 0.85
    px = []
    for pts, closed in ACCENTS[accent]:
        px.append(([(x0 + sa / 2 + u * (aw - sa), y0 + sa / 2 + v * (ah - sa)) for u, v in pts], closed))
    return strokes_mask(px, base_w + 2 * P, sa, seed_for(name + accent), wobble=2, hv=HV)


def build_masks(weight="Regular", only=None, return_shapes=False):
    W = WEIGHTS[weight]
    s, nib = W["s"], W["nib"]
    ext = extract_letters_cached()
    out = {}

    def want(n):
        return only is None or n in only

    base = {}  # name -> (ink mask, width, height)
    acc_bases = {a[0] for a in ACCENTED.values()}
    for ch, d in LETTERS.items():
        w, strokes, opts = _unpack(d)
        if want(ch) or ch in acc_bases:
            if ch in EXTRACTED:
                m, iw = place_mask(ext[ch])
                shape = offset_shape(smooth_shape(m), W["colin"] + COLIN_EXTRA.get(ch, 0))
            else:
                shape, iw = designed_shape(ch, w, strokes, opts, s), w
            base[ch] = (ink(shape, seed_for(ch), nib), iw, CAP)
        lc = ch.lower()
        if want(lc) or lc.upper() in acc_bases:
            lw = w if ch == "I" else round(w * LC_WIDTH)
            shape = designed_shape(lc, lw, strokes, opts, s * LC_STROKE, h=SMALLCAP)
            base[lc] = (ink(shape, seed_for(lc), nib * LC_STROKE), lw, SMALLCAP)
    for name, (m, iw, h) in base.items():
        if want(name):
            out[name] = m
    for name, d in list(DIGITS.items()) + list(SYMBOLS.items()):
        if not want(name):
            continue
        w, strokes, opts = _unpack(d)
        out[name] = ink(designed_shape(name, w, strokes, opts, s), seed_for(name), nib)
    for name, (b0, acc, _u) in ACCENTED.items():
        for nm, b in ((name, b0), (name[0].lower() + name[1:], b0.lower())):
            if not want(nm) or b not in base:
                continue
            m, iw, h = base[b]
            ss = s if b.isupper() else s * LC_STROKE
            a = accent_shape(nm, acc, iw, h, ss)
            out[nm] = m | ink(a, seed_for(nm + "acc"), nib * 0.8)
    return out


_EXT = None
def extract_letters_cached():
    global _EXT
    if _EXT is None:
        here = os.path.dirname(os.path.abspath(__file__))
        _EXT = extract_letters(os.path.join(here, "..", "source", "closed-sign.png"))
    return _EXT
