# -*- coding: utf-8 -*-
"""V12 试产: 中国脸模特(cand_012) × 两套服装
用法:
  python v12_tryon.py b <seeds...>   # B组合: 藏蓝泡泡袖上衣+米白长裙 (双图: 人物+套装参考)
  python v12_tryon.py d <seeds...>   # D组合: 米色衬衫+卡其亚麻半身长裙 (三图: 人物+衬衫+长裙)
基于 v10_qwen2511 (40步/CFG3), 多图 TextEncodeQwenImageEditPlus。"""
import os
import sys

sys.path.insert(0, r".\scripts")
import comfy_api
from v10_qwen2511 import NEGATIVE, OUT, PER_RUN, prep, workflow

ROOT = r"."
V12 = ROOT + r"\assets_v2\v12"

ANCHOR = V12 + r"\mdl_f1.jpg"  # F1 冷白高级脸 (AI参考·即梦, 已裁水印), 半身像
REF_B = V12 + r"\fit_blouseshirt.jpg"      # 藏蓝泡泡袖+米白长裙 全身
REF_D_TOP = V12 + r"\fit_beigedenim.jpg"   # 米色衬衫 (上身参考)
REF_D_SKIRT = V12 + r"\fit_khakilinen.jpg" # 卡其亚麻长裙 (下身参考)

LOCK = ("严格保持人体结构完全正确：双手各五根手指、指节清晰、自然放松；双脚自然且左右鞋成对同款；"
        "膝盖、脚踝、手腕骨骼点清晰；四肢轮廓平滑无抖动。"
        "头身比例符合真实人体：约七头身，头部大小正常不偏小，腿部自然不长，肩宽腰身臀线像真实身材，"
        "真实照片质感而非插画风格。"
        "五官结构正确：双眼对称、眼镜贴合眼眶不与眼睛融合、鼻嘴下巴形态自然。"
        "皮肤要有真实人像质感：可见细微毛孔与自然血色不均，有真实的高光与油光过渡，绝无蜡质塑料喷漆感。")
REALISM = ("画面达到真实电商摄影质感：面料纹理与印花随褶皱自然形变，褶皱凸处受光、凹处转暗；"
           "背景光学纯净自然无涂抹噪点；人物与场景光影方向统一，地面投影真实。")

FACE_SRC = ("图1是人物半身像，只从图1取人物的脸型、五官身份与发型，图1的取景构图不参考。"
            "输出必须是全身站姿照片：头顶到鞋履完整入画，竖幅电商模特全身构图。"
            "人物的脸部身份保持与图1完全一致（同一个人）。")
CASES = {
    "b": {
        "prompt": ("虚拟试穿换装。图2是一套服装穿搭参考。"
                   "把人物的服装替换为图2中的整套搭配：藏蓝色泡泡袖上衣 + 米白色长款半身裙，"
                   "上衣与裙子的款式、颜色、面料都照图2。只从图2取服装，忽略图2中的人物、姿态和背景。"
                   + FACE_SRC +
                   "配素色平底凉鞋。" + LOCK +
                   "双手自然垂放于身体两侧，五指自然伸直放松，手指清晰分离。" + REALISM),
        "images": [ANCHOR, REF_B],
    },
    "d": {
        "prompt": ("虚拟试穿换装。图2是米色长袖衬衫参考，图3是卡其色亚麻半身长裙参考。"
                   "把人物上装替换为图2中的米色长袖衬衫（保留图2衬衫的领型、袖型、面料质感），"
                   "下装替换为图3中的卡其色亚麻半身长裙（裙长到小腿、垂坠感照图3）。"
                   "只从图2取衬衫、从图3取长裙，忽略参考图中的人物、姿态和背景。"
                   + FACE_SRC +
                   "配米色平底凉鞋。" + LOCK +
                   "双手自然垂放于身体两侧，五指自然伸直放松，手指清晰分离。" + REALISM),
        "images": [ANCHOR, REF_D_TOP, REF_D_SKIRT],
    },
}

TRIAL_OUT = ROOT + r"\outputs_v2\v12_trial"
os.makedirs(TRIAL_OUT, exist_ok=True)


def run(case, seeds):
    c = CASES[case]
    for s in seeds:
        imgs = [prep(p, "v12_%s_in%d.png" % (case, i)) for i, p in enumerate(c["images"], 1)]
        wf = workflow(c["prompt"], NEGATIVE, imgs, s)
        wf["12"]["inputs"]["filename_prefix"] = "v12_tryon_%s_%d" % (case, s)
        print(case, s, comfy_api.run_watchdog(wf, TRIAL_OUT, per_run=PER_RUN), flush=True)


if __name__ == "__main__":
    mode = sys.argv[1]
    seeds = [int(x) for x in sys.argv[2].split(",")]
    comfy_api.wait_server()
    run(mode, seeds)
