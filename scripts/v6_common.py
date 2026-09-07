# -*- coding: utf-8 -*-
"""V6 姿态组: 真实照片基底 + 面部定向重绘(统一身份) + 服装定向重绘(统一裙款)
面部: insightface 框 → IPAdapter FaceID PlusV2(身份锚脸) + RV 重绘
服装: 服装遮罩 → IPAdapter Plus(波点裙参考) + RV 重绘
四肢/背景: 保留真实像素
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image

ROOT = r"."
POSES = os.path.join(ROOT, "assets_v2", "poses")
OUT = os.path.join(ROOT, "outputs_v2", "posev6")
os.makedirs(OUT, exist_ok=True)

CKPT = "realisticVisionV60B1_v51HyperVAE.safetensors"
ANCHOR = os.path.join(POSES, "m_dress_brown.webp")   # 身份锚+裙款参考(真实照片)
ANCHOR_FACE_BOX = [699.0, 224.4, 828.2, 398.9]        # 1500x2000
DRESS_REF_CROP = (470, 350, 1180, 1500)               # anchor 波点裙身(1500x2000)

# 每张照片: 原图 / 原尺寸 / 人脸框(原坐标)
PHOTOS = {
    "anchor":  {"file": os.path.join(POSES, "m_dress_brown.webp"), "size": (1500, 2000),
                "face": [699.0, 224.4, 828.2, 398.9]},
    "plainbg": {"file": os.path.join(POSES, "p_plainbg.jpg"), "size": (1000, 1499),
                "face": [418.8, 63.1, 531.8, 217.3]},
    "lawn":    {"file": os.path.join(POSES, "p_lawn.jpg"), "size": (960, 1248),
                "face": [372.6, 279.8, 442.1, 384.4]},
    "jump":    {"file": os.path.join(POSES, "m_jumpsuit.jpg"), "size": (1725, 2415),
                "face": [889.3, 33.5, 1080.2, 260.1]},
    "palm":    {"file": os.path.join(POSES, "p_elle_palm.jpg"), "size": (980, 1470),
                "face": [320.5, 445.6, 425.9, 562.7]},
    "tank":    {"file": os.path.join(POSES, "m_tank_cream.jpg"), "size": (2400, 3000),
                "face": [1028.1, 395.3, 1395.9, 853.5]},
}

# 服装遮罩(原图坐标, 逐张看图标定)
GARMENT_POLYS = {
    "plainbg": [(350, 555), (700, 548), (760, 900), (745, 1230), (560, 1300), (400, 1290), (330, 1180), (322, 900)],
    "lawn":    [(340, 620), (640, 600), (700, 780), (660, 1030), (380, 1020), (330, 830)],
    "jump":    [(700, 560), (1210, 550), (1260, 900), (1215, 1700), (1120, 2230), (960, 2260), (760, 1700), (690, 1100)],
    "tank":    [(880, 1050), (1520, 1040), (1600, 1450), (1660, 2050), (1610, 2600), (1440, 2700), (900, 2710), (830, 2500), (855, 1600)],
}


def face_crop_anchor():
    im = Image.open(ANCHOR).convert("RGB")
    x0, y0, x1, y1 = ANCHOR_FACE_BOX
    mx, my = (x1 - x0) * 0.35, (y1 - y0) * 0.30
    c = im.crop((int(x0 - mx), int(y0 - my), int(x1 + mx), int(y1 + my * 1.6)))
    c.save(os.path.join(OUT, "anchor_face.jpg"), quality=95)
    return os.path.join(OUT, "anchor_face.jpg")


def dress_crop_anchor():
    im = Image.open(ANCHOR).convert("RGB")
    c = im.crop(DRESS_REF_CROP)
    c.save(os.path.join(OUT, "anchor_dress.jpg"), quality=95)
    return os.path.join(OUT, "anchor_dress.jpg")


def work_image(key):
    p = PHOTOS[key]
    im = Image.open(p["file"]).convert("RGB")
    w, h = im.size
    scale = min(1024 / max(w, h), 1.0)
    W, H = int(w * scale // 8 * 8), int(h * scale // 8 * 8)
    return im.resize((W, H), Image.LANCZOS), W, H, scale


def rect_mask(W, H, box, feather=18):
    from PIL import ImageDraw, ImageFilter
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    d.rectangle(box, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(feather))
    return m


def garment_mask(key, W, H):
    """服装遮罩(工作分辨率): 工作坐标由原图坐标换算, 调用方以 GARMENT_POLYS_WORK 提供"""
    p = PHOTOS[key]
    w0, h0 = p["size"]
    sx, sy = W / w0, H / h0
    from PIL import ImageDraw, ImageFilter
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for poly in GARMENT_POLYS[key]:
        d.polygon([(int(x * sx), int(y * sy)) for x, y in poly], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(8))
    return m


def build_face_pass(person_file, mask_file, face_file, seed, denoise=0.85):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": person_file}},
        "3": {"class_type": "LoadImageMask", "inputs": {"image": mask_file, "channel": "red"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": face_file}},
        "5": {"class_type": "IPAdapterUnifiedLoaderFaceID", "inputs": {
            "model": ["1", 0], "preset": "FACEID PLUS V2", "lora_strength": 0.7, "provider": "CUDA"}},
        "6": {"class_type": "IPAdapter", "inputs": {"model": ["5", 0], "ipadapter": ["5", 1],
                                                    "image": ["4", 0], "weight": 0.9,
                                                    "weight_type": "standard", "start_at": 0.0, "end_at": 1.0}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text":
               "closeup portrait of a beautiful young asian woman face, natural detailed skin texture with pores, "
               "dark brown eyes, long black hair, soft studio light, photorealistic", "clip": ["1", 1]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text":
               "glasses, eyewear, wax skin, plastic, doll, 3d render, painting, deformed, worst quality, low quality, blurry",
               "clip": ["1", 1]}},
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
        "14": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v6face", "images": ["13", 0]}},
    }
