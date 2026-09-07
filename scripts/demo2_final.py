# -*- coding: utf-8 -*-
"""Demo2 最终版: 统一影棚背景 + 正确骨架映射 + 修复负面词污染(不用 floral 负面词)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from demo2_pose import CKPT, gen_faceid_pose, DRESS, NEG  # noqa

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POSE_DIR = os.path.join(ROOT, "assets", "poses")
OUT = os.path.join(ROOT, "outputs", "pose")
FACE_IMG = os.path.join(ROOT, "outputs", "tryon", "tryon_00005_.png")

# (名称, 骨架文件, 姿态描述) — 姿态词加权, 对抗 IPAdapter 参考图的站立构图牵引
FINAL = [
    ("walk",  "skeleton2_00001_.png", "(walking towards the camera, mid-stride:1.4)"),
    ("sit",   "skeleton2_00002_.png", "(sitting on a white stool:1.5), legs crossed"),
    ("turn",  "skeleton2_00003_.png", "(body turned sideways in three-quarter view:1.3), looking back over her shoulder"),
    ("hip",   "skeleton2_00005_.png", "(one hand on hip:1.4), elbow bent outward, standing in side view"),
    ("back",  "skeleton_00006_.png",  "(viewed from behind:1.5), back of the dress shown, head turned over her shoulder"),
    ("stand", "skeleton2_00006_.png", "standing straight facing the camera, arms relaxed at her sides"),
]

POS_FIX = (
    "(wearing a dark navy blue mini dress:1.3) covered in (pink rose floral print:1.3), "
    "colorful floral pattern all over the dress fabric, "
    "thin black ribbon straps, sweetheart neckline, bare legs, white sneakers, "
    "(full body in frame:1.2), "
    "(plain light grey seamless studio backdrop:1.4), empty studio, no props, "
    "(bright even studio lighting:1.2), e-commerce fashion photography, "
    "highly detailed fabric texture, photorealistic, masterpiece, best quality"
)
NEG_FIX = (
    "lingerie, underwear, bikini, corset, swimwear, bra, panties, nude, nsfw, "
    "wall decorations, wall art, props, plants, furniture, clutter, "
    "dark background, moody lighting, shadows, "
    "cgi, cartoon, anime, 3d, render, worst quality, low quality, blurry, deformed, "
    "bad anatomy, bad hands, extra fingers, watermark, text, logo"
)


def build(face_file, skel_file, pose_desc, seed, w=512, h=768):
    wf = gen_faceid_pose(face_file, skel_file, pose_desc, seed, w, h)
    # OpenPose 强度拉满, 保证骨架姿态落实
    wf["7"]["inputs"]["strength"] = 0.95
    # 双 IPAdapter: FaceID(人脸) 已在 3/4 节点; 叠加 PLUS(服装外观参考, 低权重)
    wf["5b"] = {"class_type": "IPAdapterUnifiedLoader",
                "inputs": {"model": ["1", 0], "preset": "PLUS (high strength)"}}
    wf["5c"] = {"class_type": "IPAdapter",
                "inputs": {"model": ["4", 0], "ipadapter": ["5b", 1], "image": ["2", 0],
                           "weight": 0.4, "weight_type": "standard",
                           "start_at": 0.0, "end_at": 1.0}}
    wf["11"]["inputs"]["model"] = ["5c", 0]
    wf["8"]["inputs"]["text"] = (
        f"a beautiful young asian woman, long straight black hair, {pose_desc}, {POS_FIX}"
    )
    wf["9"]["inputs"]["text"] = NEG_FIX
    wf["13"]["inputs"]["filename_prefix"] = "pose_v5"
    return wf


if __name__ == "__main__":
    comfy_api.wait_server()
    face_up = comfy_api.upload_image(FACE_IMG)
    for i, (key, skel, desc) in enumerate(FINAL):
        sk_up = comfy_api.upload_image(os.path.join(POSE_DIR, skel),
                                       name=f"skel_v5_{key}.png")
        paths = comfy_api.run(build(face_up["name"], sk_up["name"], desc, 99301 + i), OUT, timeout=600)
        print(key, paths)
