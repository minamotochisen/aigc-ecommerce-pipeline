# -*- coding: utf-8 -*-
"""V13 视频生成统一管线: 三条模型路线参数化
  i2v   Wan2.2 TI2V 5B 图生视频    704p 竖/横 24fps 20步(标准) / 12步(降级档)
  t2v   Wan2.2 TI2V 5B 文生视频    同上
  flf   Wan2.1 FLF2V 14B 首尾帧    1280x720 16fps 20步 CFG6(换装转场)
  l14b  Wan2.2 I2V A14B + Lightning LoRA 4步(2+2) CFG1 shift5  1280x720 16fps

用法:
  python v13_video.py shot <name> [seed] [--steps N] [--length N]
  python v13_video.py ab   <name>           # 同seed 12步vs20步 A/B
  python v13_video.py list
首帧素材: outputs_v2/upscaled_v10/*.png (2600x3466 V11 终选)
输出: outputs_v2/video_v13/
"""
import argparse
import json
import os
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HD = os.path.join(ROOT, "outputs_v2", "upscaled_v10")
V10 = os.path.join(ROOT, "outputs_v2", "v10")
OUT = os.path.join(ROOT, "outputs_v2", "video_v13")
os.makedirs(OUT, exist_ok=True)
START_CACHE = os.path.join(OUT, "_starts")
os.makedirs(START_CACHE, exist_ok=True)

UNET = "D:\\ComfyUI_windows_portable\\ComfyUI_windows_portable_nvidia\\ComfyUI_windows_portable\\ComfyUI\\models\\diffusion_models"

NEG = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，"
       "低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，"
       "毁容，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走")

TRYON = os.path.join(HD, "v10_tryon_best_hd.png")       # 换装终选(花卉吊带裙)
WALK = os.path.join(HD, "v10_pose_walk_hd.png")
BACK = os.path.join(HD, "v10_pose_back_hd.png")
SIDE = os.path.join(HD, "v10_pose_side_hd.png")
SCENE_CREAM = os.path.join(HD, "v10_scene_med_hd.png")  # 奶油室内(V11终选)
SCENE_STREET = os.path.join(HD, "v10_scene_street_hd.png")
ANCHOR = os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")  # 波点裙真实输入

# 竖版全身: 高度铺满, 水平居中; 横版: 面部偏上保留
SHOTS = {
    "runway_front": dict(
        mode="i2v", start=TRYON, portrait=True,
        pos="A beautiful young asian woman in a navy blue floral print slip dress walks forward "
            "slowly on a fashion runway, confident elegant stride, her dress flowing and swaying "
            "naturally with each step, steady camera, bright soft studio lighting, high quality, smooth motion"),
    "runway_step": dict(
        mode="i2v", start=TRYON, portrait=True,
        pos="A beautiful young asian woman in a navy blue floral print slip dress takes a clear step "
            "forward toward the camera, mid-stride, her dress hem swinging with the movement, weight "
            "shifting naturally, steady camera, bright soft studio lighting, high quality, smooth motion"),
    "runway_turn": dict(
        mode="i2v", start=SIDE, portrait=True,
        pos="A beautiful young asian woman stands still and very slowly turns her head to glance "
            "back over her shoulder toward the camera, minimal gentle motion, arms relaxed at her "
            "sides, hair barely moving, locked static camera, soft studio lighting, high quality, "
            "smooth slow motion"),
    "walk_street": dict(
        mode="i2v", start=WALK, portrait=True,
        pos="A beautiful young asian woman in a navy blue floral print slip dress walks forward "
            "gracefully, natural confident pace, her dress swaying gently with each step, steady "
            "camera, soft even studio lighting, high quality, smooth motion"),
    "fabric_wind": dict(
        mode="i2v", start=TRYON, portrait=True,
        pos="A beautiful young asian woman in a navy blue floral print slip dress stands still in "
            "front of the camera, a soft breeze makes her dress hem and long hair sway gently and "
            "naturally, static locked camera, soft studio lighting, high quality, smooth motion"),
    "pose_twirl": dict(
        mode="i2v", start=BACK, portrait=True,
        pos="A beautiful young asian woman seen from behind in a navy blue floral print slip dress "
            "very slowly turns her head to glance back toward the camera, arms hanging relaxed at "
            "her sides the whole time, minimal subtle motion, locked static camera, soft studio "
            "lighting, high quality, smooth slow motion"),
    "scene_cream": dict(
        mode="i2v", start=SCENE_CREAM, portrait=False, bias=0.12,
        pos="Slow cinematic dolly-in toward a young asian woman standing still in a bright cream "
            "minimal living room, her arms relaxed at her sides, only her dress hem and hair sway "
            "gently, sheer curtains moving in soft daylight, warm serene atmosphere, stable smooth "
            "camera movement, high quality, smooth motion"),
    "scene_street": dict(
        mode="i2v", start=SCENE_STREET, portrait=False, bias=0.12,
        pos="A beautiful young asian woman in a navy blue floral print dress walks toward the camera "
            "on a european cobblestone street, camera slowly tracks backward, her dress and hair "
            "moving naturally with her steps, golden soft daylight, high quality, smooth motion"),
    "fabric_macro": dict(
        mode="i2v", start=TRYON, portrait=False, crop=(0.30, 0.32, 0.72, 0.60),
        pos="Extreme close-up of navy blue floral jacquard dress fabric filling the entire frame, "
            "the fabric ripples and sways gently in slow motion, no hands, no objects, only flowing "
            "cloth, soft studio light gliding across the texture, macro detail, high quality, smooth motion"),
    "t2v_silk": dict(
        mode="t2v", portrait=False,
        pos="Elegant flowing silk fabric in champagne color undulating in slow motion against a soft "
            "cream studio background, luxurious waves rippling through the cloth, cinematic studio "
            "lighting, high quality, smooth motion"),
    "l14b_compare": dict(
        mode="l14b", start=TRYON, portrait=False,
        pos="A beautiful young asian woman in a navy blue floral print slip dress walks forward "
            "slowly, confident stride, her dress flowing naturally, steady camera, bright studio "
            "lighting, high quality, smooth motion"),
    "flf_changeout": dict(
        mode="flf", start=ANCHOR, end=TRYON, portrait=False,
        start_bias=0.21, end_bias=0.0,
        pos="A young asian woman stands still facing the camera in a bright studio, her brown polka "
            "dot slip dress smoothly transforms into a navy blue floral print slip dress, seamless "
            "elegant transformation, static camera, soft studio lighting, high quality, smooth motion"),
}


def crop_start(src, W, H, crop=None, tag="", bias=None):
    """源图裁到目标 WxH: 竖版全身=高度铺满水平居中; 横版=宽度铺满纵向偏上(默认0.25);
    bias 覆盖纵向偏移比例(FLF 首尾帧人脸对齐用); crop=(x0,y0,x1,y1) 归一化局部裁片"""
    im = Image.open(src).convert("RGB")
    if crop:
        cw, ch = im.width, im.height
        im = im.crop((int(crop[0] * cw), int(crop[1] * ch), int(crop[2] * cw), int(crop[3] * ch)))
    r = max(W / im.width, H / im.height)
    im2 = im.resize((int(im.width * r + 0.5), int(im.height * r + 0.5)), Image.LANCZOS)
    x0 = (im2.width - W) // 2
    if bias is None:
        bias = 0.0 if (im.height >= im.width and H >= W) else 0.25
    y0 = 0 if im2.height <= H else int((im2.height - H) * bias)
    im2 = im2.crop((x0, y0, x0 + W, y0 + H))
    name = os.path.splitext(os.path.basename(src))[0] + f"_s{W}x{H}{tag}.png"
    p = os.path.join(START_CACHE, name)
    im2.save(p)
    return p


def base_nodes():
    return {
        "clip": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["clip", 0]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["clip", 0]}},
    }


def wf_5b(mode, seed, pos, start=None, W=704, H=1280, length=49, steps=20, prefix="v13"):
    wf = base_nodes()
    wf["unet"] = {"class_type": "UNETLoader", "inputs": {
        "unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}}
    wf["vae"] = {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}}
    wf["ms"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": ["unet", 0], "shift": 8.0}}
    latent_in = {}
    if start:
        wf["img"] = {"class_type": "LoadImage", "inputs": {"image": os.path.basename(start)}}
        latent_in["start_image"] = ["img", 0]
    wf["latent"] = {"class_type": "Wan22ImageToVideoLatent", "inputs": {
        "vae": ["vae", 0], "width": W, "height": H, "length": length,
        "batch_size": 1, **latent_in}}
    wf["ks"] = {"class_type": "KSampler", "inputs": {
        "seed": seed, "steps": steps, "cfg": 5.0, "sampler_name": "uni_pc", "scheduler": "simple",
        "denoise": 1.0, "model": ["ms", 0], "positive": ["pos", 0], "negative": ["neg", 0],
        "latent_image": ["latent", 0]}}
    wf["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}}
    wf["vid"] = {"class_type": "CreateVideo", "inputs": {"images": ["dec", 0], "fps": 24}}
    wf["save"] = {"class_type": "SaveVideo", "inputs": {
        "video": ["vid", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}}
    strip(wf, "dec", prefix, length)
    return wf


def strip(wf, dec_key, prefix, length=49):
    """抽 6 帧胶片条(首/20%/40%/60%/80%/末)"""
    idxs = [round(length * f) for f in (0, 0.2, 0.4, 0.6, 0.8)]
    idxs.append(length - 1)
    n = 30
    for i, idx in enumerate(idxs):
        wf[str(n)] = {"class_type": "ImageFromBatch", "inputs": {
            "image": [dec_key, 0], "batch_index": idx, "length": 1}}
        wf[str(n + 1)] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"{prefix}_f{i}", "images": [[str(n), 0]]}}
        n += 2


def wf_flf(seed, pos, start, end, W=1280, H=720, length=73, steps=20, prefix="v13flf"):
    wf = base_nodes()
    wf["unet"] = {"class_type": "UNETLoader", "inputs": {
        "unet_name": "wan2.1_flf2v_720p_14B_fp8_e4m3fn.safetensors", "weight_dtype": "default"}}
    wf["vae"] = {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}}
    wf["cv"] = {"class_type": "CLIPVisionLoader", "inputs": {
        "clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}}
    wf["img1"] = {"class_type": "LoadImage", "inputs": {"image": os.path.basename(start)}}
    wf["img2"] = {"class_type": "LoadImage", "inputs": {"image": os.path.basename(end)}}
    wf["cve1"] = {"class_type": "CLIPVisionEncode", "inputs": {
        "clip_vision": ["cv", 0], "image": ["img1", 0], "crop": "none"}}
    wf["cve2"] = {"class_type": "CLIPVisionEncode", "inputs": {
        "clip_vision": ["cv", 0], "image": ["img2", 0], "crop": "none"}}
    wf["ms"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": ["unet", 0], "shift": 8.0}}
    wf["flf"] = {"class_type": "WanFirstLastFrameToVideo", "inputs": {
        "positive": ["pos", 0], "negative": ["neg", 0], "vae": ["vae", 0],
        "clip_vision_start_image": ["cve1", 0], "clip_vision_end_image": ["cve2", 0],
        "start_image": ["img1", 0], "end_image": ["img2", 0],
        "width": W, "height": H, "length": length, "batch_size": 1}}
    wf["ks"] = {"class_type": "KSampler", "inputs": {
        "seed": seed, "steps": steps, "cfg": 6.0, "sampler_name": "uni_pc", "scheduler": "simple",
        "denoise": 1.0, "model": ["ms", 0], "positive": ["flf", 0], "negative": ["flf", 1],
        "latent_image": ["flf", 2]}}
    wf["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}}
    wf["vid"] = {"class_type": "CreateVideo", "inputs": {"images": ["dec", 0], "fps": 16}}
    wf["save"] = {"class_type": "SaveVideo", "inputs": {
        "video": ["vid", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}}
    return wf


def wf_l14b(seed, pos, start, W=1280, H=720, length=81, prefix="v13l14b"):
    """官方 Lightning 双阶段: 4步拆2+2, CFG1, shift5, wan2.1 vae"""
    wf = base_nodes()
    wf["unet_h"] = {"class_type": "UNETLoader", "inputs": {
        "unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}}
    wf["unet_l"] = {"class_type": "UNETLoader", "inputs": {
        "unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}}
    wf["vae"] = {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}}
    wf["lora_h"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
        "model": ["unet_h", 0], "lora_name": "wan2.2_i2v_a14b_lightning_high.safetensors",
        "strength_model": 1.0}}
    wf["lora_l"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
        "model": ["unet_l", 0], "lora_name": "wan2.2_i2v_a14b_lightning_low.safetensors",
        "strength_model": 1.0}}
    wf["ms_h"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": ["lora_h", 0], "shift": 5.0}}
    wf["ms_l"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": ["lora_l", 0], "shift": 5.0}}
    wf["img"] = {"class_type": "LoadImage", "inputs": {"image": os.path.basename(start)}}
    wf["latent"] = {"class_type": "WanImageToVideo", "inputs": {
        "positive": ["pos", 0], "negative": ["neg", 0], "vae": ["vae", 0],
        "start_image": ["img", 0], "width": W, "height": H, "length": length, "batch_size": 1}}
    wf["ks1"] = {"class_type": "KSamplerAdvanced", "inputs": {
        "add_noise": "enable", "noise_seed": seed, "steps": 4, "cfg": 1.0,
        "sampler_name": "euler", "scheduler": "simple", "start_at_step": 0, "end_at_step": 2,
        "return_with_leftover_noise": "enable", "model": ["ms_h", 0],
        "positive": ["latent", 0], "negative": ["latent", 1], "latent_image": ["latent", 2]}}
    wf["ks2"] = {"class_type": "KSamplerAdvanced", "inputs": {
        "add_noise": "disable", "noise_seed": seed, "steps": 4, "cfg": 1.0,
        "sampler_name": "euler", "scheduler": "simple", "start_at_step": 2, "end_at_step": 4,
        "return_with_leftover_noise": "disable", "model": ["ms_l", 0],
        "positive": ["latent", 0], "negative": ["latent", 1], "latent_image": ["ks1", 0]}}
    wf["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": ["ks2", 0], "vae": ["vae", 0]}}
    wf["vid"] = {"class_type": "CreateVideo", "inputs": {"images": ["dec", 0], "fps": 16}}
    wf["save"] = {"class_type": "SaveVideo", "inputs": {
        "video": ["vid", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}}
    return wf


def run_shot(name, seed, steps=None, length=None):
    s = SHOTS[name]
    prefix = f"v13_{name}_{seed}"
    if s["mode"] in ("i2v", "t2v"):
        W, H = (704, 1280) if s["portrait"] else (1280, 704)
        steps = steps or 20
        length = length or 49
        start = None
        if s["mode"] == "i2v":
            start = crop_start(s["start"], W, H, s.get("crop"), bias=s.get("bias"))
            comfy_api.upload_image(start)
        wf = wf_5b(s["mode"], seed, s["pos"], start=start, W=W, H=H,
                   length=length, steps=steps, prefix=prefix)
        per_run = 900
    elif s["mode"] == "flf":
        W, H, length = 1280, 720, (length or 73)
        steps = steps or 20
        start = crop_start(s["start"], W, H, tag="A", bias=s.get("start_bias"))
        end = crop_start(s["end"], W, H, tag="B", bias=s.get("end_bias"))
        comfy_api.upload_image(start)
        comfy_api.upload_image(end)
        wf = wf_flf(seed, s["pos"], start, end, W, H, length, steps, prefix=prefix)
        per_run = 3600
    elif s["mode"] == "l14b":
        W, H, length = 1280, 720, (length or 81)
        start = crop_start(s["start"], W, H, bias=0.0)
        comfy_api.upload_image(start)
        wf = wf_l14b(seed, s["pos"], start, W, H, length, prefix=prefix)
        per_run = 3600
    else:
        raise ValueError(s["mode"])
    t0 = time.time()
    print(f"[{name}] mode={s['mode']} seed={seed} steps={steps} len={length} start...", flush=True)
    paths = comfy_api.run_watchdog(wf, OUT, per_run=per_run, attempts=2)
    dt = time.time() - t0
    rec = {"shot": name, "mode": s["mode"], "seed": seed, "steps": steps, "length": length,
           "seconds": round(dt, 1), "files": [os.path.basename(p) for p in paths]}
    with open(os.path.join(OUT, "_runs.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{name}] done {dt:.0f}s ->", [os.path.basename(p) for p in paths], flush=True)
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["shot", "ab", "list"])
    ap.add_argument("name", nargs="?")
    ap.add_argument("seed", nargs="?", type=int, default=63001)
    ap.add_argument("--steps", type=int)
    ap.add_argument("--length", type=int)
    a = ap.parse_args()
    if a.cmd == "list":
        for k, v in SHOTS.items():
            print(k, v["mode"], "portrait" if v.get("portrait") else "landscape")
    elif a.cmd == "shot":
        run_shot(a.name, a.seed, a.steps, a.length)
    elif a.cmd == "ab":
        s = SHOTS[a.name]
        assert s["mode"] in ("i2v", "t2v"), "A/B 仅支持 5B"
        run_shot(a.name, a.seed, steps=12)
        run_shot(a.name, a.seed, steps=20)
