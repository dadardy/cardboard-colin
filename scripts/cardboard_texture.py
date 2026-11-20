"""Seamless cardboard texture for the sign maker: assets/cardboard.jpg.
Periodic (FFT-filtered) noise, so it tiles without seams."""
import numpy as np
from PIL import Image

rng = np.random.default_rng(7)
W, H = 1024, 768

def periodic_noise(sx, sy):
    n = rng.normal(size=(H, W))
    fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None, :]
    filt = np.exp(-((fx * sx) ** 2 + (fy * sy) ** 2))
    out = np.real(np.fft.ifft2(np.fft.fft2(n) * filt))
    return (out - out.mean()) / out.std()

blotch = periodic_noise(60, 60)                 # broad tone variation
fibre = periodic_noise(160, 5)                 # long horizontal paper fibres (thin)
fibre2 = periodic_noise(50, 2.5)
grain = periodic_noise(1.2, 1.2)
x = np.arange(W)[None, :]
flute = np.sin(2 * np.pi * x / (W / 36)) * 0.5   # faint corrugation under the liner (36 per tile)
lum = 0.03 * blotch + 0.02 * fibre + 0.022 * fibre2 + 0.04 * grain + 0.014 * flute
specks = (periodic_noise(2.5, 2.5) > 3.1) * -0.18
lum = lum + specks
base = np.array([196, 158, 108], float) / 255
img = np.clip(base[None, None, :] * (1 + lum[..., None]) + 0.02 * fibre[..., None] * np.array([0.6, 0.3, 0.0]), 0, 1)
Image.fromarray((img * 255).astype(np.uint8)).save("assets/cardboard.jpg", quality=84, optimize=True, progressive=True)
print("assets/cardboard.jpg")
