# -*- coding: utf-8 -*-
"""V6 姿态组: 真实姿态照 × 统一波点吊带长裙 (遮罩 + IPAdapter Plus + RV 重绘)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image, ImageDraw, ImageFilter

ROOT = r"."
POSES = os.path.join(ROOT, "assets_v2", "poses")
OUT = os.path.join(ROOT, "outputs_v2", "posev6")
os.makedirs(OUT, exist_ok=True)

CKPT = "realisticVisionV60B1_v51HyperVAE.safetensors"
DRESS_REF = os.path.join(OUT, "anchor_dress.jpg")

POS = ("wearing a coffee brown polka dot slip midi dress, white polka dot print, thin spaghetti "
       "straps, soft flowing viscose fabric, natural drape and sway, e-commerce fashion "
       "photography, photorealistic, highly detailed fabric")
NEG = ("jumpsuit, trousers, pants, white dress, floral print, change background, deformed, "
       "extra limbs, bad anatomy, worst quality, low quality, blurry")

# 每张: 原图 / 原尺寸 / 服装遮罩多边形(原图坐标)
CASES = {
    "plainbg": {
        "file": os.path.join(POSES, "p_plainbg.jpg"), "size": (1000, 1499),
        "polys": [[(315, 282), (629, 282), (637, 573), (581, 895), (145, 895), (137, 758), (306, 290)]],
    },
    "lawn": {
        "file": os.path.join(POSES, "p_lawn.jpg"), "size": (960, 1248),
        "polys": [[(240, 426), (704, 426), (704, 820), (542, 828), (310, 806), (264, 689), (183, 464)]],
    },
    "jump": {
        "file": os.path.join(POSES, "m_jumpsuit.jpg"), "size": (1725, 2415),
        "polys": [[(556, 320), (1265, 311), (1285, 500), (1273, 890), (1285, 1556), (1265, 2112),
                   (1029, 2174), (709, 2168), (551, 2112), (534, 1556), (584, 834), (545, 500)]],
    },
    "palm": {
        "file": os.path.join(POSES, "p_elle_palm.jpg"), "size": (980, 1470),
        "polys": [[(182, 553), (506, 553), (521, 1106), (474, 1264), (285, 1296), (182, 1106)]],
    },
    "tank": {
        "file": os.path.join(POSES, "m_tank_cream.jpg"), "size": (2400, 3000),
        "mask_ready": "case2_dressfloral2_mask.png",
        "polys_src_img": os.path.join(ROOT, "outputs_v2", "tryon", "case2_dressfloral2_mask.png"),
    },
}


def prep(key):
    c = CASES[key]
    im = Image.open(c["file"]).convert("RGB")
    W, H = im.size
    tw = 768
    th = int(H * tw / W) // 8 * 8
    work = im.resize((tw, th), Image.LANCZOS)
    if c.get("mask_ready"):
        mask = Image.open(os.path.join(ROOT, "outputs_v2", "tryon", c["mask_ready"])).convert("RGB")
        mask = mask.resize((tw, th), Image.LANCZOS)
        m = mask.split()[0].point(lambda p: 255 if p > 100 else 0)
    else:
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        sx, sy = W / c["size"][0], H / c["size"][1]
        for poly in c["polys"]:
            d.polygon([(x * sx, y * sy) for x, y in poly], fill=255)
        m = m.point(lambda p: 255 if p > 100 else 0)
    m = m.filter(ImageFilter.GaussianBlur(6))
    return work, m


def workflow(person_file, mask_file, ref_file, seed, denoise=0.9):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": person_file}},
        "3": {"class_type": "LoadImageMask", "inputs": {"image": mask_file, "channel": "red"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": ref_file}},
        "5": {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": ["1", 0], "preset": "PLUS (high strength)"}},
        "6": {"class_type": "IPAdapter", "inputs": {"model": ["5", 0], "ipadapter": ["5", 1],
                                                    "image": ["4", 0], "weight": 0.65,
                                                    "weight_type": "standard", "start_at": 0.0, "end_at": 1.0}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["1", 1]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "9": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "10": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["9", 0], "mask": ["3", 0]}},
        "11": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 5.5,
                                                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                                                    "denoise": denoise, "model": ["6", 0],
                                                    "positive": ["7", 0], "negative": ["8", 0],
                                                    "latent_image": ["10", 0]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["1", 2]}},
        "13": {"class_type": "ImageCompositeMasked", "inputs": {"destination": ["2", 0], "source": ["12", 0],
                                                                "mask": ["3", 0], "x": 0, "y": 0,
                                                                "resize_source": False}},
        "14": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v6dress", "images": ["13", 0]}},
    }


if __name__ == "__main__":
    comfy_api.wait_server()
    up_ref = comfy_api.upload_image(DRESS_REF)
    for key, c in CASES.items():
        work, m = prep(key)
        person_p = os.path.join(OUT, f"v6g_{key}_work.png")
        mask_p = os.path.join(OUT, f"v6g_{key}_mask.png")
        work.save(person_p)
        m.save(mask_p)
        up_p = comfy_api.upload_image(person_p)
        for seed in (91001, 91002):
            up_m = comfy_api.upload_image(mask_p, name=f"{key}_gmask_{seed}.png")
            wf = workflow(up_p["name"], up_m["name"], up_ref["name"], seed)
            wf["14"]["inputs"]["filename_prefix"] = f"v6dress_{key}_{seed}"
            print(key, seed, comfy_api.run(wf, OUT, timeout=900))
