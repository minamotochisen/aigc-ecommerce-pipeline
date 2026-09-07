# -*- coding: utf-8 -*-
"""Demo3 图像净化与光板处理 — 混合管线 v3

纯扩散重绘在大面积去图案时会出现色差/纹理错配/领口漂移问题,
改用两段式:
  1) cv2.inpaint(Telea) 用周围面料色填充图案区域 -> 颜色/明暗完全一致
  2) 低 denoise(0.4-0.5) 扩散精修 -> 恢复面料纹理与褶皱, 结构锁定不漂移
案例: 红T去印花+领标 / 深蓝T平铺图去图案 / 碎花裙改纯色光板裙
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "outputs", "blank")

CKPT = "realisticVisionV60B1_v51HyperVAE.safetensors"

CASES = {
    "redtee": {
        "src": os.path.join(ROOT, "assets", "garments", "cand_redtee_floral.png"),
        "white_bg": True,
        "work": (640, 768),
        "dn": 0.4,
        "polys_src": [
            [(258, 290), (768, 285), (778, 470), (600, 512), (275, 516), (248, 420)],  # 印花
            [(452, 180), (528, 180), (528, 235), (452, 235)],  # 领标 logo(紧贴, 不碰领圈)
        ],
        "prompt": "smooth crimson red cotton jersey fabric texture, soft subtle folds, "
                  "clean t-shirt surface, product photography",
    },
    "dress": {
        "src": os.path.join(ROOT, "outputs", "tryon", "tryon_00005_.png"),
        "white_bg": False,
        "work": (528, 768),
        "dn": 0.5,
        "polys_src": [
            # 躯干部分(避开右侧手臂)
            [(200, 215), (318, 213), (322, 320), (300, 333), (205, 333), (196, 280)],
            # 裙摆(含下缘花卉, 避开手部)
            [(196, 325), (322, 325), (322, 340), (327, 342), (331, 380), (347, 383),
             (348, 422), (255, 430), (192, 415)],
        ],
        "prompt": "smooth dark navy blue dress fabric, elegant natural drape and folds, "
                  "solid color, e-commerce fashion photography",
    },
}

NEG = "print, pattern, logo, text, letters, graphic, flowers, worst quality, low quality, blurry"


def load_src(case):
    src = Image.open(case["src"])
    if case["white_bg"] and src.mode == "RGBA":
        base = Image.new("RGB", src.size, "white")
        base.paste(src, mask=src.split()[3])
        return base
    return src.convert("RGB")


def build_masks(case):
    """返回 (工作分辨率原图, 硬遮罩L, 可视化, cv2填充图)"""
    src = load_src(case)
    W, H = case["work"]
    m = Image.new("L", src.size, 0)
    d = ImageDraw.Draw(m)
    for poly in case["polys_src"]:
        d.polygon(poly, fill=255)
    src_w = src.resize((W, H), Image.LANCZOS)
    m_w = m.resize((W, H), Image.LANCZOS).point(lambda p: 255 if p > 100 else 0)
    # 环带中位色填充: 用遮罩边缘向内 31px 环带(仍属面料)的中位色填充整个遮罩区,
    # 颜色/明暗与面料一致, 杜绝 Telea 从背景/皮肤渗色
    arr = np.array(src_w)
    mask_np = np.array(m_w) > 100
    eroded = cv2.erode(mask_np.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
    band = mask_np & ~eroded
    if band.sum() > 50:
        med = np.median(arr[band].reshape(-1, 3), axis=0)
    else:
        med = np.median(arr[mask_np].reshape(-1, 3), axis=0)
    filled = arr.copy()
    filled[mask_np] = med + np.random.default_rng(7).normal(0, 2.0, (int(mask_np.sum()), 3))
    filled = np.clip(filled, 0, 255).astype(np.uint8)
    vis = src_w.copy()
    red = Image.new("RGB", vis.size, (255, 40, 40))
    vis = Image.composite(red, vis, m_w.point(lambda p: int(p * 0.5)))
    return src_w, m_w, vis, Image.fromarray(filled)


def workflow(img_file, mask_file, prompt, seed, W, H, denoise=0.45):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": img_file}},
        "3": {"class_type": "ImageScale", "inputs": {"image": ["2", 0], "width": W, "height": H,
                                                     "upscale_method": "lanczos", "crop": "disabled"}},
        "4": {"class_type": "LoadImageMask", "inputs": {"image": mask_file, "channel": "red"}},
        "5": {"class_type": "GrowMask", "inputs": {"mask": ["4", 0], "expand": 10, "tapered_corners": True}},
        "5b": {"class_type": "MaskToImage", "inputs": {"mask": ["5", 0]}},
        "5c": {"class_type": "ImageBlur", "inputs": {"image": ["5b", 0], "blur_radius": 9, "sigma": 4.0}},
        "5d": {"class_type": "ImageToMask", "inputs": {"image": ["5c", 0], "channel": "red"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["3", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["8", 0], "mask": ["5d", 0]}},
        "10": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 6.0,
                                                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                                                    "denoise": denoise, "model": ["1", 0],
                                                    "positive": ["6", 0], "negative": ["7", 0],
                                                    "latent_image": ["9", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 2]}},
        "12": {"class_type": "ImageCompositeMasked", "inputs": {"destination": ["3", 0], "source": ["11", 0],
                                                                "mask": ["5d", 0], "x": 0, "y": 0,
                                                                "resize_source": False}},
        "13": {"class_type": "SaveImage", "inputs": {"filename_prefix": "blank3", "images": ["12", 0]}},
    }


if __name__ == "__main__":
    comfy_api.wait_server()
    os.makedirs(OUT, exist_ok=True)
    for key, case in CASES.items():
        src_w, m_w, vis, filled = build_masks(case)
        img_p = os.path.join(OUT, f"{key}_filled.png")
        mask_p = os.path.join(OUT, f"{key}_mask.png")
        filled.save(img_p)
        m_w.save(mask_p)
        vis.save(os.path.join(OUT, f"{key}_maskvis.jpg"), quality=90)
        W, H = case["work"]
        for seed in (55001, 55002):
            up_img = comfy_api.upload_image(img_p)
            up_mask = comfy_api.upload_image(mask_p)
            wf = workflow(up_img["name"], up_mask["name"], case["prompt"], seed, W, H,
                          denoise=case["dn"])
            wf["13"]["inputs"]["filename_prefix"] = f"blank3_{key}"
            paths = comfy_api.run(wf, OUT, timeout=600)
            print(key, seed, paths)
