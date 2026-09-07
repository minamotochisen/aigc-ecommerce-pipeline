# -*- coding: utf-8 -*-
"""流式修正 GGUF 打包布局 -> ComfyUI UNETLoader 可用 safetensors (内存安全版)"""
import json
import os
import sys

import numpy as np
import torch
from safetensors.torch import safe_open
from safetensors.torch import save_file

GGUF_DIR = r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-GGUF"
sys.path.insert(0, GGUF_DIR)
from dequant import dequantize_tensor  # noqa

src = r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\models\diffusion_models\Qwen-Image-Edit-2509-Q4_K_M-fp16.safetensors"
dst = r".\outputs_v2\upscaled\qwen_edit2509_fp16_fixed.safetensors"

TORCH_COMPATIBLE = (None, 0, 1)  # None/F32/F16 在本流程中经 numpy 处理


def fix_tensor(k, t):
    if t.dim() == 2 and k.endswith(".weight") and k == "img_in.weight":
        return t.reshape(16, 2, 2, -1).permute(3, 0, 1, 2).contiguous()
    if t.dim() == 2 and k.endswith(".weight"):
        return t.t().contiguous()
    return t.contiguous()


with safe_open(src, framework="pt") as f:
    meta = f.metadata() or {}
    keys = list(f.keys())
    shapes = {k: tuple(f.get_slice(k).get_shape()) for k in keys}

# fp16 输出的字节布局
header = {"__metadata__": {"format": "pt"}}
offset = 0
for k in keys:
    shp = list(shapes[k])
    if k == "img_in.weight":
        n_bytes = 2 * int(np.prod(shp))
        c = int(np.prod(shp) // 64)
        shp = [c, 16, 2, 2]  # (16,2,2,C) -> (C,16,2,2)
    else:
        n_bytes = 2 * int(np.prod(shp)) if shp else 2
        if len(shp) == 2:
            shp = [shp[1], shp[0]]
    header[k] = {"dtype": "F16", "shape": shp,
                 "data_offsets": [offset, offset + n_bytes]}
    offset += n_bytes
hb = json.dumps(header, separators=(",", ":")).encode("utf-8")
hb += b" " * ((8 - len(hb) % 8) % 8)

with open(dst, "wb") as out:
    out.write(len(hb).to_bytes(8, "little"))
    out.write(hb)
    with safe_open(src, framework="pt") as f:
        n = 0
        for k in keys:
            t = f.get_tensor(k)
            if k == "img_in.weight":
                t = t.reshape(16, 2, 2, -1).permute(3, 0, 1, 2)
            elif t.dim() == 2 and k.endswith(".weight"):
                t = t.t()
            arr = t.to(torch.float16).contiguous().numpy()
            out.write(arr.tobytes())
            n += 1
            if n % 200 == 0:
                print("  wrote", n)
print("saved:", dst)
