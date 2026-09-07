# -*- coding: utf-8 -*-
"""V13 视频打包: 胶片条(入PDF) + 精选视频包 + reel 混剪
用法: python v13_pack.py [--strips-only|--reel-only]
"""
import os
import shutil
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v13_edit as e

ROOT = e.ROOT
VID = os.path.join(ROOT, "outputs_v2", "video_v13")
PLATES = os.path.join(VID, "plates")
PACK = os.path.join(ROOT, "docs", "精选视频包")
os.makedirs(PLATES, exist_ok=True)
os.makedirs(PACK, exist_ok=True)

# (镜头名, 文件, 视频包中文名, 竖版?, reel字幕)
SELECTED = [
    ("runway_step",  "v13_runway_step_63011_00001_.mp4",  "14_视频_走秀迈步", True,  "走秀迈步 · I2V"),
    ("walk_street",  "v13_walk_street_63021_00001_.mp4",  "15_视频_姿态行走", True,  "姿态行走 · I2V"),
    ("runway_turn",  "v13_runway_turn_63032_00001_.mp4",  "16_视频_回眸", True,  "回眸 · I2V"),
    ("pose_twirl",   "v13_pose_twirl_63042_00001_.mp4",   "17_视频_背身回眸", True,  "背身回眸 · I2V"),
    ("fabric_wind",  "v13_fabric_wind_63051_00001_.mp4",  "18_视频_风吹裙摆", True,  "风吹裙摆 · I2V"),
    ("scene_cream",  "v13_scene_cream_63062_00001_.mp4",  "19_视频_奶油室内", False, "奶油室内 · I2V"),
    ("scene_street", "v13_scene_street_63071_00001_.mp4", "20_视频_街拍行走", False, "街拍行走 · I2V"),
    ("fabric_macro", "v13_fabric_macro_63082_00001_.mp4", "21_视频_面料微距", False, "面料微距 · I2V"),
    ("flf_changeout", "v13flf_00001_.mp4", "22_视频_首尾帧换装转场", False, "首尾帧换装转场 · FLF2V 14B"),
    ("l14b_compare", "v13l14b_00001_.mp4", "23_视频_14B加速路线", False, "14B Lightning 4步"),
]
REEL = os.path.join(PACK, "24_视频_reel混剪.mp4")


def strips():
    """胶片条: 竖版视频 1x6 单行, 横版 3x2 两行"""
    for name, fn, _cn, portrait, _lab in SELECTED:
        p = os.path.join(VID, fn)
        if not os.path.exists(p):
            print("skip strip (missing):", fn)
            continue
        dst = os.path.join(PLATES, f"strip_{name}.jpg")
        e.strip(p, dst, cols=6 if portrait else 3)
        print("strip:", name, "1x6" if portrait else "3x2")


def pack():
    for name, fn, cn, _p, _lab in SELECTED:
        p = os.path.join(VID, fn)
        if not os.path.exists(p):
            print("skip pack (missing):", fn)
            continue
        shutil.copy2(p, os.path.join(PACK, cn + ".mp4"))
        print("pack:", cn)


def ab_plate():
    """A/B 步数对照条(评测页): 单行 4 帧并排"""
    a = os.path.join(VID, "v13_runway_front_63001_00001_.mp4")
    b = os.path.join(VID, "v13_runway_front_63001_00002_.mp4")
    if not (os.path.exists(a) and os.path.exists(b)):
        print("skip ab_plate")
        return
    import imageio
    W = 460
    # 排列: a第24帧 | b第24帧 | a末帧 | b末帧 (a=12步, b=20步)
    cells = []
    for p in (a, b):
        rd = imageio.get_reader(p)
        for i in (24, 47):
            fr = Image.fromarray(rd.get_data(i))
            fr = fr.resize((W, int(W * fr.height / fr.width)), Image.LANCZOS)
            cells.append(fr)
        rd.close()
    labs = ["12 步 · 第 24 帧", "20 步 · 第 24 帧", "12 步 · 末帧 · 149s", "20 步 · 末帧 · 203s"]
    ch = cells[0].height
    grid = Image.new("RGB", (W * 4 + 3 * 12, ch + 40), "white")
    d = ImageDraw.Draw(grid)
    f = e.font(22)
    for i, (c, lab) in enumerate(zip(cells, labs)):
        x = i * (W + 12)
        grid.paste(c, (x, 36))
        d.text((x + 2, 6), lab, fill=e.INK, font=f)
    grid.save(os.path.join(PLATES, "strip_ab_steps.jpg"), quality=90)
    print("ab_plate ok (1x4)")


def flf_plate():
    """FLF 首尾帧对照(案例页): 首帧/视频过渡帧/尾帧 单行"""
    v = os.path.join(VID, "v13flf_00001_.mp4")
    a = os.path.join(VID, "_starts", "m_dress_brown_s1280x720A.png")
    b = os.path.join(VID, "_starts", "v10_tryon_best_hd_s1280x720B.png")
    if not os.path.exists(v):
        print("skip flf_plate")
        return
    import imageio
    rd = imageio.get_reader(v)
    mid = Image.fromarray(rd.get_data(36))
    rd.close()
    W = 612
    cells = [Image.open(a), mid, Image.open(b)]
    cells = [c.resize((W, int(W * 720 / 1280)), Image.LANCZOS) for c in cells]
    labs = ["首帧 · 换装前(真实输入)", "第 36 帧 · 模型过渡", "尾帧 · 换装后(管线成片)"]
    ch = cells[0].height
    grid = Image.new("RGB", (W * 3 + 2 * 12, ch + 36), "white")
    d = ImageDraw.Draw(grid)
    f = e.font(22)
    for i, (c, lab) in enumerate(zip(cells, labs)):
        x = i * (W + 12)
        grid.paste(c, (x, 32))
        d.text((x + 2, 5), lab, fill=e.INK, font=f)
    grid.save(os.path.join(PLATES, "strip_flf.jpg"), quality=90)
    print("flf_plate ok")


def l14b_plate():
    """14B Lightning 帧对照(评测页): 与 5B 同镜头首帧/中帧对比"""
    v14 = os.path.join(VID, "v13l14b_00001_.mp4")
    v5 = os.path.join(VID, "v13_runway_front_63001_00002_.mp4")
    if not os.path.exists(v14):
        print("skip l14b_plate")
        return
    import imageio
    cells = []
    labs = []
    for tag, path, idx in [("14B · 首帧", v14, 0), ("14B · 第 40 帧", v14, 40),
                           ("5B · 首帧", v5, 0) if os.path.exists(v5) else ("5B · 首帧", v14, 0),
                           ("5B · 第 24 帧", v5, 24) if os.path.exists(v5) else ("5B · 第 24 帧", v14, 40)]:
        rd = imageio.get_reader(path)
        n = rd.count_frames()
        fr = Image.fromarray(rd.get_data(min(idx, n - 1)))
        rd.close()
        cells.append(fr)
        labs.append(tag)
    W = 612
    cells = [c.resize((W, int(W * 720 / 1280)), Image.LANCZOS) for c in cells]
    ch = cells[0].height
    grid = Image.new("RGB", (W * 4 + 3 * 12, ch + 36), "white")
    d = ImageDraw.Draw(grid)
    f = e.font(22)
    for i, (c, lab) in enumerate(zip(cells, labs)):
        x = i * (W + 12)
        grid.paste(c, (x, 32))
        d.text((x + 2, 5), lab, fill=e.INK, font=f)
    grid.save(os.path.join(PLATES, "strip_14b_vs_5b.jpg"), quality=90)
    print("l14b_plate ok")


def cards():
    """reel 字幕卡"""
    defs = [
        ("c_open", "AI 视频生成", "Wan2.2 端侧出片 · RTX 4070 Ti SUPER 单卡"),
        ("c_scene", "场景与面料动态", "图生视频 · 1280×704"),
        ("c_flf", "首尾帧换装转场", "Wan2.1 FLF2V 14B"),
        ("c_t2v14b", "14B Lightning 加速路线", "lightx2v 4步蒸馏 LoRA"),
        ("c_end", "AI 视频生成 · 完整链路", "静图管线同源身份锚 · 五维审片择优"),
    ]
    for key, t, s in defs:
        e.card(os.path.join(VID, "cards", key + ".png"), t, s)
    print("cards ok")


def reel():
    """reel: 卡+片 conform->fade->concat (24fps 归一)"""
    seq = [("card", "c_open", 1.4)]
    for name, fn, cn, p, lab in SELECTED:
        if name in ("runway_step", "walk_street", "runway_turn", "pose_twirl"):
            seq.append(("clip", name, fn))
    seq.append(("card", "c_scene", 1.2))
    for name, fn, cn, p, lab in SELECTED:
        if name in ("fabric_wind", "scene_cream", "scene_street", "fabric_macro"):
            seq.append(("clip", name, fn))
    seq.append(("card", "c_flf", 1.2))
    seq.append(("clip", "flf_changeout", "v13flf_00001_.mp4"))
    seq.append(("card", "c_t2v14b", 1.2))
    seq.append(("clip", "l14b_compare", "v13l14b_00001_.mp4"))
    seq.append(("card", "c_end", 1.8))
    tmp = []
    for item in seq:
        if item[0] == "card":
            png = os.path.join(VID, "cards", item[1] + ".png")
            mp4 = os.path.join(VID, f"_card_{item[1]}.mp4")
            e.still_card(png, hold=item[2], dst=mp4)
            tmp.append(e.fade(mp4, fin=0.25, fout=0.25))
        else:
            p = os.path.join(VID, item[2])
            if not os.path.exists(p):
                print("reel skip (missing):", item[2])
                continue
            c = os.path.join(VID, f"_conf_{item[1]}.mp4")
            e.conform(p, c)
            tmp.append(e.fade(c, fout=0.28, fin=0.22))
    e.reel(REEL, tmp)
    print("reel:", e.probe(REEL))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode != "--reel-only":
        cards()
        strips()
        pack()
        ab_plate()
        flf_plate()
        l14b_plate()
    reel()
    print("PACK DONE")
