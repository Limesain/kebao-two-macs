#!/usr/bin/env python3
"""网页截图：shot_page.py URL out.png [w h scale]"""
import sys, os
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/Users/iason/.cache/ms-playwright")
from playwright.sync_api import sync_playwright
url,out=sys.argv[1],sys.argv[2]; w=int(sys.argv[3]) if len(sys.argv)>3 else 1920; h=int(sys.argv[4]) if len(sys.argv)>4 else 1080; sc=int(sys.argv[5]) if len(sys.argv)>5 else 1
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':w,'height':h},device_scale_factor=sc); pg.goto(url); pg.wait_for_timeout(600); pg.screenshot(path=out); b.close()
print('shot ->',out)
