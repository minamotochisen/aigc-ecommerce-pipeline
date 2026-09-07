# -*- coding: utf-8 -*-
"""V9: Qwen-Image-Edit-2509 指令换装冒烟测试 (ComfyUI 0.34.0 引擎重试)
V8 在 0.29.2 上 fp16-fixed 报 img_in.weight 形状错误, 引擎更新后重验。
用法:
  python v9_qwen_edit.py            # Lightning 4步冒烟
  python v9_qwen_edit.py quality    # 无LoRA 25步质量模式
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image

ROOT = r"."
OUT = os.path.join(ROOT, "outputs_v2", "qwen")
os.makedirs(OUT, exist_ok=True)

MODEL = "Qwen-Image-Edit-2509-fp16-fixed.safetensors"
CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
VAE = "qwen_image_vae.safetensors"
LORA = "Qwen-Image-Edit-2509-Lightning-4steps-bf16.safetensors"

PERSON = os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")
GARMENT = os.path.join(ROOT, "assets_v2", "garments", "v2ref_case1_dressfloral.jpg")

PROMPT = (
    "The woman from image 1 is now wearing the navy blue floral print mini dress from "
    "image 2. Keep her face, hairstyle, body pose and the light grey studio background "
    "exactly the same. Only the dress changes."
)


def workflow(person_name, garment_name, seed, use_lora=True):
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "LoadImage", "inputs": {"image": person_name}},
        "5": {"class_type": "LoadImage", "inputs": {"image": garment_name}},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["2", 0], "prompt": PROMPT, "vae": ["3", 0],
            "image1": ["4", 0], "image2": ["5", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
        "9": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["3", 0]}},
        "13": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["6", 0], "shift": 3.1}},
        "10": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
            "denoise": 1.0, "model": ["13", 0],
            "positive": ["7", 0], "negative": ["8", 0], "latent_image": ["9", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v9qwen", "images": ["11", 0]}},
    }
    if use_lora:
        wf["6"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
            "model": ["1", 0], "lora_name": LORA, "strength_model": 1.0}}
    else:
        wf["13"]["inputs"]["model"] = ["1", 0]
        wf["10"]["inputs"]["steps"] = 25
        wf["10"]["inputs"]["cfg"] = 2.5
    return wf


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    use_lora = mode == "smoke"
    comfy_api.wait_server()

    im = Image.open(PERSON).convert("RGB")
    W, H = 832, 1120
    im = im.resize((W, H), Image.LANCZOS)
    person_p = os.path.join(OUT, "v9_person.png")
    im.save(person_p)

    up1 = comfy_api.upload_image(person_p)
    up2 = comfy_api.upload_image(GARMENT)
    seed = 88201
    wf = workflow(up1["name"], up2["name"], seed, use_lora=use_lora)
    wf["12"]["inputs"]["filename_prefix"] = f"v9qwen_{mode}_{seed}"
    print(mode, seed, comfy_api.run(wf, OUT, timeout=1800))
