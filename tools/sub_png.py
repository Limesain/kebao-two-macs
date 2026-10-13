#!/usr/bin/env python3
"""把字幕句子渲染成 1920×1080 透明 PNG：sub_png.py <cues.json> <outdir>   cues.json = [{"i":0,"text":"..."}, ...]"""
import sys, json, os, pathlib
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/Users/iason/.cache/ms-playwright")
from playwright.sync_api import sync_playwright
cues = json.load(open(sys.argv[1], encoding="utf-8")); out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
html = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:1920px;height:1080px;background:transparent;overflow:hidden}
.s{position:absolute;left:160px;right:160px;bottom:46px;text-align:center;font-family:"PingFang SC","Hiragino Sans GB",sans-serif;font-weight:300;font-size:36px;line-height:1.5;color:#ece7df;letter-spacing:.04em;text-shadow:0 2px 14px rgba(0,0,0,.85),0 0 2px rgba(0,0,0,.9)}
.s b{font-weight:300;color:#c8a96e}
</style></head><body><div class="s" id="s"></div></body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080}); pg.set_content(html)
    for c in cues:
        pg.evaluate("t => document.getElementById('s').innerHTML = t", c["text"])
        pg.screenshot(path=str(out / f"cue_{c['i']:03d}.png"), omit_background=True)
    b.close()
print("rendered", len(cues), "cues ->", out)
