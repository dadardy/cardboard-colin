"""Simulated marker: fill a stroke shape with vertical up-and-down passes of a
round nib, the way Colin filled his CLOSED sign. Edge texture comes only from
where each pass turns around (scallops on top/bottom edges, straight-ish sides
on stems), never from random edge noise."""
import numpy as np
import cv2
from skimage.morphology import skeletonize, remove_small_holes

SS = 2  # supersampling for nib rasterisation


def smooth_shape(mask, sigma=5.0):
    """Remove the photo's existing texture, keep the letter's hand-drawn form."""
    f = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)
    return f > 0.5


def offset_shape(mask, px):
    """Grow (+) or shrink (-) a smooth shape by px (shape-level, before inking)."""
    if px == 0:
        return mask
    m8 = mask.astype(np.uint8)
    sdf = cv2.distanceTransform(m8, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - m8, cv2.DIST_L2, 5)
    return sdf + px > 0


def ink(shape, seed, nib, spacing=None, overshoot=None, jitter=None):
    """shape: bool canvas. nib: nib diameter px. Returns bool canvas of ink."""
    rng = np.random.default_rng(seed)
    r = nib / 2.0
    spacing = spacing or max(2.0, nib * 0.28)
    overshoot = nib * 0.26 if overshoot is None else overshoot   # pen turn-around past the edge
    jitter = nib * 0.26 if jitter is None else jitter
    m8 = shape.astype(np.uint8)
    # nib centre must stay inside the shape: erode by r
    dt = cv2.distanceTransform(m8, cv2.DIST_L2, 5)
    core = dt >= r * 0.92
    # strokes thinner than the nib still get a pass down their middle
    sk = skeletonize(shape)
    k = int(np.ceil(spacing)) + 2
    core |= cv2.dilate(sk.astype(np.uint8), np.ones((1, k), np.uint8)).astype(bool) & shape
    H, W = shape.shape
    # how horizontal the outline is at each point: turn-around texture is strong on
    # horizontal edges and fades on diagonals (keeps slanted strokes clean)
    bl = cv2.GaussianBlur(shape.astype(np.float32), (0, 0), 3.0)
    gx, gy = np.abs(cv2.Sobel(bl, cv2.CV_32F, 1, 0)), np.abs(cv2.Sobel(bl, cv2.CV_32F, 0, 1))
    horiz = gy / (gx + gy + 1e-6)
    def hfac(y, x):
        y = int(np.clip(y, 0, H - 1)); x = int(np.clip(x, 0, W - 1))
        return float(horiz[y, x]) ** 2
    out = np.zeros((H * SS, W * SS), np.uint8)
    cols = np.where(core.any(0))[0]
    if len(cols) == 0:
        # shape thinner than the nib: just dab along its skeleton
        return shape.copy()
    x0, x1 = cols.min(), cols.max()
    n = int(np.floor((x1 - x0) / spacing)) + 1
    xs = np.linspace(x0, x1, max(n, 1)) if n > 1 else np.array([(x0 + x1) / 2.0])
    # slow wander so neighbouring passes turn around at similar heights (clustered bumps)
    slow = cv2.GaussianBlur(rng.normal(size=(1, len(xs) + 8)).astype(np.float32), (0, 0), 2.5)[0, 4:4 + len(xs)]
    slow = slow / (slow.std() + 1e-6)
    for i, x in enumerate(xs):
        xi = int(round(x))
        col = core[:, xi]
        if not col.any():
            continue
        d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0] - 1
        up = (i % 2 == 0)
        for ys, ye in zip(starts, ends):
            # pen goes up on even passes, down on odd: turn-around overshoot alternates ends
            ht, hb = hfac(ys - r, xi), hfac(ye + r, xi)
            top = ys - ht * ((overshoot if up else overshoot * 0.25) + abs(rng.normal(0, jitter)) + slow[i] * jitter * 0.8)
            bot = ye + hb * ((overshoot if not up else overshoot * 0.25) + abs(rng.normal(0, jitter)) + slow[i] * jitter * 0.8)
            xx = x + rng.normal(0, nib * 0.005)
            rr = r
            p1 = (int(round(xx * SS)), int(round(top * SS)))
            p2 = (int(round(xx * SS)), int(round(bot * SS)))
            cv2.line(out, p1, p2, 1, thickness=max(1, int(round(2 * rr * SS))), lineType=cv2.LINE_8)
    small = cv2.resize(out.astype(np.float32), (W, H), interpolation=cv2.INTER_AREA) > 0.5
    # the passes overlap and the ink bleeds: interior and stem sides are solid,
    # only the turn-arounds stick out past the stroke edge
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(nib * 0.7) | 1, int(nib * 0.7) | 1))
    solid = cv2.morphologyEx(shape.astype(np.uint8), cv2.MORPH_OPEN, disk).astype(bool)
    small |= solid
    small = remove_small_holes(small, max_size=int(nib * nib * 1.2))
    return small
