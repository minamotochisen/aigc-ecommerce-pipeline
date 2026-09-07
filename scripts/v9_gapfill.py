# -*- coding: utf-8 -*-
"""V9 缺口补齐: 背面/站姿姿态 + 白T光板 + 街拍重掷 (补丁版看门狗)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from v9_qwen2511 import ANCHOR, OUT, POSE_REFS, prep, workflow

comfy_api.wait_server()

POSE_P = ('Put the same woman from image 1 into the body pose, camera angle and background of '
          'image 2. She wears the same coffee brown polka dot slip midi dress as in image 1. '
          'Keep her exact same face, rimless glasses, makeup and long dark brown hair with '
          'bangs - do not change her identity. Ignore the person and outfit in image 2, take '
          'only the pose, framing and background. Realistic skin texture, photorealistic '
          'e-commerce fashion photography.')

STREET_P = ('Background replacement edit. Keep the woman in image 1 pixel-identical: same face, '
            'same rimless glasses, same long dark brown hair (keep her natural dark hair color, '
            'no green or olive tint), same floral dress, same pose, same camera framing, and keep '
            'her exact skin tone and clothing colors - do not color grade or re-tint the subject. '
            'Replace only the grey studio backdrop with a European old-town cobblestone street: '
            'cream plaster buildings, wooden shutters, shallow depth of field, soft overcast '
            'daylight. Composite her into the new scene naturally. Photorealistic street-style '
            'fashion photography.')

TEE_P = ('Garment cleaning edit. Remove the black text print on the chest and the neck label '
         'from this white t-shirt, turning it into a plain blank white cotton t-shirt. Keep '
         'the fabric texture, folds, shadows and the ghost mannequin shape exactly the same. '
         'No smearing, keep edges crisp.')


def gen(prompt, imgs, prefix, seeds):
    ups = [prep(p, f"{prefix}_in{i}.png") for i, p in enumerate(imgs, 1)]
    for s in seeds:
        wf = workflow(prompt, ups, s)
        wf["12"]["inputs"]["filename_prefix"] = f"{prefix}"
        print(prefix, s, comfy_api.run_watchdog(wf, OUT), flush=True)


which = sys.argv[1] if len(sys.argv) > 1 else "all"
if which in ("all", "pose"):
    gen(POSE_P, [ANCHOR, POSE_REFS["back"]], "v9_pose_back", [91401])
    gen(POSE_P, [ANCHOR, POSE_REFS["stand34"]], "v9_pose_stand34", [91401])
if which in ("all", "tee"):
    gen(TEE_P, [os.path.join(os.path.dirname(OUT), "..", "assets_v2", "garments", "g_tee_awet.jpg")],
        "v9_blank_tee", [91601, 91602])
if which in ("all", "street"):
    gen(STREET_P, [os.path.join(OUT, "tryon_best.png")], "v9_scene_street2", [91331, 91332])
print("GAP DONE")
