# -*- coding: utf-8 -*-
"""CodeFormer 人脸修复 (本地, 不经过生成模型):
用法: python_embeded/python.exe v12_codeformer.py <img1> [img2...]  (CWD 必须 = python_embeded)
输出: <img目录>/cf<w>/<stem>.png"""
import sys

import numpy as np
import cv2
import torch
from torchvision.transforms.functional import normalize
from facexlib.utils.face_restoration_helper import FaceRestoreHelper
from codeformer.basicsr.archs.codeformer_arch import CodeFormer as CodeFormerArch

W = float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].replace(".", "").isdigit() else 0.7
IMGS = sys.argv[2:] if len(sys.argv) > 2 else sys.argv[1:]

CKPT = (r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia"
        r"\ComfyUI_windows_portable\python_embeded\weights\CodeFormer\codeformer.pth")
DEV = "cuda" if torch.cuda.is_available() else "cpu"

net = CodeFormerArch(dim_embd=512, codebook_size=1024, n_head=8, n_layers=9).to(DEV)
ck = torch.load(CKPT, map_location="cpu", weights_only=True)
net.load_state_dict(ck["params_ema"] if "params_ema" in ck else ck["params"])
net.eval()

for path in IMGS:
    helper = FaceRestoreHelper(1, face_size=512, crop_ratio=(1, 1), det_model="retinaface_resnet50",
                               save_ext="png", use_parse=True, device=DEV)
    helper.clean_all()
    # cv2.imread 不支持中文路径, 先 imdecode 再传入
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert img is not None, "read fail: " + path
    helper.read_image(img)
    with torch.no_grad():
        helper.get_face_landmarks_5(only_center_face=False, resize=640, eye_dist_threshold=5)
    helper.align_warp_face()
    n = len(helper.cropped_faces)
    print(n, "faces", flush=True)
    for cf in helper.cropped_faces:
        t = cv2.resize(cf, (512, 512), interpolation=cv2.INTER_LINEAR)
        t = img2t = torch.from_numpy(t).to(DEV).float() / 255.0
        t = t.permute(2, 0, 1).flip(0)[None, ...]  # BGR -> RGB
        normalize(t, (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), inplace=True)
        with torch.no_grad():
            out = net(t, w=W, adain=True)
        if isinstance(out, (list, tuple)):
            out = out[0]
        if out.dim() == 4:
            out = out[0]
        # 官方口径: 输出范围 (-1,1), tensor2img(min_max=(-1,1)) -> RGB -> BGR
        out = (out.clamp(-1, 1) + 1) / 2
        out = out.permute(1, 2, 0).cpu().numpy()
        out = (out * 255).round().astype("uint8")[:, :, ::-1]
        helper.add_restored_face(out)
    helper.get_inverse_affine(None)
    import os as _os
    import shutil as _sh
    dst = path.rsplit(".", 1)[0] + "_cf%d.png" % int(W * 100)
    tmp = _os.path.join(_os.environ.get("TEMP", "."), "cf_out_%d.png" % int(W * 100))
    helper.paste_faces_to_input_image(save_path=tmp)
    _sh.move(tmp, dst)
    print("saved ->", dst, flush=True)
