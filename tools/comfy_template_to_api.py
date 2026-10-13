#!/usr/bin/env python3
"""用 ComfyUI 前端把 UI 工作流转成 API prompt：comfy_template_to_api.py <ui.json> <out.api.json> [--server http://127.0.0.1:8199]"""
import sys, json, os, time
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/Users/iason/.cache/ms-playwright")
from playwright.sync_api import sync_playwright
src, out = sys.argv[1], sys.argv[2]; server = sys.argv[4] if len(sys.argv) > 4 else "http://127.0.0.1:8199"
ui = json.load(open(src, encoding="utf-8"))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1600, "height": 900}); pg.goto(server, wait_until="networkidle")
    pg.wait_for_function("() => window.app && window.app.graph", timeout=60000); time.sleep(1.5)
    api = pg.evaluate("""async (wf) => { await window.app.loadGraphData(wf); await new Promise(r=>setTimeout(r,1500)); const r = await window.app.graphToPrompt(); return r.output; }""", ui)
    b.close()
json.dump(api, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("api nodes:", len(api), "->", out); print(sorted(set(v["class_type"] for v in api.values())))
