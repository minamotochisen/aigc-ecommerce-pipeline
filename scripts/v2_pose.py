# -*- coding: utf-8 -*-
"""V2 Demo2 动作裂变: InstantID(真实模特锁脸) + ControlNet OpenPose SDXL(姿态) + IPAdapter(锁裙款)

身份锚: assets_v2/models/m_dress_brown.webp (真实亚洲模特, 波点吊带长裙)
姿态源: V1 已验证的 6 张 OpenPose 骨架
输出: 896x1152 (避开 1024 方图水印敏感尺寸)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
A2 = os.path.join(ROOT, "assets_v2")
P1 = os.path.join(ROOT, "assets", "poses")
OUT = os.path.join(ROOT, "outputs_v2", "pose")

CKPT = "sd_xl_base_1.0.safetensors"
FACE_SRC = os.path.join(A2, "models", "m_dress_brown.webp")
FACE_CROP = (600, 180, 1100, 700)  # 原图1500x2000, 面部区域

DRESS = (
    "a beautiful young asian woman, long straight black hair with bangs, wearing thin gold-rimmed glasses, "
    "wearing a (coffee brown polka dot midi slip dress:1.4), white polka dot print, "
    "thin straps, v-neckline, soft flowing fabric, silver sandals, "
    "(wide shot:1.2), (full body in frame:1.3), feet and sandals visible, "
    "(warm beige seamless studio backdrop:1.3), empty plain background, no props, "
    "e-commerce fashion photography, soft studio lighting, "
    "highly detailed fabric texture, photorealistic, masterpiece, best quality"
)
NEG = (
    "lingerie, underwear, bikini, nude, nsfw, wall decorations, props, plants, furniture, clutter, "
    "dark background, moody lighting, close up, portrait crop, upper body, half body, "
    "patterned background, dotted background, blurry glasses, broken glasses, "
    "cgi, cartoon, anime, 3d, render, worst quality, low quality, "
    "blurry, deformed, bad anatomy, bad hands, extra fingers, watermark, text, logo"
)

POSES = [
    ("walk",  os.path.join(P1, "skeleton_00001_.png"),  "(walking towards the camera, mid-stride:1.4)"),
    ("sit",   os.path.join(P1, "skeleton_00002_.png"),  "(sitting elegantly on a white stool:1.5), legs crossed"),
    ("side",  os.path.join(P1, "skeleton2_00005_.png"), "(standing in side view:1.3), one hand resting on her hip"),
    ("turn",  os.path.join(P1, "skeleton2_00003_.png"), "(body turned sideways in three-quarter view:1.3), looking back over her shoulder"),
    ("back",  os.path.join(P1, "skeleton_00006_.png"),  "(viewed from behind:1.4), back of the dress shown, hair covering"),
    ("stand", os.path.join(P1, "skeleton2_00006_.png"), "standing straight facing the camera, arms relaxed at her sides"),
]

W, H = 896, 1152


def workflow(face_file, skel_file, pose_desc, seed):
    """IPAdapter Plus Face SDXL 锁脸 + OpenPose SDXL 控姿态
    (InstantID 面部 ControlNet 与 OpenPose 叠加会互相冲突烧图, 故用纯注意力方案)"""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        # IPAdapter Plus Face (SDXL, ViT-H)
        "2": {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": ["1", 0], "preset": "PLUS FACE (portraits)"}},
        "3": {"class_type": "LoadImage", "inputs": {"image": face_file}},
        "4": {"class_type": "IPAdapter", "inputs": {"model": ["2", 0], "ipadapter": ["2", 1],
                                                    "image": ["3", 0], "weight": 0.8,
                                                    "weight_type": "standard",
                                                    "start_at": 0.0, "end_at": 1.0}},
        # OpenPose SDXL 身体姿态
        "6": {"class_type": "ControlNetLoader", "inputs": {
            "control_net_name": "controlnet_openpose_sdxl_xinsir.safetensors"}},
        "7": {"class_type": "LoadImage", "inputs": {"image": skel_file}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {
            "text": DRESS + ", " + pose_desc, "clip": ["1", 1]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "11": {"class_type": "ControlNetApply", "inputs": {
            "conditioning": ["8", 0], "control_net": ["6", 0], "image": ["7", 0],
            "strength": 0.9}},
        "12": {"class_type": "EmptyLatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "13": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 5.5,
                                                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                                                    "denoise": 1.0, "model": ["4", 0],
                                                    "positive": ["11", 0], "negative": ["9", 0],
                                                    "latent_image": ["12", 0]}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["1", 2]}},
        "15": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v2pose", "images": ["14", 0]}},
    }


def make_face_crop():
    im = Image.open(FACE_SRC).convert("RGB")
    im.crop(FACE_CROP).save(os.path.join(A2, "models", "v2_face_ref.jpg"), quality=95)


if __name__ == "__main__":
    comfy_api.wait_server()
    make_face_crop()
    face_up = comfy_api.upload_image(os.path.join(A2, "models", "v2_face_ref.jpg"))
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for i, (key, skel, desc) in enumerate(POSES):
        if only and key != only:
            continue
        sk_up = comfy_api.upload_image(skel, name=f"v2skel_{key}_{i}.png")
        wf = workflow(face_up["name"], sk_up["name"], desc, 88301 + i)
        wf["14"]["inputs"]["filename_prefix"] = f"v2pose_{key}"
        print(key, comfy_api.run(wf, OUT, timeout=900))
