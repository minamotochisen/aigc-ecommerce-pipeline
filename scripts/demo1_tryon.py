# -*- coding: utf-8 -*-
"""Demo1 服装智能换装：遮罩 + IPAdapter 服装参考 + RealisticVision 局部重绘

管线: 模特图缩放 -> VAEEncode -> SetLatentNoiseMask(服装遮罩)
      -> IPAdapter(PLUS, 服装平铺参考图) -> KSampler denoise=1.0
      -> VAEDecode -> ImageCompositeMasked 回贴未遮罩区域(人脸/手臂/鞋零变化)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "outputs", "tryon")

MODEL_IMG = os.path.join(ASSETS, "models", "sdxl_model_00003_.png")

# ---- 遮罩（832x1216 原图坐标系）：人物剪影大遮罩，覆盖肩以下全身+邻接背景，
#      只保留 头部/头发 和 鞋子 —— 避免手臂与躯干遮罩边界交界处的姿态漂移与融合痕迹 ----
POLYS = [
    [(395, 318), (510, 318), (548, 338), (582, 370), (585, 720), (568, 1040),
     (455, 1042), (350, 1040), (333, 720), (338, 370), (360, 338)],
]
GROW = 10

# ---- 两组目标服装（真实电商图裁剪）----
GARMENTS = {
    "A_floral_mini": {
        "src": os.path.join(ASSETS, "garments", "cand_dress_plain_bg.jpg"),
        "crop": (140, 280, 900, 1470),  # 紧裁服装主体
        "prompt": (
            "a young asian woman wearing a dark navy blue floral print mini dress with thin black "
            "ribbon straps and sweetheart neckline, bare legs, both arms relaxed at her sides, "
            "hands resting at her sides, white sneakers, long black hair, "
            "(seamless light grey studio backdrop:1.3), e-commerce fashion photography, "
            "soft studio lighting, highly detailed fabric texture, photorealistic, masterpiece, best quality"
        ),
    },
    "B_puffsleeve": {
        "src": os.path.join(ASSETS, "garments", "cand_dress_collar.jpg"),
        "crop": (240, 180, 1400, 2100),
        "prompt": (
            "a young asian woman wearing a white and blue watercolor floral print long flowy dress "
            "with dramatic puffy short sleeves and v-neck, ruffle trim, both arms relaxed at her sides, "
            "hands resting at her sides, white sneakers, long black hair, "
            "(seamless light grey studio backdrop:1.3), e-commerce fashion photography, "
            "soft studio lighting, highly detailed fabric texture, photorealistic, masterpiece, best quality"
        ),
    },
}

NEG = (
    "nsfw, jeans, denim, t-shirt, cgi, cartoon, anime, 3d, render, worst quality, low quality, "
    "blurry, deformed, bad anatomy, bad hands, extra fingers, watermark, text, logo"
)

CKPT = "realisticVisionV60B1_v51HyperVAE.safetensors"
W, H = 528, 768  # 工作分辨率(8的倍数, 比例贴近原图)


def make_mask(path):
    im = Image.open(MODEL_IMG).convert("RGB")
    m = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(m)
    for poly in POLYS:
        d.polygon(poly, fill=255)
    m = m.resize((W, H), Image.LANCZOS).point(lambda p: 255 if p > 100 else 0)
    # 可视化: 原图半透明红罩
    vis = im.resize((W, H), Image.LANCZOS).convert("RGB")
    red = Image.new("RGB", vis.size, (255, 40, 40))
    vis = Image.composite(red, vis, m.point(lambda p: int(p * 0.45)))
    vis.save(path.replace(".png", "_vis.jpg"), quality=90)
    m.save(path)
    return path


def crop_ref(cfg, name):
    im = Image.open(cfg["src"]).convert("RGB")
    im.crop(cfg["crop"]).save(os.path.join(ASSETS, "garments", name), quality=92)


def build(model_file, ref_file, mask_file, prompt, seed):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        # 模特图
        "2": {"class_type": "LoadImage", "inputs": {"image": model_file}},
        "3": {"class_type": "ImageScale", "inputs": {"image": ["2", 0], "width": W, "height": H,
                                                     "upscale_method": "lanczos", "crop": "disabled"}},
        # 遮罩
        "4": {"class_type": "LoadImageMask", "inputs": {"image": mask_file, "channel": "red"}},
        "5": {"class_type": "GrowMask", "inputs": {"mask": ["4", 0], "expand": GROW, "tapered_corners": True}},
        # IPAdapter 服装参考
        "6": {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": ["1", 0], "preset": "PLUS (high strength)"}},
        "7": {"class_type": "LoadImage", "inputs": {"image": ref_file}},
        "8": {"class_type": "IPAdapter", "inputs": {"model": ["6", 0], "ipadapter": ["6", 1],
                                                    "image": ["7", 0], "weight": 0.75,
                                                    "weight_type": "standard",
                                                    "start_at": 0.0, "end_at": 1.0}},
        # 条件
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        # 重绘
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["3", 0], "vae": ["1", 2]}},
        "12": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["11", 0], "mask": ["5", 0]}},
        "13": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 6.5,
                                                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                                                    "denoise": 1.0, "model": ["8", 0],
                                                    "positive": ["9", 0], "negative": ["10", 0],
                                                    "latent_image": ["12", 0]}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["1", 2]}},
        # 回贴未遮罩区域, 保证人脸/手臂/鞋逐像素不变
        "15": {"class_type": "ImageCompositeMasked", "inputs": {"destination": ["3", 0], "source": ["14", 0],
                                                                "mask": ["5", 0], "x": 0, "y": 0,
                                                                "resize_source": False}},
        "16": {"class_type": "SaveImage", "inputs": {"filename_prefix": "tryon", "images": ["15", 0]}},
    }


if __name__ == "__main__":
    comfy_api.wait_server()
    mask = make_mask(os.path.join(OUT, "mask.png"))
    model_up = comfy_api.upload_image(MODEL_IMG)
    mask_up = comfy_api.upload_image(mask)
    for key, cfg in GARMENTS.items():
        ref = os.path.join(ASSETS, "garments", f"ref_{key}.jpg")
        crop_ref(cfg, f"ref_{key}.jpg")
        ref_up = comfy_api.upload_image(ref)
        for seed in (77001, 77002):
            wf = build(model_up["name"], ref_up["name"], mask_up["name"], cfg["prompt"], seed)
            paths = comfy_api.run(wf, OUT, timeout=600)
            print(key, seed, paths)
