# -*- coding: utf-8 -*-
"""脚本化超分: 4x-UltraSharp via ComfyUI API (补齐 V4 以来未脚本化的缺口)
用法: python upscale_api.py <输入文件或目录> [输出目录]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image

MODEL = "4x-UltraSharp.pth"


def upscale_one(path, outdir):
    up = comfy_api.upload_image(path)
    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": up["name"]}},
        "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": MODEL}},
        "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "SaveImage", "inputs": {"filename_prefix": "hd", "images": ["3", 0]}},
    }
    outs = comfy_api.run(wf, outdir, timeout=900)
    paths = []
    for node_out in outs.values():
        for img in node_out.get("images", []):
            paths.append(os.path.join(outdir, img["filename"]))
    # 限宽 2600px(电商主图规格), LANCZOS 缩回并轻锐化
    for p in paths:
        im = Image.open(p)
        if im.width > 2600:
            im = im.resize((2600, int(im.height * 2600 / im.width)), Image.LANCZOS)
            im.save(p)
    return paths


def main():
    src = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(src), "upscaled")
    os.makedirs(outdir, exist_ok=True)
    files = [src] if os.path.isfile(src) else [
        os.path.join(src, f) for f in sorted(os.listdir(src))
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    for f in files:
        print(f, "->", upscale_one(f, outdir))


if __name__ == "__main__":
    main()
