#!/usr/bin/env python3
"""鹈鹕骑自行车 SVG（本地模型，LM Studio 原生接口）：pelican.py --host H:P --model KEY --name 名 --out 目录 [--reasoning off|low|medium|none] [--temp 0.7]"""
import argparse, json, re, time, urllib.request, pathlib
ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); ap.add_argument("--model", required=True); ap.add_argument("--name", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--reasoning", default="off"); ap.add_argument("--temp", type=float, default=0.7); ap.add_argument("--max", type=int, default=4000); a = ap.parse_args()
PROMPT = "Generate an SVG of a pelican riding a bicycle. Output only the SVG code, nothing else."
body = {"model": a.model, "input": PROMPT, "context_length": 16384, "max_output_tokens": a.max, "temperature": a.temp, "store": False}
if a.reasoning != "none": body["reasoning"] = a.reasoning
req = urllib.request.Request(f"http://{a.host}/api/v1/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
t0 = time.time(); d = json.load(urllib.request.urlopen(req, timeout=3600)); wall = time.time() - t0
text = "".join(o.get("content", "") for o in d.get("output", []) if o.get("type") == "message")
m = re.search(r"<svg[\s\S]*?</svg>", text); svg = m.group(0) if m else ""
out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
(out / f"{a.name}.svg").write_text(svg or text, encoding="utf-8")
st = d.get("stats") or {}
rec = {"name": a.name, "model": a.model, "reasoning": a.reasoning, "temp": a.temp, "wall_s": round(wall, 1), "tps": st.get("tokens_per_second"), "ttft_s": st.get("time_to_first_token_seconds"), "out_tok": st.get("total_output_tokens"), "reason_tok": st.get("reasoning_output_tokens"), "svg_ok": bool(m), "svg_bytes": len(svg), "prompt": PROMPT}
(out / f"{a.name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8"); print(json.dumps(rec, ensure_ascii=False))
