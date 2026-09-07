# -*- coding: utf-8 -*-
"""V13: 重渲染作品集 PDF(含视频章节), 溢出检查 + judge 评审页导出"""
import os

from playwright.sync_api import sync_playwright
import fitz

ROOT = r"."
HTML = os.path.join(ROOT, 'portfolio_v2.html')
PDF = os.path.join(ROOT, '黄焙鑫-AIGC电商视觉作品集.pdf')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 1200})
    page.goto("file:///" + HTML.replace("\\", "/"))
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    infos = page.evaluate("""() => Array.from(document.querySelectorAll('.page')).map((el, i) => ({
        i: i + 1, sw: el.scrollWidth, sh: el.scrollHeight, cw: el.clientWidth, ch: el.clientHeight }))""")
    bad = [x for x in infos if x["sw"] > x["cw"] + 1 or x["sh"] > x["ch"] + 1]
    print(["p%d:%s" % (x["i"], "OVER" if x in bad else "ok") for x in infos])
    if bad:
        raise SystemExit("overflow: " + str(bad))
    page.pdf(path=PDF, width="210mm", height="297mm", print_background=True,
             prefer_css_page_size=True,
             margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    browser.close()

doc = fitz.open(PDF)
doc.set_metadata({'title': '黄焙鑫 · AIGC电商视觉作品集', 'author': '黄焙鑫',
                  'subject': 'AIGC 电商女装作品集：换装 / 场景重绘 / 动作裂变 / 光板净化 / 技术评测 / AI视频生成 / 落地合规',
                  'creator': 'Z.ai'})
doc.save(PDF, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
d2 = fitz.open(PDF)
for i, page in enumerate(d2):
    pix = page.get_pixmap(dpi=150)
    pix.save(os.path.join(ROOT, '_judge2', f'page{i+1:02d}.png'))
print('rendered', d2.page_count, 'pages')
