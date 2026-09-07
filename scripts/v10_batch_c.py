# -*- coding: utf-8 -*-
"""V10 批次C: 全部5姿态用混合prompt补拍 (每姿态2 seeds = 10张, ~35分钟)"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v10_qwen2511 as v10

POSE_SEEDS = {
    "handonhip": (91715, 91716),
    "walking":   (91725, 91726),
    "side":      (91735, 91736),
    "back":      (91745, 91746),
    "stand34":   (91755, 91756),
}


def main():
    comfy_api.wait_server()
    c = v10.CASES["pose"]
    for pose_key, seeds in POSE_SEEDS.items():
        imgs = [v10.prep(v10.ANCHOR, "pose_anchor.png"),
                v10.prep(v10.POSE_REFS[pose_key], f"pose_ref_{pose_key}.jpg")]
        for seed in seeds:
            t0 = time.time()
            wf = v10.workflow(c["prompt"], v10.NEGATIVE, imgs, seed, steps=v10.STEPS)
            wf["12"]["inputs"]["filename_prefix"] = f"v10_pose_{pose_key}_{seed}"
            try:
                comfy_api.run(wf, v10.OUT, timeout=600)
                print("OK", pose_key, seed, round(time.time() - t0, 1), "s", flush=True)
            except Exception as e:
                print("FAIL", pose_key, seed, type(e).__name__, flush=True)
                comfy_api.wait_server()


if __name__ == "__main__":
    main()
