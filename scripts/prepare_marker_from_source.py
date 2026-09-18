"""
Takes the user-supplied marker-source.jpg, center-crops it to a perfect
square, and resizes to 2100x2100px (7in @ 300 DPI) as assets/marker.png.
"""
from PIL import Image

ROOT = "/Volumes/DT022/coding-space/Claude Code/AR Sthanam"
SRC = f"{ROOT}/marker-source.jpg"
OUT = f"{ROOT}/assets/marker.png"
DPI = 300
SIZE_IN = 7
PX = DPI * SIZE_IN  # 2100

img = Image.open(SRC).convert("RGB")
w, h = img.size
side = min(w, h)
left = (w - side) // 2
top = (h - side) // 2
img = img.crop((left, top, left + side, top + side))
img = img.resize((PX, PX), Image.LANCZOS)
img.save(OUT, dpi=(DPI, DPI))
print("saved", OUT, img.size)
