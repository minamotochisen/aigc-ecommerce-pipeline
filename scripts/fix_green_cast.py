# -*- coding: utf-8 -*-
"""修复 AI 换景后头发/暗部的橄榄绿色偏: HSV 色相平移(仅限暗部绿像素, 可选区域限制)
用法: python fix_green_cast.py <输入> <输出> [y_min_ratio y_max_ratio]
"""
import sys

import numpy as np
from PIL import Image


def fix(src, dst, y_min=0.0, y_max=1.0, hue_lo=60, hue_hi=170, val_hi=150, shift_to=28.0, strength=0.85):
    im = Image.open(src).convert("RGB")
    hsv = np.array(im.convert("HSV"), dtype=np.float32)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    h = im.height
    region = np.zeros_like(H, dtype=bool)
    region[int(h * y_min):int(h * y_max), :] = True
    # 暗部 + 绿色相 + 有一定饱和度(区分于灰色墙)
    mask = region & (H >= hue_lo) & (H <= hue_hi) & (V <= val_hi) & (S >= 40)
    print(f"pixels: {mask.sum()} ({mask.mean() * 100:.2f}%)")
    # 色相平移到 shift_to(棕), 按强度混合, 保持 V 与 S
    delta = shift_to - H[mask]
    H[mask] = (H[mask] + delta * strength) % 256
    out = Image.fromarray(hsv.astype(np.uint8), mode="HSV").convert("RGB")
    out.save(dst, quality=95)
    print("saved:", dst)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    y_min = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    y_max = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    fix(src, dst, y_min, y_max)
