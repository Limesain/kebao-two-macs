#!/usr/bin/env python3
"""把目录里的 SVG 渲染成 PNG（Playwright）：svg_render.py <svgdir> <outdir> [w h]"""
import sys, os, pathlib
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/Users/iason/.cache/ms-playwright")
from playwright.sync_api import sync_playwright
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
w, h = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (800, 600)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
    for f in sorted(src.glob("*.svg")):
        svg = f.read_text(encoding="utf-8")
        if "<svg" not in svg: print("skip (no svg):", f.name); continue
        html = f"<!doctype html><html><head><meta charset='utf-8'><style>html,body{{margin:0;width:{w}px;height:{h}px;background:#f4f1ea;display:flex;align-items:center;justify-content:center;overflow:hidden}}svg{{max-width:{w-40}px;max-height:{h-40}px;width:auto;height:auto}}</style></head><body>{svg}</body></html>"
        pg.set_content(html); pg.wait_for_timeout(200); pg.screenshot(path=str(out / (f.stem + ".png"))); print("rendered", f.stem)
    b.close()
