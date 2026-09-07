# -*- coding: utf-8 -*-
"""V12 量化评估: CLIP-T(文本-姿态一致性) + CLIP-I(身份/编辑一致性)
用法: python eval_metrics_v12.py  (需 CLIP 缓存, 首次下载走 HF_ENDPOINT=https://hf-mirror.com)
输出: outputs_v2/eval_report_v12.json
"""
import json
import os

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

ROOT = r"."
V12 = os.path.join(ROOT, "outputs_v2", "v12")
TRIAL = os.path.join(ROOT, "outputs_v2", "v12_trial")
OUT = os.path.join(ROOT, "outputs_v2", "eval_report_v12.json")

MODEL = "openai/clip-vit-large-patch14"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 姿态六格: 正面两张 + 修正prompt三姿态 + 净化正面
POSE_PROMPTS = {
    "b_94102": "a woman standing facing the camera wearing a navy blue puff sleeve blouse and cream white midi skirt",
    "b_94103": "a woman standing facing the camera wearing a navy blue puff sleeve blouse and cream white midi skirt",
    "pose_back_94222": "a woman seen from behind looking back over her shoulder wearing a navy blue blouse and cream skirt",
    "pose_walking": "a woman walking mid-stride wearing a navy blue puff sleeve blouse and cream white midi skirt",
    "pose_handonhip": "a woman standing with one hand on her hip wearing a navy blue blouse and cream white skirt",
    "clean_bkg": "a woman standing facing the camera in front of a plain clean wall wearing navy blouse and cream skirt",
}


def path_of(stem):
    # 优先 CodeFormer 修复版
    for p in (os.path.join(V12, "v12_%s_cf70.png" % stem),
              os.path.join(TRIAL, "v12_tryon_%s_hd_cf70.png" % stem),
              os.path.join(TRIAL, "v12_tryon_%s_00001_.png" % stem),
              os.path.join(V12, "v12_%s_00001_.png" % stem)):
        if os.path.exists(p):
            return p
    raise FileNotFoundError(stem)


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

    anchor = encode_images([os.path.join(ROOT, "assets_v2", "v12", "mdl_f1.jpg")])
    for n in names:
        f2 = encode_images([path_of(n)])
        report["clip_i_identity"][n] = round((f2 * anchor).sum(-1).item(), 4)
    vals = list(report["clip_i_identity"].values())
    report["clip_i_avg"] = round(sum(vals) / len(vals), 4)

    # 编辑一致性: 换景/净化 before vs after
    pairs = {
        "scene_cream": (os.path.join(TRIAL, "v12_tryon_b_94102_00001_.png"),
                        os.path.join(V12, "v12_scene_cream_b_94201_00001_.png")),
        "scene_street": (os.path.join(TRIAL, "v12_tryon_b_94102_00001_.png"),
                         os.path.join(V12, "v12_scene_street_b_94213_00001_.png")),
        "clean_bkg": (os.path.join(TRIAL, "v12_tryon_b_94101_00001_.png"),
                      os.path.join(V12, "v12_clean_bkg_94252_00001_.png")),
    }
    for case, (b, a) in pairs.items():
        if not os.path.exists(a):
            continue
        fb = encode_images([b])
        fa = encode_images([a])
        report.setdefault("clip_i_edit", {})[case] = round((fb * fa).sum(-1).item(), 4)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
