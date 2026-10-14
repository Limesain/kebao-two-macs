#!/usr/bin/env python3
"""逐帧截图式录制（动画由页面的 window.__seek(t) 决定，保证 4K 下 30 fps 平滑）：
frames_page.py --url URL --out out.mp4 [--dur 秒] [--fps 30] [--w 1920 --h 1080 --scale 2]
页面需实现 window.__seek(t)（秒）并在就绪后设置 window.__ready=true；--dur 不给则读 window.__dur。"""
import argparse, pathlib, subprocess, shutil, os, time, json
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/Users/iason/.cache/ms-playwright")
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser(); ap.add_argument('--url',required=True); ap.add_argument('--out',required=True); ap.add_argument('--dur',type=float,default=None); ap.add_argument('--fps',type=int,default=30)
ap.add_argument('--w',type=int,default=1920); ap.add_argument('--h',type=int,default=1080); ap.add_argument('--scale',type=int,default=2); ap.add_argument('--css',default=None); a=ap.parse_args()
out=pathlib.Path(a.out); tmp=out.parent/('_frames_'+out.stem); shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir(parents=True)
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':a.w*a.scale,'height':a.h*a.scale},device_scale_factor=1); pg=ctx.new_page()
    if a.scale>1: pg.add_init_script("document.addEventListener('DOMContentLoaded',()=>{document.documentElement.style.zoom='%d';});" % a.scale)
    if a.css: pg.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const st=document.createElement('style'); st.textContent=%s; document.head.appendChild(st);});" % json.dumps(a.css))
    pg.goto(a.url); t0=time.time()
    while time.time()-t0<120 and not pg.evaluate('window.__ready===true'): time.sleep(0.2)
    dur=a.dur or float(pg.evaluate('window.__dur||10')); n=int(round(dur*a.fps))
    for i in range(n):
        pg.evaluate('t=>window.__seek(t)', i/a.fps); pg.screenshot(path=str(tmp/f'f{i:05d}.jpg'),type='jpeg',quality=93)
    b.close()
subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(a.fps),'-i',str(tmp/'f%05d.jpg'),'-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
shutil.rmtree(tmp,ignore_errors=True); print(f"frames {n} -> {out} ({dur:.1f}s)")
