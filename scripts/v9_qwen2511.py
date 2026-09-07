# -*- coding: utf-8 -*-
"""V9 主力管线: Qwen-Image-Edit-2511 指令编辑 (fp8mixed, 官方参数)
四种模式:
  python v9_qwen2511.py tryon    # 换装: 波点裙模特 x 花卉裙紧裁 -> 花卉裙模特
  python v9_qwen2511.py scene    # 场景: 换装结果 -> 地中海 / 街拍 (链式, 人物保持)
  python v9_qwen2511.py pose     # 姿态迁移: 锚模特 x 姿态参考 -> 同一人同裙新姿态
  python v9_qwen2511.py blank    # 光板净化: 去印花
官方参数: euler/simple, steps 20 (40 更优), cfg 4.0, ModelSamplingAuraFlow shift 3.1, CFGNorm
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image

ROOT = r"."
OUT = os.path.join(ROOT, "outputs_v2", "v9")
os.makedirs(OUT, exist_ok=True)

MODEL = "qwen_image_edit_2511_fp8mixed.safetensors"
CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
VAE = "qwen_image_vae.safetensors"

ANCHOR = os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")   # 波点裙模特 1500x2000
GARMENT = os.path.join(ROOT, "assets_v2", "garments", "v2ref_case1_dressfloral.jpg")
POSES = os.path.join(ROOT, "assets_v2", "poses")

# 姿态参考: 图库真实姿态照(非锚模特, 仅提供构图/肢体)
POSE_REFS = {
    "handonhip": os.path.join(POSES, "p_plainbg.jpg"),
    "walking":   os.path.join(POSES, "p_lawn.jpg"),
    "side":      os.path.join(POSES, "p_elle_palm.jpg"),
    "back":      os.path.join(POSES, "m_tank_cream.jpg"),
    "stand34":   os.path.join(POSES, "m_jumpsuit.jpg"),
}

MAX_SIDE = 1024  # 工作分辨率上限(Qwen 友好, 16 的倍数在 resize 内部处理)


def prep(path, name):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    scale = min(MAX_SIDE / max(w, h), 1.0)
    im = im.resize((max(int(w * scale) // 16 * 16, 256), max(int(h * scale) // 16 * 16, 256)), Image.LANCZOS)
    p = os.path.join(OUT, name)
    im.save(p)
    return comfy_api.upload_image(p)


def workflow(prompt, images, seed, steps=20, cfg=4.0):
    """images: [文件名字符串或upload_image返回dict, ...] 按 image1..imageN 传入"""
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "5": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
        "6": {"class_type": "VAEEncode", "inputs": {"pixels": ["8", 0], "vae": ["3", 0]}},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["2", 0], "prompt": prompt, "vae": ["3", 0]}},
        "8n": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
        "9": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
            "denoise": 1.0, "model": ["5", 0], "positive": ["7", 0], "negative": ["8n", 0],
            "latent_image": ["6", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v9", "images": ["11", 0]}},
    }
    # image1..imageN
    for i, img in enumerate(images, 1):
        key = f"image{i}"
        node_id = str(20 + i)
        wf[node_id] = {"class_type": "LoadImage", "inputs": {"image": img["name"] if isinstance(img, dict) else img}}
        wf["7"]["inputs"][key] = [node_id, 0]
        if i == 1:
            wf["6"]["inputs"]["pixels"] = [node_id, 0]
    return wf


CASES = {
    "tryon": {
        "prompt": ("Virtual try-on garment swap. Image 1 is the person, image 2 shows only the garment. "
                   "Replace the woman's brown polka dot slip dress with the navy blue floral print mini "
                   "dress with black bow-tie shoulder straps from image 2. Ignore the person, pose and "
                   "background in image 2 - take only the dress. Keep everything else from image 1 "
                   "exactly unchanged: her exact same face, her rimless glasses, same makeup, same long "
                   "dark brown hair with bangs, her exact same standing pose, same camera framing, same "
                   "grey textured studio backdrop. The floral print follows the dress folds naturally. "
                   "Photorealistic."),
        "images": [ANCHOR, GARMENT],
        "seeds": (91105, 91106, 91107, 91108),
    },
    "scene_med": {
        "prompt": ("Background replacement edit. Keep the woman in image 1 pixel-identical: same face, "
                   "same rimless glasses, same long dark brown hair (keep her natural dark hair color, "
                   "no green or olive tint), same floral dress, same pose, same camera framing, and keep "
                   "her exact skin tone and clothing colors - do not color grade or re-tint the subject. "
                   "Replace only the grey studio backdrop with a sunlit Mediterranean scene: white stone "
                   "arch wall, warm terracotta tile floor, golden sunlight with a soft arch shadow "
                   "falling across the wall. Composite her into the new scene with naturally matching "
                   "warm light direction. Photorealistic e-commerce fashion photography."),
        "images": [os.path.join(OUT, "tryon_best.png")],
        "seeds": (91221, 91222, 91223),
    },
    "scene_street": {
        "prompt": ("Background replacement edit. Keep the woman in image 1 pixel-identical: same face, "
                   "same rimless glasses, same long dark brown hair (keep her natural dark hair color, "
                   "no green or olive tint), same floral dress, same pose, same camera framing, and keep "
                   "her exact skin tone and clothing colors - do not color grade or re-tint the subject. "
                   "Replace only the grey studio backdrop with a European old-town cobblestone street: "
                   "cream plaster buildings, wooden shutters, shallow depth of field, soft overcast "
                   "daylight. Composite her into the new scene naturally. Photorealistic street-style "
                   "fashion photography."),
        "images": [os.path.join(OUT, "tryon_best.png")],
        "seeds": (91321, 91322, 91323),
    },
    "pose": {
        "prompt": ("Put the same woman from image 1 into the body pose, camera angle and background of "
                   "image 2. She wears the same coffee brown polka dot slip midi dress as in image 1. "
                   "Keep her exact same face, rimless glasses, makeup and long dark brown hair with "
                   "bangs - do not change her identity. Ignore the person and outfit in image 2, take "
                   "only the pose, framing and background. Realistic skin texture, photorealistic "
                   "e-commerce fashion photography."),
        "images": [ANCHOR, None],  # None 处运行时填姿态参考
        "seeds": (91401,),
    },
    "blank": {
        "prompt": ("Garment cleaning edit. Remove the large floral print from the red t-shirt, turning "
                   "it into a plain red cotton t-shirt. Keep the fabric texture, folds, shadows, the "
                   "neckline and the ghost mannequin shape exactly the same. No smearing, keep edges "
                   "crisp."),
        "images": [os.path.join(ROOT, "assets", "garments", "cand_redtee_floral.png")],
        "seeds": (91501, 91502),
    },
    "blank_tee": {
        "prompt": ("Garment cleaning edit. Remove the black text print on the chest and the neck label "
                   "from this white t-shirt, turning it into a plain blank white cotton t-shirt. Keep "
                   "the fabric texture, folds, shadows and the ghost mannequin shape exactly the same. "
                   "No smearing, keep edges crisp."),
        "images": [os.path.join(ROOT, "assets_v2", "garments", "g_tee_awet.jpg")],
        "seeds": (91601, 91602),
    },
}


def run_case(case):
    c = CASES[case]
    if case == "pose":
        for pose_key, ref in POSE_REFS.items():
            imgs = [prep(ANCHOR, "pose_anchor.png"), prep(ref, f"pose_ref_{pose_key}.jpg")]
            for seed in c["seeds"]:
                wf = workflow(c["prompt"], [u for u in imgs], seed)
                wf["12"]["inputs"]["filename_prefix"] = f"v9_pose_{pose_key}_{seed}"
                print(pose_key, seed, comfy_api.run_watchdog(wf, OUT), flush=True)
        return
    images = [prep(p, f"{case}_in{i}.png") for i, p in enumerate(c["images"], 1)]
    for seed in c["seeds"]:
        wf = workflow(c["prompt"], images, seed)
        wf["12"]["inputs"]["filename_prefix"] = f"v9_{case}_{seed}"
        print(case, seed, comfy_api.run_watchdog(wf, OUT), flush=True)


if __name__ == "__main__":
    case = sys.argv[1] if len(sys.argv) > 1 else "tryon"
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    comfy_api.wait_server()
    run_case(case)
