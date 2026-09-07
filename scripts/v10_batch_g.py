# -*- coding: utf-8 -*-
"""V10 批次G: 普通模式重出 lowvram 受损图 (场景x4 + 光板x4 + 行走x2 + 回眸x2)"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v10_qwen2511 as v10

OUT = v10.OUT


def run(case, pose_key, seed, prefix, denoise=None):
    c = v10.CASES[case]
    if case == "pose":
        imgs = [v10.prep(v10.ANCHOR, "pose_anchor.png"),
                v10.prep(v10.POSE_REFS[pose_key], f"pose_ref_{pose_key}.jpg")]
    else:
        imgs = [v10.prep(p, f"{case}_in{i}.png") for i, p in enumerate(c["images"], 1)]
    t0 = time.time()
    wf = v10.workflow(c["prompt"], v10.NEGATIVE, imgs, seed, steps=v10.STEPS)
    if denoise:
        wf["9"]["inputs"]["denoise"] = denoise
    wf["12"]["inputs"]["filename_prefix"] = prefix
    comfy_api.run(wf, OUT, timeout=600)
    print("OK", prefix, round(time.time() - t0, 1), "s", flush=True)


def main():
    comfy_api.wait_server()
    run("scene_med", None, 91790, "v10_scene_med_91790")
    run("scene_med", None, 91791, "v10_scene_med_91791")
    run("scene_street", None, 91793, "v10_scene_street_91793")
    run("scene_street", None, 91794, "v10_scene_street_91794")
    run("blank_tee", None, 91795, "v10_blank_tee_91795")
    run("blank_tee", None, 91796, "v10_blank_tee_91796")
    run("blank", None, 91797, "v10_blank_91797")
    run("blank", None, 91798, "v10_blank_91798")
    run("pose", "walking", 91799, "v10_pose_walking_91799")
    run("pose", "walking", 91800, "v10_pose_walking_91800")
    run("pose", "side", 91805, "v10_pose_side_91805")
    run("pose", "side", 91806, "v10_pose_side_91806")


if __name__ == "__main__":
    main()
