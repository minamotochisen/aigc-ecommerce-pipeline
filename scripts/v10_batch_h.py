# -*- coding: utf-8 -*-
"""V10 批次H: 掩膜版场景替换 (人物像素锁定, 只重绘背景) med x2 + street x2"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v10_qwen2511 as v10

OUT = v10.OUT
MODEL = v10.MODEL
CLIP = v10.CLIP
VAE = v10.VAE


def masked_workflow(prompt, negative, image_upload, mask_name, seed, steps=20, cfg=4.0):
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "5": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
        "20": {"class_type": "LoadImage", "inputs": {"image": image_upload["name"] if isinstance(image_upload, dict) else image_upload}},
        "6": {"class_type": "VAEEncode", "inputs": {"pixels": ["20", 0], "vae": ["3", 0]}},
        "22": {"class_type": "LoadImageMask", "inputs": {"image": mask_name, "channel": "alpha"}},
        "23": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["6", 0], "mask": ["22", 0]}},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["2", 0], "prompt": prompt, "vae": ["3", 0], "image1": ["20", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 0]}},
        "9": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
            "denoise": 1.0, "model": ["5", 0], "positive": ["7", 0], "negative": ["8", 0],
            "latent_image": ["23", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v10_scene_masked", "images": ["11", 0]}},
    }
    return wf


def main():
    comfy_api.wait_server()
    img = comfy_api.upload_image(os.path.join(OUT, "tryon_best.png"))
    mask_name = "scene_person_mask.png"
    c_med = v10.CASES["scene_med"]
    c_st = v10.CASES["scene_street"]
    for seed in (91810, 91811):
        t0 = time.time()
        wf = masked_workflow(c_med["prompt"], v10.NEGATIVE, img, mask_name, seed)
        wf["12"]["inputs"]["filename_prefix"] = f"v10_scene_mmasked_{seed}"
        comfy_api.run(wf, OUT, timeout=600)
        print("OK masked med", seed, round(time.time() - t0, 1), flush=True)
    for seed in (91812, 91813):
        t0 = time.time()
        wf = masked_workflow(c_st["prompt"], v10.NEGATIVE, img, mask_name, seed)
        wf["12"]["inputs"]["filename_prefix"] = f"v10_scene_smasked_{seed}"
        comfy_api.run(wf, OUT, timeout=600)
        print("OK masked street", seed, round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    main()
