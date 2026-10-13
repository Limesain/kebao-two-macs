#!/usr/bin/env python3
# 需要：PLAYWRIGHT_BROWSERS_PATH=/Users/iason/.cache/ms-playwright
"""把 assets/web/cards/*.html 渲染成 1080×1920 PNG 到 assets/cards/。用法：render_cards.py [name ...]"""
import sys, pathlib
from playwright.sync_api import sync_playwright
R = pathlib.Path(__file__).resolve().parent.parent
import os
src = R / os.environ.get("CARDS_SRC","assets/web/cards"); out = R / os.environ.get("CARDS_OUT","assets/cards"); out.mkdir(parents=True, exist_ok=True)
names = sys.argv[1:] or [p.stem for p in sorted(src.glob("*.html")) if not p.stem.startswith("_")]
with sync_playwright() as p:
    b = p.chromium.launch()
    W=int(os.environ.get("CARD_W",1080)); H=int(os.environ.get("CARD_H",1920)); S=int(os.environ.get("CARD_SCALE",1))
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=S)
    for n in names:
        pg.goto((src / f"{n}.html").as_uri()); pg.wait_for_timeout(300)
        pg.screenshot(path=str(out / f"{n}.png"), full_page=False)
        print("rendered", out / f"{n}.png")
    b.close()
