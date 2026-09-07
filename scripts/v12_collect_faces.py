# -*- coding: utf-8 -*-
"""V12: 补搜高清中国女模特正脸照 → assets_v2/v12/faces/
要求: 单人正面/微侧、脸部清晰、竖幅半身或全身、无水印
"""
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request

ROOT = r"."
OUT = os.path.join(ROOT, "assets_v2", "v12", "faces")
os.makedirs(OUT, exist_ok=True)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

QUERIES = [
    ("portrait", "中国女模特 半身 正面 高清 肖像 棚拍", 8),
    ("portrait2", "亚洲 女模特 素颜感 高清 肖像 室内", 8),
    ("portrait3", "中国 女生 模特 大众脸 高清 人像 摄影", 8),
    ("portrait4", "chinese female model portrait front face studio", 8),
]


def bing_search(q, first=1):
    url = ("https://cn.bing.com/images/search?q=" + urllib.parse.quote(q)
           + "&form=HDRSC2&first=%d&mkt=zh-CN" % first)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
        s = r.read().decode("utf-8", "ignore")
    items = re.findall(r'm="(\{.*?\})"', s)
    out = []
    for it in items:
        try:
            j = json.loads(it.replace("&quot;", '"').replace("&amp;", "&"))
        except Exception:
            continue
        u, t = j.get("murl"), (j.get("t") or "")
        if u:
            out.append((u, t))
    return out


def download(u, path):
    req = urllib.request.Request(u, headers={"User-Agent": UA,
                                             "Referer": "https://cn.bing.com/"})
    with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
        data = r.read(25 * 1024 * 1024)
    if len(data) < 40_000:  # 脸部清晰度底线
        return False, 0
    open(path, "wb").write(data)
    return True, len(data)


def main():
    manifest = []
    seen = set()
    idx = 0
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    for tag, q, want in QUERIES:
        try:
            results = bing_search(q)
        except Exception as e:
            print("search fail", tag, e)
            continue
        ok = 0
        for u, t in results:
            if u in seen or ok >= want:
                continue
            seen.add(u)
            idx += 1
            m = re.search(r"\.(jpe?g|png|webp)(?:[?#]|$)", u.lower())
            ext = "." + ("jpg" if not m or m.group(1).startswith("jp") else m.group(1))
            path = os.path.join(OUT, "face_%s_%02d%s" % (tag, idx, ext))
            try:
                good, size = download(u, path)
            except Exception:
                if os.path.exists(path):
                    os.remove(path)
                continue
            if not good:
                os.remove(path) if os.path.exists(path) else None
                continue
            try:
                from PIL import Image
                with Image.open(path) as im:
                    im.verify()
                with Image.open(path) as im:
                    w, h = im.size
            except Exception:
                os.remove(path)
                continue
            # 半身或全身竖幅; 脸不能太小(按短边占比粗筛, 精确的交给人脸检测)
            if w < 500 or h < 600 or h / w > 2.6 or h / w < 0.8:
                os.remove(path)
                continue
            ok += 1
            manifest.append({"file": os.path.basename(path), "w": w, "h": h,
                             "title": t[:60], "src": u})
            print("ok", os.path.basename(path), w, "x", h, size // 1024, "KB |", t[:36])
    with open(os.path.join(OUT, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("total kept:", len(manifest))


if __name__ == "__main__":
    main()
