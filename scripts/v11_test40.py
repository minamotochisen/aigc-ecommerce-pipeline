# -*- coding: utf-8 -*-
"""V11 前置验证: 当前驱动下 40 步采样是否稳定 (V10 时 >20 步卡死被归因于 nvlddmkm 驱动故障, 后经重启机器根治)
跑 1 张 tryon 40 步, 成功则 STEPS 升 40, 卡死(watchdog 900s 超时)则维持 20 步方案。"""
import sys
import time

sys.path.insert(0, r".\scripts")
import comfy_api
from v10_qwen2511 import CASES, NEGATIVE, OUT, prep, workflow

c = CASES["tryon"]
imgs = [prep(p, "v11t40_in%d.png" % i) for i, p in enumerate(c["images"], 1)]
wf = workflow(c["prompt"], NEGATIVE, imgs, 92001, steps=40)
wf["12"]["inputs"]["filename_prefix"] = "v11_test40_92001"

t0 = time.time()
paths = comfy_api.run_watchdog(wf, OUT, per_run=900)
dt = time.time() - t0
print("40STEP_OK %.0fs -> %s" % (dt, paths), flush=True)
