# -*- coding: utf-8 -*-
"""V10: 必应图片搜索搜集真实电商模特摄影样本 → assets_v2/refs_real/"""
import json
import os
import re
import ssl
import urllib.parse
import urllib.request

ROOT = r"."
OUT = os.path.join(ROOT, "assets_v2", "refs_real")
os.makedirs(OUT, exist_ok=True)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

QUERIES = [
    ("studio", "电商女装模特 影棚 全身 实拍 连衣裙",
     ["女装", "模特", "连衣裙", "裙", "穿搭", "服装", "时尚", "实拍", "拍摄"]),
    ("studio2", "淘宝女装模特 白底 全身 站姿 实拍",
     ["女装", "模特", "连衣裙", "裙", "穿搭", "服装", "时尚", "实拍", "拍摄"]),
    ("street", "女装模特 街拍 走路 全身 实拍",
     ["街拍", "模特", "穿搭", "女装", "时尚", "裙", "走路"]),
    ("lookback", "连衣裙模特 回眸 姿势 实拍",
     ["连衣裙", "模特", "裙", "回眸", "姿势", "拍照", "穿搭"]),
    ("hands", "女装模特 站姿 自然 手部 姿势 实拍",
     ["模特", "站姿", "姿势", " pose", "pose", "摆拍", "拍照", "女装", "穿搭"]),
    ("sit", "女装模特 坐姿 全身 实拍 电商",
     ["模特", "坐姿", "女装", "裙", "穿搭", "拍摄", "实拍"]),
]


def keep_title(t, kws):
    t = t.lower()
    return any(k.lower() in t for k in kws)


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
        data = r.read(20 * 1024 * 1024)
    if len(data) < 30_000:
        return False
    open(path, "wb").write(data)
    return True


def main():
    manifest = []
    seen = set()
    idx = 0
    for tag, q, kws in QUERIES:
        try:
            results = bing_search(q)
        except Exception as e:
            print("search fail", tag, e)
            continue
        results = [(u, t) for u, t in results if keep_title(t, kws)]
        print("query", tag, "results after title filter:", len(results))
        ok = 0
        for u, t in results:
            if u in seen or ok >= 9:
                continue
            seen.add(u)
            idx += 1
            ext = ".jpg"
            m = re.search(r"\.(jpe?g|png|webp)(?:[?#]|$)", u.lower())
            if m:
                ext = "." + ("jpg" if m.group(1).startswith("jp") else m.group(1))
            path = os.path.join(OUT, "real_%s_%02d%s" % (tag, idx, ext))
            try:
                if not download(u, path):
                    os.remove(path) if os.path.exists(path) else None
                    continue
            except Exception:
                continue
            # 校验: PIL 可开 + 竖幅全身向
            try:
                from PIL import Image
                with Image.open(path) as im:
                    im.verify()
                with Image.open(path) as im:
                    w, h = im.size
            except Exception:
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            if w < 600 or h < 800 or h / w > 2.4:
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            ok += 1
            manifest.append({"file": os.path.basename(path), "w": w, "h": h,
                             "title": t[:60], "src": u})
            print("ok", os.path.basename(path), w, "x", h, "|", t[:36])
    with open(os.path.join(OUT, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("total kept:", len(manifest))


if __name__ == "__main__":
    main()
