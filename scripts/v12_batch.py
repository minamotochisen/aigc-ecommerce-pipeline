# -*- coding: utf-8 -*-
"""V12 全册资产批量: 场景重绘x4 + 姿态x3 + 背景净化x2 (新模特F1)
用法: python v12_batch.py scenes|poses|clean|all
"""
import os
import sys

sys.path.insert(0, r".\scripts")
import comfy_api
from v10_qwen2511 import NEGATIVE, PER_RUN, LOCK, REALISM, POSE_REFS, prep, workflow

ROOT = r"."
TRIAL = ROOT + r"\outputs_v2\v12_trial"
OUT = ROOT + r"\outputs_v2\v12"
os.makedirs(OUT, exist_ok=True)

B_BASE = TRIAL + r"\v12_tryon_b_94102_00001_.png"   # 藏蓝泡泡袖+米白长裙
D_BASE = TRIAL + r"\v12_tryon_d_94113_00001_.png"   # 米色衬衫+卡其长裙
B_CLUTTER = TRIAL + r"\v12_tryon_b_94101_00001_.png"  # 有钉照片背景的B底

DESC_B = ("同一张脸（冷白肌肤、不戴眼镜）、同样黑色长直发中分发型、同样金色细项链、"
          "同样藏蓝色泡泡袖上衣与米白色长裙、同样姿态构图、同样肤色与服装颜色，禁止对人物重新调色")
DESC_D = ("同一张脸（冷白肌肤、不戴眼镜）、同样黑色长直发中分发型、同样银色细项链、"
          "同样米色坑纹针织开衫与白色吊带内搭、同样卡其色麂皮半身长裙与白色编织手提包、"
          "同样姿态构图、同样肤色与服装颜色，禁止对人物重新调色")

POSE_PROMPT = ("Put the same woman from image 1 into the exact body pose, camera angle and framing "
               "of image 2. She wears the same navy blue puff-sleeve blouse and cream white pleated "
               "midi skirt as in image 1 - no added ribbons or bows, same outfit. Keep her exact same "
               "face, cold fair skin, long straight black hair with center part, no glasses, thin gold "
               "necklace - do not change her identity. "
               "Ignore the person, outfit AND background in image 2, take only the pose and framing. "
               "Replace the background with a clean light gray seamless studio backdrop with soft even "
               "photography lighting, like a professional e-commerce fashion studio shot. "
               "The body pose must copy image 2 precisely: same arm and hand placement, same leg weight "
               "distribution, same head direction. For example if image 2 shows a hand on the hip, her "
               "palm rests on her hip with the elbow out; if walking, mid-stride; if looking back over "
               "shoulder, her back is to the camera with the face turned to the lens. "
               "全身构图，头顶到脚完整入画。" + LOCK + " " + REALISM)

POSE_OVERRIDES = {
    # 参考库无背影图, 背影回眸用显式文字指令
    "pose_back": ("Full body fashion studio shot: the same woman from image 1 is seen FROM BEHIND, "
                  "her back to the camera, head turned back over her right shoulder so her face is "
                  "visible to the lens, right hand resting on her hip, weight on one leg. "
                  "She wears the same navy blue puff-sleeve blouse and cream white pleated midi skirt "
                  "as in image 1 - the back of the blouse and skirt shown honestly. Keep her exact same "
                  "face (visible in profile over the shoulder), cold fair skin, long straight black hair "
                  "with center part flowing down her back, no glasses, thin gold necklace. "
                  "Clean light gray seamless studio backdrop with soft even photography lighting, "
                  "professional e-commerce fashion studio shot. "
                  "全身构图，头顶到鞋完整入画。" + LOCK + " " + REALISM),
}

CASES = {
    "scene_cream_b": {
        "prompt": ("背景替换。图1人物保持完全不变：" + DESC_B + "。"
                   "只把背景替换为奶油色极简室内场景：奶油白色墙面、原木色地板、柔和的窗帘漫射光、"
                   "浅景深、温馨干净的电商女装摄影氛围。人物合成进新场景时，主光方向与环境光自然匹配"
                   "（柔和漫射光），地面投影柔和真实。" + LOCK + " " + REALISM),
        "images": [B_BASE], "seeds": [94201, 94202],
    },
    "scene_street_d": {
        "prompt": ("背景替换。图1人物保持完全不变：" + DESC_D + "。"
                   "只把背景替换为欧洲老城石板街：奶油色墙面、木质百叶窗，阴天柔和漫射光、"
                   "背景有真实的光学景深虚化，无强烈直射阳光。人物合成进新场景时光影自然融合、"
                   "环境色柔和过渡，地面投影浅而柔和，绝无涂抹马赛克。" + LOCK + " " + REALISM),
        "images": [D_BASE], "seeds": [94211, 94212],
    },
    "scene_street_b": {
        "prompt": ("背景替换。图1人物保持完全不变：" + DESC_B + "。"
                   "只把背景替换为欧洲老城石板街：奶油色墙面、木质百叶窗，阴天柔和漫射光、"
                   "背景有真实的光学景深虚化，无强烈直射阳光。人物合成进新场景时光影自然融合、"
                   "环境色柔和过渡，地面投影浅而柔和，绝无涂抹马赛克。" + LOCK + " " + REALISM),
        "images": [B_BASE], "seeds": [94213, 94214],
    },
    "pose_back": {
        "prompt": POSE_OVERRIDES["pose_back"], "images": [B_BASE, POSE_REFS["front"]], "seeds": [94222, 94223],
    },
    "pose_walking": {
        "prompt": POSE_PROMPT, "images": [B_BASE, POSE_REFS["walking"]], "seeds": [94232],
    },
    "pose_handonhip": {
        "prompt": POSE_PROMPT, "images": [B_BASE, POSE_REFS["handonhip"]], "seeds": [94242],
    },
    "clean_bkg": {
        "prompt": ("画面净化。图1人物保持完全不变：" + DESC_B + "。"
                   "只把背景墙面上的照片、明信片、图钉与所有杂物去除，替换为干净平整的浅米色乳胶漆墙面，"
                   "墙面颜色质感均匀一致，保留原有的柔和光影渐变，绝无色块涂抹斑与模糊区。" + LOCK + " " + REALISM),
        "images": [B_CLUTTER], "seeds": [94251, 94252],
    },
}

GROUPS = {
    "scenes": ["scene_cream_b", "scene_street_d", "scene_street_b"],
    "poses": ["pose_back", "pose_walking", "pose_handonhip"],
    "clean": ["clean_bkg"],
}


def main():
    group = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = sum([GROUPS[g] for g in ([group] if group != "all" else GROUPS)], [])
    comfy_api.wait_server()
    for name in names:
        c = CASES[name]
        for s in c["seeds"]:
            imgs = [prep(p, "v12b_%s_in%d.png" % (name, i)) for i, p in enumerate(c["images"], 1)]
            wf = workflow(c["prompt"], NEGATIVE, imgs, s)
            wf["12"]["inputs"]["filename_prefix"] = "v12_%s_%d" % (name, s)
            print(name, s, comfy_api.run_watchdog(wf, OUT, per_run=PER_RUN), flush=True)


if __name__ == "__main__":
    main()
