"""Raster pipeline: extract Colin's letters, draw designed glyphs, roughen, trace."""
import hashlib
import numpy as np
import cv2
from PIL import Image
from shapely.geometry import LineString, Polygon, MultiPolygon
from shapely.ops import unary_union
from skimage.morphology import remove_small_holes, remove_small_objects
import potrace

CAP = 480          # cap height in px (drawing scale = the photo's scale)
SMALLCAP = 372     # lowercase = small caps
STROKE = 45        # measured median marker width on the sign, px
K = 700.0 / CAP    # font units per px (cap height 700 / 1000 UPM)
P = 50             # canvas side padding px
YT = 680           # canvas rows above baseline
YB = 220           # canvas rows below baseline
SIDEBEARING = 22   # px each side of the ink


def seed_for(name):
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


# ---------------------------------------------------------------- extraction
def extract_letters(src_path):
    """Return {char: bool mask} for C L O S E D cut from the photo, normalised so
    the letter's height is CAP+8 px. Cleaned: blur, threshold, fill pinholes."""
    im = np.array(Image.open(src_path).convert("L")).astype(np.float32)
    b = cv2.GaussianBlur(im, (0, 0), 1.2)
    th = (b < 110).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(th, 8)
    big = [i for i in range(1, n) if st[i, 4] > 20000 and st[i, 1] < 400]
    big.sort(key=lambda i: st[i, 0])
    assert len(big) == 6, len(big)
    out = {}
    for i, ch in zip(big, "CLOSED"):
        x, y, w, h, _ = st[i]
        m = lab[y:y + h, x:x + w] == i
        m = remove_small_holes(m, max_size=400)
        scale = (CAP + 8) / h
        m2 = cv2.resize(m.astype(np.float32), (round(w * scale), round(h * scale)),
                        interpolation=cv2.INTER_LINEAR) > 0.5
        m2 = remove_small_holes(m2, max_size=400)
        out[ch] = m2
    return out


def place_mask(m, base_y=-4):
    """Put an extracted mask on a glyph canvas; returns canvas, ink width px."""
    h, w = m.shape
    canvas = np.zeros((YT + YB, w + 2 * P), bool)
    top = YT - (base_y + h)
    canvas[top:top + h, P:P + w] = m
    return canvas, w


# ---------------------------------------------------------------- skeletons
def _round_corners(pts, r, closed):
    if r <= 0 or len(pts) < 3:
        return pts
    pts = [np.array(p, float) for p in pts]
    n = len(pts)
    out = []
    rng = range(n) if closed else range(1, n - 1)
    if not closed:
        out.append(pts[0])
    for i in rng:
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        da, dc = a - b, c - b
        la, lc = np.linalg.norm(da), np.linalg.norm(dc)
        rr = min(r, la / 2, lc / 2)
        p0, p2 = b + da / la * rr, b + dc / lc * rr
        for t in np.linspace(0, 1, 9):
            out.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t ** 2 * p2)
    if not closed:
        out.append(pts[-1])
    return [tuple(p) for p in out]


def _densify(pts, closed, step=6.0):
    pts = list(pts) + ([pts[0]] if closed else [])
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.array(a), np.array(b)
        n = max(1, int(np.linalg.norm(b - a) / step))
        for t in np.arange(n) / n:
            out.append(a + (b - a) * t)
    out.append(np.array(pts[-1]))
    return np.array(out)


class Wobble:
    """Smooth hand-drawn wobble applied to skeleton points."""
    def __init__(self, seed, amp=4.0):
        r = np.random.default_rng(seed)
        self.terms = [(r.uniform(140, 480), r.uniform(0, 6.3), r.uniform(0.4, 1.0)) for _ in range(6)]
        self.amp = amp

    def __call__(self, P_):
        x, y = P_[:, 0], P_[:, 1]
        dx = sum(a * np.sin(y / wl * 6.283 + ph) for wl, ph, a in self.terms[:3])
        dy = sum(a * np.sin(x / wl * 6.283 + ph) for wl, ph, a in self.terms[3:])
        norm = sum(a for _, _, a in self.terms[:3])
        return P_ + self.amp * np.stack([dx, dy * 0.6], 1) / norm


def norm_to_px(strokes, w, h, s, yoff=0.0, xoff=0.0):
    """normalised strokes -> px strokes (y up from baseline)."""
    cw, ch = w - s, h - s
    res = []
    for pts, closed in strokes:
        res.append(([(xoff + s / 2 + u * cw, yoff + s / 2 + v * ch) for u, v in pts], closed))
    return res


def strokes_mask(px_strokes, canvas_w, s, seed, round_r=0, dots=(), dotside=None, wobble=6.0, hv=None):
    geoms = []
    wob = Wobble(seed, wobble)
    for pts, closed in px_strokes:
        pts = _round_corners(pts, round_r, closed) if round_r else pts
        d = wob(_densify(pts, closed))
        if hv:
            # up-and-down marker motion: horizontal strokes come out taller than
            # stems are wide. Width depends on each piece's direction.
            dd = np.vstack([d, d[:1]]) if closed else d
            for a, b in zip(dd[:-1], dd[1:]):
                v = b - a
                L = np.hypot(*v)
                if L < 1e-6:
                    continue
                c = abs(v[0]) / L  # 1 = horizontal
                ww = s * (hv[0] + (hv[1] - hv[0]) * c ** 1.5)
                geoms.append(LineString([a, b]).buffer(ww / 2, cap_style=3, join_style=2))
            continue
        if closed:
            g = Polygon(d).exterior.buffer(s / 2, join_style=2, mitre_limit=2.0)
        else:
            g = LineString(d).buffer(s / 2, cap_style=3, join_style=2, mitre_limit=2.2)
        geoms.append(g)
    side = dotside or s * 1.3
    for (x, y) in dots:
        x, y = wob(np.array([[x, y]]))[0]
        geoms.append(Polygon([(x - side / 2, y - side / 2), (x + side / 2, y - side / 2),
                              (x + side / 2, y + side / 2), (x - side / 2, y + side / 2)]))
    geom = unary_union(geoms) if geoms else None
    m = np.zeros((YT + YB, canvas_w), np.uint8)
    if geom is None or geom.is_empty:
        return m.astype(bool)
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    SH = 4
    def to_px(coords):
        a = np.array(coords)
        return np.round(np.stack([(a[:, 0] + P) * 16, (YT - a[:, 1]) * 16], 1)).astype(np.int32)
    for pg in polys:
        t = np.zeros_like(m)
        cv2.fillPoly(t, [to_px(pg.exterior.coords)], 1, lineType=cv2.LINE_8, shift=SH)
        for hole in pg.interiors:
            cv2.fillPoly(t, [to_px(hole.coords)], 0, lineType=cv2.LINE_8, shift=SH)
        m |= t
    return m.astype(bool)


# ---------------------------------------------------------------- roughening
def _sdf(m):
    m8 = m.astype(np.uint8)
    return cv2.distanceTransform(m8, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - m8, cv2.DIST_L2, 5)


def _field(rng, shape, sx, sy):
    f = cv2.GaussianBlur(rng.normal(size=shape).astype(np.float32), (0, 0), sigmaX=sx, sigmaY=sy)
    return f / (f.std() + 1e-6)


def noise_field(shape, seed, hi=4.2, mid=1.4, lo=2.6):
    rng = np.random.default_rng(seed)
    def bumps(f):  # sparse outward blobs, smooth in between (like re-inked marker)
        return np.maximum(f - 0.35, 0) * 1.9 - 0.25
    return (hi * bumps(_field(rng, shape, 8.0, 3.6))          # horizontal marker ticks
            + 0.6 * hi * bumps(_field(rng, shape, 3.6, 8.0))  # vertical ticks on horizontal edges
            + mid * _field(rng, shape, 5.0, 5.0)
            + lo * _field(rng, shape, 28, 28))         # slow stroke-width wander


def roughen(clean, seed, offset=0.0, amount=1.0):
    f = _sdf(clean) + offset + amount * noise_field(clean.shape, seed)
    m = f > 0
    m = remove_small_objects(m, max_size=80)
    m = remove_small_holes(m, max_size=80)
    return m


def reweight_extracted(m, seed, offset):
    if offset == 0:
        return m
    f = _sdf(m) + offset + 0.8 * noise_field(m.shape, seed, hi=2.6, mid=1.2, lo=1.0)
    out = remove_small_holes(remove_small_objects(f > 0, max_size=80), max_size=80)
    return out


# ---------------------------------------------------------------- tracing
def trace(mask):
    """Trace a canvas mask -> list of contours, each a list of segments in font units:
    ('M', p) ('L', p) ('C', c1, c2, p)."""
    bm = potrace.Bitmap(~mask)
    plist = bm.trace(turdsize=20, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                     alphamax=1.0, opticurve=True, opttolerance=0.35)
    def fu(pt):
        return ((pt.x - P) * K, (YT - pt.y) * K)
    contours = []
    for curve in plist:
        c = [("M", fu(curve.start_point))]
        for seg in curve.segments:
            if seg.is_corner:
                c.append(("L", fu(seg.c)))
                c.append(("L", fu(seg.end_point)))
            else:
                c.append(("C", fu(seg.c1), fu(seg.c2), fu(seg.end_point)))
        contours.append(c)
    return contours
