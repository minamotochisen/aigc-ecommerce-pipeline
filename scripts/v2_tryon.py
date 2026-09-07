# -*- coding: utf-8 -*-
"""V2 Demo1 服装智能换装 (SDXL 栈, 高分辨率真实模特照)

管线: 真实模特照 + 真实服装图(IPAdapter Plus SDXL 参考)
      -> 剪影/服装区遮罩(GrowMask+羽化) -> SDXL 局部重绘 denoise 1.0
      -> ImageCompositeMasked 回贴(脸/姿态/鞋零变化)
案例:
  case1_dressfloral: C_dress 波点吊带长裙 -> 碎花吊带短裙(裙换裙, 亚洲模特)
  case2_blouse:      A_tank 背心+阔腿裤   -> 白色荷叶边衬衫(上装替换)
  case3_dressstripe: D_jump 棕色连体裤    -> 条纹泡泡袖连衣裙(连体裤换裙)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
A2 = os.path.join(ROOT, "assets_v2")
OUT = os.path.join(ROOT, "outputs_v2", "tryon")

CKPT = "sd_xl_base_1.0.safetensors"
# 模特照原图 -> (工作分辨率, 遮罩多边形[工作分辨率坐标])
CASES = {
    "case1_dressfloral": {
        "model_src": os.path.join(A2, "models", "m_dress_brown.webp"),
        "work": (896, 1184),
        # 裙换裙(同长度), 只遮裙子区域
        "polys_work": [
            (300, 270), (492, 275), (545, 424), (568, 612), (558, 770), (548, 918),
            (560, 1000), (490, 1075), (420, 1085), (340, 1030), (292, 950), (285, 849),
            (295, 681), (270, 513), (300, 375),
        ],
        "ref_src": os.path.join(ROOT, "assets", "garments", "ref_A_floral_mini.jpg"),
        "ref_crop": (20, 40, 580, 655),  # 紧裁裙身面料(不带背景)
        "prompt": (
            "a young asian woman wearing a (dark navy blue floral print slip midi dress:1.4), "
            "pink rose floral pattern all over the dress, thin straps, v-neckline, "
            "flowy ankle-length skirt, silver sandals, long black hair, "
            "(cool grey seamless studio backdrop:1.2), e-commerce fashion photography, "
            "soft studio lighting, highly detailed fabric, photorealistic, masterpiece, best quality"
        ),
    },
    "case2_dressfloral2": {
        "model_src": os.path.join(A2, "models", "m_tank_cream.jpg"),
        "work": (896, 1120),
        # 遮罩: 背心+阔腿裤全区域(至画面底缘)
        "polys_work": [
            (280, 380), (650, 380), (682, 560), (702, 760), (692, 940), (684, 1118),
            (298, 1118), (272, 900), (255, 700), (260, 530),
        ],
        "ref_src": os.path.join(ROOT, "assets", "garments", "ref_A_floral_mini.jpg"),
        "ref_crop": (20, 40, 580, 655),
        "prompt": (
            "a young woman wearing a (dark navy blue floral print mini dress:1.4), "
            "pink rose floral pattern all over the dress, thin black ribbon straps, "
            "sweetheart neckline, flowy skirt, bare legs, long brown hair, "
            "(seamless white studio background:1.2), e-commerce fashion photography, "
            "soft daylight, highly detailed fabric, photorealistic, masterpiece, best quality"
        ),
    },
    "case2_scene": {
        "model_src": os.path.join(A2, "models", "m_tank_cream.jpg"),
        "work": (896, 1120),
        # 全幅遮罩 + 重羽化: 换场景不换装
        "polys_work": [
            [(35, 22), (862, 22), (862, 1116), (35, 1116)],
        ],
        "ref_skip": True,
        "ref_src": os.path.join(A2, "models", "m_tank_cream.jpg"),
        "ref_crop": (0, 0, 10, 10),
        "prompt": (
            "the same young woman wearing the same black ribbed tank top and cream wide-leg "
            "trousers, standing in front of a (warm terracotta stucco wall:1.3) with a large "
            "arch shadow, golden hour sunlight, minimalist mediterranean architecture, "
            "fashion editorial photography, depth of field, photorealistic, masterpiece, best quality"
        ),
    },
    "case4_dressstripe": {
        "model_src": os.path.join(A2, "models", "m_jumpsuit.jpg"),
        "work": (896, 1248),
        # 硬遮罩多边形: 躯干+袖 / 左腿 / 右腿 (含白T领口)
        "polys_work": [
            [(225, 175), (690, 172), (695, 258), (676, 390), (700, 520), (688, 560),
             (262, 560), (240, 470), (205, 345), (228, 228)],
            [(262, 545), (452, 545), (455, 1145), (305, 1145)],
            [(458, 545), (690, 545), (678, 1148), (505, 1148)],
        ],
        "ref_src": os.path.join(A2, "garments", "g_tcherassi.png"),
        "ref_crop": (690, 760, 1360, 1860),  # 极紧裁纯面料
        "prompt": (
            "a young woman wearing an (opaque blue and orange striped plaid midi dress:1.3) with "
            "dramatic puffy short sleeves, belted waist, v-neck, bare legs, white sneakers, "
            "hair tied back, (cool grey seamless studio backdrop:1.3), e-commerce fashion "
            "photography, soft studio lighting, highly detailed fabric, photorealistic, masterpiece"
        ),
    },
    "case3_scene": {
        "model_src": os.path.join(A2, "models", "m_dress_brown.webp"),
        "work": (896, 1184),
        # 全身剪影大遮罩(含背景): 整体换场景, 服装保持不变
        "polys_work": [
            [(40, 25), (856, 25), (856, 1180), (40, 1180)],
        ],
        "ref_src": os.path.join(A2, "models", "m_dress_brown.webp"),
        "ref_crop": (0, 0, 10, 10),  # 场景变换无需服装参考(占位)
        "ref_skip": True,
        "prompt": (
            "a young asian woman wearing the same (coffee brown polka dot slip midi dress:1.4), "
            "white polka dot print, thin straps, silver sandals, long black hair, "
            "walking on a (sunlit old european stone street:1.3), warm afternoon sunlight, "
            "blurred street background with cafe and green plants, candid fashion editorial "
            "photography, depth of field, photorealistic, masterpiece, best quality"
        ),
    },
}

NEG = (
    "blonde hair, pink background, beige background, "
    "transparent, sheer, see-through, translucent, nsfw, polka dots, jumpsuit, tank top, cgi, cartoon, anime, 3d, render, worst quality, "
    "low quality, blurry, deformed, bad anatomy, bad hands, extra fingers, watermark, text, logo"
)


def load_work(case):
    im = Image.open(case["model_src"]).convert("RGB")
    W, H = case["work"]
    return im.resize((W, H), Image.LANCZOS)


def build_mask(case, out_prefix):
    im = load_work(case)
    W, H = case["work"]
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    polys = case["polys_work"]
    if polys and isinstance(polys[0][0], (list, tuple)):  # 多边形列表
        for poly in polys:
            d.polygon(poly, fill=255)
    else:
        d.polygon(polys, fill=255)
    m = m.point(lambda p: 255 if p > 100 else 0)
    vis = im.copy()
    red = Image.new("RGB", (W, H), (255, 40, 40))
    vis = Image.composite(red, vis, m.point(lambda p: int(p * 0.5)))
    vis.save(os.path.join(OUT, f"{out_prefix}_maskvis.jpg"), quality=90)
    return im, m


def workflow(img_file, mask_file, ref_file, prompt, seed, denoise=1.0):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoadImage", "inputs": {"image": img_file}},
        "6": {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": ["1", 0], "preset": "PLUS (high strength)"}},
        "7": {"class_type": "LoadImage", "inputs": {"image": ref_file}},
        "8": {"class_type": "IPAdapter", "inputs": {"model": ["6", 0], "ipadapter": ["6", 1],
                                                    "image": ["7", 0], "weight": 0.5,
                                                    "weight_type": "standard", "start_at": 0.0, "end_at": 1.0}},
        "4": {"class_type": "LoadImageMask", "inputs": {"image": mask_file, "channel": "red"}},
        "5": {"class_type": "GrowMask", "inputs": {"mask": ["4", 0], "expand": 30, "tapered_corners": True}},
        "5b": {"class_type": "MaskToImage", "inputs": {"mask": ["5", 0]}},
        "5c": {"class_type": "ImageBlur", "inputs": {"image": ["5b", 0], "blur_radius": 11, "sigma": 5.0}},
        "5d": {"class_type": "ImageToMask", "inputs": {"image": ["5c", 0], "channel": "red"}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}},
        "12": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["11", 0], "mask": ["5", 0]}},
        "13": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 32, "cfg": 6.5,
                                                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                                                    "denoise": denoise, "model": ["8", 0],
                                                    "positive": ["9", 0], "negative": ["10", 0],
                                                    "latent_image": ["12", 0]}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["1", 2]}},
        "15": {"class_type": "ImageCompositeMasked", "inputs": {"destination": ["2", 0], "source": ["14", 0],
                                                                "mask": ["5", 0], "x": 0, "y": 0,
                                                                "resize_source": False}},
        "16": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v2tryon", "images": ["15", 0]}},
    }


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "mask"
    os.makedirs(OUT, exist_ok=True)
    if mode == "mask":
        for key, case in CASES.items():
            im, m = build_mask(case, key)
            im.save(os.path.join(OUT, f"{key}_in.png"))
            m.save(os.path.join(OUT, f"{key}_mask.png"))
            # 裁剪并保存服装参考
            ref = Image.open(case["ref_src"]).convert("RGB").crop(case["ref_crop"])
            ref.save(os.path.join(A2, "garments", f"v2ref_{key}.jpg"), quality=92)
            print("mask ready:", key)
    elif mode == "run":
        comfy_api.wait_server()
        for key, case in CASES.items():
            up_img = comfy_api.upload_image(os.path.join(OUT, f"{key}_in.png"))
            up_mask = comfy_api.upload_image(os.path.join(OUT, f"{key}_mask.png"),
                                             name=f"{key}_mask_{sys.argv[2]}.png")
            if case.get("ref_skip"):
                up_ref = {"name": "placeholder.png"}
            else:
                ref_p = os.path.join(A2, "garments", f"v2ref_{key}.jpg")
                up_ref = comfy_api.upload_image(ref_p)
            for seed in (int(sys.argv[2]),):
                if case.get("ref_skip"):
                    wf = workflow(up_img["name"], up_mask["name"], up_img["name"], case["prompt"], seed)
                    del wf["6"], wf["7"], wf["8"]
                    wf["13"]["inputs"]["model"] = ["1", 0]
                    wf["13"]["inputs"]["positive"] = ["9", 0]
                else:
                    wf = workflow(up_img["name"], up_mask["name"], up_ref["name"], case["prompt"], seed)
                wf["16"]["inputs"]["filename_prefix"] = f"v2tryon_{key}_{seed}"
                print(key, comfy_api.run(wf, OUT, timeout=900))
