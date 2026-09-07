# -*- coding: utf-8 -*-
"""V10 批次A: lowvram服务器专用(无看门狗, 串行单进程, 禁止并发触碰ComfyUI)
python v10_batch_a.py   # tryon x2 + pose 5x2 + blank x2 + blank_tee x2 = 16张
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v10_qwen2511 as v10

JOBS = [
    ("tryon", None, 91702), ("tryon", None, 91703),
    ("pose", "handonhip", 91711), ("pose", "handonhip", 91712),
    ("pose", "walking", 91721), ("pose", "walking", 91722),
    ("pose", "side", 91731), ("pose", "side", 91732),
    ("pose", "back", 91741), ("pose", "back", 91742),
    ("pose", "stand34", 91751), ("pose", "stand34", 91752),
    ("blank", None, 91771), ("blank", None, 91772),
    ("blank_tee", None, 91781), ("blank_tee", None, 91782),
]


def main():
    comfy_api.wait_server()
    cache = {}
    for case, pose_key, seed in JOBS:
        c = v10.CASES[case]
        t0 = time.time()
        try:
            if case == "pose":
                if pose_key not in cache:
                    cache[pose_key] = [v10.prep(v10.ANCHOR, "pose_anchor.png"),
                                       v10.prep(v10.POSE_REFS[pose_key], f"pose_ref_{pose_key}.jpg")]
                imgs = cache[pose_key]
                prefix = f"v10_pose_{pose_key}_{seed}"
            else:
                key = case
                if key not in cache:
                    cache[key] = [v10.prep(p, f"{case}_in{i}.png") for i, p in enumerate(c["images"], 1)]
                imgs = cache[key]
                prefix = f"v10_{case}_{seed}"
            wf = v10.workflow(c["prompt"], v10.NEGATIVE, imgs, seed, steps=v10.STEPS)
            wf["12"]["inputs"]["filename_prefix"] = prefix
            paths = comfy_api.run(wf, v10.OUT, timeout=600)
            print("OK", prefix, round(time.time() - t0, 1), "s", flush=True)
        except Exception as e:
            print("FAIL", case, pose_key, seed, type(e).__name__, str(e)[:80], flush=True)
            comfy_api.wait_server()


if __name__ == "__main__":
    main()
