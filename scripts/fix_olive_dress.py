# -*- coding: utf-8 -*-
"""橄榄色连衣裙 -> 巧克力棕 色相定向校正
仅调整: 中等饱和度 + 橄榄色相范围 + 裙子区域(可限纵向范围)的像素
用法: python fix_olive_dress.py <in> <out> [y_min y_max]
"""
import sys

import numpy as np
from PIL import Image


def fix(src, dst, y_min=0.25, y_max=0.95,
        hue_lo=24, hue_hi=42, sat_lo=60, shift=-14, sat_mul=1.18, val_mul=1.06):
    im = Image.open(src).convert("RGB")
    rgb = np.array(im, dtype=np.float32)
    hsv = np.array(im.convert("HSV"), dtype=np.float32)
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    h = im.height
    region = np.zeros_like(H, dtype=bool)
    region[int(h * y_min):int(h * y_max), :] = True
    mask = (region & (H >= hue_lo) & (H <= hue_hi) & (S >= sat_lo) & (V >= 40)
            & (G >= R * 0.92))  # 橄榄/棕色 G 接近 R; 皮肤 R 明显大于 G, 排除避免误伤
    print(f"pixels: {mask.sum()} ({mask.mean() * 100:.2f}%)  H-mean={H[mask].mean():.0f}" if mask.sum() else "no pixels")
    H[mask] = np.clip(H[mask] + shift, 0, 255)
    S[mask] = np.clip(S[mask] * sat_mul, 0, 255)
    V[mask] = np.clip(V[mask] * val_mul, 0, 255)
    out = Image.fromarray(hsv.astype(np.uint8), mode="HSV").convert("RGB")
    out.save(dst, quality=95)
    print("saved:", dst)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    y_min = float(sys.argv[3]) if len(sys.argv) > 3 else 0.25
    y_max = float(sys.argv[4]) if len(sys.argv) > 4 else 0.95
    fix(src, dst, y_min, y_max)
