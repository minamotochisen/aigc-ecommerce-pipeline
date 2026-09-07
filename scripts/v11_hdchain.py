# -*- coding: utf-8 -*-
"""V11 HD 链: 选中图 -> 4x超分(限宽2600) -> DWPose验收 -> HD上 facefix/handfix/footfix
用法:
  python v11_hdchain.py <img...>          # 依次超分+验收, 打印报告
  python v11_hdchain.py --fix <hd_img>    # 按 HD report 修脸/手/脚(各一次)
产物: outputs_v2/upscaled_v10/<stem>_hd.png + _verify 报告 + fixchain 输出
"""
import json
import os
import subprocess
import sys

ROOT = r"."
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import comfy_api

COMFY_DIR = comfy_api.COMFY_DIR
COMFY_PY = os.path.join(COMFY_DIR, "python_embeded", "python.exe")
VERIFY = os.path.join(ROOT, "scripts", "v10_verify.py")
HD = os.path.join(ROOT, "outputs_v2", "upscaled_v10")
MAXW = 2600


def upscale(src, dst):
    import time as _t
    import urllib.parse
    from PIL import Image
    marker = _t.time() - 5
    up = comfy_api.upload_image(src)
    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": up["name"]}},
        "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x-UltraSharp.pth"}},
        "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "SaveImage", "inputs": {"filename_prefix": "hd", "images": ["3", 0]}},
    }
    comfy_api._req(comfy_api.COMFY + "/prompt", json.dumps({"prompt": wf}).encode())
    # SaveImage 落在 ComfyUI 自己的 output 目录, 直接扫盘取最新; 服务器假死则重启重投
    out_root = os.path.join(COMFY_DIR, "ComfyUI", "output")
    newest = None
    for attempt in range(3):
        deadline = _t.time() + (600 if attempt == 0 else 120)
        while _t.time() < deadline:
            cands = [os.path.join(out_root, f) for f in os.listdir(out_root)
                     if f.startswith("hd_") and f.endswith(".png")
                     and os.path.getmtime(os.path.join(out_root, f)) > marker]
            if cands:
                newest = max(cands, key=os.path.getmtime)
                break
            _t.sleep(3)
        if newest:
            break
        print("upscale stalled, restart server, attempt", attempt + 1, flush=True)
        comfy_api.restart_server()
        comfy_api._req(comfy_api.COMFY + "/prompt", json.dumps({"prompt": wf}).encode())
    if not newest:
        raise RuntimeError("upscale output not found for " + src)
    _t.sleep(1)
    im = Image.open(newest).convert("RGB")
    if im.width > MAXW:
        im = im.resize((MAXW, int(im.height * MAXW / im.width)), Image.LANCZOS)
    im.save(dst)
    os.remove(newest)
    print("upscale ->", dst, im.size, flush=True)


def verify(png):
    name = os.path.splitext(os.path.basename(png))[0]
    subprocess.run([COMFY_PY, VERIFY, png], check=True, capture_output=True, text=True, cwd=COMFY_DIR)
    rep = json.load(open(os.path.join(ROOT, "outputs_v2", "v10", "_verify", name + "_report.json"),
                         encoding="utf-8"))
    print(name, {k: rep.get(k) for k in ("verdict", "torso_leg_ratio", "handR_visible",
                                         "handL_visible", "handR_spread", "handL_spread")})
    return rep


def fix_all(png, seed):
    """按 report 依次 facefix -> 复验 -> handfix -> footfix (每个修复后更新当前图)"""
    import v11_fixchain as fc
    import v10_qwen2511 as q
    cur = png
    seed = seed
    rep = verify(cur)
    fb = rep.get("_facebox")
    if fb:
        seed += 1
        q.facefix(cur, fb, seed, context=0.45)
        cur = os.path.join(q.OUT, "facefix_final_%d.png" % seed)
        rep = verify(cur)
    for mode, key in (("handfix", "_handboxes"), ("footfix", "_footboxes")):
        boxes = rep.get(key) or {}
        for side, box in sorted(boxes.items()):
            seed += 1
            print("HD", mode, side, flush=True)
            if mode == "handfix":
                q.handfix(cur, box, seed)
            else:
                fc_foot(cur, box, seed)
            cur = os.path.join(q.OUT, ("handfix_final_%d.png" % seed) if mode == "handfix"
                               else ("footfix_final_%d.png" % seed))
            rep = verify(cur)
    print("FINAL:", cur)
    return cur


def fc_foot(cur, box, seed):
    import comfy_api
    import v10_qwen2511 as q
    from PIL import Image, ImageFilter
    im = Image.open(cur).convert("RGB")
    W, H = im.size
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * 0.35), int(bh * 0.35)
    cx1, cy1 = max(0, x1 - mx), max(0, y1 - my)
    cx2, cy2 = min(W, x2 + mx), min(H, y2 + my)
    crop = im.crop((cx1, cy1, cx2, cy2))
    scale = 768 / max(crop.size)
    big = crop.resize((int(crop.size[0] * scale) // 16 * 16,
                       int(crop.size[1] * scale) // 16 * 16), Image.LANCZOS)
    src = os.path.join(q.OUT, "_footfix_in.png")
    big.save(src)
    prompt = ("修复这张照片中人物的脚部：双脚结构完全正确，脚趾五根、形态自然不粘连，"
              "左右鞋同款成对，脚与鞋遮挡关系正确，承重自然。保持画面中其他所有内容与构图完全不变，"
              "保持光线与地面关系不变。真实人像摄影质感。")
    wf = q.workflow(prompt, q.NEGATIVE, [comfy_api.upload_image(src)], seed)
    wf["12"]["inputs"]["filename_prefix"] = "v11_footfix"
    comfy_api.run_watchdog(wf, q.OUT, per_run=q.PER_RUN)
    outs = sorted([f for f in os.listdir(q.OUT) if f.startswith("v11_footfix") and f.endswith(".png")],
                  key=lambda f: os.path.getmtime(os.path.join(q.OUT, f)))
    fixed = Image.open(os.path.join(q.OUT, outs[-1])).convert("RGB").resize(crop.size, Image.LANCZOS)
    mask = Image.new("L", crop.size, 0)
    mask.paste(Image.new("L", (bw, bh), 255), (x1 - cx1, y1 - cy1))
    mask = mask.filter(ImageFilter.GaussianBlur(10))
    im.paste(fixed, (cx1, cy1), mask)
    dst = os.path.join(q.OUT, "footfix_final_%d.png" % seed)
    im.save(dst)
    print("footfix saved:", dst, flush=True)


if __name__ == "__main__":
    comfy_api.wait_server()
    args = sys.argv[1:]
    if args and args[0] == "--fix":
        fix_all(args[1], 92500)
    else:
        for a in args:
            stem = os.path.splitext(os.path.basename(a))[0]
            upscale(a, os.path.join(HD, stem + "_hd.png"))
            verify(os.path.join(HD, stem + "_hd.png"))
