# -*- coding: utf-8 -*-
"""V9 模特视频化: Wan 2.2 5B TI2V — V9 换装成品静图 → 小幅动态片段
动作策略(如实定位为动态预览): 缓步 + 裙摆摆动, 避免大幅走秀导致的肢体崩坏
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api

ROOT = r"."
HD9 = os.path.join(ROOT, "outputs_v2", "upscaled_v9")
OUT = os.path.join(ROOT, "outputs_v2", "video")
os.makedirs(OUT, exist_ok=True)

START_IMG = os.path.join(HD9, "v9_tryon_full_91121_hd.png")

POS = (
    "A beautiful young asian woman with glasses in a navy blue floral print dress stands and "
    "turns slowly toward the camera, gentle small steps, her dress swaying softly, hair moving "
    "naturally in a light breeze, warm studio lighting, steady camera, photorealistic, high "
    "quality, smooth motion"
)
NEG = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，"
       "低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，"
       "毁容，形态畸形的肢体，手指融合，杂乱的背景，三条腿，背景人很多，倒着走，脸部变色，眼镜消失")


def workflow(seed, length=49, width=1280, height=704, steps=20):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": os.path.basename(START_IMG_LSC)}},
        "5": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["2", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 0]}},
        "8": {"class_type": "Wan22ImageToVideoLatent", "inputs": {
            "vae": ["3", 0], "width": width, "height": height, "length": length,
            "batch_size": 1, "start_image": ["4", 0]}},
        "9": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": 5.0,
                                                   "sampler_name": "uni_pc", "scheduler": "simple",
                                                   "denoise": 1.0, "model": ["5", 0],
                                                   "positive": ["6", 0], "negative": ["7", 0],
                                                   "latent_image": ["8", 0]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "CreateVideo", "inputs": {"images": ["10", 0], "fps": 24}},
        "12": {"class_type": "SaveVideo", "inputs": {"video": ["11", 0], "filename_prefix": "v9video",
                                                     "format": "auto", "codec": "auto"}},
    }


START_IMG_LSC = START_IMG  # 占位, __main__ 中覆盖

if __name__ == "__main__":
    comfy_api.wait_server()
    from PIL import Image
    # 预裁横版首帧(偏上保留面部)
    im = Image.open(START_IMG).convert("RGB")
    W, H = 1280, 704
    r = max(W / im.width, H / im.height)
    im2 = im.resize((int(im.width * r + 0.5), int(im.height * r + 0.5)), Image.LANCZOS)
    x0 = (im2.width - W) // 2
    y0 = max(0, int((im2.height - H) * 0.25))
    im2 = im2.crop((x0, y0, x0 + W, y0 + H))
    start_path = os.path.join(HD9, "c1_start_landscape.png")
    im2.save(start_path)
    globals()["START_IMG_LSC"] = start_path
    workflow.__globals__["START_IMG_LSC"] = start_path
    print("start frame:", im2.size)
    comfy_api.upload_image(start_path)

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 52901
    length = int(sys.argv[2]) if len(sys.argv) > 2 else 49
    wf = workflow(seed, length=length, width=W, height=H)
    print("gen:", comfy_api.run_watchdog(wf, OUT, per_run=1800, attempts=3))
