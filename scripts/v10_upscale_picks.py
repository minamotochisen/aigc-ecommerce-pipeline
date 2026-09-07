# -*- coding: utf-8 -*-
"""V10 终选图超分: 内联 4x-UltraSharp (处理 comfy_api.run 的 list 返回)"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image

ROOT = r"."
V10 = os.path.join(ROOT, "outputs_v2", "v10")
HD10 = os.path.join(ROOT, "outputs_v2", "upscaled_v10")
os.makedirs(HD10, exist_ok=True)

PICKS = {
    "tryon_best.png": "v10_tryon_best",
    "v10_scene_mmasked_91810_00001_.png": "v10_scene_med",
    "v10_scene_smasked_91812_00001_.png": "v10_scene_street",
    "v10_pose_handonhip_91715_00001_.png": "v10_pose_hip",
    "v10_pose_walking_91725_00001_.png": "v10_pose_walk",
    "v10_pose_side_91736_00001_.png": "v10_pose_side",
    "v10_pose_front_91767_00001_.png": "v10_pose_stand",
    "v10_pose_stand34_91751_00001_.png": "v10_pose_34",
}


def upscale_inline(path, out):
    up = comfy_api.upload_image(path)
    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": up["name"]}},
        "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x-UltraSharp.pth"}},
        "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "SaveImage", "inputs": {"filename_prefix": "hdtmp", "images": ["3", 0]}},
    }
    comfy_api.run(wf, HD10, timeout=900)
    cands = sorted(glob.glob(os.path.join(HD10, "hdtmp_*.png")),
                   key=os.path.getmtime, reverse=True)
    if not cands:
        raise RuntimeError("no upscaled output")
    os.replace(cands[0], out)
    im = Image.open(out)
    if im.width > 2600:
        im = im.resize((2600, int(im.height * 2600 / im.width)), Image.LANCZOS)
        im.save(out)


def main():
    # 认领遗留的 hd_0000*.png (按 PICKS 顺序: tryon_best 已认领, hd_00002_ = med)
    legacy = sorted(glob.glob(os.path.join(HD10, "hd_*.png")), key=os.path.getmtime)
    order = [d for d in PICKS.values() if not os.path.exists(os.path.join(HD10, d + "_hd.png"))]
    for src_stem, dst in zip(legacy, order):
        os.replace(src_stem, os.path.join(HD10, dst + "_hd.png"))
        print("claimed legacy ->", dst, flush=True)
    for src, dst in PICKS.items():
        out = os.path.join(HD10, dst + "_hd.png")
        if os.path.exists(out):
            print("skip", dst, flush=True)
            continue
        upscale_inline(os.path.join(V10, src), out)
        print("HD:", dst, flush=True)


if __name__ == "__main__":
    main()
