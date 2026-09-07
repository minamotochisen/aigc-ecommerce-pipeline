# -*- coding: utf-8 -*-
"""V11: 必应搜集热门商业化模特样本(按 2025-2026 主流背景风格) → assets_v2/refs_bg/
背景风格依据调研: 极简影棚无缝 / 奶油莫兰迪室内 / 法式轻奢室内 / 拱形墙影棚 / 商业街拍。网络任务, 不占 GPU。"""
import json
import os
import re
import ssl
import urllib.parse
import urllib.request

ROOT = r"."
OUT = os.path.join(ROOT, "assets_v2", "refs_bg")
os.makedirs(OUT, exist_ok=True)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

QUERIES = [
    ("seamless", "女装模特 影棚 无缝背景 全身 实拍 连衣裙",
     ["女装", "模特", "连衣裙", "裙", "拍摄", "实拍", "时尚"]),
    ("seamless2", "淘宝女装模特 灰色 背景 全身 站姿 棚拍",
     ["女装", "模特", "裙", "拍摄", "棚拍", "影棚"]),
    ("cream", "女装模特 奶油风 室内 场景 拍摄 连衣裙",
     ["模特", "室内", "裙", "场景", "拍摄", "奶油"]),
    ("french", "法式 轻奢 室内 女装 模特 拍摄 大理石 落地窗",
     ["模特", "室内", "法式", "轻奢", "女装", "拍摄"]),
    ("arch", "女装拍摄 拱形 弧形墙 背景 模特 极简",
     ["拱形", "弧形", "背景", "模特", "拍摄", "极简", "墙"]),
    ("studio_beige", "女装模特 米色 墙面 极简 背景 拍摄 全身",
     ["米色", "背景", "模特", "女装", "拍摄", "极简"]),
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
            if u in seen or ok >= 8:
                continue
            seen.add(u)
            idx += 1
            ext = ".jpg"
            m = re.search(r"\.(jpe?g|png|webp)(?:[?#]|$)", u.lower())
            if m:
                ext = "." + ("jpg" if m.group(1).startswith("jp") else m.group(1))
            path = os.path.join(OUT, "bg_%s_%02d%s" % (tag, idx, ext))
            try:
                if not download(u, path):
                    if os.path.exists(path):
                        os.remove(path)
                    continue
            except Exception:
                continue
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
                             "tag": tag, "title": t[:60], "src": u})
            print("ok", os.path.basename(path), w, "x", h, "|", t[:36])
    with open(os.path.join(OUT, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("total kept:", len(manifest))


if __name__ == "__main__":
    main()
