# -*- coding: utf-8 -*-
"""V4 CatVTON (ICLR 2025) 专用 VTON 对比测试
输入: 模特图 + 服装区域遮罩 + 服装参考图 → 换装
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api

ROOT = r"."
OUT = os.path.join(ROOT, "outputs_v2", "catvton")

PERSON = os.path.join(ROOT, "outputs_v2", "tryon", "case1_dressfloral_in.png")   # 模特图 896x1184
MASK = os.path.join(ROOT, "outputs_v2", "tryon", "case1_dressfloral_mask.png")   # 服装遮罩
GARMENT = os.path.join(ROOT, "assets_v2", "garments", "v2ref_case1_dressfloral.jpg")


def workflow(person_name, mask_name, garment_name, seed):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": person_name}},
        "2": {"class_type": "LoadImageMask", "inputs": {"image": mask_name, "channel": "red"}},
        "3": {"class_type": "LoadImage", "inputs": {"image": garment_name}},
        "4": {"class_type": "CatVTONWrapper", "inputs": {
            "image": ["1", 0], "mask": ["2", 0], "refer_image": ["3", 0],
            "mask_grow": 25, "mixed_precision": "fp16", "seed": seed,
            "steps": 40, "cfg": 2.5}},
        "5": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v4cat", "images": ["4", 0]}},
    }


if __name__ == "__main__":
    comfy_api.wait_server()
    up_p = comfy_api.upload_image(PERSON)
    up_m = comfy_api.upload_image(MASK)
    up_g = comfy_api.upload_image(GARMENT)
    for seed in (79001, 79002):
        up_m = comfy_api.upload_image(MASK, name=f"catvton_mask_{seed}.png")
        wf = workflow(up_p["name"], up_m["name"], up_g["name"], seed)
        wf["5"]["inputs"]["filename_prefix"] = f"v4cat_{seed}"
        print(seed, comfy_api.run(wf, OUT, timeout=1800))
