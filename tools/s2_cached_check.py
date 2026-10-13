#!/usr/bin/env python3
"""找出 wall_s 异常短（ComfyUI 缓存命中、计时失真）的本地 sidecar：s2_cached_check.py [阈值秒=6]"""
import json, pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent; th = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
for sub in ("images", "edits", "inpaint", "flipbook/local", "storyboard", "duel"):
    for j in sorted((R / "s2" / sub).glob("*.json")):
        if j.name.endswith(".api.json") or j.name.startswith("_"): continue
        d = json.load(open(j, encoding="utf-8"))
        if d.get("engine") != "upscale" and (d.get("wall_s") or 0) < th: print(f"{sub}/{j.stem}\t{d.get('wall_s')}s\t{d.get('engine')}\t{d.get('machine')}")
