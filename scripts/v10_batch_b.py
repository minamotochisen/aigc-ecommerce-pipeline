# -*- coding: utf-8 -*-
"""V10 批次B: tryon全身取景版x3 + 场景x4 (场景依赖 tryon_best.png 先就位)
用法:
  python v10_batch_b.py tryon   # 3张全身换装
  python v10_batch_b.py scene   # 复制选定tryon为tryon_best后跑4张场景
  python v10_batch_b.py pose2   # 修正姿态prompt的叉腰/回眸补拍
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v10_qwen2511 as v10


def run(case, pose_key, seed, n):
    c = v10.CASES[case]
    if case == "pose":
        imgs = [v10.prep(v10.ANCHOR, "pose_anchor.png"),
                v10.prep(v10.POSE_REFS[pose_key], f"pose_ref_{pose_key}.jpg")]
        prefix = f"v10_pose_{pose_key}_{seed}"
    else:
        imgs = [v10.prep(p, f"{case}_in{i}.png") for i, p in enumerate(c["images"], 1)]
        prefix = f"v10_{case}_{seed}"
    t0 = time.time()
    wf = v10.workflow(c["prompt"], v10.NEGATIVE, imgs, seed, steps=v10.STEPS)
    wf["12"]["inputs"]["filename_prefix"] = prefix
    paths = comfy_api.run(wf, v10.OUT, timeout=600)
    print("OK", prefix, round(time.time() - t0, 1), "s", flush=True)


def main():
    mode = sys.argv[1]
    comfy_api.wait_server()
    if mode == "tryon":
        for seed in (91704, 91705, 91706):
            run("tryon", None, seed, 3)
    elif mode == "scene":
        for seed in (91761, 91762):
            run("scene_med", None, seed, 2)
        for seed in (91763, 91764):
            run("scene_street", None, seed, 2)
    elif mode == "pose2":
        for seed in (91713, 91714):
            run("pose", "handonhip", seed, 2)
        for seed in (91733, 91734):
            run("pose", "side", seed, 2)


if __name__ == "__main__":
    main()
