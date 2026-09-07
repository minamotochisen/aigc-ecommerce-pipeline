# -*- coding: utf-8 -*-
"""V10 场景终版合成: 丰富背景(全去噪版) + 干净人物层(掩膜版) = 两全
用法: python v10_composite.py <bg_img> <person_img> <out>
"""
import os
import sys

from PIL import Image, ImageFilter

MASK = r".\outputs_v2\v10\scene_person_mask.png"


def composite(bg_path, person_path, out, feather=1.5):
    bg = Image.open(bg_path).convert("RGB")
    ps = Image.open(person_path).convert("RGB")
    if bg.size != ps.size:
        ps = ps.resize(bg.size, Image.LANCZOS)
    m = Image.open(MASK).convert("L")
    if m.size != bg.size:
        m = m.resize(bg.size, Image.LANCZOS)
    # mask: bg=白255, person=黑0 -> 人物alpha = 反转; 内缩切掉基底残影像素再轻羽化
    person_alpha = Image.eval(m, lambda v: 255 - v)
    person_alpha = person_alpha.filter(ImageFilter.MinFilter(17))
    person_alpha = person_alpha.filter(ImageFilter.GaussianBlur(1.0))
    out_img = Image.composite(ps, bg, person_alpha)
    out_img.save(out, quality=93) if out.endswith(".jpg") else out_img.save(out)
    print("composite ->", out)


if __name__ == "__main__":
    bg, person, out = sys.argv[1], sys.argv[2], sys.argv[3]
    composite(bg, person, out)
