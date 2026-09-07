# -*- coding: utf-8 -*-
"""V13 视频剪辑/审片工具 (ffmpeg = imageio_ffmpeg 自带)
子命令:
  conform <in> <out>   归一到 1280x704@24fps h264, 竖版模糊背景垫底
  card    <out.png> <title> <sub>    1280x704 字幕卡
  reel    <out.mp4> <clip...>        逐段淡入淡出 + concat(输入须已 conform/card 转序列)
  strip   <in> <out.jpg>             6帧胶片条(2x3)
  gif     <in> <out.gif>             预览 GIF
  inspect <in> [outdir]              首中尾3帧+规格(审片用)
"""
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VID = os.path.join(ROOT, "outputs_v2", "video_v13")
os.makedirs(VID, exist_ok=True)
FF = __import__("imageio_ffmpeg").get_ffmpeg_exe()
CANVAS = (1280, 704)
FPS = 24
FONT_TTC = "C:/Windows/Fonts/msyh.ttc"
INK = (26, 36, 56)

_tc = {}


def font(size):
    size = max(14, int(size))
    if size not in _tc:
        _tc[size] = ImageFont.truetype(FONT_TTC, size)
    return _tc[size]


def ff(args, timeout=600):
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-1500:]}")
    return r.stderr


def probe(path):
    """仅用 ffmpeg -i 解析时长/帧率/分辨率"""
    r = subprocess.run([FF, "-i", path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    s = r.stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    fps = re.search(r"([\d.]+) fps", s)
    wh = re.search(r"Video:.*?, (\d+)x(\d+)", s)
    d = None
    if dur:
        d = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))
    return dict(seconds=d, fps=float(fps.group(1)) if fps else None,
                size=(int(wh.group(1)), int(wh.group(2))) if wh else None)


def conform(src, dst, W=CANVAS[0], H=CANVAS[1], fps=FPS):
    """任意比例 -> WxH@fps: 横版等比缩放加黑边微模糊底, 竖版同理; 统一 h264 yuv420p"""
    fg = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black")
    ff(["-i", src, "-vf", fg, "-r", str(fps), "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-an", dst])


def card(dst, title, sub=""):
    W, H = CANVAS
    im = Image.new("RGB", (W, H), (247, 246, 243))
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - 6, W, H], fill=INK)
    f1, f2 = font(64), font(30)
    d.text((90, H // 2 - 70), title, fill=INK, font=f1)
    if sub:
        d.text((92, H // 2 + 24), sub, fill=(110, 120, 136), font=f2)
    im.save(dst, quality=92)
    return dst


def still_card(src_png, hold=1.2, dst=None):
    """PNG 卡 -> 定长视频段(24fps)"""
    dst = dst or src_png.rsplit(".", 1)[0] + ".mp4"
    n = max(2, round(hold * FPS))
    ff(["-loop", "1", "-i", src_png, "-frames:v", str(n), "-vf", "format=yuv420p",
        "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", dst])
    return dst


def fade(src, dur=None, fout=0.35, fin=0.35, dst=None):
    """首尾淡入淡出(黑场过渡)"""
    dst = dst or src.rsplit(".", 1)[0] + "_f.mp4"
    d = dur or probe(src)["seconds"]
    fo = max(0.0, d - fout)
    ff(["-i", src, "-vf",
        f"fade=t=in:st=0:d={fin},fade=t=out:st={fo:.3f}:d={fout},format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-an", dst])
    return dst


def reel(dst, clips):
    """clips: 已 fade 的同规格 mp4; concat 后统一重编码归一帧率(防混帧率)"""
    lst = os.path.join(VID, "_concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c).replace(chr(92), '/')}'\n")
    tmp = dst.replace(".mp4", "_raw.mp4")
    ff(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", tmp])
    ff(["-i", tmp, "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-an", dst])
    os.remove(tmp)
    return dst


def strip(src, dst, idxs=(0, 9, 19, 29, 39, 47), w=640, cols=3):
    """精确抽指定帧号列表拼胶片条; cols=6 单行横条(竖版视频), cols=3 两行(横版视频)"""
    import imageio
    rd = imageio.get_reader(src)
    n = rd.count_frames()
    cells = []
    for i in idxs:
        if i >= n:
            i = n - 1
        fr = Image.fromarray(rd.get_data(int(i)))
        fr = fr.resize((w, int(w * fr.height / fr.width)), Image.LANCZOS)
        cells.append(fr)
    rd.close()
    rows = (len(cells) + cols - 1) // cols
    cw = max(c.width for c in cells)
    ch = max(c.height for c in cells)
    grid = Image.new("RGB", (cw * cols + (cols - 1) * 8, ch * rows + (rows - 1) * 8), "white")
    for i, fr in enumerate(cells[:cols * rows]):
        r, c = divmod(i, cols)
        grid.paste(fr, (c * (cw + 8), r * (ch + 8)))
    grid.save(dst, quality=90)
    return dst, n


def gif(src, dst, fps=12, w=440):
    ff(["-i", src, "-vf", f"fps={fps},scale={w}:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse",
        "-loop", "0", dst], timeout=300)
    return dst


def inspect(src, outdir=None):
    outdir = outdir or os.path.join(VID, "_inspect")
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(src))[0]
    rd = __import__("imageio").get_reader(src)
    n = rd.count_frames()
    picks = [0, n // 2, n - 2]
    outs = []
    for i in picks:
        p = os.path.join(outdir, f"{stem}_f{i}.png")
        Image.fromarray(rd.get_data(int(i))).save(p)
        outs.append(p)
    rd.close()
    print(stem, probe(src), "frames:", n)
    return outs


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "conform":
        conform(sys.argv[2], sys.argv[3])
    elif a == "card":
        card(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif a == "reel":
        reel(sys.argv[2], sys.argv[3:])
    elif a == "strip":
        strip(sys.argv[2], sys.argv[3])
    elif a == "gif":
        gif(sys.argv[2], sys.argv[3])
    elif a == "inspect":
        inspect(sys.argv[2])
    print("OK")
