# -*- coding: utf-8 -*-
"""V13 14B 慢跑: l14b(4步) + FLF(20步) — 静态显存模式, 长轮询防加载期误判"""
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v13_video as v

# 权重加载期 HTTP 线程可能长时间无响应: 放宽每次请求超时
_orig = comfy_api._req
def patient(url, data=None, timeout=180):
    return _orig(url, data=data, timeout=timeout)
comfy_api._req = patient


def run_one(shot_name, prefix, seed):
    s = v.SHOTS[shot_name]
    if s["mode"] == "flf":
        W, H, length = 1280, 720, 73
        start = v.crop_start(s["start"], W, H, tag="A", bias=s.get("start_bias"))
        end = v.crop_start(s["end"], W, H, tag="B", bias=s.get("end_bias"))
        comfy_api.upload_image(start)
        comfy_api.upload_image(end)
        wf = v.wf_flf(seed, s["pos"], start, end, W, H, length, 20, prefix=prefix)
        meta = {"mode": "flf", "length": length, "steps": 20}
    else:
        W, H, length = 1280, 720, 81
        start = v.crop_start(s["start"], W, H, bias=0.0)
        comfy_api.upload_image(start)
        wf = v.wf_l14b(seed, s["pos"], start, W, H, length, prefix=prefix)
        meta = {"mode": "l14b", "length": length, "steps": "4(2+2)"}
    t0 = time.time()
    print(f"[{shot_name}] {meta} seed={seed} submit...", flush=True)
    paths = comfy_api.run(wf, v.OUT, timeout=9000)
    dt = time.time() - t0
    rec = {"shot": shot_name, "seed": seed, "seconds": round(dt, 1),
           "files": [os.path.basename(p) for p in paths], "vram_mode": "static", **meta}
    with open(os.path.join(v.OUT, "_runs.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{shot_name}] done {dt:.0f}s ->", [os.path.basename(p) for p in paths], flush=True)


if __name__ == "__main__":
    order = sys.argv[1:] or ["l14b_compare", "flf_changeout"]
    for shot in order:
        prefix = "v13l14b" if shot == "l14b_compare" else "v13flf"
        seed = 63110 if shot == "l14b_compare" else 63101
        try:
            run_one(shot, prefix, seed)
        except Exception as ex:
            print(f"[{shot}] FAILED: {type(ex).__name__} {str(ex)[:400]}", flush=True)
    print("SLOWRUN_DONE", flush=True)
