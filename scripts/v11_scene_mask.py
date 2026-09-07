# -*- coding: utf-8 -*-
"""V11 场景掩膜: rembg(u2net) 人像分割 -> alpha 掩膜PNG (bg白=重绘, 人物黑=锁定)
V10 色差法在浅色渐变背景上把脸部误判为背景导致重绘伤脸, 换语义分割根治。
用法: python_embeded/python.exe v11_scene_mask.py [src.png]
输出: outputs_v2/v10/scene_person_mask.png (兼容 v10_batch_h.masked_workflow)"""
import os
import sys

from PIL import Image, ImageFilter
from rembg import new_session, remove

ROOT = r"."
OUT = os.path.join(ROOT, "outputs_v2", "v10")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "tryon_best.png")
DST = os.path.join(OUT, "scene_person_mask.png")

im = Image.open(SRC).convert("RGB")
# u2net CPU 推理, 避免与 ComfyUI 抢 GPU
session = new_session("u2net", providers=["CPUExecutionProvider"])
person = remove(im, session=session, alpha_matting=False)  # RGBA, alpha=人像
alpha = person.getchannel("A")
W, H = im.size

# 人物掩膜清理: 闭运算填裙装孔洞 + 轻膨胀盖发丝
alpha = alpha.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(5))
alpha = alpha.filter(ImageFilter.MaxFilter(5))
# 边框保护 12px (避免边缘漏光)
import PIL.ImageDraw as ImageDraw
d = ImageDraw.Draw(alpha)
d.rectangle([0, 0, W - 1, 11], fill=255)
d.rectangle([0, H - 12, W - 1, H - 1], fill=255)
d.rectangle([0, 0, 11, H - 1], fill=255)
d.rectangle([W - 12, 0, W - 1, H - 1], fill=255)

# 重绘掩膜: 白=背景重绘, 黑=人物锁定 (反转人物alpha)
from PIL import ImageOps
mask = ImageOps.invert(alpha)
# 羽化: 人物边界过渡带 (最终 SetLatentNoiseMask 用)
mask = mask.filter(ImageFilter.GaussianBlur(2.5))
mask.save(DST)

cov = sum(1 for p in mask.getdata() if p > 128) / (W * H) * 100
print("mask saved: %s  repaint coverage: %.1f%%" % (DST, cov))
