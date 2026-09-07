# -*- coding: utf-8 -*-
"""V12: facexlib 检测人脸 → 裁脸部特写 → 拼对比页
在 python_embeded 目录下运行 (facexlib weights 相对路径):
  ./python.exe <脚本路径>
"""
import os
import sys
import traceback

import cv2
import numpy as np

ASSETS = r".\assets_v2\v12"
OUT_SHEET = os.path.join(ASSETS, "_face_closeups.png")
CROP_DIR = os.path.join(ASSETS, "facecrops")
os.makedirs(CROP_DIR, exist_ok=True)

# 全部候选: 新搜的 + 旧库
SRC = (
    [os.path.join(ASSETS, "faces", f) for f in sorted(os.listdir(os.path.join(ASSETS, "faces")))
     if f.lower().endswith((".jpg", ".png", ".webp"))]
    + [os.path.join(ASSETS, f) for f in [
        "mdl_cand025.jpg", "mdl_shirtpants.png", "mdl_studio1.jpg",
        "mdl_studio2.jpg", "mdl_vest.jpg", "mdl_knit.jpg", "mdl_suit.jpg", "mdl_cand012.jpg"]]
)


def imread_cn(path):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def main():
    from facexlib.utils.face_restoration_helper import FaceRestoreHelper

    rows = []
    for path in SRC:
        if not os.path.exists(path):
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            img = imread_cn(path)
            if img is None:
                print("SKIP unreadable", name)
                continue
            helper = FaceRestoreHelper(
                upscale_factor=1, face_size=512, det_model="retinaface_resnet50",
                save_ext="png", device="cuda",
                model_rootpath=os.path.join("weights", "facexlib"))
            helper.clean_all()
            helper.read_image(img)
            n = helper.get_face_landmarks_5(only_center_face=False, resize=640,
                                            eye_dist_threshold=5)
            if n == 0 or not helper.all_landmarks_5:
                print("SKIP no-face", name)
                continue
            # 取最大的脸 (按关键点外接框面积)
            best, best_area = None, 0
            for lm in helper.all_landmarks_5:
                x0, y0 = lm.min(axis=0)
                x1, y1 = lm.max(axis=0)
                a = (x1 - x0) * (y1 - y0)
                if a > best_area:
                    best_area, best = a, lm
            x0, y0 = best.min(axis=0)
            x1, y1 = best.max(axis=0)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            w, h = (x1 - x0), (y1 - y0)
            # 外扩: 脸部特写 ~2.2x 关键点框, 中心略上移留额头
            side = max(w, h) * 2.2
            cy = cy - side * 0.06
            H, W = img.shape[:2]
            x0c, x1c = int(max(0, cx - side / 2)), int(min(W, cx + side / 2))
            y0c, y1c = int(max(0, cy - side / 2)), int(min(H, cy + side / 2))
            crop = img[y0c:y1c, x0c:x1c]
            if crop.size == 0 or crop.shape[0] < 60 or crop.shape[1] < 60:
                print("SKIP tiny-crop", name)
                continue
            out_path = os.path.join(CROP_DIR, name + "_face.png")
            cv2.imencode(".png", crop)[1].tofile(out_path)
            rows.append((name, out_path, img.shape[1], img.shape[0], n))
            print("ok", name, "faces:", n, "crop:", crop.shape[1], "x", crop.shape[0])
        except Exception as e:
            print("FAIL", name, type(e).__name__, str(e)[:100])
            traceback.print_exc()

    if not rows:
        print("no faces cropped")
        return
    rows.sort(key=lambda r: r[0])

    # 拼对比页: 每行5个, 单元 380x475 + 标签
    from PIL import Image as PImage
    from PIL import ImageDraw, ImageFont
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)
    cols = 5
    cell_w, cell_h, label_h = 380, 475, 56
    n_rows = (len(rows) + cols - 1) // cols
    sheet = PImage.new("RGB", (cols * cell_w, n_rows * (cell_h + label_h)), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    tags = {}
    for i, (name, crop_path, w, h, nf) in enumerate(rows):
        r, c = divmod(i, cols)
        im = PImage.open(crop_path)
        im.thumbnail((cell_w - 8, cell_h - 8))
        sheet.paste(im, (c * cell_w + 4, r * (cell_h + label_h) + 4))
        tag = chr(65 + r) + str(c + 1)
        draw.text((c * cell_w + 10, r * (cell_h + label_h) + cell_h + 6),
                  "%s %s (%dx%d%s)" % (tag, name, w, h, " 多脸!" if nf > 1 else ""),
                  fill=(20, 20, 20), font=font)
        tags[tag] = name
    sheet.save(OUT_SHEET)
    print("sheet ->", OUT_SHEET)
    print("tags:", json_dumps(tags))


def json_dumps(tags):
    import json
    return json.dumps(tags, ensure_ascii=False)


if __name__ == "__main__":
    main()
