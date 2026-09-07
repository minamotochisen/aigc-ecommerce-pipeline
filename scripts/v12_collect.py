# -*- coding: utf-8 -*-
"""V12: 必应搜集试产素材 → assets_v2/v12/
A) 中国脸模特锚定照候选 (棚拍全身正面实拍)
B) 温柔小众衬衫 + 素雅长裙 服装候选 (上身/平铺)
网络任务, 不占 GPU。"""
import json
import os
import re
import ssl
import urllib.parse
import urllib.request

ROOT = r"."
OUT = os.path.join(ROOT, "assets_v2", "v12")
os.makedirs(OUT, exist_ok=True)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

QUERIES = [
    # 模特锚定照候选
    ("model_cn", "中国 女模特 棚拍 全身 正面 实拍 简约",
     ["模特", "拍摄", "写真", "女装", "穿搭"]),
    ("model_cn2", "亚洲 女模特 影棚 全身站姿 电商 服装",
     ["模特", "棚拍", "影棚", "电商"]),
    ("model_cn3", "中国 女模特 全身 白衬衫 长裙 棚拍",
     ["模特", "衬衫", "长裙", "穿搭"]),
    # 衬衫候选 (温柔小众)
    ("blouse1", "温柔 飘带 衬衫 女 小众设计 上身",
     ["衬衫", "上衣", "温柔", "小众"]),
    ("blouse2", "奶杏色 荷叶边 衬衫 女 温柔 上身 实拍",
     ["衬衫", "上衣", "温柔"]),
    ("blouse3", "立领 长袖 衬衫 女 设计感 小众 穿搭",
     ["衬衫", "立领", "设计感"]),
    # 长裙候选 (素雅)
    ("skirt1", "素色 长裙 半身裙 女 温柔 鱼尾 上身",
     ["长裙", "半身裙", "裙"]),
    ("skirt2", "米色 长裙 女 优雅 全身 实拍 穿搭",
     ["长裙", "裙", "穿搭"]),
    ("set1", "衬衫 长裙 套装 女 温柔 全身 穿搭 实拍",
     ["衬衫", "长裙", "套装", "穿搭"]),
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
    if len(data) < 25_000:
        return False
    open(path, "wb").write(data)
    return True


def main():
    manifest = []
    seen = set()
    for tag, q, kws in QUERIES:
        try:
            results = bing_search(q)
        except Exception as e:
            print("search fail", tag, e)
            continue
        results = [(u, t) for u, t in results if keep_title(t, kws)]
        print("query", tag, "->", len(results), flush=True)
        ok = 0
        for u, t in results:
            if u in seen or ok >= 8:
                continue
            seen.add(u)
            idx = len(manifest) + 1
            path = os.path.join(OUT, "%s_%02d.jpg" % (tag, idx))
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
            if w < 500 or h < 600 or h / w > 2.6:
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            ok += 1
            manifest.append({"file": os.path.basename(path), "w": w, "h": h,
                             "tag": tag, "title": t[:60], "src": u})
            print("ok", os.path.basename(path), w, "x", h, "|", t[:36], flush=True)
    with open(os.path.join(OUT, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("total kept:", len(manifest))


if __name__ == "__main__":
    main()
