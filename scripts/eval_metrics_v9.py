# -*- coding: utf-8 -*-
"""V9 量化评估: CLIP-T(文本-姿态一致性) + CLIP-I(身份/编辑一致性)
用法: HF_ENDPOINT=https://hf-mirror.com python eval_metrics_v9.py
输出: outputs_v2/eval_report_v9.json
"""
import json
import os

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

ROOT = r"."
HD = os.path.join(ROOT, "outputs_v2", "upscaled_v9")
RAW = os.path.join(ROOT, "outputs_v2", "v9")
OUT = os.path.join(ROOT, "outputs_v2", "eval_report_v9.json")

MODEL = "openai/clip-vit-large-patch14"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 姿态 stem(优先取超分 _hd)
POSE_PROMPTS = {
    "v9_tryon_full_91121": "a woman standing facing the camera in a coffee brown polka dot slip midi dress",
    "v9_pose_glasses_hip": "a woman standing with one hand on her hip wearing a coffee brown polka dot slip dress",
    "v9_pose_glasses_walk2": "a woman walking on a lawn wearing a coffee brown polka dot slip midi dress",
    "v9_pose_glasses_side": "a woman looking back over her shoulder wearing a coffee brown polka dot slip dress",
    "v9_pose_back_91402": "a woman standing in full length wearing a coffee brown polka dot slip midi dress",
    "v9_pose_glasses_stand": "a woman standing in three-quarter view wearing a coffee brown polka dot slip midi dress",
}


def path_of(stem):
    p = os.path.join(HD, stem + "_hd.png")
    if os.path.exists(p):
        return p
    return os.path.join(RAW, stem + "_00001_.png")


@torch.no_grad()
def main():
    model = CLIPModel.from_pretrained(MODEL).to(DEVICE).eval()
    proc = CLIPProcessor.from_pretrained(MODEL)

    def _tensor(x):
        for attr in ("pooler_output", "image_embeds", "text_embeds"):
            v = getattr(x, attr, None)
            if v is not None:
                return v
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

    names = list(POSE_PROMPTS)
    feats = encode_images([path_of(n) for n in names])
    tfeat = encode_texts([POSE_PROMPTS[n] for n in names])
    sims = (feats * tfeat).sum(-1).tolist()
    for n, s in zip(names, sims):
        report["clip_t"][n] = round(s, 4)
    report["clip_t_avg"] = round(sum(sims) / len(sims), 4)

    anchor = encode_images([os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")])
    for n in names:
        f2 = encode_images([path_of(n)])
        report["clip_i_identity"][n] = round((f2 * anchor).sum(-1).item(), 4)
    vals = list(report["clip_i_identity"].values())
    report["clip_i_avg"] = round(sum(vals) / len(vals), 4)

    # 场景/换装编辑一致性: before vs after (越高 = 人物/服装保持越好)
    pairs = {
        "tryon": ("v9_tryon_full_91121", "v9_tryon_full_91121"),  # 占位, 下面单独算
        "scene_med": ("v9_tryon_full_91121", "v9_scene_med_91252"),
        "scene_street": ("v9_tryon_full_91121", "v9_street3"),
    }
    anchor_full = os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")
    for case, (b, a) in pairs.items():
        bp = anchor_full if case == "tryon" else path_of(b)
        fb = encode_images([bp])
        fa = encode_images([path_of(a)])
        report.setdefault("clip_i_edit", {})[case] = round((fb * fa).sum(-1).item(), 4)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
