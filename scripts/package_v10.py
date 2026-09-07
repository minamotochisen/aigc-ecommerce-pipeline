# -*- coding: utf-8 -*-
"""V10 作品集素材打包: 终选图(upscaled_v10) -> plates + single + 图片包
光板两图沿用 V9 成品(plate_blank_tee/red.jpg 不动)。"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HD = os.path.join(ROOT, "outputs_v2", "upscaled_v10")
V10 = os.path.join(ROOT, "outputs_v2", "v10")
PLATES = os.path.join(ROOT, "outputs_v2", "plates")
SINGLE = os.path.join(PLATES, "single")
PACK = os.path.join(ROOT, "docs", "精选图片包")

INK = (26, 36, 56)
MUTED = (110, 120, 136)
FONT_TTC = "C:/Windows/Fonts/msyh.ttc"
_fc = {}

TRYON_HD = "v10_tryon_best_hd"
MED_HD = "v10_scene_med_hd"
ST_HD = "v10_scene_street_hd"
POSE_HD = {
    "叉腰": "v10_pose_hip_hd",
    "行走": "v10_pose_walk_hd",
    "回眸": "v10_pose_side_hd",
    "站姿": "v10_pose_stand_hd",
    "3-4站": "v10_pose_34_hd",
}
ANCHOR_FRONT = os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")


def font(size):
    size = max(14, int(size))
    if size not in _fc:
        _fc[size] = ImageFont.truetype(FONT_TTC, size)
    return _fc[size]


def load_hd(stem, target_w=1500):
    p = os.path.join(HD, stem + ".png")
    im = Image.open(p).convert("RGB")
    if im.width < target_w:
        r = target_w / im.width
        im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=70, threshold=2))
    return im


def caption(im, text, sub=""):
    bar = max(58, int(im.width * 0.062))
    out = Image.new("RGB", (im.width, im.height + bar), "white")
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    d.rectangle([0, im.height, im.width, im.height + 3], fill=INK)
    f1, f2 = font(bar * 0.42), font(bar * 0.30)
    d.text((14, im.height + int(bar * 0.18)), text, fill=INK, font=f1)
    if sub:
        w = d.textlength(text, font=f1)
        d.text((14 + w + 20, im.height + int(bar * 0.26)), sub, fill=MUTED, font=f2)
    return out


def hpair(p1, p2, gap=14):
    H = max(p1.height, p2.height)
    out = Image.new("RGB", (p1.width + p2.width + gap, H), "white")
    out.paste(p1, (0, 0))
    out.paste(p2, (p1.width + gap, 0))
    return out


def fit_h(im, h):
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)


def save(im, name, q=90):
    os.makedirs(PLATES, exist_ok=True)
    p = os.path.join(PLATES, name)
    im.save(p, quality=q) if name.endswith(".jpg") else im.save(p)
    print("plate:", name, im.size)


def main():
    anchor = load_hd(TRYON_HD, 1500)
    a_src = Image.open(ANCHOR_FRONT).convert("RGB")
    med = load_hd(MED_HD)
    st = load_hd(ST_HD)

    # Case1 换装
    b = caption(fit_h(a_src, 1500), "输入 · 真实模特照", "咖啡色波点吊带长裙")
    a = caption(fit_h(anchor, 1500), "输出 · Qwen-Image-Edit-2511 指令换装", "藏青花卉吊带裙 · 手部经定向修复")
    save(hpair(b, a), "plate_case1.jpg", 91)

    # Case2/3 场景(全场景重绘: 人物一体生成, 光影原生统一)
    b2 = caption(fit_h(a_src, 1500), "输入 · 换装成片", "影棚底图")
    a2 = caption(fit_h(med, 1500), "输出 · 全场景重绘", "奶油风极简室内 · 原生光影")
    save(hpair(b2, a2), "plate_case2.jpg", 91)
    a3 = caption(fit_h(st, 1500), "输出 · 全场景重绘", "欧洲石板街 · 原生光影")
    save(hpair(b2, a3), "plate_case3.jpg", 91)

    # 姿态六宫格
    cells = []
    for cn, stem in POSE_HD.items():
        cells.append(caption(fit_h(load_hd(stem, 1100), 1150), f"姿态 · {cn}"))
    front = caption(fit_h(a_src, 1150), "姿态 · 正面(真实锚定照)")
    cells.insert(0, front)
    cw = max(c.width for c in cells)
    ch = max(c.height for c in cells)
    grid = Image.new("RGB", (cw * 3 + 28, ch * 2 + 14), "white")
    for i, c in enumerate(cells):
        r, col = divmod(i, 3)
        grid.paste(c, (col * (cw + 14), r * (ch + 14)))
    save(grid, "plate_pose_grid.jpg", 89)

    # 封面
    save(load_hd(TRYON_HD, 1600), "plate_cover.jpg", 92)

    # 单张
    os.makedirs(SINGLE, exist_ok=True)
    singles = {
        "c1_before.jpg": fit_h(a_src, 1800),
        "c1_after.jpg": fit_h(anchor, 1800),
        "c2_before.jpg": fit_h(anchor, 1800),
        "c2_after.jpg": fit_h(med, 1800),
        "c3_before.jpg": fit_h(anchor, 1800),
        "c3_after.jpg": fit_h(st, 1800),
        "pose_anchor.jpg": fit_h(a_src, 1400),
        "qwen_main.jpg": fit_h(anchor, 1800),
    }
    for name, im in singles.items():
        im.save(os.path.join(SINGLE, name), quality=91)
        print("single:", name)

    # 精选图片包
    os.makedirs(PACK, exist_ok=True)
    pack = {
        "01_换装_输入_波点长裙.jpg": fit_h(a_src, 1800),
        "02_换装_输出_花卉吊带裙.jpg": fit_h(anchor, 1800),
        "03_场景重绘_奶油风室内.jpg": fit_h(med, 1800),
        "04_场景变换_街拍.jpg": fit_h(st, 1800),
        "06_姿态裂变_六宫格.jpg": grid,
    }
    for dst, im in pack.items():
        im.convert("RGB").save(os.path.join(PACK, dst), quality=92)
        print("pack:", dst)


if __name__ == "__main__":
    main()
