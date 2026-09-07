# -*- coding: utf-8 -*-
"""V4 量化评估: CLIP-T(文本-图像一致性) + CLIP-I(身份/图像一致性)

用法:
  HF_ENDPOINT=https://hf-mirror.com python eval_metrics.py
输出: outputs_v2/eval_report.json + 控制台表格
"""
import json
import os

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

ROOT = r"."
HD = os.path.join(ROOT, "outputs_v2", "upscaled")
OUT = os.path.join(ROOT, "outputs_v2", "eval_report.json")

MODEL = "openai/clip-vit-large-patch14"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 姿态描述(与生成提示词的服装/姿态要点对齐)
POSE_PROMPTS = {
    "v6_final_anchor.png": "a woman standing facing the camera in a coffee brown polka dot slip midi dress",
    "v6_final_plainbg.png": "a woman standing with hands on hips wearing a coffee brown polka dot slip dress",
    "v6_final_lawn.png": "a woman walking on a lawn wearing a coffee brown polka dot slip dress with boots",
    "v6_final_jump.png": "a woman standing with legs apart wearing a coffee brown polka dot slip midi dress",
    "v6_final_palm.png": "back view of a woman in a coffee brown polka dot slip midi dress among palm trees",
    "v6_final_tank.png": "a woman standing in three-quarter view wearing a coffee brown polka dot slip midi dress",
}


@torch.no_grad()
def main():
    model = CLIPModel.from_pretrained(MODEL).to(DEVICE).eval()
    proc = CLIPProcessor.from_pretrained(MODEL)

    def _tensor(x):
        if hasattr(x, "pooler_output") and x.pooler_output is not None:
            return x.pooler_output
        if hasattr(x, "image_embeds") and x.image_embeds is not None:
            return x.image_embeds
        if hasattr(x, "text_embeds") and x.text_embeds is not None:
            return x.text_embeds
        return x

    def encode_images(paths):
        ims = [Image.open(p).convert("RGB") for p in paths]
        inp = proc(images=ims, return_tensors="pt").to(DEVICE)
        f = _tensor(model.get_image_features(**inp))
        return f / f.norm(dim=-1, keepdim=True)

    def encode_texts(texts):
        inp = proc(text=texts, return_tensors="pt", padding=True, truncation=True).to(DEVICE)
        f = _tensor(model.get_text_features(**inp))
        return f / f.norm(dim=-1, keepdim=True)

    report = {"clip_t": {}, "clip_i_identity": {}}

    # ---- CLIP-T: 六宫格姿态一致性 ----
    names = list(POSE_PROMPTS)
    feats = encode_images([os.path.join(HD, n) for n in names])
    tfeat = encode_texts([POSE_PROMPTS[n] for n in names])
    sims = (feats * tfeat).sum(-1).tolist()
    for n, s in zip(names, sims):
        report["clip_t"][n] = round(s, 4)
    report["clip_t_avg"] = round(sum(sims) / len(sims), 4)

    # ---- CLIP-I: 身份一致性(姿态图 vs 身份锚参考照 两两均值) ----
    anchor = encode_images([os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")])
    for n in names:
        f2 = encode_images([os.path.join(HD, n)])
        report["clip_i_identity"][n] = round((f2 * anchor).sum(-1).item(), 4)
    vals = list(report["clip_i_identity"].values())
    report["clip_i_avg"] = round(sum(vals) / len(vals), 4)

    # ---- 场景重绘: 图像一致性(before vs after, 越高=服装/人物保持越好) ----
    for case, (b, a) in {
        "scene_B": ("c2_before_hd.png", "c2_after_hd.png"),
        "scene_C": ("c3_before_hd.png", "c3_after_hd.png"),
    }.items():
        fb = encode_images([os.path.join(HD, b)])
        fa = encode_images([os.path.join(HD, a)])
        report.setdefault("clip_i_edit", {})[case] = round((fb * fa).sum(-1).item(), 4)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
