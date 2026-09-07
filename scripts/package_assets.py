# -*- coding: utf-8 -*-
"""作品集素材打包: 生成对比拼图 + 精选图片包 + 归档中间产物"""
import os
import shutil

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLATES = os.path.join(ROOT, "outputs", "plates")
PACK = os.path.join(ROOT, "docs", "精选图片包")
ARCHIVE = os.path.join(ROOT, "outputs", "_archive")

FONT_TTC = "C:/Windows/Fonts/msyh.ttc"
_font_cache = {}


def get_font(size):
    size = max(12, int(size))
    if size not in _font_cache:
        _font_cache[size] = ImageFont.truetype(FONT_TTC, size)
    return _font_cache[size]

INK = (26, 36, 56)
MUTED = (110, 120, 136)


def load(p, up=1.6):
    im = Image.open(p).convert("RGB")
    if up > 1 and im.width < 700:
        im = im.resize((int(im.width * up), int(im.height * up)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=60, threshold=2))
    return im


def label_bar(im, text, sub=""):
    bar_h = max(64, int(im.width * 0.115))
    out = Image.new("RGB", (im.width, im.height + bar_h), "white")
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    f1, f2 = get_font(bar_h * 0.44), get_font(bar_h * 0.30)
    d.rectangle([0, im.height, im.width, im.height + 4], fill=INK)
    d.text((12, im.height + int(bar_h * 0.16)), text, fill=INK, font=f1)
    if sub:
        w = d.textlength(text, font=f1)
        d.text((12 + w + 18, im.height + int(bar_h * 0.22)), sub, fill=MUTED, font=f2)
    return out


def hrow(items, gap=14, pad=0):
    """横向拼接 [(img, label, sub)]"""
    imgs = [label_bar(im, t, s) if t else im for im, t, s in items]
    H = max(i.height for i in imgs)
    W = sum(i.width for i in imgs) + gap * (len(imgs) - 1) + pad * 2
    out = Image.new("RGB", (W, H), "white")
    x = pad
    for i in imgs:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


def grid(items, cols, gap=14, pad=0):
    """网格拼接 [(img, label, sub)]"""
    imgs = [label_bar(im, t, s) if t else im for im, t, s in items]
    rows = (len(imgs) + cols - 1) // cols
    cw = max(i.width for i in imgs)
    ch = max(i.height for i in imgs)
    W = cw * cols + gap * (cols - 1) + pad * 2
    H = ch * rows + gap * (rows - 1) + pad * 2
    out = Image.new("RGB", (W, H), "white")
    for k, im in enumerate(imgs):
        r, c = divmod(k, cols)
        out.paste(im, (pad + c * (cw + gap), pad + r * (ch + gap)))
    return out


def save(im, name, q=90):
    os.makedirs(PLATES, exist_ok=True)
    p = os.path.join(PLATES, name)
    if name.endswith(".jpg"):
        im.save(p, quality=q)
    else:
        im.save(p)
    print("plate:", name, im.size)


def fit_h(im, h):
    w = int(im.width * h / im.height)
    return im.resize((w, h), Image.LANCZOS)


def main():
    A = os.path.join(ROOT, "assets")
    T = os.path.join(ROOT, "outputs", "tryon")
    P = os.path.join(ROOT, "outputs", "pose")
    B = os.path.join(ROOT, "outputs", "blank")
    E = os.path.join(os.path.dirname(ROOT), "13_ecommerce_project")

    orig = load(os.path.join(A, "models", "sdxl_model_00003_.png"))
    mask_vis = load(os.path.join(T, "mask_vis.jpg"))
    tryon_a = load(os.path.join(T, "tryon_00005_.png"))
    tryon_b = load(os.path.join(T, "tryon_00007_.png"))
    ref_a = load(os.path.join(A, "garments", "ref_A_floral_mini.jpg"))
    ref_b = load(os.path.join(A, "garments", "ref_B_puffsleeve.jpg"))

    # ---- Demo1 拼图 ----
    h = 980
    save(hrow([
        (fit_h(orig, h), "原模特图 · SDXL 生成", "白T+牛仔裤"),
        (fit_h(ref_a, h), "目标服装 · 真实电商图", "碎花吊带裙"),
        (fit_h(tryon_a, h), "换装结果", "脸/姿态/鞋 0 变化"),
    ], gap=16), "plate_tryon_a.jpg")
    save(hrow([
        (fit_h(orig, h), "原模特图", ""),
        (fit_h(ref_b, h), "目标服装 · 真实电商图", "白色花长裙"),
        (fit_h(tryon_b, h), "换装结果", ""),
    ], gap=16), "plate_tryon_b.jpg")
    save(hrow([
        (fit_h(orig, 860), "① 原图", "SDXL 全身模特"),
        (fit_h(mask_vis, 860), "② 服装区遮罩", "人物剪影多边形+羽化"),
        (fit_h(tryon_a, 860), "③ IPAdapter 参考 + 局部重绘", "denoise 1.0 仅遮罩内"),
    ], gap=14), "plate_tryon_process.jpg")

    # ---- Demo2 拼图 ----
    pose_files = [
        ("pose_v5_00007_.png", "行走动势", "skeleton_00001_.png"),
        ("pose_v5_00008_.png", "坐姿", "skeleton_00002_.png"),
        ("pose_v5_00009_.png", "侧身", "skeleton2_00005_.png"),
        ("pose_v5_00003_.png", "回眸", "skeleton2_00003_.png"),
        ("back_final_99902_00001_.png", "背面", "skeleton_00006_.png"),
        ("pose_v5_00006_.png", "站姿", "skeleton2_00006_.png"),
    ]
    pose_imgs = []
    for f, cn, _ in pose_files:
        im = load(os.path.join(P, f), up=1.3)
        pose_imgs.append((im, f"姿态 · {cn}", ""))
    save(grid(pose_imgs, cols=3, gap=12), "plate_pose_grid.jpg", q=88)

    skels = [(cn, load(os.path.join(A, "poses", s), up=1.0)) for _, cn, s in pose_files]
    sk_row = hrow([(fit_h(s, 420), cn, "") for cn, s in skels], gap=10)
    save(sk_row, "plate_pose_skeletons.jpg", q=88)

    # ---- Demo3 拼图 ----
    tee_before = load(os.path.join(B, "redtee_in.png"))
    tee_after = load(os.path.join(B, "blank3_redtee_00003_.png"))
    tee_vis = load(os.path.join(B, "redtee_maskvis.jpg"))
    hh = 900
    save(hrow([
        (fit_h(tee_before, hh), "处理前 · 真实电商图", "花卉印花 + 领标 logo"),
        (fit_h(tee_vis, hh), "图案区遮罩", "印花 + 领标两块区域"),
        (fit_h(tee_after, hh), "处理后 · 光板服装", "纯色面料, 纹理自然"),
    ], gap=14), "plate_blank_tee.jpg")

    dr_before = load(os.path.join(B, "dress_in.png"))
    dr_after = load(os.path.join(B, "dress_blank_00007_.png"))
    save(hrow([
        (fit_h(dr_before, hh), "处理前 · 换装成品(碎花)", ""),
        (fit_h(dr_after, hh), "处理后 · 纯色光板裙", "改款设计, 模特/姿态不变"),
    ], gap=16), "plate_blank_dress.jpg")

    # ---- Demo4 ----
    perfume = load(os.path.join(E, "test_perfume.png"))
    save(label_bar(perfume, "SDXL 电商商品场景图 · 系统实拍输出", "1024×1024 · 9-15s/张"), "plate_perfume.jpg", q=92)

    # ---- 封面图条 ----
    strip = hrow([
        (fit_h(tryon_a, 700), "", ""), (fit_h(tryon_b, 700), "", ""),
        (fit_h(load(os.path.join(P, "pose_v5_00008_.png"), 1.3), 700), "", ""),
        (fit_h(tee_after, 700), "", ""),
    ], gap=10)
    save(strip, "plate_cover_strip.jpg", q=90)

    # ---- 精选图片包 ----
    os.makedirs(PACK, exist_ok=True)
    pack = {
        os.path.join(A, "models", "sdxl_model_00003_.png"): "01_换装_原模特图.png",
        os.path.join(T, "tryon_00005_.png"): "02_换装_效果_碎花吊带裙.png",
        os.path.join(T, "tryon_00007_.png"): "03_换装_效果_白色花长裙.png",
        os.path.join(PLATES, "plate_pose_grid.jpg"): "04_动作裂变_六宫格.jpg",
        os.path.join(B, "redtee_in.png"): "05_光板净化_印花T恤_前.png",
        os.path.join(B, "blank3_redtee_00003_.png"): "06_光板净化_印花T恤_后.png",
        os.path.join(B, "dress_in.png"): "07_光板净化_碎花裙_前.png",
        os.path.join(B, "dress_blank_00007_.png"): "08_光板净化_碎花裙_后.png",
        os.path.join(E, "test_perfume.png"): "09_电商商品图_SDXL系统.png",
    }
    for src, dst in pack.items():
        im = Image.open(src)
        if im.mode in ("RGBA", "P"):
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[3])
            im = bg
        if im.width < 700:
            im = im.resize((int(im.width * 1.6), int(im.height * 1.6)), Image.LANCZOS)
        im.convert("RGB").save(os.path.join(PACK, dst), quality=92)
        print("pack:", dst)

    # ---- 归档中间产物 ----
    os.makedirs(ARCHIVE, exist_ok=True)
    keep = {"tryon_00005_.png", "tryon_00007_.png", "mask.png", "mask_vis.jpg",
            "redtee_in.png", "redtee_mask.png", "redtee_maskvis.jpg", "redtee_filled.png",
            "dress_in.png", "dress_mask_v5.png", "dress_maskvis.jpg", "dress_filled.png",
            "blank3_redtee_00003_.png", "blank3_redtee_00004_.png",
            "dress_blank_00007_.png", "dress_blank_00008_.png", "dress_blank_00009_.png",
            "pose_v5_00003_.png", "pose_v5_00005_.png", "pose_v5_00006_.png",
            "pose_v5_00007_.png", "pose_v5_00008_.png", "pose_v5_00009_.png",
            "pose_v5_00013_.png", "back_final_99902_00001_.png"}
    moved = 0
    for d in (T, P, B):
        for f in os.listdir(d):
            p = os.path.join(d, f)
            if os.path.isfile(p) and f not in keep and not f.startswith("plate"):
                shutil.move(p, os.path.join(ARCHIVE, f))
                moved += 1
    print("archived:", moved)


if __name__ == "__main__":
    main()
