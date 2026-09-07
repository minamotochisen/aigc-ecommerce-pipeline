# -*- coding: utf-8 -*-
"""V10 场景掩膜: 从 tryon_best 背景色差建人物剪影 → alpha 掩膜PNG (bg白=重绘, 人物黑=锁定)"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

OUT = r".\outputs_v2\v10"
SRC = os.path.join(OUT, "tryon_best.png")
DST = os.path.join(OUT, "scene_person_mask.png")

im = Image.open(SRC).convert("RGB")
a = np.asarray(im).astype(np.float32)
h, w, _ = a.shape

# 背景色 = 四角 40px 中位数
corners = np.concatenate([
    a[:40, :40].reshape(-1, 3), a[:40, -40:].reshape(-1, 3),
    a[-40:, :40].reshape(-1, 3), a[-40:, -40:].reshape(-1, 3)])
bg = np.median(corners, axis=0)

dist = np.linalg.norm(a - bg[None, None, :], axis=2)
person = dist > 42  # 与背景色差阈值

# 去小块: 用 PIL 中值/最大值滤波做形态学
m = Image.fromarray((person * 255).astype(np.uint8))
m = m.filter(ImageFilter.MedianFilter(5))
m = m.filter(ImageFilter.MaxFilter(9))    # 膨胀, 盖住发丝边缘
m = m.filter(ImageFilter.MinFilter(5))    # 收缩回outline
m = m.filter(ImageFilter.MaxFilter(15))   # 闭运算: 填充裙装浅色花点造成的内部孔洞
m = m.filter(ImageFilter.MinFilter(13))
m = m.filter(ImageFilter.MaxFilter(3))
arr = np.array(m, copy=True)

# 保护图像边框 12px (避免边缘效应)
arr[:12, :] = 0
arr[-12:, :] = 0
arr[:, :12] = 0
arr[:, -12:] = 0

# 大目标过滤: 只保留最大连通域的近似 —— 用行/列密度清理孤立小块(简化: 面积阈值按 8x8 块)
blk = arr[: h // 8 * 8, : w // 8 * 8].reshape(h // 8, 8, w // 8, 8).mean(axis=(1, 3))
small = blk < 8
mask_small = np.kron(small, np.ones((8, 8), dtype=bool))[:h, :w]
arr[mask_small] = 0

alpha = Image.fromarray(255 - arr)  # bg=255(重绘), person=0(锁定)
alpha = alpha.filter(ImageFilter.GaussianBlur(2.5))  # 羽化过渡
rgba = im.copy().convert("RGBA")
rgba.putalpha(alpha)
rgba.save(DST)
cover = float((arr > 128).mean())
print("mask saved:", DST, " repaint coverage: %.1f%%" % (cover * 100))
