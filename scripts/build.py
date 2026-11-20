#!/usr/bin/env python3
"""Build Cardboard Colin: TTF, OTF and WOFF2 for Light, Regular, Bold.

    python scripts/build.py            # all weights
    python scripts/build.py Regular    # one weight
"""
import os, sys, json
import numpy as np
import cv2
import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import trace, K, P, YT, SIDEBEARING
from glyphs import build_masks, WEIGHTS
from glyphdefs import UNICODES, ACCENTED, DIGITS

ROOT = os.path.join(HERE, "..")
FAMILY = "Cardboard Colin"
VERSION = "1.200"
COPYRIGHT = "Copyright 2026 Colin & Ryan"
UPM = 1000
ASC, DESC = 900, -250
SPACE = 210
WEIGHT_CLASS = {"Light": 300, "Regular": 400, "Bold": 700}

# ---------------------------------------------------------------- outlines
def contours_to_path(contours):
    path = pathops.Path()
    pen = path.getPen()
    for c in contours:
        for seg in c:
            if seg[0] == "M":
                pen.moveTo(seg[1])
            elif seg[0] == "L":
                pen.lineTo(seg[1])
            else:
                pen.curveTo(seg[1], seg[2], seg[3])
        pen.closePath()
    return path


def glyph_order_and_cmap():
    order = [".notdef", "space", "nbspace"]
    cmap = {0x20: "space", 0xA0: "nbspace"}
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        order.append(c); cmap[ord(c)] = c
    for c in "abcdefghijklmnopqrstuvwxyz":
        order.append(c); cmap[ord(c)] = c
    for name, u in UNICODES.items():
        if name not in order:
            order.append(name); cmap[u] = name
    for name, (_b, _a, u) in ACCENTED.items():
        lc = name[0].lower() + name[1:]
        order += [name, lc]
        cmap[u] = name
        cmap[u + 0x20] = lc
    return order, cmap


# ---------------------------------------------------------------- kerning
def profiles(mask, lsb_px, adv_px):
    """Left/right ink profiles per 8px band, relative to the glyph's advance box,
    with vertical dilation so nearby strokes count."""
    m = cv2.dilate(mask.astype(np.uint8), np.ones((41, 1), np.uint8)) > 0
    cols = np.where(m.any(0))[0]
    x0 = cols.min()
    rows = m.shape[0]
    L = np.full(rows, np.inf); R = np.full(rows, np.inf)
    for r in np.where(m.any(1))[0]:
        xs = np.where(m[r])[0]
        L[r] = (xs.min() - x0) + lsb_px
        R[r] = adv_px - ((xs.max() - x0) + lsb_px)
    return L, R


def auto_kern(masks, metrics, names):
    prof = {n: profiles(masks[n], metrics[n][1] / K, metrics[n][0] / K) for n in names if n in masks}
    ref = np.nanmin(prof["H"][1] + prof["H"][0])  # gap between two straight stems
    pairs = {}
    punct = {n for n in prof if not (len(n) == 1 or n in DIGITS or n[0].isalpha() and n not in UNICODES)}
    for a in prof:
        Ra = prof[a][1]
        for b in prof:
            if a in punct and b in punct:
                continue
            gap = np.min(Ra + prof[b][0])
            if not np.isfinite(gap):
                continue
            k = (ref - gap) * 0.55 * K
            k = max(k, -100)
            if k <= -18:
                pairs[(a, b)] = int(round(k / 5) * 5)
    return pairs


# ---------------------------------------------------------------- build
def build_weight(weight, outdir):
    masks = build_masks(weight)
    order, cmap = glyph_order_and_cmap()
    paths, metrics = {}, {}
    sb = SIDEBEARING * K
    for name in order:
        if name in (".notdef", "space", "nbspace"):
            continue
        path = contours_to_path(trace(masks[name]))
        path.simplify(fix_winding=True, keep_starting_points=False)
        bp = BoundsPen(None); path.draw(bp)
        xmin, ymin, xmax, ymax = bp.bounds
        shift = sb - xmin
        moved = pathops.Path()
        path.draw(TransformPen(moved.getPen(), (1, 0, 0, 1, shift, 0)))
        paths[name] = moved
        metrics[name] = (int(round(xmax - xmin + 2 * sb)), int(round(sb)))
    # .notdef box
    nd = pathops.Path(); p = nd.getPen()
    for rect in [((50, 0), (50, 700), (450, 700), (450, 0)), ((100, 50), (400, 50), (400, 650), (100, 650))]:
        p.moveTo(rect[0]); [p.lineTo(q) for q in rect[1:]]; p.closePath()
    paths[".notdef"] = nd; metrics[".notdef"] = (500, 50)
    for n in ("space", "nbspace"):
        paths[n] = pathops.Path(); metrics[n] = (SPACE, 0)

    KPUNCT = {"period", "comma", "ellipsis", "quotesingle", "quotedbl", "quoteleft", "quoteright",
              "quotedblleft", "quotedblright", "quotesinglbase", "quotedblbase", "hyphen",
              "parenleft", "parenright", "exclam", "question", "colon", "semicolon", "slash"}
    kern_names = [n for n in order if n not in (".notdef", "space", "nbspace")
                  and (n in KPUNCT or n not in UNICODES or n in DIGITS)]
    pairs = auto_kern(masks, metrics, kern_names)
    fea = "languagesystem DFLT dflt;\nlanguagesystem latn dflt;\nfeature kern {\n"
    fea += "".join(f"  pos {a} {b} {v};\n" for (a, b), v in sorted(pairs.items()))
    fea += "} kern;\n"

    ps_style = weight
    style_map = {"Light": ("Cardboard Colin Light", "Regular"), "Regular": (FAMILY, "Regular"), "Bold": (FAMILY, "Bold")}
    fam, sub = style_map[weight]
    psname = f"CardboardColin-{weight}"
    names = dict(
        copyright=COPYRIGHT, familyName=fam, styleName=sub,
        uniqueFontIdentifier=f"{VERSION};NONE;{psname}", fullName=f"{FAMILY} {weight}",
        psName=psname, version=f"Version {VERSION}",
        manufacturer="Colin & Ryan", designer="Colin (lettering) & Ryan",
        description="A shaky cardboard-sign marker font, grown from Colin's hand-drawn CLOSED sign.",
        vendorURL="https://github.com/dadardy/cardboard-colin",
        licenseDescription="This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org",
        licenseInfoURL="https://openfontlicense.org",
        typographicFamily=FAMILY, typographicSubfamily=weight,
    )
    os.makedirs(outdir, exist_ok=True)
    results = {}
    for flavor in ("ttf", "otf"):
        fb = FontBuilder(UPM, isTTF=(flavor == "ttf"))
        fb.setupGlyphOrder(order)
        fb.setupCharacterMap(cmap)
        if flavor == "ttf":
            glyphs = {}
            for n in order:
                q = paths[n]
                q2 = pathops.Path(); q.draw(q2.getPen())
                q2.simplify(fix_winding=True, clockwise=True) if n != ".notdef" else None
                tp = TTGlyphPen(None)
                q2.draw(Cu2QuPen(tp, max_err=1.0, reverse_direction=False))
                glyphs[n] = tp.glyph()
            fb.setupGlyf(glyphs)
        else:
            cs = {}
            for n in order:
                q2 = pathops.Path(); paths[n].draw(q2.getPen())
                if n != ".notdef":
                    q2.simplify(fix_winding=True, clockwise=False)
                pen = T2CharStringPen(metrics[n][0], None)
                q2.draw(pen)
                cs[n] = pen.getCharString()
            fb.setupCFF(psname, {"FullName": f"{FAMILY} {weight}", "FamilyName": fam,
                                 "Weight": weight, "Copyright": COPYRIGHT}, cs, {})
        lsbs = {}
        for n in order:
            bp = BoundsPen(None); paths[n].draw(bp)
            lsbs[n] = (metrics[n][0], int(round(bp.bounds[0])) if bp.bounds else 0)
        fb.setupHorizontalMetrics(lsbs)
        fb.setupHorizontalHeader(ascent=ASC, descent=DESC, lineGap=0)
        fb.setupNameTable(names)
        fs = {"Light": 0x40, "Regular": 0x40, "Bold": 0x20}[weight] | 0x80  # USE_TYPO_METRICS
        fb.setupOS2(usWeightClass=WEIGHT_CLASS[weight], usWidthClass=3, fsSelection=fs,
                    sTypoAscender=ASC, sTypoDescender=DESC, sTypoLineGap=0,
                    usWinAscent=1000, usWinDescent=320, sxHeight=int(372 * K), sCapHeight=700,
                    achVendID="NONE", fsType=0, version=4)
        fb.setupPost(isFixedPitch=0, underlinePosition=-150, underlineThickness=60)
        fb.font["head"].macStyle = 1 if weight == "Bold" else 0
        fb.font["head"].fontRevision = float(VERSION)
        addOpenTypeFeaturesFromString(fb.font, fea)
        fn = os.path.join(outdir, flavor, f"{psname}.{flavor}")
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        fb.save(fn)
        results[flavor] = fn
    # woff2 from the TTF
    f = TTFont(results["ttf"]); f.flavor = "woff2"
    wfn = os.path.join(outdir, "woff2", f"{psname}.woff2")
    os.makedirs(os.path.dirname(wfn), exist_ok=True)
    f.save(wfn)
    results["woff2"] = wfn
    results["kern_pairs"] = len(pairs)
    return results


if __name__ == "__main__":
    weights = sys.argv[1:] or list(WEIGHTS)
    for w in weights:
        r = build_weight(w, os.path.join(ROOT, "fonts"))
        print(w, json.dumps(r))
