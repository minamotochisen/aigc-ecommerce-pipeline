# -*- coding: utf-8 -*-
"""V11 批次: 重建人物掩膜 -> 掩膜场景替换(40步/CFG3) cream x2 + street x2
前置: tryon_best.png 已更新为 V11 选定成片。"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v10_qwen2511 as v10
from v10_batch_h import masked_workflow

OUT = v10.OUT

# 1) 重建掩膜 (rembg 只装在 ComfyUI 内嵌 python, 读 tryon_best.png)
COMFY_PY = (r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia"
            r"\ComfyUI_windows_portable\python_embeded\python.exe")
subprocess.run([COMFY_PY, os.path.join(os.path.dirname(__file__), "v11_scene_mask.py")], check=True)


def main():
    comfy_api.wait_server()
    img = comfy_api.upload_image(os.path.join(OUT, "tryon_best.png"))
    mask_name = "scene_person_mask.png"
    jobs = [("cream", v10.CASES["scene_cream"]["prompt"], 92210, 92211),
            ("street", v10.CASES["scene_street"]["prompt"], 92212, 92213)]
    for tag, prompt, s1, s2 in jobs:
        for seed in (s1, s2):
            t0 = time.time()
            wf = masked_workflow(prompt, v10.NEGATIVE, img, mask_name, seed, steps=40, cfg=3.0)
            wf["12"]["inputs"]["filename_prefix"] = f"v11_scene_{tag}_{seed}"
            comfy_api.run_watchdog(wf, OUT, per_run=v10.PER_RUN)
            print("OK", tag, seed, round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    main()
