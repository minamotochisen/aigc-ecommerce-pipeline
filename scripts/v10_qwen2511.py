# -*- coding: utf-8 -*-
"""V10 管线: Qwen-Image-Edit-2511 (基于 V9, 按调研_v10.md 落实修复)
改动:
  1. steps 20 -> 40 (官方 2511 模板质量基线, 本地实测解析 blueprints/Image Edit (Qwen 2511).json)
  2. 负面分支改为 TextEncodeQwenImageEditPlus + 同图输入 (对齐官方模板), 负面文本针对 R0 评审硬伤
  3. 正面 prompt 重写: 结构锁定(姿态/四肢/手五指/脚成对) + 真实感(印花随褶皱/皮肤质感/背景纯净)
  4. handfix 模式: 手部区域裁剪放大 -> 单独修手 -> 羽化回贴 (全身图 1024px 手部仅~30px 的根因解法)
  5. per_run 900s 适配 40 步
用法:
  python v10_qwen2511.py tryon [seeds...]   # 换装
  python v10_qwen2511.py pose handonhip 91711 91712   # 指定姿态+seeds
  python v10_qwen2511.py scene_med / scene_street     # 场景(链式)
  python v10_qwen2511.py blank / blank_tee            # 光板
  python v10_qwen2511.py handfix <img> <x1,y1,x2,y2>  # 手部修复回贴
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
from PIL import Image

ROOT = r"."
OUT = os.path.join(ROOT, "outputs_v2", "v10")
os.makedirs(OUT, exist_ok=True)

MODEL = "qwen_image_edit_2511_fp8mixed.safetensors"
CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
VAE = "qwen_image_vae.safetensors"

ANCHOR = os.path.join(ROOT, "assets_v2", "models", "m_dress_brown.webp")
GARMENT = os.path.join(ROOT, "assets_v2", "garments", "v2ref_case1_dressfloral.jpg")
POSES = os.path.join(ROOT, "assets_v2", "poses")
POSE_REFS = {
    "handonhip": os.path.join(POSES, "p_plainbg.jpg"),
    "walking":   os.path.join(POSES, "p_lawn.jpg"),
    "side":      os.path.join(POSES, "p_elle_palm.jpg"),
    "back":      os.path.join(POSES, "m_tank_cream.jpg"),
    "front":     os.path.join(POSES, "m_tank_cream.jpg"),
    "stand34":   os.path.join(POSES, "m_jumpsuit.jpg"),
}

MAX_SIDE = 1024
# 步数决策(V11更新): V10期间">20步必卡死"经定位为nvlddmkm驱动故障期表现, 重启机器后自愈。
# 2026-08-31晚实测 40步 364s/张 稳定通过(v11_test40.py, seed92001), 恢复官方模板基线 40步/CFG3/euler/simple。
# 兜底: 若再次卡死, run_watchdog 会重启并重排队; 仍失败则回退 20步+负面词补偿方案。
STEPS = 40
PER_RUN = 900

# 负面提示: 针对 R0 豆包评审的跨页硬伤 (中文, Qwen 原生语种)
NEGATIVE = ("畸形的手, 手指粘连, 多余的手指, 缺失的手指, 模糊的手指, 蜡状手, "
            "扭曲的脚, 脚趾畸形, 左右鞋不成对, 膝盖变形, 肢体边缘波浪抖动, "
            "多余或缺失的肢体, 蜡质塑料皮肤, 皮肤过度光滑, 印花平贴漂浮不随褶皱, "
            "背景涂抹马赛克, 半透明涂抹伪影, 发丝悬空断裂, "
            "头部偏小, 腿部过度拉长, 身材比例失调, 五官畸形, 眼镜与眼睛融合, "
            "模糊, 低质量, 画质差, 变形")

# 结构锁定 + 真实感通用段 (拼入各 case)。V11: 加头身比锁定(R0 头小腿长) + 皮肤纹理词(调研: pores/油光)
LOCK = ("严格保持人体结构完全正确：双手各五根手指、指节清晰、自然放松；双脚自然且左右鞋成对同款；"
        "膝盖、脚踝、手腕骨骼点清晰；四肢轮廓平滑无抖动。"
        "头身比例符合真实人体：约七头身，头部大小正常不偏小，腿部自然不长，肩宽腰身臀线像真实身材，"
        "真实照片质感而非插画风格。"
        "五官结构正确：双眼对称、眼镜贴合眼眶不与眼睛融合、鼻嘴下巴形态自然。"
        "皮肤要有真实人像质感：可见细微毛孔与自然血色不均，有真实的高光与油光过渡，绝无蜡质塑料喷漆感。")
REALISM = ("画面达到真实电商摄影质感：面料印花图案连续完整，随褶皱自然形变，褶皱凸处受光、凹处转暗；"
           "背景光学纯净自然无涂抹噪点；人物与场景光影方向统一，地面投影真实。")


def prep(path, name):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    scale = min(MAX_SIDE / max(w, h), 1.0)
    im = im.resize((max(int(w * scale) // 16 * 16, 256), max(int(h * scale) // 16 * 16, 256)), Image.LANCZOS)
    p = os.path.join(OUT, name)
    im.save(p)
    return comfy_api.upload_image(p)


def workflow(prompt, negative, images, seed, steps=STEPS, cfg=3.0):
    """images: [upload dict/file name, ...] -> image1..imageN
    负面分支用纯文本 CLIPTextEncode(省 VL 图像编码; 实测带图负面编码致显存溢出卸载、40步卡死)"""
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "5": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
        "6": {"class_type": "VAEEncode", "inputs": {"pixels": ["8", 0], "vae": ["3", 0]}},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "clip": ["2", 0], "prompt": prompt, "vae": ["3", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 0]}},
        "9": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
            "denoise": 1.0, "model": ["5", 0], "positive": ["7", 0], "negative": ["8", 0],
            "latent_image": ["6", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": "v10", "images": ["11", 0]}},
    }
    for i, img in enumerate(images, 1):
        key = f"image{i}"
        node_id = str(20 + i)
        wf[node_id] = {"class_type": "LoadImage", "inputs": {"image": img["name"] if isinstance(img, dict) else img}}
        wf["7"]["inputs"][key] = [node_id, 0]
        if i == 1:
            wf["6"]["inputs"]["pixels"] = [node_id, 0]
    return wf


CASES = {
    # ---- 换装: 结构锁定 + 手部姿态归一 + 印花随褶皱 + 全身取景锁定 ----
    "tryon": {
        "prompt": ("虚拟试穿换装。图1是人物，图2只有服装。把女士的咖啡色波点吊带长裙替换为图2中的"
                   "藏青色碎花印花吊带短裙（黑色蝴蝶结肩带）。只从图2取这条裙子，忽略图2中的人物、姿态和背景。"
                   "图1中其余一切保持完全不变：同一张脸、同一副无框眼镜、同样妆容、同样的深棕色齐刘海长发、"
                   "同样的灰色影棚背景。取景必须与图1完全一致：全身构图，头顶到鞋履完整入画，"
                   "人物站姿、脚部位置和镜头距离都不许改变。" + LOCK +
                   "双手自然垂放于身体两侧，五指自然伸直放松，手指清晰分离。" + REALISM),
        "images": [ANCHOR, GARMENT],
    },
    # ---- 场景: 人物像素级锁定 + 光影匹配。V11: 换热门商业背景(奶油极简室内/柔和街拍),
    # 光线选柔和(阴天/窗帘光), 避免硬阳光与影棚人物光割裂(R0 P3/P4 致命项)
    "scene_cream": {
        "prompt": ("背景替换。图1人物保持完全不变：同一张脸、同一副无框眼镜、同样深棕色长发（保持自然深色发色，"
                   "禁止绿色橄榄色偏色）、同一条碎花裙、同样姿态构图、同样肤色与服装颜色，禁止对人物重新调色。"
                   "只把背景替换为奶油色极简室内场景：奶油白色墙面、原木色地板、柔和的窗帘漫射光、"
                   "浅景深、温馨干净的电商女装摄影氛围。人物合成进新场景时，主光方向与环境光自然匹配"
                   "（柔和漫射光），地面投影柔和真实。" + LOCK + " " + REALISM),
        "images": [os.path.join(OUT, "tryon_best.png")],
    },
    "scene_med": {
        "prompt": ("背景替换。图1人物保持完全不变：同一张脸、同一副无框眼镜、同样深棕色长发（保持自然深色发色，"
                   "禁止绿色橄榄色偏色）、同一条碎花裙、同样姿态构图、同样肤色与服装颜色，禁止对人物重新调色。"
                   "只把灰色影棚背景替换为阳光地中海场景：白色石拱墙、暖色陶土地面、金色阳光与拱形影。"
                   "人物合成进新场景时，主光方向与环境光自然匹配，地面投影柔和真实。" + LOCK + " " + REALISM),
        "images": [os.path.join(OUT, "tryon_best.png")],
    },
    "scene_street": {
        "prompt": ("背景替换。图1人物保持完全不变：同一张脸、同一副无框眼镜、同样深棕色长发（保持自然深色发色，"
                   "禁止绿色橄榄色偏色）、同一条碎花裙、同样姿态构图、同样肤色与服装颜色，禁止对人物重新调色。"
                   "只把灰色影棚背景替换为欧洲老城石板街：奶油色墙面、木质百叶窗，阴天柔和漫射光、"
                   "背景有真实的光学景深虚化，无强烈直射阳光。人物合成进新场景时光影自然融合、"
                   "环境色柔和过渡，地面投影浅而柔和，绝无涂抹马赛克。" + LOCK + " " + REALISM),
        "images": [os.path.join(OUT, "tryon_best.png")],
    },
    # ---- 姿态: V9验证过的英文指令 + 姿态照抄强调 + 中文结构锁定。
    # V11: 背景与姿态参考解耦——统一换成浅灰影棚无缝背景(R0: 户外格光影割裂致命 + 用户要求热门商业背景)
    "pose": {
        "prompt": ("Put the same woman from image 1 into the exact body pose, camera angle and framing "
                   "of image 2. She wears the same coffee brown polka dot slip midi dress as in image 1 - "
                   "no added ribbons or bows, same plain polka dot dress. Keep her exact same face, rimless "
                   "glasses, makeup and long dark brown hair with bangs - do not change her identity. "
                   "Ignore the person, outfit AND background in image 2, take only the pose and framing. "
                   "Replace the background with a clean light gray seamless studio backdrop with soft even "
                   "photography lighting, like a professional e-commerce fashion studio shot. "
                   "The body pose must copy image 2 precisely: same arm and hand placement, same leg weight "
                   "distribution, same head direction. For example if image 2 shows a hand on the hip, her "
                   "palm rests on her hip with the elbow out; if walking, mid-stride; if looking back over "
                   "shoulder, her back is to the camera with the face turned to the lens. "
                   "全身构图，头顶到脚完整入画。" + LOCK + " " + REALISM),
        "images": [ANCHOR, None],
    },
    # ---- 光板: 纹理保真 ----
    "blank": {
        "prompt": ("服装净化。去除红色T恤上的大面积花卉印花，变成纯红色棉质T恤。"
                   "严格保持面料织纹、褶皱、阴影、领口和人台形状完全不变。"
                   "原印花区域的面料颜色必须均匀一致，保留棉质针织纹理，绝不许出现色块涂抹斑或纹理变平。"),
        "images": [os.path.join(ROOT, "assets", "garments", "cand_redtee_floral.png")],
    },
    "blank_tee": {
        "prompt": ("服装净化。去除白色T恤胸口的黑色文字印花和领标，变成纯白空白棉质T恤。"
                   "严格保持面料织纹、褶皱、阴影、领口双层结构和人台形状完全不变，"
                   "领口内侧细节要完整保留，绝不许出现模糊涂抹。"),
        "images": [os.path.join(ROOT, "assets_v2", "garments", "g_tee_awet.jpg")],
    },
}


def run_seeds(case, seeds):
    c = CASES[case]
    for s in seeds:
        if case == "pose":
            pose_key, seed = s
            imgs = [prep(ANCHOR, "pose_anchor.png"), prep(POSE_REFS[pose_key], f"pose_ref_{pose_key}.jpg")]
            wf = workflow(c["prompt"], NEGATIVE, imgs, seed)
            wf["12"]["inputs"]["filename_prefix"] = f"v10_pose_{pose_key}_{seed}"
        else:
            imgs = [prep(p, f"{case}_in{i}.png") for i, p in enumerate(c["images"], 1)]
            wf = workflow(c["prompt"], NEGATIVE, imgs, s)
            wf["12"]["inputs"]["filename_prefix"] = f"v10_{case}_{s}"
        print(case, s, comfy_api.run_watchdog(wf, OUT, per_run=PER_RUN), flush=True)


def handfix(img_path, box, seed=91801, context=0.35, work=768):
    """手部修复: 裁剪 box(带 context 边距) -> 放大到 work 边长 -> Qwen 修手 -> 缩回羽化回贴"""
    im = Image.open(img_path).convert("RGB")
    W, H = im.size
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * context), int(bh * context)
    cx1, cy1 = max(0, x1 - mx), max(0, y1 - my)
    cx2, cy2 = min(W, x2 + mx), min(H, y2 + my)
    crop = im.crop((cx1, cy1, cx2, cy2))
    scale = work / max(crop.size)
    big = crop.resize((int(crop.size[0] * scale) // 16 * 16, int(crop.size[1] * scale) // 16 * 16), Image.LANCZOS)
    src = os.path.join(OUT, "_handfix_in.png")
    big.save(src)
    up = comfy_api.upload_image(src)
    prompt = ("修复这张照片中人物的手部：把手修正为结构完全正确的自然手，五根手指、指节清晰、"
              "粗细自然、自然放松的姿态。保持画面中其他所有内容与构图完全不变，保持皮肤质感、"
              "光线和袖口/衣料与手的关系不变。真实人像摄影质感。")
    wf = workflow(prompt, NEGATIVE, [up], seed)
    wf["12"]["inputs"]["filename_prefix"] = "v10_handfix"
    comfy_api.run_watchdog(wf, OUT, per_run=PER_RUN)
    # 取最新输出
    outs = sorted([f for f in os.listdir(OUT) if f.startswith("v10_handfix") and f.endswith(".png")],
                  key=lambda f: os.path.getmtime(os.path.join(OUT, f)))
    fixed_big = Image.open(os.path.join(OUT, outs[-1])).convert("RGB").resize(crop.size, Image.LANCZOS)
    # 羽化回贴
    from PIL import ImageFilter
    mask = Image.new("L", crop.size, 0)
    inner = Image.new("L", (bw, bh), 255)
    mask.paste(inner, (x1 - cx1, y1 - cy1))
    mask = mask.filter(ImageFilter.GaussianBlur(12))
    im.paste(fixed_big, (cx1, cy1), mask)
    dst = os.path.join(OUT, "handfix_final_%d.png" % seed)
    im.save(dst)
    print("handfix saved:", dst, flush=True)


def facefix(img_path, box, seed=92101, context=0.45, work=896):
    """V11 人脸修复: 裁剪脸部区域放大 -> 以锚定照脸部特写作身份参考(image2) -> 一致性重绘 -> 羽化回贴。
    box 来自 DWPose 面部关键点(鼻/眼/耳)包盒外扩。调研: RunComfy 建议"裁剪脸部特写作为额外身份参考"。"""
    im = Image.open(img_path).convert("RGB")
    W, H = im.size
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * context), int(bh * context)
    cx1, cy1 = max(0, x1 - mx), max(0, y1 - my)
    cx2, cy2 = min(W, x2 + mx), min(H, y2 + my)
    crop = im.crop((cx1, cy1, cx2, cy2))
    scale = work / max(crop.size)
    big = crop.resize((int(crop.size[0] * scale) // 16 * 16, int(crop.size[1] * scale) // 16 * 16), Image.LANCZOS)
    # 身份参考: 锚定照上部 40% 作为脸部区域
    anchor = Image.open(ANCHOR).convert("RGB")
    aw, ah = anchor.size
    ref = anchor.crop((int(aw * 0.2), 0, int(aw * 0.8), int(ah * 0.42)))
    src = os.path.join(OUT, "_facefix_in.png")
    big.save(src)
    refp = os.path.join(OUT, "_facefix_ref.png")
    ref.save(refp)
    prompt = ("图1是一位女士的脸部特写照片，图2是同一位女士的参考照片。"
              "参考图2中的脸部身份，修复图1中人物的脸部：保持是同一个人，五官结构完全正确——"
              "双眼对称、眼镜镜框贴合眼眶且不与眼睛融合、鼻子嘴唇下巴形态自然、下颌线清晰；"
              "皮肤有真实人像质感：可见细微毛孔与自然血色，无蜡质塑料感。"
              "严格保持图1中的拍摄角度、光线方向和背景完全不变；"
              "头发和发丝必须保持图1原样：同样的发型、同样的发丝走向，禁止重绘或改变任何头发。"
              "只把脸部修正为与图2身份一致的自然人脸。真实人像摄影质感。")
    wf = workflow(prompt, NEGATIVE, [comfy_api.upload_image(src), comfy_api.upload_image(refp)], seed)
    wf["12"]["inputs"]["filename_prefix"] = "v11_facefix"
    comfy_api.run_watchdog(wf, OUT, per_run=PER_RUN)
    outs = sorted([f for f in os.listdir(OUT) if f.startswith("v11_facefix") and f.endswith(".png")],
                  key=lambda f: os.path.getmtime(os.path.join(OUT, f)))
    fixed_big = Image.open(os.path.join(OUT, outs[-1])).convert("RGB").resize(crop.size, Image.LANCZOS)
    from PIL import ImageFilter
    mask = Image.new("L", crop.size, 0)
    inner = Image.new("L", (bw, bh), 255)
    mask.paste(inner, (x1 - cx1, y1 - cy1))
    mask = mask.filter(ImageFilter.GaussianBlur(10))
    im.paste(fixed_big, (cx1, cy1), mask)
    dst = os.path.join(OUT, "facefix_final_%d.png" % seed)
    im.save(dst)
    print("facefix saved:", dst, flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "tryon"
    comfy_api.wait_server()
    if mode == "handfix":
        img = sys.argv[2]
        box = json.loads(sys.argv[3])
        seed = int(sys.argv[4]) if len(sys.argv) > 4 else 91801
        handfix(img, box, seed)
    elif mode == "facefix":
        img = sys.argv[2]
        box = json.loads(sys.argv[3])
        seed = int(sys.argv[4]) if len(sys.argv) > 4 else 92101
        facefix(img, box, seed)
    elif mode == "pose":
        pose_key = sys.argv[2]
        seeds = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [91711, 91712]
        run_seeds("pose", [(pose_key, s) for s in seeds])
    else:
        seeds = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [91701, 91702, 91703]
        run_seeds(mode, seeds)
