# -*- coding: utf-8 -*-
"""V10 批次D: handfix tryon选图 -> 场景x4 -> 正面/站立姿态x4 (串行, ~35min)"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v10_qwen2511 as v10

OUT = v10.OUT
TRYON_PICK = os.path.join(OUT, "v10_tryon_91704_00001_.png")
VERIFY = os.path.join(OUT, "_verify", "v10_tryon_91704_00001__report.json")


def main():
    comfy_api.wait_server()
    # 1. handfix 双手 (boxes 来自 verify report; 缺则全图跳过)
    rep = json.load(open(VERIFY, encoding="utf-8"))
    boxes = rep.get("_handboxes", {})
    seed = 91801
    for side in ("R", "L"):
        if side in boxes:
            v10.handfix(TRYON_PICK, boxes[side], seed=seed)
            seed += 1
    fixed = os.path.join(OUT, "handfix_final_%d.png" % (seed - 1))
    if os.path.exists(fixed):
        shutil.copy(fixed, os.path.join(OUT, "tryon_best.png"))
        print("tryon_best <- handfixed 91704", flush=True)
    else:
        shutil.copy(TRYON_PICK, os.path.join(OUT, "tryon_best.png"))
        print("tryon_best <- raw 91704 (handfix skipped)", flush=True)

    # 2. 场景 x4
    c_med = v10.CASES["scene_med"]
    c_st = v10.CASES["scene_street"]
    imgs_med = [v10.prep(os.path.join(OUT, "tryon_best.png"), "scene_med_in1.png")]
    imgs_st = [v10.prep(os.path.join(OUT, "tryon_best.png"), "scene_street_in1.png")]
    for seed in (91761, 91762):
        t0 = time.time()
        wf = v10.workflow(c_med["prompt"], v10.NEGATIVE, imgs_med, seed, steps=v10.STEPS)
        wf["12"]["inputs"]["filename_prefix"] = f"v10_scene_med_{seed}"
        comfy_api.run(wf, OUT, timeout=600)
        print("OK scene_med", seed, round(time.time() - t0, 1), flush=True)
    for seed in (91763, 91764):
        t0 = time.time()
        wf = v10.workflow(c_st["prompt"], v10.NEGATIVE, imgs_st, seed, steps=v10.STEPS)
        wf["12"]["inputs"]["filename_prefix"] = f"v10_scene_street_{seed}"
        comfy_api.run(wf, OUT, timeout=600)
        print("OK scene_street", seed, round(time.time() - t0, 1), flush=True)

    # 3. 正面/站立姿态 x4 (anchor 双输入, 波点裙正面自然垂手站姿)
    c_pose = v10.CASES["pose"]
    front_prompt = (
        "Image 2 shows the target standing pose: standing upright facing the camera, arms relaxed "
        "at the sides, feet slightly apart. Put the woman from image 1 into this pose. She wears "
        "the same coffee brown polka dot slip midi dress as in image 1 - no added ribbons or bows. "
        "Keep her exact same face, rimless glasses, makeup and long dark brown hair with bangs. "
        "Same plain grey studio backdrop as image 1. Full body framing, head to feet visible. "
        "双手各五根手指自然垂放、指节清晰；双脚自然成对凉鞋；膝盖脚踝骨点清晰。"
        "皮肤真实质感，波点随褶皱形变，影棚背景纯净。")
    imgs = [v10.prep(v10.ANCHOR, "pose_anchor.png"), v10.prep(v10.ANCHOR, "pose_ref_front.jpg")]
    for seed in (91765, 91766, 91767, 91768):
        t0 = time.time()
        wf = v10.workflow(front_prompt, v10.NEGATIVE, imgs, seed, steps=v10.STEPS)
        wf["12"]["inputs"]["filename_prefix"] = f"v10_pose_front_{seed}"
        comfy_api.run(wf, OUT, timeout=600)
        print("OK pose_front", seed, round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    main()
