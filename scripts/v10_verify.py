# -*- coding: utf-8 -*-
"""V10 出图验收: DWPose 关键点比对 + 手/脚放大裁片
用 ComfyUI 内嵌 python 运行:
  python_embeded/python.exe v10_verify.py <img1> [img2 ...] [--ref pose_ref.jpg]
输出: outputs_v2/v10/_verify/<name>_report.json + <name>_handL/R.png + <name>_footL/R.png
"""
import json
import os
import sys

sys.path.insert(0, r"ComfyUI/custom_nodes/comfyui_controlnet_aux/src")
from custom_controlnet_aux.dwpose import DwposeDetector  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = r"."
VDIR = os.path.join(ROOT, "outputs_v2", "v10", "_verify")
os.makedirs(VDIR, exist_ok=True)

# DWPose 18 点: 0鼻 1颈 2R肩 3R肘 4R腕 5L肩 6L肘 7L腕 8R髋 9R膝 10R踝 11L髋 12L膝 13L踝
WRISTS = (4, 7)
ANKLES = (10, 13)
MIN_CONF = 0.3


def to_arr(kp):
    return np.array([[k.x, k.y, k.score] if k is not None else [np.nan, np.nan, 0.0]
                     for k in kp], dtype=np.float32)


def detect(det, path):
    im = Image.open(path).convert("RGB")
    poses = det.detect_poses(np.array(im))
    if not poses:
        return None, None, im.size
    best = max(poses, key=lambda p: p.body.total_score)
    return to_arr(best.body.keypoints), best, im.size


def angle(a, b, c):
    ba = a[:2] - b[:2]
    bc = c[:2] - b[:2]
    cos = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return float(np.degrees(np.arccos(np.clip(cos, -1, 1))))


def verify(det, path, ref_kp=None):
    kp, pose, (W, H) = detect(det, path)
    name = os.path.splitext(os.path.basename(path))[0]
    rep = {"image": path, "w": W, "h": H}
    if kp is None:
        rep["verdict"] = "FAIL: no person detected"
        return rep
    conf = kp[:, 2]
    vis = int((conf >= MIN_CONF).sum())
    rep["visible_kp"] = vis

    # 躯干/腿长比例
    ok = lambda i: conf[i] >= MIN_CONF
    if ok(1) and ok(8) and ok(11):
        hip_mid = (kp[8][:2] + kp[11][:2]) / 2
        torso = float(np.linalg.norm(kp[1][:2] - hip_mid))
    else:
        torso = None
    if ok(10) and ok(13) and ok(8) and ok(11):
        ankle_mid = (kp[10][:2] + kp[13][:2]) / 2
        hip_mid = (kp[8][:2] + kp[11][:2]) / 2
        leg = float(np.linalg.norm(ankle_mid - hip_mid))
    else:
        leg = None
    if torso and leg:
        r = torso / leg
        rep["torso_leg_ratio"] = round(r, 3)
        rep["ratio_ok"] = bool(0.45 <= r <= 1.05)

    # 腿部角度 (髋-膝-踝)
    for side, (hip, knee, ankle) in {"R": (8, 9, 10), "L": (11, 12, 13)}.items():
        if ok(hip) and ok(knee) and ok(ankle):
            rep[f"knee_angle_{side}"] = round(angle(kp[hip], kp[knee], kp[ankle]), 1)

    # 与姿态参考比对: 膝角/肘角差
    if ref_kp is not None:
        diffs = []
        for (h, k, a) in [(8, 9, 10), (11, 12, 13), (2, 3, 4), (5, 6, 7)]:
            if all(ok(i) for i in (h, k, a)):
                for rk in [ref_kp]:
                    if all(rk[i][2] >= MIN_CONF for i in (h, k, a)):
                        ga = angle(kp[h], kp[k], kp[a])
                        ra = angle(rk[h], rk[k], rk[a])
                        diffs.append(abs(ga - ra))
        if diffs:
            rep["ref_joint_angle_max_diff"] = round(float(max(diffs)), 1)
            rep["ref_joint_diff_ok"] = bool(max(diffs) <= 25)

    rep["kp_visible_ok"] = bool(vis >= 13)
    fails = [k for k in ("ratio_ok", "ref_joint_diff_ok", "kp_visible_ok")
             if k in rep and not rep[k]]
    rep["verdict"] = ("FAIL: " + ",".join(fails)) if fails else "PASS(quant)"

    # 手部量化: 每只手21关键点可见数与展开度(并指/蜡状手展开度异常小)
    im = Image.open(path).convert("RGB")
    rep["_handboxes"] = {}
    rep["_footboxes"] = {}
    # V11: 人脸框 (鼻0/眼14,15/耳16,17 包盒外扩, 供 facefix)
    face_idx = [0, 14, 15, 16, 17]
    if all(ok(i) for i in face_idx):
        fx = [kp[i][0] for i in face_idx]
        fy = [kp[i][1] for i in face_idx]
        ear_span = max(abs(kp[16][0] - kp[17][0]), abs(kp[14][0] - kp[15][0]), 8)
        eye_mid_y = (kp[14][1] + kp[15][1]) / 2
        nose_y = kp[0][1]
        dh = max(nose_y - eye_mid_y, 6)
        rep["_facebox"] = [int(max(0, min(fx) - ear_span * 0.45)),
                           int(max(0, eye_mid_y - dh * 2.6)),
                           int(min(W, max(fx) + ear_span * 0.45)),
                           int(min(H, nose_y + dh * 2.4))]
    for side, idx in {"R": ANKLES[0], "L": ANKLES[1]}.items():
        if ok(idx):
            x, y = kp[idx][0], kp[idx][1]
            r = max(int(min(W, H) * 0.05), 110)
            rep["_footboxes"][side] = [int(max(0, x - r)), int(max(0, y - r * 1.15)),
                                       int(min(W, x + r)), int(min(H, y + r))]
    if pose is not None:
        for side, hand in {"R": pose.right_hand, "L": pose.left_hand}.items():
            if not hand:
                continue
            hk = np.array([[k.x, k.y, k.score] if k is not None else [np.nan, np.nan, 0.0]
                           for k in hand], dtype=np.float32)
            vis_h = int((hk[:, 2] >= MIN_CONF).sum())
            valid = hk[hk[:, 2] >= MIN_CONF][:, :2]
            spread = float(np.ptp(valid, axis=0).max()) if len(valid) >= 2 else 0.0
            rep[f"hand{side}_visible"] = vis_h
            rep[f"hand{side}_spread"] = round(spread, 1)
            if vis_h >= 4 and len(valid) >= 2:
                x1b, y1b = valid.min(axis=0)
                x2b, y2b = valid.max(axis=0)
                pad = max(x2b - x1b, y2b - y1b) * 0.3 + 24
                rep["_handboxes"][side] = [int(max(0, x1b - pad)), int(max(0, y1b - pad)),
                                           int(min(W, x2b + pad)), int(min(H, y2b + pad))]

    # 手/脚放大裁片 (腕/踝为中心; 手部有关键点则按手部包盒)
    for tag, idxs in {"hand": WRISTS, "foot": ANKLES}.items():
        for side, idx in zip("LR", idxs):
            if ok(idx):
                x, y = kp[idx][0], kp[idx][1]
                r = max(int(min(W, H) * 0.09), 90)
                if tag == "hand" and rep.get(f"hand{side}_visible", 0) >= 6:
                    hand_pts = (pose.right_hand if side == "R" else pose.left_hand) if pose is not None else None
                    if hand_pts:
                        hkk = np.array([[k.x, k.y, k.score] if k is not None else [np.nan, np.nan, 0.0]
                                        for k in hand_pts], dtype=np.float32)
                        good = hkk[hkk[:, 2] >= MIN_CONF]
                        if len(good):
                            x1b, y1b = good[:, :2].min(axis=0)
                            x2b, y2b = good[:, :2].max(axis=0)
                            pad = max((x2b - x1b), (y2b - y1b)) * 0.35 + 20
                            box = (max(0, int(x1b - pad)), max(0, int(y1b - pad)),
                                   min(W, int(x2b + pad)), min(H, int(y2b + pad)))
                            crop = im.crop(box)
                            if crop.size[0] < 260:
                                crop = crop.resize((crop.size[0] * 2, crop.size[1] * 2), Image.LANCZOS)
                            crop.save(os.path.join(VDIR, f"{name}_{tag}{side}.png"))
                            continue
                box = (max(0, int(x - r)), max(0, int(y - r)), min(W, int(x + r)), min(H, int(y + r)))
                crop = im.crop(box)
                if crop.size[0] < 260:
                    crop = crop.resize((crop.size[0] * 2, crop.size[1] * 2), Image.LANCZOS)
                crop.save(os.path.join(VDIR, f"{name}_{tag}{side}.png"))
    return rep


def main():
    args = sys.argv[1:]
    ref_path = None
    if "--ref" in args:
        i = args.index("--ref")
        ref_path = args[i + 1]
        args = args[:i] + args[i + 2:]
    det = DwposeDetector.from_pretrained("lllyasviel/Annotators",
                                         torchscript_device="cpu" if os.environ.get("V10_CPU") else "cuda")
    ref_kp = None
    if ref_path:
        ref_kp, _ = detect(det, ref_path)
    for p in args:
        rep = verify(det, p, ref_kp)
        print(json.dumps(rep, ensure_ascii=False), flush=True)
        out = os.path.join(VDIR, os.path.splitext(os.path.basename(p))[0] + "_report.json")
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
