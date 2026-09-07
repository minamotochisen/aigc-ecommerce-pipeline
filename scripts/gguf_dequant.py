# -*- coding: utf-8 -*-
"""GGUF -> fp16 safetensors 反量化(绕过 ComfyUI-GGUF 节点校验 bug)"""
import os, sys, json
import torch
from safetensors.torch import save_file
import gguf

GGUF_DIR = r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-GGUF"
sys.path.insert(0, GGUF_DIR)
from dequant import dequantize_tensor

src = sys.argv[1]
dst = sys.argv[2]

reader = gguf.GGUFReader(src)
import numpy as np
TORCH_COMPATIBLE = (None, gguf.GGMLQuantizationType.F32, gguf.GGMLQuantizationType.F16)
sd = {}
arch = ""
try:
    for f in reader.fields.values():
        if f.name == "general.architecture":
            arch = bytes(f.parts[-1]).decode("utf-8", errors="replace")
except Exception:
    pass
print("arch:", arch)

n = 0
for tensor in reader.tensors:
    name = tensor.name
    qtype = getattr(tensor, "tensor_type", None)
    oshape = tuple(tensor.shape)
    if qtype in TORCH_COMPATIBLE:
        arr = np.asarray(tensor.data).astype(np.float16)
        t = torch.from_numpy(arr)
    else:
        shim = type("T", (), {})()
        shim.data = torch.from_numpy(np.asarray(tensor.data).copy())
        shim.tensor_type = qtype
        shim.tensor_shape = oshape
        shim.shape = oshape
        t = dequantize_tensor(shim, dtype=torch.float16)
    sd[name] = t.contiguous()
    n += 1
    if n % 200 == 0:
        print(f"  dequantized {n} tensors...")
print(f"total {n} tensors, saving...")

# ComfyUI diffusion_models 需要 model.diffusion_model 前缀或裸键均可; 裸键即可被识别
sd_out = {k: v for k, v in sd.items()}
save_file(sd_out, dst, metadata={"format": "pt"})
print("saved:", dst, round(os.path.getsize(dst) / 1048576), "MB")
