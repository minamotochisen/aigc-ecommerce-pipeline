# -*- coding: utf-8 -*-
"""V2 Demo3 图像净化与光板处理 (SDXL 混合管线: 环带中位色填充 + 低强度扩散纹理精修)

案例1 awet_tee:  白T胸前"AWET"文字印花+领标 -> 纯白光板T
案例2 red_tee:   红T大花卉印花 -> 纯红光板T (V1 素材复用)
案例3 polka_dress: 波点吊带裙(上身图) -> 纯咖啡色光板裙
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
A2 = os.path.join(ROOT, "assets_v2")
OUT = os.path.join(ROOT, "outputs_v2", "blank")

CKPT = "sd_xl_base_1.0.safetensors"

CASES = {
    "awet_tee": {
        "src": os.path.join(A2, "garments", "g_tee_awet.jpg"),
        "work": (1024, 1024),
        "dn": 0.35,
        "polys_src": [  # 工作分辨率坐标(src==work)
            [(450, 330), (580, 330), (580, 390), (450, 390)],   # 胸前文字
            [(445, 112), (560, 112), (560, 160), (445, 160)],   # 领标
        ],
        "prompt": "plain white cotton t-shirt fabric, clean smooth surface, "
                  "subtle cotton weave texture, product photography, e-commerce",
    },
    "red_tee": {
        "src": os.path.join(ROOT, "assets", "garments", "cand_redtee_floral.png"),
        "white_bg": True,
        "work": (684, 820),
        "dn": 0.4,
        "polys_src": [  # 工作分辨率坐标(原1000x1200坐标x0.684)
            [(176, 198), (525, 195), (532, 321), (410, 350), (188, 353), (170, 287)],
            [(309, 123), (361, 123), (361, 161), (309, 161)],
        ],
        "prompt": "smooth crimson red cotton jersey fabric texture, soft subtle folds, "
                  "clean t-shirt surface, product photography",
    },
    "polka_dress": {
        "src": os.path.join(A2, "models", "m_dress_brown.webp"),
        "work": (896, 1184),
        "dn": 0.45,
        "polys_src": [  # 整条裙子(工作分辨率, 同 v2_tryon case1 校准值)
            [(295, 278), (490, 283), (545, 424), (565, 612), (555, 770), (545, 918),
             (598, 975), (560, 1061), (420, 1125), (360, 1130), (315, 1066), (245, 987),
             (230, 849), (240, 681), (215, 513), (245, 375)],
        ],
        "prompt": "solid coffee brown slip dress fabric, smooth matte texture, elegant natural "
                  "drape and folds, no pattern, e-commerce fashion photography",
    },
}

NEG = ("print, pattern, polka dots, logo, text, letters, graphic, flowers, "
       "worst quality, low quality, blurry")


def load_src(case):
    src = Image.open(case["src"])
    if case.get("white_bg") and src.mode == "RGBA":
        base = Image.new("RGB", src.size, "white")
        base.paste(src, mask=src.split()[3])
        return base
    return src.convert("RGB")


def build(case, key):
    src = load_src(case)
    W, H = case["work"]
    src_w = src.resize((W, H), Image.LANCZOS)
    # 遮罩统一画在工作分辨率坐标系
    m_w = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m_w)
    for poly in case["polys_src"]:
        d.polygon(poly, fill=255)
    m_w = m_w.point(lambda p: 255 if p > 100 else 0)
    # 环带中位色填充
    arr = np.array(src_w)
    mask_np = np.array(m_w) > 100
    eroded = cv2.erode(mask_np.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    band = mask_np & ~eroded
    if band.sum() > 50:
        med = np.median(arr[band].reshape(-1, 3), axis=0)
    else:
        med = np.median(arr[mask_np].reshape(-1, 3), axis=0)
    filled = arr.copy()
    filled[mask_np] = med + np.random.default_rng(7).normal(0, 2.0, (int(mask_np.sum()), 3))
    filled = np.clip(filled, 0, 255).astype(np.uint8)
    # 可视化
    vis = src_w.copy()
    red = Image.new("RGB", (W, H), (255, 40, 40))
    vis = Image.composite(red, vis, m_w.point(lambda p: int(p * 0.5)))
    return src_w, m_w, vis, Image.fromarray(filled)


def workflow(img_file, mask_file, prompt, seed, W, H, denoise):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": img_file}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "4": {"class_type": "LoadImageMask", "inputs": {"image": mask_file, "channel": "red"}},
        "5": {"class_type": "GrowMask", "inputs": {"mask": ["4", 0], "expand": 10, "tapered_corners": True}},
        "5b": {"class_type": "MaskToImage", "inputs": {"mask": ["5", 0]}},
        "5c": {"class_type": "ImageBlur", "inputs": {"image": ["5b", 0], "blur_radius": 9, "sigma": 4.0}},
        "5d": {"class_type": "ImageToMask", "inputs": {"image": ["5c", 0], "channel": "red"}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["8", 0], "mask": ["5d", 0]}},
        "10": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 6.0,
                                                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                                                    "denoise": denoise, "model": ["1", 0],
                                                    "positive": ["6", 0], "negative": ["7", 0],
                                                    "latent_image": ["9", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 2]}},
        "12": {"class_type": "ImageCompositeMasked", "inputs": {"destination": ["2", 0], "source": ["11", 0],
                                                                "mask": ["5d", 0], "x": 0, "y": 0,
                                                                "resize_source": False}},
        "13": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v2blank", "images": ["12", 0]}},
    }


if __name__ == "__main__":
    import cv2
    mode = sys.argv[1] if len(sys.argv) > 1 else "mask"
    os.makedirs(OUT, exist_ok=True)
    if mode == "mask":
        for key, case in CASES.items():
            src_w, m_w, vis, filled = build(case, key)
            src_w.save(os.path.join(OUT, f"{key}_in.png"))
            m_w.save(os.path.join(OUT, f"{key}_mask.png"))
            vis.save(os.path.join(OUT, f"{key}_maskvis.jpg"), quality=90)
            filled.save(os.path.join(OUT, f"{key}_filled.png"))
            print("mask ready:", key)
    elif mode == "run":
        comfy_api.wait_server()
        for key, case in CASES.items():
            up_img = comfy_api.upload_image(os.path.join(OUT, f"{key}_filled.png"))
            up_mask = comfy_api.upload_image(os.path.join(OUT, f"{key}_mask.png"),
                                             name=f"{key}_mask_{sys.argv[2]}.png")
            W, H = case["work"]
            wf = workflow(up_img["name"], up_mask["name"], case["prompt"],
                          int(sys.argv[2]), W, H, case["dn"])
            wf["13"]["inputs"]["filename_prefix"] = f"v2blank_{key}"
            print(key, comfy_api.run(wf, OUT, timeout=900))
