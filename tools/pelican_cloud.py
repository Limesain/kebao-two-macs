#!/usr/bin/env python3
"""云端鹈鹕：pelican_cloud.py deepseek|openai <name> <outdir>（密钥只从环境变量读）"""
import os, sys, json, re, time, urllib.request, pathlib
which, name, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
PROMPT = "Generate an SVG of a pelican riding a bicycle. Output only the SVG code, nothing else."
t0 = time.time()
if which.startswith("deepseek"):
    key = os.environ["DEEPSEEK_API_KEY"]; url = "https://api.deepseek.com/chat/completions"
    body = {"model": "deepseek-flash", "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 8000, "temperature": 0.7}
    if which == "deepseek-nothink": body["thinking"] = {"type": "disabled"}
    else: body["reasoning_effort"] = "low"; body["max_tokens"] = 16000
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}), timeout=600))
    text = d["choices"][0]["message"].get("content", "") or ""; usage = d.get("usage", {}); meta = {"model": d.get("model"), "usage": usage}
elif which == "xai":
    key = os.environ["XAI_API_KEY"]; url = "https://api.x.ai/v1/chat/completions"
    body = {"model": "grok-4.7", "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 8000, "temperature": 0.7}
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}), timeout=600))
    text = d["choices"][0]["message"].get("content", "") or ""; meta = {"model": d.get("model"), "usage": d.get("usage")}
else:
    key = os.environ["OPENAI_API_KEY"]; url = "https://api.openai.com/v1/responses"
    body = {"model": "gpt-6-astra", "input": PROMPT, "reasoning": {"effort": "medium"}, "max_output_tokens": 8000}
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}), timeout=600))
    text = "".join(c.get("text", "") for o in d.get("output", []) if o.get("type") == "message" for c in o.get("content", []) if c.get("type") == "output_text"); meta = {"model": d.get("model"), "usage": d.get("usage")}
wall = time.time() - t0
m = re.search(r"<svg[\s\S]*?</svg>", text); svg = m.group(0) if m else ""
(out / f"{name}.svg").write_text(svg or text, encoding="utf-8")
rec = {"name": name, "cloud": which, "wall_s": round(wall, 1), "svg_ok": bool(m), "svg_bytes": len(svg), **meta, "prompt": PROMPT}
(out / f"{name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8"); print(json.dumps(rec, ensure_ascii=False)[:400])
