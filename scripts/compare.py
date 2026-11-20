"""Before/after: v1.1 fonts (build/v11-fonts) vs current fonts, stacked per weight."""
import sys
from PIL import Image, ImageDraw, ImageFont
OLD, NEW = "build/v11-fonts", "fonts/ttf"
out = sys.argv[1] if len(sys.argv) > 1 else "specimen/before-after.png"
CARD, INK, PAPER, MUTED = (201, 164, 115), (28, 26, 30), (250, 246, 238), (110, 100, 90)
W, ROW = 1600, 300
im = Image.new("RGB", (W, 80 + 3 * (2 * ROW + 60)), PAPER); d = ImageDraw.Draw(im)
F = lambda folder, wt, sz: ImageFont.truetype(f"{folder}/CardboardColin-{wt}.ttf", sz)
d.text((40, 20), "Cardboard Colin: v1.1 (before) vs beta (after, zig-zag marker passes)", font=F(NEW, "Bold", 44), fill=INK)
y = 90
for wt in ["Light", "Regular", "Bold"]:
    for tag, folder in (("before", OLD), ("after", NEW)):
        d.rectangle([40, y, 700, y + ROW - 20], fill=CARD)
        d.text((60, y + 10), "CLOSED", font=F(folder, wt, 220), fill=INK)
        d.text((730, y + 20), "The quick brown fox", font=F(folder, wt, 64), fill=INK)
        d.text((730, y + 100), "jumps over the lazy dog.", font=F(folder, wt, 64), fill=INK)
        d.text((730, y + 190), f"{wt} · {tag}", font=F(NEW, "Regular", 38), fill=MUTED)
        y += ROW
    y += 60
im.save(out); print(out)
