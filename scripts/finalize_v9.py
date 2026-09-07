# -*- coding: utf-8 -*-
"""V9 最终化: 对选定成片逐一超分并命名对齐 package_v9 约定 (<stem>_hd.png)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image

ROOT = r"."
V9 = os.path.join(ROOT, "outputs_v2", "v9")
HD9 = os.path.join(ROOT, "outputs_v2", "upscaled_v9")
os.makedirs(HD9, exist_ok=True)

STEMS = [
    "v9_tryon_full_91121",
    "v9_scene_med_91252",
    "v9_street3",
    "v9_pose_glasses_hip",
    "v9_pose_glasses_walk2",
    "v9_pose_glasses_side",
    "v9_pose_back_91402",
    "v9_pose_glasses_stand",
    "v9_white4",
]


def upscale_to_hd(path, stem):
    up = comfy_api.upload_image(path)
    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": up["name"]}},
        "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x-UltraSharp.pth"}},
        "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "SaveImage", "inputs": {"filename_prefix": "tmpup", "images": ["3", 0]}},
    }
    paths = comfy_api.run(wf, HD9, timeout=600)
    src = paths[0] if paths else None
    im = Image.open(src)
    if im.width > 2600:
        im = im.resize((2600, int(im.height * 2600 / im.width)), Image.LANCZOS)
    dst = os.path.join(HD9, stem + "_hd.png")
    im.save(dst)
    if src and os.path.abspath(src) != os.path.abspath(dst):
        os.remove(src)
    print(stem, "->", dst, im.size, flush=True)


if __name__ == "__main__":
    comfy_api.wait_server()
    for stem in STEMS:
        dst = os.path.join(HD9, stem + "_hd.png")
        if os.path.exists(dst):
            print("skip", stem)
            continue
        p = os.path.join(V9, stem + "_00001_.png")
        if not os.path.exists(p):
            print("MISSING", stem)
            continue
        upscale_to_hd(p, stem)
    print("FINALIZE DONE")
