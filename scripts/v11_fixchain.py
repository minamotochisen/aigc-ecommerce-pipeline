# -*- coding: utf-8 -*-
"""V11 修复链驱动:
  adopt  <png>            : 选定换装主图 -> 备份V10 -> 复制为 tryon_best.png -> verify
  verify <png>            : 跑 DWPose 验收, 打印 report 关键字段
  facefix <png> <seed>    : 按 report._facebox 做人脸身份修复回贴
  handfix <png> <seed>    : 按 report._handboxes 逐手修复
  footfix <png> <seed>    : 按 report._footboxes 逐脚修复
用法示例:
  python v11_fixchain.py adopt outputs_v2/v10/v10_tryon_92011_00001_.png
  python v11_fixchain.py facefix outputs_v2/v10/tryon_best.png 92101
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = r"."
V10 = os.path.join(ROOT, "outputs_v2", "v10")
VERIFY_DIR = os.path.join(V10, "_verify")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

COMFY_PY = (r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia"
            r"\ComfyUI_windows_portable\python_embeded\python.exe")
VERIFY = os.path.join(ROOT, "scripts", "v10_verify.py")


def run_verify(png):
    name = os.path.splitext(os.path.basename(png))[0]
    # v10_verify.py 内部用相对路径导入 custom_nodes, 必须 cwd=ComfyUI 目录
    subprocess.run([COMFY_PY, VERIFY, png], check=True, capture_output=True, text=True,
                   cwd=comfy_api.COMFY_DIR)
    rp = os.path.join(VERIFY_DIR, name + "_report.json")
    rep = json.load(open(rp, encoding="utf-8"))
    keys = ["verdict", "torso_leg_ratio", "kp_visible", "handL_visible", "handR_visible",
            "handL_spread", "handR_spread"]
    print(name, {k: rep.get(k) for k in keys if k in rep})
    print("facebox:", rep.get("_facebox"))
    print("handboxes:", rep.get("_handboxes"))
    print("footboxes:", rep.get("_footboxes"))
    return rp, rep


def fix(mode, png, seed):
    """facefix/handfix/footfix: 用最新 verify report 的框逐个修复, 输出 <mode>_final_<seed>.png"""
    name = os.path.splitext(os.path.basename(png))[0]
    rp = os.path.join(VERIFY_DIR, name + "_report.json")
    rep = json.load(open(rp, encoding="utf-8"))
    import v10_qwen2511 as q
    if mode == "facefix":
        box = rep.get("_facebox")
        if not box:
            print("no facebox; skip")
            return
        q.facefix(png, box, seed)
        return
    boxes = rep.get("_handboxes" if mode == "handfix" else "_footboxes") or {}
    cur = png
    for side, box in sorted(boxes.items()):
        seed += 1
        print(mode, side, box, "seed", seed, flush=True)
        if mode == "handfix":
            q.handfix(cur, box, seed)
        else:
            # footfix: 与 handfix 同框架, prompt 换脚部
            import comfy_api
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
            src = os.path.join(V10, "_footfix_in.png")
            big.save(src)
            prompt = ("修复这张照片中人物的脚部：双脚结构完全正确，脚趾五根、形态自然不粘连，"
                      "左右鞋同款成对，脚与鞋遮挡关系正确，承重自然。保持画面中其他所有内容与构图完全不变，"
                      "保持光线与地面关系不变。真实人像摄影质感。")
            wf = q.workflow(prompt, q.NEGATIVE, [comfy_api.upload_image(src)], seed)
            wf["12"]["inputs"]["filename_prefix"] = "v11_footfix"
            comfy_api.run_watchdog(wf, V10, per_run=q.PER_RUN)
            outs = sorted([f for f in os.listdir(V10) if f.startswith("v11_footfix") and f.endswith(".png")],
                          key=lambda f: os.path.getmtime(os.path.join(V10, f)))
            fixed = Image.open(os.path.join(V10, outs[-1])).convert("RGB").resize(crop.size, Image.LANCZOS)
            mask = Image.new("L", crop.size, 0)
            mask.paste(Image.new("L", (bw, bh), 255), (x1 - cx1, y1 - cy1))
            mask = mask.filter(ImageFilter.GaussianBlur(10))
            im.paste(fixed, (cx1, cy1), mask)
            dst = os.path.join(V10, "footfix_final_%d.png" % seed)
            im.save(dst)
            print("footfix saved:", dst, flush=True)
            cur = dst


def adopt(png):
    bak = os.path.join(V10, "tryon_best_v10backup.png")
    dst = os.path.join(V10, "tryon_best.png")
    if os.path.exists(dst) and not os.path.exists(bak):
        shutil.copy2(dst, bak)
        print("backed up ->", bak)
    shutil.copy2(png, dst)
    print("adopted ->", dst)
    run_verify(dst)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "adopt":
        adopt(sys.argv[2])
    elif mode == "verify":
        run_verify(sys.argv[2])
    elif mode in ("facefix", "handfix", "footfix"):
        seed = int(sys.argv[3]) if len(sys.argv) > 3 else 92101
        import comfy_api
        comfy_api.wait_server()
        fix(mode, sys.argv[2], seed)
    else:
        print("unknown mode", mode)
