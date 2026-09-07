# -*- coding: utf-8 -*-
"""V5 视频后处理: 找最新生成的走秀视频 → 拷贝/抽帧/胶片条/GIF → 图片包"""
import glob
import os
import shutil

import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = r"."
COMFY_OUT = r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\output"
OUT = os.path.join(ROOT, "outputs_v2", "video")
PACK = os.path.join(ROOT, "docs", "精选图片包")
PLATES = os.path.join(ROOT, "outputs_v2", "plates")
INK, MUTED = (26, 36, 56), (110, 120, 136)
FONT_TTC = "C:/Windows/Fonts/msyh.ttc"


def font(size):
    return ImageFont.truetype(FONT_TTC, max(14, int(size)))


def find_newest_mp4():
    cands = sorted(glob.glob(os.path.join(COMFY_OUT, "**", "*.mp4"), recursive=True),
                   key=os.path.getmtime)
    return cands[-1] if cands else None


def frames_from_video(mp4, n=6):
    cap = cv2.VideoCapture(mp4)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idxs = [int(round(i * (total - 1) / (n - 1))) for i in range(n)]
    out = []
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if ok:
            out.append(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    cap.release()
    return out, total


def main():
    mp4 = find_newest_mp4()
    assert mp4, "未找到生成的视频"
    print("video:", mp4)
    os.makedirs(OUT, exist_ok=True)
    mp4_dst = os.path.join(OUT, "walkshow.mp4")
    shutil.copy(mp4, mp4_dst)

    frs, total = frames_from_video(mp4_dst, 6)
    print("frames:", len(frs), "total:", total)

    # GIF (作品集/聊天窗口可发)
    gifs = []
    step = max(1, len(frs) * 3 // 24)
    cap = cv2.VideoCapture(mp4_dst)
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % (step * 3) == 0:
            im = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
            g = Image.fromarray(im)
            g.thumbnail((420, 760))
            gifs.append(g)
        i += 1
    cap.release()
    if gifs:
        gifs[0].save(os.path.join(OUT, "walkshow.gif"), save_all=True,
                     append_images=gifs[1:], duration=280, loop=0, quality=85)
        print("gif saved:", len(gifs), "frames")

    # 胶片条拼图 (3 关键帧)
    labels = ["起始帧", "中间帧", "结尾帧"]
    picks = [frs[0], frs[len(frs) // 2], frs[-1]]
    cells = []
    for im, lb in zip(picks, labels):
        p = Image.fromarray(im)
        p = p.resize((360, int(360 * p.height / p.width)), Image.LANCZOS)
        bar = 56
        c = Image.new("RGB", (p.width, p.height + bar), "white")
        c.paste(p, (0, 0))
        dd = ImageDraw.Draw(c)
        dd.rectangle([0, p.height, p.width, p.height + 3], fill=INK)
        dd.text((12, p.height + 12), lb, fill=INK, font=font(22))
        cells.append(c)
    strip = Image.new("RGB", (sum(c.width for c in cells) + 28, max(c.height for c in cells)), "white")
    x = 0
    for c in cells:
        strip.paste(c, (x, 0)); x += c.width + 14
    strip.save(os.path.join(PLATES, "plate_video_strip.jpg"), quality=90)
    print("strip saved")

    # 图片包
    os.makedirs(PACK, exist_ok=True)
    shutil.copy(mp4_dst, os.path.join(PACK, "11_模特视频化_走秀视频.mp4"))
    strip.save(os.path.join(PACK, "12_模特视频化_关键帧条.jpg"), quality=90)
    if gifs:
        gifs[0].save(os.path.join(PACK, "13_模特视频化_预览.gif"), save_all=True,
                     append_images=gifs[1:], duration=280, loop=0)
    print("pack updated")


if __name__ == "__main__":
    main()
