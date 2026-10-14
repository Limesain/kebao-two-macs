#!/usr/bin/env python3
"""无头录制网页为视频（Playwright）。用法：
  record_page.py --url URL --out out.mp4 [--w 1920 --h 1080] [--max 300] [--fps 30] [--png first.png]
页面把 document.title 设为 DONE 表示完成；录完后用 ffmpeg 转成 H.264 mp4（高码率）。"""
import argparse, pathlib, subprocess, time, shutil, json, os
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/Users/iason/.cache/ms-playwright")
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser(); ap.add_argument('--url',required=True); ap.add_argument('--out',required=True); ap.add_argument('--w',type=int,default=1920); ap.add_argument('--h',type=int,default=1080)
ap.add_argument('--max',type=int,default=300); ap.add_argument('--tail',type=float,default=2.5); ap.add_argument('--log',default=None); ap.add_argument('--scale',type=int,default=1); ap.add_argument('--css',default=None)
a=ap.parse_args(); out=pathlib.Path(a.out); tmp=out.parent/('_rec_'+out.stem); tmp.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    # Playwright 的录像不会放大视口：要 4K 就把视口开到 w*scale，再用 CSS zoom 把 1920×1080 的页面放大 scale 倍
    ctx=b.new_context(viewport={'width':a.w*a.scale,'height':a.h*a.scale},device_scale_factor=1,record_video_dir=str(tmp),record_video_size={'width':a.w*a.scale,'height':a.h*a.scale})
    pg=ctx.new_page()
    if a.scale>1: pg.add_init_script("document.addEventListener('DOMContentLoaded',()=>{document.documentElement.style.zoom='%d';});" % a.scale)
    if a.css: pg.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const st=document.createElement('style'); st.textContent=%s; document.head.appendChild(st);});" % json.dumps(a.css))
    pg.goto(a.url); t0=time.time()
    while time.time()-t0<a.max:
        if pg.title()=='DONE': break
        time.sleep(0.5)
    time.sleep(a.tail)
    log=None
    try: log=pg.evaluate('window.__log||null')
    except Exception: pass
    ctx.close(); b.close()
webm=max(tmp.glob('*.webm'), key=lambda f: f.stat().st_size)  # 同名目录里可能残留被杀掉的 0 字节录像
subprocess.run(['ffmpeg','-v','error','-y','-i',str(webm),'-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p','-r','30','-movflags','+faststart',str(out)],check=True)
shutil.rmtree(tmp,ignore_errors=True)
dur=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(out)],capture_output=True,text=True).stdout.strip()
print(f"recorded {out} ({float(dur):.1f}s)")
if a.log and log is not None: pathlib.Path(a.log).write_text(json.dumps(log,ensure_ascii=False,indent=1)); print('log ->',a.log)
