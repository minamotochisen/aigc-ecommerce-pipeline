# -*- coding: utf-8 -*-
"""pass2: 修正 GGUF 打包布局 -> ComfyUI UNETLoader 可用布局"""
import torch
from safetensors.torch import safe_open, save_file

src = r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\models\diffusion_models\Qwen-Image-Edit-2509-Q4_K_M-fp16.safetensors"
dst = r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\models\diffusion_models\Qwen-Image-Edit-2509-fp16-fixed.safetensors"

out = {}
with safe_open(src, framework="pt") as f:
    keys = list(f.keys())
    n = 0
    for k in keys:
        t = f.get_tensor(k)
        if t.dim() == 2 and k.endswith(".weight"):
            # GGUF 打包布局: [packed_in, out]
            # conv 特例: img_in.weight (patch embed conv2d)
            if k == "img_in.weight":
                # [64, 3072] -> (16,2,2,3072) -> (3072,16,2,2)
                t = t.reshape(16, 2, 2, -1).permute(3, 0, 1, 2).contiguous()
            else:
                t = t.t().contiguous()
        out[k] = t
        n += 1
        if n % 400 == 0:
            print("  fixed", n)
save_file(out, dst, metadata={"format": "pt"})
print("saved:", dst)
