# -*- coding: utf-8 -*-
"""V10 批次J: 91830修手链 -> 验收图输出 -> 超分(tryon_new + 91745背面) -> 掩膜重建 -> 掩膜场景x4"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v10_qwen2511 as v10

ROOT = v10.ROOT
OUT = v10.OUT
HD10 = os.path.join(ROOT, "outputs_v2", "upscaled_v10")
PICK = os.path.join(OUT, "v10_tryon_b_91830_00001_.png")
PY = sys.executable
EMB = r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\python_embeded\python.exe"


def verify_cpu(paths):
    env = dict(os.environ, V10_CPU="1")
    r = subprocess.run([EMB, os.path.join(ROOT, "scripts", "v10_verify.py"), *paths],
                       capture_output=True, text=True, env=env, cwd=os.path.dirname(EMB))
    boxes = {}
    for line in r.stdout.splitlines():
        if line.startswith("{"):
            d = json.loads(line)
            boxes[os.path.basename(d["image"])] = d.get("_handboxes", {})
    return boxes


def upscale_inline(path, out):
    up = comfy_api.upload_image(path)
    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": up["name"]}},
        "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x-UltraSharp.pth"}},
        "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "SaveImage", "inputs": {"filename_prefix": "hdtmp", "images": ["3", 0]}},
    }
    comfy_api.run(wf, HD10, timeout=900)
    cands = sorted(glob.glob(os.path.join(HD10, "hdtmp_*.png")), key=os.path.getmtime, reverse=True)
    os.replace(cands[0], out)
    im = Image.open(out)
    if im.width > 2600:
        im = im.resize((2600, int(im.height * 2600 / im.width)), Image.LANCZOS)
        im.save(out)


def main():
    comfy_api.wait_server()
    # 1. handfix 链: R -> L (已有产物则复用)
    final = os.path.join(OUT, "handfix_final_91841.png")
    if not os.path.exists(final):
        seed = 91840
        cur = PICK
        for attempt in range(2):
            boxes = verify_cpu([cur])
            side = "R" if attempt == 0 else "L"
            bb = boxes.get(os.path.basename(cur), {}).get(side)
            if not bb:
                print("no box for", side, flush=True)
                break
            v10.handfix(cur, bb, seed=seed)
            cur = os.path.join(OUT, "handfix_final_%d.png" % seed)
            seed += 1
        final = cur
    shutil.copy(final, os.path.join(OUT, "tryon_best.png"))
    print("tryon_best <-", final, flush=True)

    # 2. 超分: tryon_new + P6背面图
    upscale_inline(os.path.join(OUT, "tryon_best.png"), os.path.join(HD10, "v10_tryon_best_hd.png"))
    print("HD tryon_best", flush=True)
    upscale_inline(os.path.join(OUT, "v10_pose_back_91745_00001_.png"),
                   os.path.join(HD10, "v10_pose_back_hd.png"))
    print("HD pose_back", flush=True)

    # 3. 掩膜重建
    subprocess.run([PY, os.path.join(ROOT, "scripts", "v10_scene_mask.py")], check=True)

    # 4. 掩膜场景 x4
    c_med = v10.CASES["scene_med"]
    c_st = v10.CASES["scene_street"]
    img = comfy_api.upload_image(os.path.join(OUT, "tryon_best.png"))
    mask_name = "scene_person_mask.png"
    for seed in (91815, 91816):
        t0 = time.time()
        wf = v10_batch_h_wf(c_med["prompt"], v10.NEGATIVE, img, mask_name, seed)
        wf["12"]["inputs"]["filename_prefix"] = f"v10_scene_mmasked_{seed}"
        comfy_api.run(wf, OUT, timeout=600)
        print("OK masked med", seed, round(time.time() - t0, 1), flush=True)
    for seed in (91817, 91818):
        t0 = time.time()
        wf = v10_batch_h_wf(c_st["prompt"], v10.NEGATIVE, img, mask_name, seed)
        wf["12"]["inputs"]["filename_prefix"] = f"v10_scene_smasked_{seed}"
        comfy_api.run(wf, OUT, timeout=600)
        print("OK masked street", seed, round(time.time() - t0, 1), flush=True)


def v10_batch_h_wf(prompt, negative, image_upload, mask_name, seed, steps=20, cfg=4.0):
    import v10_batch_h
    return v10_batch_h.masked_workflow(prompt, negative, image_upload, mask_name, seed, steps, cfg)


if __name__ == "__main__":
    main()
