"""Regenerate the website's social preview image and favicons from the built fonts."""
from PIL import Image, ImageDraw, ImageFont
CARD, INK = (201, 164, 115), (28, 26, 30)
F = lambda w, s: ImageFont.truetype(f"fonts/ttf/CardboardColin-{w}.ttf", s)

im = Image.new("RGB", (1200, 630), CARD); d = ImageDraw.Draw(im)
for x in range(0, 1200, 9):
    d.line([(x, 0), (x, 630)], fill=(193, 156, 107), width=2)
d.text((70, 60), "CARDBOARD", font=F("Bold", 190), fill=INK)
d.text((70, 250), "COLIN", font=F("Bold", 190), fill=INK)
d.text((75, 460), "A free hand-drawn marker font,", font=F("Regular", 54), fill=INK)
d.text((75, 530), "straight off a CLOSED sign.", font=F("Regular", 54), fill=INK)
src = Image.open("source/closed-sign.png").convert("RGB"); src.thumbnail((430, 200))
x0 = 1200 - src.width - 60
im.paste(src, (x0, 300)); d.rectangle([x0 - 4, 296, 1200 - 56, 304 + src.height], outline=INK, width=4)
d.text((x0, 314 + src.height), "the original sign", font=F("Regular", 36), fill=INK)
im.save("assets/og-image.png", optimize=True)

big = Image.new("RGBA", (512, 512), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
d.rounded_rectangle([0, 0, 511, 511], radius=90, fill=CARD)
f = F("Bold", 400); bb = d.textbbox((0, 0), "CC", font=f)
s = min(420 / (bb[2] - bb[0]), 400 / (bb[3] - bb[1])); f = F("Bold", int(400 * s))
bb = d.textbbox((0, 0), "CC", font=f); w, h = bb[2] - bb[0], bb[3] - bb[1]
d.text(((512 - w) / 2 - bb[0], (512 - h) / 2 - bb[1]), "CC", font=f, fill=INK)
for size, name in [(512, "icon-512.png"), (180, "apple-touch-icon.png"), (32, "favicon-32.png")]:
    big.resize((size, size), Image.LANCZOS).save("assets/" + name)
big.save("favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("site assets written")
