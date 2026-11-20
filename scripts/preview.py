"""Quick raster preview: python scripts/preview.py Regular C,L,O,S,E,D,A,B out.png"""
import sys, numpy as np
from PIL import Image
sys.path.insert(0, "scripts")
from glyphs import build_masks
weight, names, out = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
ms = build_masks(weight, only=set(names))
parts = []
for n in names:
    m = ms[n]; c = np.where(m.any(0))[0]
    parts.append(m[:, max(c.min() - 14, 0): c.max() + 14])
img = np.concatenate(parts, 1)
Image.fromarray(np.where(img, 0, 255).astype(np.uint8)).save(out)
