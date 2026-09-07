# -*- coding: utf-8 -*-
"""Demo3-裙装案例 v5: 碎花裙 -> 纯色光板裙 (denoise=1.0 全重绘 + 廓形锚定提示词)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "outputs", "blank")

SRC = os.path.join(ROOT, "outputs", "tryon", "tryon_00005_.png")
W, H = 528, 768

POLY = [(192, 200), (340, 196), (350, 290), (348, 408), (300, 442), (240, 448),
        (200, 430), (188, 380), (182, 290)]

POS = (
    "a young asian woman wearing (plain solid dark navy blue mini dress:1.4), "
    "thin black ribbon straps, sweetheart neckline, fitted bodice, flowy skirt above the knee, "
    "no print, no pattern, bare legs, white sneakers, long black hair, "
    "(seamless light grey studio backdrop:1.2), e-commerce fashion photography, "
    "soft studio lighting, highly detailed fabric, photorealistic, masterpiece, best quality"
)
NEG = (
    "floral, print, pattern, flowers, lace, cgi, cartoon, anime, 3d, render, "
    "worst quality, low quality, blurry, deformed, bad anatomy, watermark, text, logo"
)


def make_mask():
    src = Image.open(SRC).convert("RGB")
    m = Image.new("L", src.size, 0)
    d = ImageDraw.Draw(m)
    d.polygon(POLY, fill=255)
    m = m.resize((W, H), Image.LANCZOS).point(lambda p: 255 if p > 100 else 0)
    return src.resize((W, H), Image.LANCZOS), m


def workflow(img_file, mask_file, seed):
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "realisticVisionV60B1_v51HyperVAE.safetensors"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": img_file}},
        "4": {"class_type": "LoadImageMask", "inputs": {"image": mask_file, "channel": "red"}},
        "5": {"class_type": "GrowMask", "inputs": {"mask": ["4", 0], "expand": 10, "tapered_corners": True}},
        "5b": {"class_type": "MaskToImage", "inputs": {"mask": ["5", 0]}},
        "5c": {"class_type": "ImageBlur", "inputs": {"image": ["5b", 0], "blur_radius": 9, "sigma": 4.0}},
        "5d": {"class_type": "ImageToMask", "inputs": {"image": ["5c", 0], "channel": "red"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["1", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["8", 0], "mask": ["5d", 0]}},
        "10": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 6.5,
                                                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                                                    "denoise": 1.0, "model": ["1", 0],
                                                    "positive": ["6", 0], "negative": ["7", 0],
                                                    "latent_image": ["9", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["1", 2]}},
        "12": {"class_type": "ImageCompositeMasked", "inputs": {"destination": ["2", 0], "source": ["11", 0],
                                                                "mask": ["5d", 0], "x": 0, "y": 0,
                                                                "resize_source": False}},
        "13": {"class_type": "SaveImage", "inputs": {"filename_prefix": "dress_blank", "images": ["12", 0]}},
    }


if __name__ == "__main__":
    comfy_api.wait_server()
    src, mask = make_mask()
    img_p = os.path.join(OUT, "dress_in.png")
    mask_p = os.path.join(OUT, "dress_mask_v5.png")
    src.save(img_p)
    mask.save(mask_p)
    up_img = comfy_api.upload_image(img_p)
    for seed in (56001, 56002, 56003):
        # 唯一文件名: ComfyUI 按文件名缓存节点输出, 同名换内容不会失效
        up_mask = comfy_api.upload_image(mask_p, name=f"dress_mask_v5_{seed}.png")
        wf = workflow(up_img["name"], up_mask["name"], seed)
        print(seed, comfy_api.run(wf, OUT, timeout=600))
