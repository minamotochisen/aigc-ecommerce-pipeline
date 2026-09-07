# -*- coding: utf-8 -*-
"""V3 作品集素材打包: 超分高清源 -> 高清拼图 + 精选图片包 + 单张图 (纯作品集风)"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HD = os.path.join(ROOT, "outputs_v2", "upscaled")
PLATES = os.path.join(ROOT, "outputs_v2", "plates")
SINGLE = os.path.join(PLATES, "single")
PACK = os.path.join(ROOT, "docs", "精选图片包")

INK = (26, 36, 56)
MUTED = (110, 120, 136)
FONT_TTC = "C:/Windows/Fonts/msyh.ttc"
_fc = {}


def font(size):
    size = max(14, int(size))
    if size not in _fc:
        _fc[size] = ImageFont.truetype(FONT_TTC, size)
    return _fc[size]


def load(name, target_w=1500):
    """从超分目录按文件名加载(已 1500px), 低于目标宽则再放大并锐化"""
    im = Image.open(os.path.join(HD, name)).convert("RGB")
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


def load_red_input():
    """红T输入原图(1000x1200 RGBA), 白底化并放大"""
    im = Image.open(os.path.join(ROOT, "assets", "garments", "cand_redtee_floral.png"))
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        im = bg
    im = im.convert("RGB")
    if im.width < 1300:
        r = 1300 / im.width
        im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    return im


def main():
    # ---------- Case01 换装A ----------
    b = caption(fit_h(load("c1_before_hd.png"), 1500), "输入 · 真实模特照", "咖啡色波点吊带长裙")
    a = caption(fit_h(load("c1_after_hd.png"), 1500), "输出 · SDXL 局部重绘", "藏青花卉提花吊带裙")
    save(hpair(b, a), "plate_case1.jpg", 91)

    # ---------- Case02 场景重绘B ----------
    b = caption(fit_h(load("c2_before_hd.png"), 1500), "输入 · 影棚原片", "黑色背心 + 米色阔腿裤")
    a = caption(fit_h(load("c2_after_hd.png"), 1500), "输出 · 场景重绘", "地中海拱墙 · 黄金时刻光影")
    save(hpair(b, a), "plate_case2.jpg", 91)

    # ---------- Case03 场景重绘C ----------
    b = caption(fit_h(load("c3_before_hd.png"), 1500), "输入 · 影棚原片", "同款同模特")
    a = caption(fit_h(load("c3_after_hd.png"), 1500), "输出 · 场景重绘", "街拍光影 · 服装不变")
    save(hpair(b, a), "plate_case3.jpg", 91)

    # ---------- Case04 姿态裂变六宫格 ----------
    pose_files = [
        ("pose_walk_hd.png", "行走动势"), ("pose_sit_hd.png", "坐姿"),
        ("pose_side3_00003_hd.png", "侧身"), ("pose_turn_hd.png", "回眸"),
        ("pose_back_hd.png", "背面"), ("pose_stand_hd.png", "站姿"),
    ]
    cells = [caption(fit_h(load(f, 1100), 1150), f"姿态 · {cn}") for f, cn in pose_files]
    cw = max(c.width for c in cells)
    ch = max(c.height for c in cells)
    grid = Image.new("RGB", (cw * 3 + 28, ch * 2 + 14), "white")
    for i, c in enumerate(cells):
        r, col = divmod(i, 3)
        grid.paste(c, (col * (cw + 14), r * (ch + 14)))
    save(grid, "plate_pose_grid.jpg", 89)

    # ---------- Case05 光板净化 ----------
    def load_tee_input():
        im = Image.open(os.path.join(ROOT, "assets_v2", "garments", "g_tee_awet.jpg")).convert("RGB")
        if im.width < 1300:
            r = 1300 / im.width
            im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
        return im
    tee_in = load_tee_input()
    b_tee = caption(tee_in, "输入 · 带文字印花 + 领标", "真实电商图")
    a_tee = caption(load("blank_tee_hd.png"), "输出 · 纯白光板", "可作新品开发底版")
    save(hpair(b_tee, a_tee), "plate_blank_tee.jpg", 91)

    red_in = load_red_input()
    b2 = caption(red_in, "输入 · 大面积花卉印花", "真实电商图")
    a2 = caption(load("blank_red_hd.png"), "输出 · 纯色光板", "印花完全移除")
    save(hpair(b2, a2), "plate_blank_red.jpg", 91)

    # ---------- 封面 ----------
    save(load("c1_after_hd.png", 1600), "plate_cover.jpg", 92)

    # ---------- 精选图片包 ----------
    os.makedirs(PACK, exist_ok=True)
    pack = {
        "c1_before_hd.png": "01_换装A_输入_波点长裙.jpg",
        "c1_after_hd.png": "02_换装A_输出_花卉提花裙.jpg",
        "c2_before_hd.png": "03_场景重绘B_输入_影棚.jpg",
        "c2_after_hd.png": "04_场景重绘B_输出_地中海光影.jpg",
        "c3_after_hd.png": "05_场景变换_街拍.jpg",
        "grid": "06_动作裂变_六宫格.jpg",
        "tee_input": "07_光板净化_文字T恤_输入.jpg",
        "blank_tee_hd.png": "08_光板净化_文字T恤_输出.jpg",
        "blank_red_hd.png": "10_光板净化_印花T恤_输出.jpg",
    }
    extras = {"grid": grid, "tee_input": tee_in, "red_input": red_in}
    for key, dst in pack.items():
        im = extras.get(key) or load(key, 1300)
        im.convert("RGB").save(os.path.join(PACK, dst), quality=92)
        print("pack:", dst)

    # ---------- 单张导出 (HTML 用) ----------
    os.makedirs(SINGLE, exist_ok=True)
    singles = [
        ("c1_before_hd.png", "c1_before.jpg"), ("c1_after_hd.png", "c1_after.jpg"),
        ("c2_before_hd.png", "c2_before.jpg"), ("c2_after_hd.png", "c2_after.jpg"),
        ("c3_before_hd.png", "c3_before.jpg"), ("c3_after_hd.png", "c3_after.jpg"),
        (tee_in, "b1_before.jpg"), (load("blank_red_hd.png"), "b2_after.jpg"),
    ]
    for key, dst in singles:
        im = key if hasattr(key, "convert") else load(key, 1300)
        im.convert("RGB").save(os.path.join(SINGLE, dst), quality=91)
        print("single:", dst)
    anchor = Image.open(os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")).convert("RGB")
    anchor.save(os.path.join(SINGLE, "pose_anchor.jpg"), quality=91)
    print("single: pose_anchor.jpg")


def load_red_input_for_pack():
    im = Image.open(os.path.join(ROOT, "assets", "garments", "cand_redtee_floral.png"))
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        im = bg
    im = im.convert("RGB")
    if im.width < 1300:
        r = 1300 / im.width
        im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    return im


if __name__ == "__main__":
    main()
