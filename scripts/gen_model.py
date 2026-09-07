# -*- coding: utf-8 -*-
"""生成电商女装模特基础图：白T+牛仔裤、影棚背景、全身竖构图"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "models")

POS = (
    "full body fashion photo of a beautiful young asian woman, 25 years old, long straight black hair, "
    "natural makeup, wearing a plain white crew-neck t-shirt and light blue slim jeans, white sneakers, "
    "standing straight, arms relaxed at sides, looking at camera, "
    "e-commerce studio photography, seamless light grey studio background, soft even lighting, "
    "(high detailed skin:1.2), 8k uhd, dslr, soft lighting, masterpiece, best quality, realistic photo, film grain"
)
NEG = (
    "(nsfw:1.4), cgi, fake, cartoon, anime, plastic skin, 3d, render, illustration, "
    "worst quality, low quality, blurry, deformed, bad anatomy, bad hands, extra fingers, "
    "extra limbs, missing limbs, watermark, text, logo, jpeg artifacts"
)


def build_t2i(seed, width=512, height=768, pos=POS, neg=NEG, prefix="model_base"):
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "realisticVisionV60B1_v51HyperVAE.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": 30, "cfg": 6.5, "sampler_name": "dpmpp_2m",
                         "scheduler": "karras", "denoise": 1, "model": ["1", 0],
                         "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"filename_prefix": prefix, "images": ["6", 0]}},
    }


if __name__ == "__main__":
    comfy_api.wait_server()
    for i, seed in enumerate([20260828, 20260829, 20260830, 20260831]):
        paths = comfy_api.run(build_t2i(seed), OUT, timeout=300)
        print(f"seed={seed} -> {paths}")
