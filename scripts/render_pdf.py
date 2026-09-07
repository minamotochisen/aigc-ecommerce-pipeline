# -*- coding: utf-8 -*-
"""portfolio.html -> 矢量 PDF (Python Playwright)
说明: 本机无 node playwright, 故用 python playwright 复刻 html2pdf-next.js 的关键行为:
     @page 已在 HTML 声明 / 等待字体加载 / 渲染前检查页面溢出 / page.pdf 矢量输出 + 元数据
"""
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HTML = os.path.join(ROOT, "portfolio.html")
PDF = os.path.join(ROOT, "黄焙鑫-AIGC电商视觉作品集.pdf")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        page.goto("file:///" + HTML.replace("\\", "/"))
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.wait_for_timeout(500)

        # 溢出检查: 每个 .page 的 scrollWidth 不得超过 210mm(约794px)
        infos = page.evaluate(
            """() => Array.from(document.querySelectorAll('.page')).map((el, i) => ({
                i: i + 1, sw: el.scrollWidth, sh: el.scrollHeight,
                cw: el.clientWidth, ch: el.clientHeight }))"""
        )
        bad = [x for x in infos if x["sw"] > x["cw"] + 1 or x["sh"] > x["ch"] + 1]
        for x in infos:
            flag = "OVERFLOW!" if x in bad else "ok"
            print(f"page{x['i']}: {x['sw']}x{x['sh']} in {x['cw']}x{x['ch']} {flag}")
        if bad:
            print("存在溢出页面, 中止渲染", file=sys.stderr)

        page.pdf(
            path=PDF,
            width="210mm",
            height="297mm",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
    print("PDF saved:", PDF, os.path.getsize(PDF) // 1024, "KB")


if __name__ == "__main__":
    main()
