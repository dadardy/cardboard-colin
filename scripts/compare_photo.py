"""Photo crops of Colin's C L O S E D (top) vs the font's glyphs (rows below).
python scripts/compare_photo.py out.png [Weight ...]"""
import sys, os, numpy as np, cv2
from PIL import Image, ImageDraw
sys.path.insert(0, "scripts")
from render import CAP
from glyphs import build_masks

out = sys.argv[1]
weights = sys.argv[2:] or ["Regular"]
im = np.array(Image.open("source/closed-sign.png").convert("L")).astype(np.float32)
b = cv2.GaussianBlur(im, (0, 0), 1.2)
th = (b < 110).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(th, 8)
big = sorted([i for i in range(1, n) if st[i, 4] > 20000 and st[i, 1] < 400], key=lambda i: st[i, 0])
H = CAP + 60
def row_photo():
    tiles = []
    for i in big:
        x, y, w, h, _ = st[i]
        pad = 12
        crop = im[max(y - pad, 0):y + h + pad, max(x - pad, 0):x + w + pad]
        sc = (CAP + 8) / h
        crop = cv2.resize(crop, (round(crop.shape[1] * sc), round(crop.shape[0] * sc)), interpolation=cv2.INTER_AREA)
        t = np.full((H, crop.shape[1] + 30), 200, np.float32)
        y0 = (H - crop.shape[0]) // 2
        t[y0:y0 + crop.shape[0], 15:15 + crop.shape[1]] = crop
        tiles.append(t)
    return np.concatenate(tiles, 1)
def row_font(wt):
    ms = build_masks(wt, only=set("CLOSED"))
    tiles = []
    for ch in "CLOSED":
        m = ms[ch]; c = np.where(m.any(0))[0]; r = np.where(m.any(1))[0]
        m = m[r.min():r.max() + 1, c.min():c.max() + 1]
        t = np.full((H, m.shape[1] + 54), 200, np.float32)
        y0 = (H - m.shape[0]) // 2
        t[y0:y0 + m.shape[0], 27:27 + m.shape[1]][m] = 70
        tiles.append(t)
    return np.concatenate(tiles, 1)
rows = [("Colin's photo", row_photo())] + [(w, row_font(w)) for w in weights]
Wd = max(r.shape[1] for _, r in rows)
img = np.full((sum(r.shape[0] + 40 for _, r in rows), Wd), 255, np.float32)
y = 0
labels = []
for name, r in rows:
    labels.append((y, name)); img[y + 40:y + 40 + r.shape[0], :r.shape[1]] = r; y += r.shape[0] + 40
pil = Image.fromarray(img.astype(np.uint8)).convert("RGB")
d = ImageDraw.Draw(pil)
for yy, name in labels:
    d.text((10, yy + 10), name, fill=(0, 0, 0))
pil = pil.resize((pil.width // 2, pil.height // 2), Image.LANCZOS)
pil.save(out)
