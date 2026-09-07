# -*- coding: utf-8 -*-
"""V4 Qwen-Image-Edit 2509 (GGUF Q4) 双输入虚拟试穿
输入: 模特图(image1) + 服装图(image2) → 指令换装
加速: Lightning 4steps LoRA (cfg 1.0)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image

ROOT = r"."
OUT = os.path.join(ROOT, "outputs_v2", "qwen")

MODEL = "Qwen-Image-Edit-2509-fp16-fixed.safetensors"
CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
VAE = "qwen_image_vae.safetensors"
LORA = "Qwen-Image-Edit-2509-Lightning-4steps-bf16.safetensors"

PERSON = os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")   # 模特原图 1500x2000
GARMENT = os.path.join(ROOT, "assets_v2", "garments", "v2ref_case1_dressfloral.jpg")  # 花卉裙紧裁

PROMPT = (
    "The woman from image 1 is now wearing the navy blue floral print mini dress from "
    "image 2. Keep her face, hairstyle, body pose and the light grey studio background "
    "exactly the same. Only the dress changes."
)


def workflow(person_name, garment_name, seed, W, H):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "LoadImage", "inputs": {"image": person_name}},
        "5": {"class_type": "LoadImage", "inputs": {"image": garment_name}},
        "6": {"class_type": "LoraLoaderModelOnly", "inputs": {
            "model": ["1", 0], "lora_name": LORA, "strength_model": 1.0}},
        # 2509 多图编辑: 引用 image1(模特) 与 image2(服装)
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["2", 0], "prompt": PROMPT, "vae": ["3", 0],
            "image1": ["4", 0], "image2": ["5", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
        "9": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["3", 0]}},
        "13": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "10": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 25, "cfg": 2.5,
                                                    "sampler_name": "euler", "scheduler": "simple",
                                                    "denoise": 1.0, "model": ["1", 0],
                                                    "positive": ["7", 0], "negative": ["8", 0],
                                                    "latent_image": ["9", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v4qwen", "images": ["11", 0]}},
    }


if __name__ == "__main__":
    comfy_api.wait_server()

    # 预处理: 模特图缩到 832x1120 (16 的倍数, Qwen 友好)
    im = Image.open(PERSON).convert("RGB")
    W, H = 832, 1120
    im = im.resize((W, H), Image.LANCZOS)
    person_p = os.path.join(OUT, "qwen_person.png")
    os.makedirs(OUT, exist_ok=True)
    im.save(person_p)
    garment_p = GARMENT

    up1 = comfy_api.upload_image(person_p)
    up2 = comfy_api.upload_image(garment_p)
    for seed in (88101, 88102):
        wf = workflow(up1["name"], up2["name"], seed, W, H)
        wf["12"]["inputs"]["filename_prefix"] = f"v4qwen_{seed}"
        print(seed, comfy_api.run(wf, OUT, timeout=1200))
