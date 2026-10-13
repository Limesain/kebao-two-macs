#!/usr/bin/env python3
"""OpenRouter 出图：or_image.py --model ID --prompt "..." --out name [--ar 16:9] [--res 2K] [--size WxH] [--ref img.png ...] [--outdir s2/cloud]
密钥只从 OPENROUTER_API_KEY 读；每次记录 usage.cost 到 sidecar json 与 s2/cloud/_spend.jsonl。"""
import os, sys, json, time, base64, argparse, urllib.request, pathlib
ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--prompt", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--ar", default=None); ap.add_argument("--res", default=None); ap.add_argument("--size", default=None); ap.add_argument("--ref", nargs="*", default=[]); ap.add_argument("--outdir", default="s2/cloud"); ap.add_argument("--quality", default=None); a = ap.parse_args()
key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("OPENROUTER_API_KEY missing")
body = {"model": a.model, "prompt": a.prompt, "n": 1, "output_format": "png"}
if a.ar: body["aspect_ratio"] = a.ar
if a.res: body["resolution"] = a.res
if a.size: body["size"] = a.size
if a.quality: body["quality"] = a.quality
if a.ref:
    refs = []
    for r in a.ref:
        b = pathlib.Path(r).read_bytes(); mt = "image/png" if r.lower().endswith(".png") else "image/jpeg"
        refs.append({"type": "image_url", "image_url": {"url": f"data:{mt};base64,{base64.b64encode(b).decode()}"}})
    body["input_references"] = refs
req = urllib.request.Request("https://openrouter.ai/api/v1/images", data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com/Limesain/kebao-two-macs", "X-Title": "kebao-two-macs"})
t0 = time.time()
try:
    d = json.load(urllib.request.urlopen(req, timeout=600))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read()[:500].decode(errors="replace")); sys.exit(1)
wall = time.time() - t0
out = pathlib.Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
imgs = d.get("data") or []
if not imgs: print("no image:", json.dumps(d)[:500]); sys.exit(1)
b64 = imgs[0].get("b64_json"); mt = imgs[0].get("media_type", "image/png"); ext = "png" if "png" in mt else ("jpg" if "jpe" in mt else "webp")
png = out / f"{a.out}.{ext}"; png.write_bytes(base64.b64decode(b64))
usage = d.get("usage") or {}; cost = usage.get("cost")
rec = {"name": a.out, "model": a.model, "provider": "openrouter", "prompt": a.prompt, "aspect_ratio": a.ar, "resolution": a.res, "size": a.size, "refs": a.ref, "wall_s": round(wall, 1), "cost_usd": cost, "usage": usage, "file": str(png), "when": time.strftime("%Y-%m-%d %H:%M:%S")}
(out / f"{a.out}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
with open(out / "_spend.jsonl", "a", encoding="utf-8") as f: f.write(json.dumps({"name": a.out, "model": a.model, "cost_usd": cost, "when": rec["when"]}, ensure_ascii=False) + "\n")
print(json.dumps({k: rec[k] for k in ("name", "model", "wall_s", "cost_usd", "file")}, ensure_ascii=False))
