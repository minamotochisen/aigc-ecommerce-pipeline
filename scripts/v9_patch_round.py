# -*- coding: utf-8 -*-
"""V9 补丁轮: 擦除式光板重试 + 戴眼镜姿态测试"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from v9_qwen2511 import ANCHOR, OUT, POSE_REFS, prep, workflow

comfy_api.wait_server()

RED_P = ("Erase the floral print from the t-shirt. Keep the photo exactly identical: same red "
         "heather fabric texture, same wrinkles and folds, same shadows, same background, same "
         "framing. Only the printed pattern disappears, replaced by the same plain red fabric "
         "that surrounds it. Do not repaint or smooth the fabric.")
TEE_P = ("Erase the black text on the chest and the neck label. Keep the photo exactly "
         "identical: same white cotton fabric texture, same wrinkles, same shadows, same "
         "background, same framing. Only the text and the label disappear. Do not repaint or "
         "smooth the fabric.")

POSE_P = ('Put the same woman from image 1 into the body pose, camera angle and background of '
          'image 2. She wears the same coffee brown polka dot slip midi dress as in image 1 and '
          'her thin rimless glasses. Keep her exact same face, makeup and long dark brown hair '
          'with bangs - do not change her identity, she must look like the same woman as image 1. '
          'Ignore the person and outfit in image 2, take only the pose, framing and background. '
          'Realistic skin texture, photorealistic e-commerce fashion photography.')


def prep_white(path, name):
    """RGBA 先合成白底再转 RGB, 避免 PIL 黑底合成导致模型崩坏"""
    from PIL import Image
    im = Image.open(path)
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        im = bg
    im = im.convert("RGB")
    p = os.path.join(OUT, name)
    im.save(p)
    return comfy_api.upload_image(p)


def gen(prompt, imgs, prefix, seeds, white=False):
    ups = [prep_white(p, f"{prefix}_in{i}.png") if white else prep(p, f"{prefix}_in{i}.png")
           for i, p in enumerate(imgs, 1)]
    for s in seeds:
        wf = workflow(prompt, ups, s)
        wf["12"]["inputs"]["filename_prefix"] = f"{prefix}"
        print(prefix, s, comfy_api.run_watchdog(wf, OUT), flush=True)


which = sys.argv[1] if len(sys.argv) > 1 else "all"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if which in ("all", "tee"):
    gen(RED_P, [os.path.join(ROOT, "assets", "garments", "cand_redtee_floral.png")], "v9_red3", [91521], white=True)
    gen(TEE_P, [os.path.join(ROOT, "assets_v2", "garments", "g_tee_awet.jpg")], "v9_tee2", [91611, 91612])
if which in ("all", "pose"):
    gen(POSE_P, [ANCHOR, POSE_REFS["handonhip"]], "v9_pose_glasses_hip", [91411])
    gen(POSE_P, [ANCHOR, POSE_REFS["walking"]], "v9_pose_glasses_walk", [91411])
print("PATCH DONE")
