# -*- coding: utf-8 -*-
"""V9 作品集素材打包: Qwen-Edit-2511 输出 -> 超分 -> 高清拼图 + 单张 + 图片包
先运行 upscale_api.py 生成 outputs_v2/upscaled_v9/ 下 *_hd.png, 再运行本脚本。
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HD = os.path.join(ROOT, "outputs_v2", "upscaled_v9")
V9 = os.path.join(ROOT, "outputs_v2", "v9")
PLATES = os.path.join(ROOT, "outputs_v2", "plates")
SINGLE = os.path.join(PLATES, "single")
PACK = os.path.join(ROOT, "docs", "精选图片包")

INK = (26, 36, 56)
MUTED = (110, 120, 136)
FONT_TTC = "C:/Windows/Fonts/msyh.ttc"
_fc = {}

# ---- 本轮选定成片(评审择优后确定) ----
TRYON_BEST = "v9_tryon_full_91121"          # 换装主图(封面/P2 AFTER/P8 方案二)
SCENE_MED_BEST = "v9_scene_med_91252"       # 地中海终试(发丝清晰/无绿偏)
SCENE_STREET_BEST = "v9_street3"            # 街拍终试(00001)
POSE_BESTS = {                              # 姿态宫格: 锚定身份 + 眼镜统一
    "正面": "v9_anchor_front",              # 锚定真实照(波点吊带长裙)
    "叉腰": "v9_pose_glasses_hip",
    "行走": "v9_pose_glasses_walk2",
    "回眸": "v9_pose_glasses_side",
    "站姿": "v9_pose_back_91402",
    "3-4站": "v9_stand2_fixed",             # R2: 巧克力棕校正版(手部/裙色均优于旧格)
}
ANCHOR_FRONT = os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")
CROP_BOTTOM = {}  # R2: stand2 成对凉鞋, 无需裁脚
BLANK_TEE_BEST = "v9_white4"                # 白T: Qwen 整件替换
BLANK_RED_FALLBACK_V4 = True                # 红T: 混合管线 V4 成片(outputs_v2/upscaled/blank_red_hd.png)
BLANK_RED_BEST = "v9_blank_91501"           # Qwen 备选(留档)


def font(size):
    size = max(14, int(size))
    if size not in _fc:
        _fc[size] = ImageFont.truetype(FONT_TTC, size)
    return _fc[size]


def load_hd(stem, target_w=1500):
    """优先取超分图, 否则取原始图并放大锐化"""
    p_hd = os.path.join(HD, stem + "_hd.png")
    p_raw = os.path.join(V9, stem + "_00001_.png")
    p = p_hd if os.path.exists(p_hd) else p_raw
    im = Image.open(p).convert("RGB")
    if stem in CROP_BOTTOM:  # 裁掉底部缺陷(如不成对的鞋)
        im = im.crop((0, 0, im.width, int(im.height * (1 - CROP_BOTTOM[stem]))))
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


def crop_top_frac(im, keep):
    """成对裁切: 保留上部 keep 比例(3/4 构图), 规避场景重绘的腿部涂抹"""
    return im.crop((0, 0, im.width, int(im.height * keep)))


def main():
    # ---------- Case1 换装 ----------
    anchor = load_hd(TRYON_BEST, 1500)
    a_src = Image.open(os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")).convert("RGB")
    b = caption(fit_h(a_src, 1500), "输入 · 真实模特照", "咖啡色波点吊带长裙")
    a = caption(fit_h(anchor, 1500), "输出 · Qwen-Image-Edit-2511 指令换装", "藏青花卉提花吊带裙")
    save(hpair(b, a), "plate_case1.jpg", 91)

    # ---------- Case2 场景·地中海 ----------
    med = load_hd(SCENE_MED_BEST)
    b = caption(fit_h(a_src, 1500), "输入 · 影棚原片", "同一模特同一裙装")
    a = caption(fit_h(med, 1500), "输出 · 背景替换", "地中海拱门 · 黄金时刻光影")
    save(hpair(b, a), "plate_case2.jpg", 91)

    # ---------- Case3 场景·街拍 ----------
    st = load_hd(SCENE_STREET_BEST)
    a = caption(fit_h(st, 1500), "输出 · 背景替换", "欧洲石板街 · 同人同装")
    save(hpair(b, a), "plate_case3.jpg", 91)

    # ---------- 姿态六宫格 ----------
    cells = []
    for cn, stem in POSE_BESTS.items():
        im = (Image.open(ANCHOR_FRONT).convert("RGB") if stem == "v9_anchor_front" else load_hd(stem, 1100))
        cells.append(caption(fit_h(im, 1150), f"姿态 · {cn}"))
    cw = max(c.width for c in cells)
    ch = max(c.height for c in cells)
    grid = Image.new("RGB", (cw * 3 + 28, ch * 2 + 14), "white")
    for i, c in enumerate(cells):
        r, col = divmod(i, 3)
        grid.paste(c, (col * (cw + 14), r * (ch + 14)))
    save(grid, "plate_pose_grid.jpg", 89)

    # ---------- 光板净化 (V4 混合管线成片: Qwen 指令路线在两输入上均有涂抹, 留档 outputs_v2/v9) ----------
    def load_tee_input():
        im = Image.open(os.path.join(ROOT, "assets_v2", "garments", "g_tee_awet.jpg")).convert("RGB")
        if im.width < 1300:
            r = 1300 / im.width
            im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
        return im
    tee_in = load_tee_input()
    b_tee = caption(fit_h(tee_in, 2000), "输入 · 带文字印花 + 领标", "真实电商图")
    a_tee = caption(fit_h(Image.open(os.path.join(ROOT, "outputs_v2", "upscaled", "blank_tee_hd.png")).convert("RGB"), 2000),
                    "输出 · 纯白光板", "混合修复管线")
    save(hpair(b_tee, a_tee), "plate_blank_tee.jpg", 91)

    red_in = Image.open(os.path.join(ROOT, "assets", "garments", "cand_redtee_floral.png"))
    if red_in.mode == "RGBA":
        bg = Image.new("RGB", red_in.size, "white")
        bg.paste(red_in, mask=red_in.split()[3])
        red_in = bg
    red_in = red_in.convert("RGB")
    if red_in.width < 1300:
        r = 1300 / red_in.width
        red_in = red_in.resize((int(red_in.width * r), int(red_in.height * r)), Image.LANCZOS)
    b2 = caption(red_in, "输入 · 大面积花卉印花", "真实电商图")
    a2 = caption(fit_h(Image.open(os.path.join(ROOT, "outputs_v2", "upscaled", "blank_red_hd.png")).convert("RGB"), 2000),
                 "输出 · 纯色光板", "混合修复管线")
    save(hpair(b2, a2), "plate_blank_red.jpg", 91)

    # ---------- 封面 ----------
    save(load_hd(TRYON_BEST, 1600), "plate_cover.jpg", 92)

    # ---------- 单张(HTML 用) ----------
    os.makedirs(SINGLE, exist_ok=True)
    red_out_single = (Image.open(os.path.join(ROOT, "outputs_v2", "upscaled", "blank_red_hd.png")).convert("RGB")
                      if BLANK_RED_FALLBACK_V4 else load_hd(BLANK_RED_BEST, 1300))
    singles = {
        "c1_before.jpg": fit_h(a_src, 1800),
        "c1_after.jpg": fit_h(anchor, 1800),
        "c2_before.jpg": fit_h(anchor, 1800),
        "c2_after.jpg": fit_h(med, 1800),
        "c3_before.jpg": fit_h(anchor, 1800),
        "c3_after.jpg": fit_h(st, 1800),
        "b2_after.jpg": red_out_single,
        "pose_anchor.jpg": fit_h(a_src, 1400),
        "qwen_main.jpg": fit_h(anchor, 1800),
    }
    for name, im in singles.items():
        im.save(os.path.join(SINGLE, name), quality=91)
        print("single:", name)

    # ---------- 精选图片包 ----------
    os.makedirs(PACK, exist_ok=True)
    pack = {
        "01_换装_输入_波点长裙.jpg": fit_h(a_src, 1800),
        "02_换装_输出_花卉提花裙.jpg": fit_h(anchor, 1800),
        "03_场景重绘_地中海光影.jpg": fit_h(med, 1800),
        "04_场景变换_街拍.jpg": fit_h(st, 1800),
        "06_姿态裂变_六宫格.jpg": grid,
        "08_光板净化_文字T恤_输出.jpg": fit_h(Image.open(os.path.join(ROOT, "outputs_v2", "upscaled", "blank_tee_hd.png")).convert("RGB"), 1300),
        "10_光板净化_印花T恤_输出.jpg": red_out_single,
    }
    for dst, im in pack.items():
        im.convert("RGB").save(os.path.join(PACK, dst), quality=92)
        print("pack:", dst)


if __name__ == "__main__":
    main()
