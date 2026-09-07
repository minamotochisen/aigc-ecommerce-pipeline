# -*- coding: utf-8 -*-
"""V11 HD 区域修复驱动: 对指定 HD 图的 box 区域做定向重绘回贴
用法: python v11_regionfix.py"""
import json
import os
import sys

sys.path.insert(0, r".\scripts")
import comfy_api
comfy_api.wait_server()
from v10_qwen2511 import NEGATIVE, workflow, OUT, PER_RUN
from PIL import Image, ImageFilter

HD = r".\outputs_v2\upscaled_v10"

HAIR_P = ("修复这张照片中人物的头发：发丝走向自然、根根分明，有真实的头发光泽与细节，"
          "消除任何玻璃状、蜡状、涂抹状的发丝伪影。严格保持脸部、五官、眼镜、姿势、构图、"
          "服装和背景完全不变，只修复头发。真实人像摄影质感。")
SHOE_P = ("修复这张照片中人物的双脚与鞋子：双脚结构正确、脚趾自然，左右鞋子同款成对、"
          "款式颜色一致（白色平底/低跟凉鞋），脚与鞋遮挡关系正确。严格保持腿部姿势、裤裙、"
          "地面、光影和构图完全不变，只修复双脚鞋子。真实人像摄影质感。")
WATCH_P = ("修复这张照片中人物手腕上的手表：表带与表盘细节清晰真实、佩戴自然贴合手腕。"
           "严格保持手部形态、手臂姿势、服装和背景完全不变，只修复手表。真实人像摄影质感。")


def regionfix(img_path, box, prompt, seed, work=896, tag="fix"):
    im = Image.open(img_path).convert("RGB")
    W, H = im.size
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * 0.25), int(bh * 0.25)
    cx1, cy1 = max(0, x1 - mx), max(0, y1 - my)
    cx2, cy2 = min(W, x2 + mx), min(H, y2 + my)
    crop = im.crop((cx1, cy1, cx2, cy2))
    scale = work / max(crop.size)
    big = crop.resize((int(crop.size[0] * scale) // 16 * 16,
                       int(crop.size[1] * scale) // 16 * 16), Image.LANCZOS)
    src = os.path.join(OUT, "_region_in.png")
    big.save(src)
    wf = workflow(prompt, NEGATIVE, [comfy_api.upload_image(src)], seed)
    wf["12"]["inputs"]["filename_prefix"] = "v11_region"
    comfy_api.run_watchdog(wf, OUT, per_run=PER_RUN)
    outs = sorted([f for f in os.listdir(OUT) if f.startswith("v11_region") and f.endswith(".png")],
                  key=lambda f: os.path.getmtime(os.path.join(OUT, f)))
    fixed = Image.open(os.path.join(OUT, outs[-1])).convert("RGB").resize(crop.size, Image.LANCZOS)
    mask = Image.new("L", crop.size, 0)
    mask.paste(Image.new("L", (bw, bh), 255), (x1 - cx1, y1 - cy1))
    mask = mask.filter(ImageFilter.GaussianBlur(14))
    im.paste(fixed, (cx1, cy1), mask)
    dst = os.path.join(OUT, "region_%s_%d.png" % (tag, seed))
    im.save(dst)
    print("regionfix ->", dst, flush=True)
    return dst


JOBS = [
    # (hd文件, box, prompt, tag)
    (HD + r"\v10_tryon_best_hd.png", [700, 80, 1950, 950], HAIR_P, "hair"),
    (HD + r"\v10_tryon_best_hd.png", [1290, 1500, 1880, 2200], WATCH_P, "watch"),
    (HD + r"\v10_scene_med_hd.png", [700, 80, 1950, 950], HAIR_P, "hair"),
    (HD + r"\v10_scene_street_hd.png", [700, 80, 1950, 950], HAIR_P, "hair"),
    (HD + r"\v10_pose_walk_hd.png", [650, 2950, 1950, 3460], SHOE_P, "shoe"),
    (HD + r"\v10_pose_stand_hd.png", [650, 2950, 1950, 3460], SHOE_P, "shoe"),
]

if __name__ == "__main__":
    seed = 92600
    for path, box, prompt, tag in JOBS:
        seed += 1
        cur = regionfix(path, box, prompt, seed, tag=tag)
        # 直接回写 HD 文件
        import shutil
        shutil.copy2(cur, path)
        print("updated", path, flush=True)
    print("REGION FIX DONE", flush=True)
