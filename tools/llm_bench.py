#!/usr/bin/env python3
"""LM Studio 原生接口基准：python3 llm_bench.py --host HOST --model KEY --label NAME [--prompt-set short|medium|long] [--reasoning off] [--ctx N] [--repeat 3] [--doc FILE]
每次请求记录 LM Studio 返回的 stats（tokens_per_second / time_to_first_token）与客户端墙钟时间，追加写入 data/s1/<label>.jsonl"""
import argparse, json, time, urllib.request, pathlib, sys
P = {
 "short":  "用三句话解释：为什么统一内存让 Mac 适合在本地跑大语言模型？",
 "medium": "写一个 Python 函数，把一个目录里的截图按日期归档到子文件夹（形如 2026-10-13/），并给出用法示例。只给代码和一段简短说明。",
 "long":   "下面是一份很长的文档。请用五句话概括它讲了什么，并指出一个你觉得最有意思的细节。\n\n",
}
ap = argparse.ArgumentParser()
ap.add_argument("--host", default="127.0.0.1:1234"); ap.add_argument("--model", required=True); ap.add_argument("--label", required=True)
ap.add_argument("--prompt-set", default="short"); ap.add_argument("--reasoning", default="off"); ap.add_argument("--ctx", type=int, default=32768)
ap.add_argument("--repeat", type=int, default=1); ap.add_argument("--max-out", type=int, default=300); ap.add_argument("--doc", default=None)
ap.add_argument("--machine", default="?"); ap.add_argument("--note", default="")
a = ap.parse_args()
out = pathlib.Path(__file__).resolve().parent.parent / "data" / "s1" / f"{a.label}.jsonl"; out.parent.mkdir(parents=True, exist_ok=True)
prompt = P[a.prompt_set]
if a.prompt_set == "long":
    prompt += pathlib.Path(a.doc).read_text(encoding="utf-8", errors="ignore")
for i in range(a.repeat):
    body = {"model": a.model, "input": prompt, "context_length": a.ctx, "max_output_tokens": a.max_out, "temperature": 0.7, "store": False}
    if a.reasoning != "none": body["reasoning"] = a.reasoning
    req = urllib.request.Request(f"http://{a.host}/api/v1/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=3600))
    except Exception as e:
        body = ""
        try: body = e.read().decode("utf-8", "ignore")[:400]
        except Exception: pass
        rec = {"label": a.label, "machine": a.machine, "model": a.model, "prompt_set": a.prompt_set, "run": i+1, "error": (str(e)+" "+body)[:600], "ts": time.strftime("%F %T")}
        out.open("a").write(json.dumps(rec, ensure_ascii=False)+"\n"); print(json.dumps(rec, ensure_ascii=False)); continue
    wall = time.time() - t0
    text = "".join(o.get("content","") for o in d.get("output",[]) if o.get("type")=="message")
    st = d.get("stats") or {}
    rec = {"label": a.label, "machine": a.machine, "model": a.model, "prompt_set": a.prompt_set, "reasoning": a.reasoning, "ctx": a.ctx, "run": i+1,
           "tps": st.get("tokens_per_second"), "ttft_s": st.get("time_to_first_token_seconds"), "in_tok": st.get("input_tokens"), "out_tok": st.get("output_tokens"),
           "wall_s": round(wall, 2), "stats_raw": st, "note": a.note, "ts": time.strftime("%F %T"), "answer_head": text.strip()[:160]}
    out.open("a").write(json.dumps(rec, ensure_ascii=False)+"\n")
    print(f"[{a.label}] run{i+1}: {rec['tps'] and round(rec['tps'],1)} t/s | TTFT {rec['ttft_s']} s | in {rec['in_tok']} out {rec['out_tok']} | wall {rec['wall_s']} s")
