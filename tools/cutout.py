# -*- coding: utf-8 -*-
"""姜林角色：白底照片抠图 + 叠加网格（全程 RGB，避免通道顺序踩坑）。"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "source.jpg")
OUT = os.path.join(ROOT, "build")
os.makedirs(OUT, exist_ok=True)

SCALE = 0.5  # 1760x2368 -> 880x1184

im = Image.open(SRC).convert("RGB")
W0, H0 = im.size
im = im.resize((int(W0 * SCALE), int(H0 * SCALE)), Image.LANCZOS)
W, H = im.size
rgb = np.array(im)                     # HxWx3, RGB
im.save(os.path.join(OUT, "src.png"))
print("work size", W, H, "from", W0, H0)

bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
mask = np.zeros((H, W), np.uint8)
rect = (int(W * 0.12), int(H * 0.01), int(W * 0.78), int(H * 0.985))
bgd = np.zeros((1, 65), np.float64)
fgd = np.zeros((1, 65), np.float64)
cv2.grabCut(bgr, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)

# 白底：四边连通的近白像素强制判为背景
dist_white = np.sqrt(((rgb.astype(np.float32) - 255.0) ** 2).sum(axis=2))
near_white = (dist_white < 26).astype(np.uint8)
ff = near_white.copy()
m2 = np.zeros((H + 2, W + 2), np.uint8)
for pt in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]:
    cv2.floodFill(ff, m2, pt, 2)
bg_white = (ff == 2) & (fg == 0)
fg[bg_white] = 0

alpha = cv2.GaussianBlur(fg, (0, 0), 1.0)
rgba = np.dstack([rgb, alpha])
cut = Image.fromarray(rgba, "RGBA")
cut.save(os.path.join(OUT, "cutout.png"))
print("fg px", int((fg > 0).sum()), "of", fg.size)

# 棋盘预览（PIL 合成，RGB 顺序）
tile = 14
chk = Image.new("RGB", (W, H))
dc = ImageDraw.Draw(chk)
for y in range(0, H, tile):
    for x in range(0, W, tile):
        c = 205 if ((x // tile + y // tile) % 2) else 160
        dc.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(c, c, c))
chk = chk.convert("RGBA")
chk.alpha_composite(cut)
prev = chk.convert("RGB")
prev.save(os.path.join(OUT, "cutout_checker.png"))

# 网格（坐标 = 工作图 1x 像素）
g = prev.copy()
d = ImageDraw.Draw(g)
for x in range(0, W, 40):
    col = (255, 0, 0) if x % 160 == 0 else (90, 150, 255)
    d.line([(x, 0), (x, H)], fill=col, width=1)
    if x % 160 == 0:
        d.text((x + 2, 2), str(x), fill=(255, 0, 0))
for y in range(0, H, 40):
    col = (255, 0, 0) if y % 160 == 0 else (90, 150, 255)
    d.line([(0, y), (W, y)], fill=col, width=1)
    if y % 160 == 0:
        d.text((2, y + 1), str(y), fill=(255, 0, 0))
g.save(os.path.join(OUT, "grid.png"))
print("saved", OUT)
