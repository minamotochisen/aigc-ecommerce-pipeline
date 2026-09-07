# -*- coding: utf-8 -*-
"""Demo2 创意动作裂变：IPAdapter FaceID(保持人脸) + ControlNet OpenPose(控制姿态)

阶段1: SDXL 生成 6 张不同姿态的参考图(仅用于提取骨架)
阶段2: OpenposePreprocessor 提取骨架
阶段3: FaceID + OpenPose 生成"同一模特同一服装"的多姿态图
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POSE_DIR = os.path.join(ROOT, "assets", "poses")
OUT = os.path.join(ROOT, "outputs", "pose")

FACE_IMG = os.path.join(ROOT, "outputs", "tryon", "tryon_00005_.png")  # 换装成品=身份锚点

POSES = {
    "walk": "walking towards camera, mid-stride, dress flowing, one leg forward",
    "sit": "sitting elegantly on a white stool, legs crossed",
    "turn": "three-quarter turn, body facing sideways, looking back over her shoulder at camera",
    "hip": "standing with one hand on hip, elbow bent outward, weight shifted to one leg, confident pose",
    "back": "viewed from behind, back of the dress fully shown, head turned to her right",
    "lean": "standing with one hand touching her hair, body slightly turned, gentle smile",
}

CKPT = "realisticVisionV60B1_v51HyperVAE.safetensors"
DRESS = (
    "a beautiful young asian woman, long straight black hair, wearing a dark navy blue floral "
    "print mini dress with thin black ribbon straps, pink floral print, sweetheart neckline, "
    "bare legs, white sneakers, (seamless plain light grey studio backdrop:1.4), plain empty background, "
    "e-commerce fashion photography, soft studio lighting, highly detailed fabric texture, "
    "photorealistic, masterpiece, best quality"
)
NEG = (
    "flowers in background, flower wall, floral background, plants, curtain, furniture, "
    "nsfw, cgi, cartoon, anime, 3d, render, worst quality, low quality, blurry, deformed, "
    "bad anatomy, bad hands, extra fingers, watermark, text, logo"
)


def sdxl_pose(pose_desc, seed):
    pos = (
        f"(full body shot:1.4), wide shot, entire figure visible head to toe, feet visible on floor, "
        f"standing far from camera, {pose_desc}, {DRESS}"
    )
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 28, "cfg": 7.0,
                                                   "sampler_name": "dpmpp_2m", "scheduler": "karras",
                                                   "denoise": 1.0, "model": ["1", 0],
                                                   "positive": ["2", 0], "negative": ["3", 0],
                                                   "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "pose_ref2", "images": ["6", 0]}},
    }


def extract_skeleton(img_name):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "2": {"class_type": "OpenposePreprocessor", "inputs": {
            "detect_hand": "enable", "detect_body": "enable", "detect_face": "enable",
            "resolution": 512, "image": ["1", 0]}},
        "3": {"class_type": "SaveImage", "inputs": {"filename_prefix": "skeleton", "images": ["2", 0]}},
    }


def extract_skeleton2(img_name):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "2": {"class_type": "OpenposePreprocessor", "inputs": {
            "detect_hand": "enable", "detect_body": "enable", "detect_face": "enable",
            "resolution": 512, "image": ["1", 0]}},
        "3": {"class_type": "SaveImage", "inputs": {"filename_prefix": "skeleton2", "images": ["2", 0]}},
    }


def gen_faceid_pose(face_file, skel_file, pose_desc, seed, w=512, h=768):
    return {
        # FaceID 身份
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": face_file}},
        "3": {"class_type": "IPAdapterUnifiedLoaderFaceID", "inputs": {
            "model": ["1", 0], "preset": "FACEID PLUS V2", "lora_strength": 0.7, "provider": "CUDA"}},
        "4": {"class_type": "IPAdapter", "inputs": {
            "model": ["3", 0], "ipadapter": ["3", 1], "image": ["2", 0],
            "weight": 0.9, "weight_type": "standard", "start_at": 0.0, "end_at": 1.0}},
        # OpenPose 姿态
        "5": {"class_type": "ControlNetLoader", "inputs": {
            "control_net_name": "control_v11p_sd15_openpose_fp16.safetensors"}},
        "6": {"class_type": "LoadImage", "inputs": {"image": skel_file}},
        "7": {"class_type": "ControlNetApply", "inputs": {
            "conditioning": ["8", 0], "control_net": ["5", 0], "image": ["6", 0], "strength": 0.85}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": DRESS + ", " + pose_desc, "clip": ["1", 1]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "10": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "11": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 6.5,
                                                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                                                    "denoise": 1.0, "model": ["4", 0],
                                                    "positive": ["7", 0], "negative": ["9", 0],
                                                    "latent_image": ["10", 0]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["1", 2]}},
        "13": {"class_type": "SaveImage", "inputs": {"filename_prefix": "pose_gen", "images": ["12", 0]}},
    }


if __name__ == "__main__":
    comfy_api.wait_server()
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"

    if stage in ("all", "refs"):
        # 阶段1: 姿态参考图(重拍版 pose_ref2_*)
        for i, (key, desc) in enumerate(POSES.items()):
            paths = comfy_api.run(sdxl_pose(desc, 88201 + i), POSE_DIR, timeout=600)
            print("ref", key, paths)

    if stage in ("all", "skel"):
        # 阶段2: 提取骨架(重拍版 skeleton2_*)
        for i, key in enumerate(POSES):
            up = comfy_api.upload_image(os.path.join(POSE_DIR, f"pose_ref2_{i + 1:05d}_.png"))
            paths = comfy_api.run(extract_skeleton2(up["name"]), POSE_DIR, timeout=300)
            print("skel", key, paths)

    if stage in ("all", "gen"):
        # 阶段3: FaceID + OpenPose 生成
        face_up = comfy_api.upload_image(FACE_IMG)
        for i, (key, desc) in enumerate(POSES.items()):
            skel = os.path.join(POSE_DIR, f"skeleton2_{i + 1:05d}_.png")
            sk_up = comfy_api.upload_image(skel)
            paths = comfy_api.run(
                gen_faceid_pose(face_up["name"], sk_up["name"], desc, 99101 + i), OUT, timeout=600)
            print("gen", key, paths)
