# -*- coding: utf-8 -*-
"""V5: 在作品集中插入 模特视频化 页(胶片条+说明), 重渲染 PDF"""
import os

from playwright.sync_api import sync_playwright
import fitz

ROOT = r"."
HTML = os.path.join(ROOT, 'portfolio_v2.html')
PDF = os.path.join(ROOT, '黄焙鑫-AIGC电商视觉作品集.pdf')

NEW_PAGE = '''<!-- P8 模特视频化 -->
<div class="page">
  <div class="head"><div class="no">04</div><div class="t">模特视频化</div>
    <div class="en">FASHION VIDEO</div></div>
  <div class="sub">换装静图 → Wan 2.2 I2V 图生视频 → <b>5 秒走秀视频</b>。静图管线与视频管线共用同一身份锚，图片与视频素材一键联动，<b>电商 AIGC 的下一战场</b>。</div>
  <img src="outputs_v2/plates/plate_video_strip.jpg" style="width:100%; display:block; border:1px solid var(--line);" alt="">
  <div style="height:4mm"></div>
  <div style="display:flex; gap:6mm;">
    <div class="card" style="flex:1; padding:8px 10px;">
      <div style="font-size:9.5px; font-weight:700; margin-bottom:1.5mm;">生成链路</div>
      <div style="font-size:8.5px; color:var(--muted); line-height:1.7;">Wan 2.2 TI2V 5B（阿里开源）· 704×1280 · 24fps · 图生视频。首帧为换装管线输出的静图，走秀动作由文本提示驱动。</div>
    </div>
    <div class="card" style="flex:1; padding:8px 10px;">
      <div style="font-size:9.5px; font-weight:700; margin-bottom:1.5mm;">交付形态</div>
      <div style="font-size:8.5px; color:var(--muted); line-height:1.7;">mp4 视频文件（随图片包交付）+ 关键帧条 + 预览 GIF。视频可直接用于详情页头图、短视频种草与直播轮播位。</div>
    </div>
  </div>
  <div class="pagefoot"><span>04 模特视频化</span><span>08</span></div>
</div>

<!-- P9 落地与合规 -->'''

with open(HTML, encoding='utf-8') as f:
    s = f.read()
if 'P8 模特视频化' not in s:
    anchor = '<!-- P9 落地与合规 -->'
    assert anchor in s
    s = s.replace(anchor, NEW_PAGE, 1)
    # 落地页编号 04 -> 05, 页脚同步
    s = s.replace('<div class="no">04</div><div class="t">落地与合规</div>',
                  '<div class="no">05</div><div class="t">落地与合规</div>')
    s = s.replace('<div class="pagefoot"><span>04 落地与合规</span><span>08</span></div>',
                  '<div class="pagefoot"><span>05 落地与合规</span><span>09</span></div>')
    # 视频化页页码 08
    s = s.replace('<div class="pagefoot"><span>04 模特视频化</span><span>08</span></div>',
                  '<div class="pagefoot"><span>04 模特视频化</span><span>08</span></div>')
    # 评测页页脚 08 保持, 落地页 09 保持
    open(HTML, 'w', encoding='utf-8').write(s)
    print('video page inserted')
else:
    print('already inserted')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 1200})
    page.goto("file:///" + HTML.replace("\\", "/"))
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    infos = page.evaluate("""() => Array.from(document.querySelectorAll('.page')).map((el, i) => ({
        i: i + 1, sw: el.scrollWidth, sh: el.scrollHeight, cw: el.clientWidth, ch: el.clientHeight }))""")
    bad = [x for x in infos if x["sw"] > x["cw"] + 1 or x["sh"] > x["ch"] + 1]
    print(["p%d:%s" % (x["i"], "OVER" if x in bad else "ok") for x in infos])
    if bad:
        raise SystemExit("overflow")
    page.pdf(path=PDF, width="210mm", height="297mm", print_background=True,
             prefer_css_page_size=True,
             margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    browser.close()

doc = fitz.open(PDF)
doc.set_metadata({'title': '黄焙鑫 · AIGC电商视觉作品集', 'author': '黄焙鑫',
                  'subject': 'AIGC 电商女装作品集：换装 / 场景重绘 / 动作裂变 / 光板净化 / 模特视频化 / 落地合规',
                  'creator': 'Z.ai'})
doc.save(PDF, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
d2 = fitz.open(PDF)
for i, page in enumerate(d2):
    pix = page.get_pixmap(dpi=150)
    pix.save(os.path.join(ROOT, '_judge2', f'page{i+1:02d}.png'))
print('rendered', d2.page_count, 'pages')
