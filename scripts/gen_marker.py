"""
Generates a high-contrast, feature-rich, asymmetric marker image for
MindAR image tracking, sized for a 7in square card printed at 300 DPI.

Good AR markers need: lots of local contrast/corners, no repeating
symmetric pattern (so orientation is unambiguous), and no large flat
areas. MindAR converts the marker to grayscale before extracting
features, so color carries no tracking information — this version is
pure black/white/gray so it prints correctly on a monochrome printer
without losing any contrast a color printer would have preserved.
"""
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont

random.seed(42)
np.random.seed(42)

DPI = 300
SIZE_IN = 7
PX = DPI * SIZE_IN  # 2100

# Voronoi-style cell texture in low-res grayscale, upscaled for crisp cell edges.
GRID = 260
n_points = 140
pts = np.random.rand(n_points, 2) * GRID
vals = np.random.randint(20, 236, size=n_points)  # grayscale value per cell

yy, xx = np.mgrid[0:GRID, 0:GRID]
coords = np.stack([xx, yy], axis=-1).reshape(-1, 2).astype(np.float32)

# nearest-point assignment (chunked to keep memory sane)
nearest_val = np.zeros(coords.shape[0], dtype=np.uint8)
chunk = 20000
for i in range(0, coords.shape[0], chunk):
    c = coords[i:i + chunk]
    d = ((c[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
    idx = d.argmin(axis=1)
    nearest_val[i:i + chunk] = vals[idx]

grid_img = nearest_val.reshape(GRID, GRID)
img = Image.fromarray(grid_img, mode="L").resize((PX, PX), Image.NEAREST)
img = img.convert("RGB")

draw = ImageDraw.Draw(img)

# Thin dark cell-boundary lines for extra corner features (recompute nearest at grid res, find edges)
edges = np.zeros_like(grid_img, dtype=bool)
edges[1:, :] |= grid_img[1:, :] != grid_img[:-1, :]
edges[:, 1:] |= grid_img[:, 1:] != grid_img[:, :-1]
edge_img = Image.fromarray((edges * 255).astype(np.uint8), mode="L").resize((PX, PX), Image.NEAREST)
edge_np = np.array(edge_img)
base_np = np.array(img)
base_np[edge_np > 0] = [10, 10, 10]
img = Image.fromarray(base_np, mode="RGB")
draw = ImageDraw.Draw(img)

# Asymmetric registration marks (different size/position each corner so
# orientation/scale is unambiguous to the tracker). Grayscale only —
# distinguished by size/position, not hue, so nothing is lost in B/W print.
margin = int(PX * 0.04)
corner_boxes = [
    (margin, margin, margin + 170, margin + 170, (15, 15, 15)),                      # top-left, larger, near-black
    (PX - margin - 110, margin, PX - margin, margin + 110, (15, 15, 15)),            # top-right, smaller, near-black
    (margin, PX - margin - 110, margin + 110, PX - margin, (15, 15, 15)),            # bottom-left, near-black
    (PX - margin - 150, PX - margin - 150, PX - margin, PX - margin, (15, 15, 15)),  # bottom-right, near-black
]
for (x0, y0, x1, y1, color) in corner_boxes:
    draw.rectangle([x0, y0, x1, y1], fill=color)
    draw.rectangle([x0, y0, x1, y1], outline=(255, 255, 255), width=6)

# Off-center accent shapes to break any residual symmetry.
draw.ellipse([PX * 0.55, PX * 0.15, PX * 0.78, PX * 0.38], fill=(210, 210, 210), outline=(10, 10, 10), width=8)
draw.polygon(
    [(PX * 0.18, PX * 0.62), (PX * 0.35, PX * 0.55), (PX * 0.40, PX * 0.78), (PX * 0.20, PX * 0.85)],
    fill=(60, 60, 60), outline=(10, 10, 10)
)

# Label band across the middle-bottom area for identification + more edge features.
band_h = int(PX * 0.09)
band_y0 = int(PX * 0.44)
draw.rectangle([0, band_y0, PX, band_y0 + band_h], fill=(255, 255, 255))
draw.rectangle([0, band_y0, PX, band_y0 + band_h], outline=(10, 10, 10), width=6)

label = "AR STHANAM · CARD MARKER 01"
font = None
for path in [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]:
    try:
        font = ImageFont.truetype(path, int(band_h * 0.5))
        break
    except Exception:
        continue
if font is None:
    font = ImageFont.load_default()

bbox = draw.textbbox((0, 0), label, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
draw.text(((PX - tw) / 2, band_y0 + (band_h - th) / 2 - bbox[1]), label, fill=(10, 10, 10), font=font)

out_path = "/Volumes/DT022/coding-space/Claude Code/AR Sthanam/assets/marker.png"
img.save(out_path, dpi=(DPI, DPI))
print("saved", out_path, img.size)
