"""Simulated marker squiggle, modelled on Colin's CLOSED sign.

Colin filled every stroke by scribbling the marker UP AND DOWN while moving
along the stroke. So for each stroke shape we drive a pen with a round nib:

* the pen makes vertical passes; each pass runs the full vertical extent of the
  stroke at that x position. On a horizontal bar that's a SHORT pass, on a
  vertical stem it's a LONG pass, on a diagonal it's in between (the vertical
  extent of a slanted band grows with its steepness);
* consecutive passes are joined by a short turn-around, making one continuous
  zig-zag path;
* the hand isn't a machine: pass spacing and how far each pass reaches vary
  (seeded per glyph and weight), so horizontals get uneven scalloped edges and,
  occasionally, a pass lands far enough from the last one that a sliver of
  cardboard shows through. Long passes (stems) vary much less.

The ink is the union of the nib swept along that path. No noise is added."""
import numpy as np
import cv2
from skimage.morphology import skeletonize, remove_small_holes

SS = 3  # supersampling for nib rasterisation


def smooth_shape(mask, sigma=5.0):
    """Remove the photo's existing texture, keep the letter's hand-drawn form."""
    f = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)
    return f > 0.5


def offset_shape(mask, px):
    if px == 0:
        return mask
    m8 = mask.astype(np.uint8)
    sdf = cv2.distanceTransform(m8, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - m8, cv2.DIST_L2, 5)
    return sdf + px > 0


def _runs(col):
    d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0] - 1))


def ink(shape, seed, nib, spacing=0.8, spacing_var=0.22, reach_var=0.30, gap_rate=0.07):
    """shape: bool canvas (the stroke outline). nib: marker line width in px."""
    rng = np.random.default_rng(seed)
    r = nib / 2.0
    H, W = shape.shape
    dt = cv2.distanceTransform(shape.astype(np.uint8), cv2.DIST_L2, 5)
    core = dt >= r * 0.7                        # where the nib centre may travel
    sk = skeletonize(shape)                     # thin parts still get a pass
    core |= cv2.dilate(sk.astype(np.uint8), np.ones((1, max(3, int(nib))), np.uint8)).astype(bool) & shape
    core = cv2.morphologyEx(core.astype(np.uint8), cv2.MORPH_OPEN,
                            np.ones((max(3, int(nib * 0.6)), 1), np.uint8)).astype(bool)
    cols = np.where(core.any(0))[0]
    out = np.zeros((H * SS, W * SS), np.uint8)
    if len(cols) == 0:
        return shape.copy()
    thick = max(1, int(round(nib * SS)))

    def seg(p, q):
        cv2.line(out, (int(round(p[0] * SS)), int(round(p[1] * SS))),
                 (int(round(q[0] * SS)), int(round(q[1] * SS))), 1, thickness=thick, lineType=cv2.LINE_8)

    def runs_at(x):
        return _runs(core[:, int(round(min(max(x, 0), W - 1)))])

    # 1. where the hand puts each pass (x positions), with occasional wide steps
    xs, joined = [float(cols.min())], [False]
    while xs[-1] < cols.max():
        x = xs[-1]
        rs = runs_at(x)
        short_only = all((ye - ys) < 2.2 * nib for ys, ye in rs)
        step = nib * spacing * (1 + rng.normal(0, spacing_var))
        j = True
        ahead = [runs_at(x + nib * k) for k in (1.5, 2.5, 3.5)]
        far_from_end = all(a and all((ye2 - ys2) < 2.2 * nib for ys2, ye2 in a) for a in ahead)
        after_stem = any((ye - ys) >= 2.2 * nib for ys, ye in runs_at(x - nib))
        if rs and short_only and far_from_end and not after_stem and rng.random() < gap_rate:
            step, j = nib * rng.uniform(1.08, 1.3), False   # lands wide: cardboard shows
        xs.append(x + float(np.clip(step, nib * 0.35, nib * 1.35)))
        joined.append(j)
    xs[-1] = min(xs[-1], float(cols.max()))

    # 2. the body of each stroke between the pass ends (the passes overlap, so the
    #    middle of a stroke is solid ink); only its top/bottom faces get eroded,
    #    so stem sides stay as straight as Colin drew them and every horizontal
    #    edge is made by pass turn-arounds. Wide steps leave a cardboard sliver.
    e = max(1, int(round(r * 0.9)))
    body = cv2.erode(shape.astype(np.uint8), np.ones((2 * e + 1, 1), np.uint8)).astype(bool)
    for xa, xb, j in zip(xs[:-1], xs[1:], joined[1:]):
        if j:
            continue
        lo, hi = int(np.ceil(xa + r * 0.98)), int(np.floor(xb - r * 0.98))
        kind = rng.choice(["through", "top", "bottom"], p=[0.4, 0.3, 0.3])
        for c in range(max(lo, 0), min(hi, W - 1) + 1):
            for ys, ye in _runs(body[:, c]):
                cut = int(ys + (ye - ys) * 0.6)
                if kind == "through":
                    body[ys:ye + 1, c] = False
                elif kind == "top":
                    body[ys:cut, c] = False
                else:
                    body[ye - (cut - ys):ye + 1, c] = False
    # 3. drive the pen: continuous up/down zig-zag
    prev, going_up, slow = [], True, 0.0
    def passes(x, going_up, slow, conn_prev):
        cur = []
        for ys, ye in runs_at(x):
            L = ye - ys + nib                        # vertical extent of the stroke here
            longp = L > 3.0 * nib
            var = reach_var * (0.25 if longp else 1.0)
            dtop = r * (rng.normal(0.0, var) + 0.35 * var * slow)   # + past / - short of edge
            dbot = r * (rng.normal(0.0, var) - 0.35 * var * slow)
            top, bot = ys - dtop, ye + dbot
            drift = rng.normal(0, nib * (0.06 if longp else 0.03))
            a, b = (x - drift / 2, bot), (x + drift / 2, top)
            if not going_up:
                a, b = b, a
            seg(a, b)
            for (pt, pb, pa, pz) in conn_prev:   # turn-around joining the previous pass
                if min(pb, ye) - max(pt, ys) > -nib * 0.3 and abs(pz[1] - a[1]) < 1.2 * nib:
                    yj = min(pz[1], a[1]) + r * 0.35 if not going_up else max(pz[1], a[1]) - r * 0.35
                    if not going_up:
                        yj = max(min(pz[1], a[1]), yj)
                    seg((pz[0], yj), (a[0], yj))
                    break
            cur.append((ys, ye, a, b))
        return cur
    for x, j in zip(xs, joined):
        slow = 0.7 * slow + 0.3 * rng.normal()      # neighbouring passes reach alike
        prev = passes(x, going_up, slow, prev if j else [])
        going_up = not going_up
    ink_ = cv2.resize(out.astype(np.float32), (W, H), interpolation=cv2.INTER_AREA) > 0.5
    # the nib only overshoots along its travel (up/down), never out of a stem's side
    clip = cv2.dilate(shape.astype(np.uint8), np.ones((int(nib * 1.2) | 1, 3), np.uint8)).astype(bool)
    ink_ = (ink_ & clip) | body
    ink_ = remove_small_holes(ink_, max_size=int(0.3 * nib * nib))   # no pinprick specks
    return ink_
