# -*- coding: utf-8 -*-
"""V10 视频化: 用 V10 换装成片作首帧, 复用 v9_video 的 Wan2.2 TI2V 工作流
用法: python v10_video.py [seed] [length]
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v9_video

ROOT = v9_video.ROOT
HD10 = os.path.join(ROOT, "outputs_v2", "upscaled_v10")
OUT = os.path.join(ROOT, "outputs_v2", "video")
os.makedirs(OUT, exist_ok=True)
START_IMG = os.path.join(HD10, "v10_tryon_best_hd.png")


def main():
    im = Image.open(START_IMG).convert("RGB")
    W, H = 1280, 704
    r = max(W / im.width, H / im.height)
    im2 = im.resize((int(im.width * r + 0.5), int(im.height * r + 0.5)), Image.LANCZOS)
    x0 = (im2.width - W) // 2
    y0 = max(0, int((im2.height - H) * 0.25))
    im2 = im2.crop((x0, y0, x0 + W, y0 + H))
    start_path = os.path.join(HD10, "c1_start_landscape.png")
    im2.save(start_path)
    v9_video.workflow.__globals__["START_IMG_LSC"] = start_path
    print("start frame:", im2.size)
    comfy_api.upload_image(start_path)

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 53001
    length = int(sys.argv[2]) if len(sys.argv) > 2 else 49
    wf = v9_video.workflow(seed, length=length, width=W, height=H)
    wf["12"]["inputs"]["filename_prefix"] = "v10video"
    # 抽 6 帧出胶片条素材
    for i, idx in enumerate([0, 9, 19, 29, 39, 48]):
        n1, n2 = 30 + i * 2, 31 + i * 2
        wf[str(n1)] = {"class_type": "ImageFromBatch", "inputs": {
            "image": ["10", 0], "batch_index": idx, "length": 1}}
        wf[str(n2)] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"v10frame_{i}", "images": [[str(n1), 0]]}}
    print("gen:", comfy_api.run(wf, OUT, timeout=3000))


if __name__ == "__main__":
    main()
