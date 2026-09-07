# -*- coding: utf-8 -*-
"""V10: 下载真实模特样本图 + 校验 + 生成审阅拼图"""
import os
import concurrent.futures
import urllib.request
import ssl

ROOT = r"."
RAW = os.path.join(ROOT, "assets_v2", "refs_real")
TMP = os.path.join(ROOT, "_v10tmp")
os.makedirs(RAW, exist_ok=True)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def fetch(job):
    idx, url = job
    path = os.path.join(RAW, "cand_%03d.jpg" % idx)
    if os.path.exists(path):
        return (idx, "cached")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Referer": "https://image.baidu.com/"})
        with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
            data = r.read(15 * 1024 * 1024)
        if len(data) < 25_000:
            return (idx, "too_small_bytes")
        open(path, "wb").write(data)
        from PIL import Image
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            w, h = im.size
        os.remove(path) if (w < 480 or h < 700) else None
        if w < 480 or h < 700:
            return (idx, "rejected_%dx%d" % (w, h))
        return (idx, "ok_%dx%d" % (w, h))
    except Exception as e:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        return (idx, "fail:%s" % str(e)[:50])


def main():
    urls = [l.strip() for l in open(os.path.join(TMP, "refs_urls.txt"),
                                    encoding="utf-8") if l.strip()]
    jobs = list(enumerate(urls, 1))
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for idx, st in ex.map(fetch, jobs):
            results[idx] = st
    ok = sum(1 for v in results.values() if v.startswith(("ok", "cached")))
    print("kept:", ok, "/", len(urls))
    for idx in sorted(results):
        st = results[idx]
        if not st.startswith(("ok", "cached")):
            print("drop %03d %s" % (idx, st))

    # 审阅拼图: 每张缩略 240x340, 每页 5x6=30 张, 文件名标注
    from PIL import Image, ImageDraw
    files = sorted(f for f in os.listdir(RAW) if f.startswith("cand_"))
    TW, TH, COLS, ROWS = 240, 340, 5, 6
    per = COLS * ROWS
    for p in range((len(files) + per - 1) // per):
        sheet = Image.new("RGB", (COLS * TW + (COLS + 1) * 4,
                                  ROWS * TH + (ROWS + 1) * 22), "#222")
        d = ImageDraw.Draw(sheet)
        batch = files[p * per:(p + 1) * per]
        for i, f in enumerate(batch):
            im = Image.open(os.path.join(RAW, f)).convert("RGB")
            im.thumbnail((TW, TH))
            cx = (i % COLS) * TW + (i % COLS + 1) * 4
            cy = (i // COLS) * (TH + 22) + 22
            sheet.paste(im, (cx, cy))
            d.text((cx + 2, cy - 18), f.replace("cand_", "").replace(".jpg", ""),
                   fill="yellow")
        out = os.path.join(TMP, "sheet_%d.jpg" % (p + 1))
        sheet.save(out, quality=88)
        print("sheet:", out, len(batch))


if __name__ == "__main__":
    main()
