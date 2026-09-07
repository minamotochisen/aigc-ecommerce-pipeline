# -*- coding: utf-8 -*-
"""V11 场景合成: 全去噪场景版(背景完整) + 干净人物层(rembg掩膜锁人) + 轻量光影适配
用法: python v11_composite.py <bg_img> <person_img> <out>
适配: 人物层亮度/色温向场景环境轻微靠拢(Lab均值差, 限幅), 避免"影棚人贴进场景"的割裂感。"""
import os
import sys

from PIL import Image, ImageFilter

MASK = r".\outputs_v2\v10\scene_person_mask.png"


def lab_shift(person, bg, max_l=12.0, max_ab=8.0):
    """以 numpy RGB 均值近似 Lab 粗调: 亮度用 Y 系数, 色调用 R/B 通道偏移, 限幅防过匹配"""
    import numpy as np
    pa = np.asarray(person, dtype=np.float32)
    ba = np.asarray(bg.resize((64, 64)), dtype=np.float32)
    # 只统计背景图四角 1/9 区域(纯背景, 避免人物干扰)
    h, w = ba.shape[:2]
    corners = np.concatenate([ba[:h//3, :w//3].reshape(-1, 3), ba[:h//3, -w//3:].reshape(-1, 3)])
    dl = float(corners[:, 1].mean() - pa[:, :, 1].mean())          # G 通道近似亮度
    da = float(corners[:, 0].mean() - pa[:, :, 0].mean())          # R 通道近似暖色
    db = float(corners[:, 2].mean() - pa[:, :, 2].mean())          # B 通道近似冷色
    dl = max(-max_l, min(max_l, dl))
    da = max(-max_ab, min(max_ab, da))
    db = max(-max_ab, min(max_ab, db))
    out = pa.copy()
    out[:, :, 1] += dl
    out[:, :, 0] += da
    out[:, :, 2] += db
    print("light adapt: dG=%.1f dR=%.1f dB=%.1f" % (dl, da, db))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def composite(bg_path, person_path, out, erode=5):
    import numpy as np
    bg = Image.open(bg_path).convert("RGB")
    ps = Image.open(person_path).convert("RGB")
    if bg.size != ps.size:
        ps = ps.resize(bg.size, Image.LANCZOS)
    m = Image.open(MASK).convert("L")
    if m.size != bg.size:
        m = m.resize(bg.size, Image.LANCZOS)
    ma = np.asarray(m, dtype=np.uint8)
    # 掩膜: 白=重绘背景(255), 黑=人物(0)。硬阈值取人物, 去掉 rembg 带进来的地面半透明影子
    person = (ma < 70)
    ys, xs = np.where(person)
    feet_y, feet_cx = int(ys.max()), int(xs[ys > ys.max() - 40].mean())
    # 人物alpha: 轻内缩+羽化
    person_alpha = Image.fromarray((person * 255).astype(np.uint8))
    person_alpha = person_alpha.filter(ImageFilter.MinFilter(erode))
    person_alpha = person_alpha.filter(ImageFilter.GaussianBlur(1.2))
    ps = lab_shift(ps, bg)
    # 合成接触投影: 脚下椭圆软阴影(室内柔光/阴天均自然)
    W, H = bg.size
    pw = int(xs.max() - xs.min())
    sh_w, sh_h = int(pw * 0.55), int(pw * 0.13)
    shadow = Image.new("L", (W, H), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(shadow).ellipse(
        [feet_cx - sh_w // 2, feet_y - sh_h // 2, feet_cx + sh_w // 2, feet_y + sh_h], fill=90)
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    dark = Image.new("RGB", (W, H), (30, 25, 20))
    bg = Image.composite(dark, bg, shadow)
    out_img = Image.composite(ps, bg, person_alpha)
    out_img.save(out, quality=93) if out.endswith(".jpg") else out_img.save(out)
    print("composite ->", out)


if __name__ == "__main__":
    composite(sys.argv[1], sys.argv[2], sys.argv[3])
