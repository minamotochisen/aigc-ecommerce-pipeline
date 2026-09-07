# -*- coding: utf-8 -*-
"""修复 Qwen-Image-Edit-2509-fp16-fixed.safetensors 的 img_in.weight 形状
diffusers 转换残留: Conv2d [3072,16,2,2] 未展平为 Linear [3072,64]。
展平前后字节序完全一致, 只需原地重写 safetensors 头部 JSON, 数据零拷贝。
"""
import json
import struct

P = (r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia"
     r"\ComfyUI_windows_portable\ComfyUI\models\diffusion_models"
     r"\Qwen-Image-Edit-2509-fp16-fixed.safetensors")
BAK = P + ".header.bak.json"

with open(P, "rb") as f:
    n = struct.unpack("<Q", f.read(8))[0]
    raw = f.read(n)
with open(BAK, "w", encoding="utf-8") as f:
    f.write(raw.decode("utf-8", errors="replace"))

hdr = json.loads(raw)
hdr.pop("__metadata__", None)
w = hdr["img_in.weight"]
assert w["shape"] == [3072, 16, 2, 2], w
w["shape"] = [3072, 64]

new = json.dumps(hdr, separators=(",", ":")).encode()
assert len(new) <= n, "new header larger, needs offset rewrite"
new += b" " * (n - len(new))  # safetensors 允许空白填充, 保持 data_offsets 不变

with open(P, "r+b") as f:
    f.write(struct.pack("<Q", n))
    f.write(new)
print(f"fixed img_in.weight -> [3072, 64], header {n}B kept, backup: {BAK}")
