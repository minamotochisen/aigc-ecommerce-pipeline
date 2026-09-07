# -*- coding: utf-8 -*-
"""V12 作品集素材打包: 终选图 -> plates + single + 图片包
前置: 择优场景/姿态已超分+CodeFormer (文件名见常量)
光板红T沿用 V9 成品(plate_blank_red.jpg 不动), 白T位换成 V12 背景净化 before/after。"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
V12 = os.path.join(ROOT, "outputs_v2", "v12")
TRIAL = os.path.join(ROOT, "outputs_v2", "v12_trial")
PLATES = os.path.join(ROOT, "outputs_v2", "plates")
SINGLE = os.path.join(PLATES, "single")
PACK = os.path.join(ROOT, "docs", "精选图片包")
HD_OUT = os.path.join(ROOT, "outputs_v2", "upscaled_v12")

INK = (26, 36, 56)
MUTED = (110, 120, 136)
FONT_TTC = "C:/Windows/Fonts/msyh.ttc"
_fc = {}

# ---- 终选文件 (相对 TRIAL/V12, 均为 超分+CF 后成品) ----
B_FINAL = "v12_tryon_b_94102_hd_cf70.png"       # 组合B 主图 (TRIAL)
D_FINAL = "v12_tryon_d_94113_hd_cf70.png"       # 组合D 主图 (TRIAL)
CREAM_FINAL = "upscaled_v12/v12_scene_cream_b_94201_hd_cf70.png"   # 奶油室内 (V12)
STREET_FINAL = "upscaled_v12/v12_scene_street_b_94213_hd_cf70.png" # 石板街 (V12)
CLEAN_FINAL = "v12_clean_bkg_94252_cf70.png"    # 背景净化后 (V12)
B_STUDIO = "v12_tryon_b_94102_00001_.png"       # B 影棚 1024 (TRIAL)
D_STUDIO = "v12_tryon_d_94113_00001_.png"       # D 影棚 1024 (TRIAL)
B_CLUTTER = "v12_tryon_b_94101_00001_.png"      # 净化前 (TRIAL)
REF_OUTFIT = os.path.join(ROOT, "assets_v2", "v12", "fit_blouseshirt.jpg")
ANCHOR = os.path.join(ROOT, "assets_v2", "v12", "mdl_f1.jpg")

POSE_CELLS = [  # (标签, 绝对路径)
    ("正面", "pose_front_1"), ("正面·变体", "pose_front_2"),
    ("回眸", "pose_back"), ("行走", "pose_walking"), ("叉腰", "pose_handonhip"),
]


def font(size):
    size = max(14, int(size))
    if size not in _fc:
        _fc[size] = ImageFont.truetype(FONT_TTC, size)
    return _fc[size]


def load(path, target_w=1500):
    im = Image.open(path).convert("RGB")
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


def vp(p):
    if os.path.isabs(p):
        return p
    if p.startswith("upscaled_v12"):
        return os.path.join(ROOT, "outputs_v2", *p.split("/"))
    return os.path.join(V12, p)


def tp(p):
    return os.path.join(TRIAL, p) if not os.path.isabs(p) else p


def main():
    b_final = load(tp(B_FINAL), 1500)
    d_final = load(tp(D_FINAL), 1500)
    cream = load(vp(CREAM_FINAL), 1500)
    street = load(vp(STREET_FINAL), 1500)
    clean = load(vp(CLEAN_FINAL), 1400)
    ref = Image.open(REF_OUTFIT).convert("RGB")
    anchor = Image.open(ANCHOR).convert("RGB")

    # Case1 换装 (before=服装参考, after=B组合成片)
    b = caption(fit_h(ref, 1500), "输入 · 服装参考图", "藏蓝泡泡袖上衣 + 米白长裙")
    a = caption(fit_h(b_final, 1500), "输出 · 指令换装 + 面部修复", "Qwen-Edit-2511 · 40步 · CodeFormer")
    save(hpair(b, a), "plate_case1.jpg", 91)

    # Case2/3 场景 (全场景重绘)
    b2 = caption(fit_h(load(tp(B_STUDIO), 1400), 1500), "输入 · 换装成片", "影棚底图")
    a2 = caption(fit_h(cream, 1500), "输出 · 全场景重绘", "奶油风极简室内 · 原生光影")
    save(hpair(b2, a2), "plate_case2.jpg", 91)
    a3 = caption(fit_h(street, 1500), "输出 · 全场景重绘", "欧洲石板街 · 原生光影")
    save(hpair(b2, a3), "plate_case3.jpg", 91)

    # 姿态六宫格 (正面2张来自组合B三seed择优2张, 其余为姿态迁移)
    cells = []
    front1 = caption(fit_h(load(tp(B_FINAL), 1100), 1150), "姿态 · 正面")
    front2 = caption(fit_h(load(tp("v12_tryon_b_94103_00001_.png"), 1100), 1150), "姿态 · 正面·变体")
    back = caption(fit_h(load(vp("upscaled_v12/v12_pose_back_94222_hd_cf70.png"), 1100), 1150), "姿态 · 回眸")
    walk = caption(fit_h(load(vp("v12_pose_walking_94232_cf70.png"), 1100), 1150), "姿态 · 行走")
    hip = caption(fit_h(load(vp("v12_pose_handonhip_94242_cf70.png"), 1100), 1150), "姿态 · 叉腰")
    clean6 = caption(fit_h(load(vp(CLEAN_FINAL), 1100), 1150), "姿态 · 净化正面")
    cells = [front1, front2, back, walk, hip, clean6]
    cw = max(c.width for c in cells)
    ch = max(c.height for c in cells)
    grid = Image.new("RGB", (cw * 3 + 28, ch * 2 + 14), "white")
    for i, c in enumerate(cells):
        r, col = divmod(i, 3)
        grid.paste(c, (col * (cw + 14), r * (ch + 14)))
    save(grid, "plate_pose_grid.jpg", 89)

    # P7 净化 before/after
    cb = caption(fit_h(load(tp(B_CLUTTER), 1400), 1400), "输入 · 背景有杂物")
    ca = caption(fit_h(clean, 1400), "输出 · 指令净化", "去除钉挂照片 · 墙面质感重建")
    save(hpair(cb, ca), "plate_clean.jpg", 91)

    # 封面
    save(load(tp(B_FINAL), 1600), "plate_cover.jpg", 92)

    # 单张
    os.makedirs(SINGLE, exist_ok=True)
    singles = {
        "c1_before.jpg": fit_h(ref, 1800),
        "c1_after.jpg": fit_h(b_final, 1800),
        "c2_before.jpg": fit_h(load(tp(B_STUDIO), 1500), 1800),
        "c2_after.jpg": fit_h(cream, 1800),
        "c3_before.jpg": fit_h(load(tp(D_STUDIO), 1500), 1800),
        "c3_after.jpg": fit_h(street, 1800),
        "pose_anchor.jpg": fit_h(anchor, 1400),
    }
    for name, im in singles.items():
        im.save(os.path.join(SINGLE, name), quality=91)
        print("single:", name)

    # 精选图片包
    os.makedirs(PACK, exist_ok=True)
    pack = {
        "01_换装_输入_服装参考.jpg": fit_h(ref, 1800),
        "02_换装_输出_藏蓝泡泡袖.jpg": fit_h(b_final, 1800),
        "03_场景重绘_奶油风室内.jpg": fit_h(cream, 1800),
        "04_场景变换_街拍.jpg": fit_h(street, 1800),
        "05_姿态裂变_六宫格.jpg": grid,
    }
    for dst, im in pack.items():
        im.convert("RGB").save(os.path.join(PACK, dst), quality=92)
        print("pack:", dst)


if __name__ == "__main__":
    main()
