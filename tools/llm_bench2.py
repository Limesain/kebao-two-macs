#!/usr/bin/env python3
"""S1 v2 基准（LM Studio 原生接口 /api/v1/chat）。记录完整参数与模型元数据。
用法：llm_bench2.py --machine studio|mbp --host H:P --model KEY --tests short,code,long50,long100,turns,sustain --ctx 65536 [--sustain-sec 180]
元数据：--meta '{"modelKey":...}'（由调用方从 `lms ps --json` 取得）。输出 data/s1v2/<machine>_<tag>.jsonl"""
import argparse, json, time, urllib.request, pathlib, statistics
R = pathlib.Path(__file__).resolve().parent.parent
PROMPTS = {
 "short": "用三句话解释：为什么统一内存让 Mac 适合在本地跑大语言模型？",
 "code":  "写一个 Python 函数，把一个目录里的截图按日期归档到子文件夹（形如 2026-10-13/），并给出用法示例。只给代码和一段简短说明。",
 "logic": "一个人是否能够同时拥有二伯和三叔？请先给出结论，再说明理由。",
 "long":  "下面是一份很长的文档。请用五句话概括它讲了什么，并指出一个你觉得最有意思的细节。\n\n",
}
TURNS = ["我想十二月去香港玩三天，主要想吃东西和逛街，帮我先列个大方向。",
         "第一天安排在尖沙咀和旺角，具体怎么走？",
         "我不吃辣，把你刚才提到的店里辣的去掉，再补两家。",
         "第二天想去离岛，南丫岛和长洲二选一，给我理由。",
         "把这三天压缩成一个表格，只要地点和时间段。",
         "最后用一句话总结这趟行程的风格。"]
ap = argparse.ArgumentParser(); ap.add_argument("--machine", required=True); ap.add_argument("--host", required=True); ap.add_argument("--model", required=True)
ap.add_argument("--tag", required=True); ap.add_argument("--tests", default="short,code"); ap.add_argument("--ctx", type=int, default=65536); ap.add_argument("--reasoning", default="off")
ap.add_argument("--meta", default="{}"); ap.add_argument("--sustain-sec", type=int, default=180); ap.add_argument("--temp", type=float, default=0.7); ap.add_argument("--doc", default="sanguo-120k")
a = ap.parse_args(); meta = json.loads(a.meta)
out = R/"data"/"s1v2"/f"{a.machine}_{a.tag}.jsonl"; out.parent.mkdir(parents=True, exist_ok=True)
def call(inp, max_out, prev=None, store=False):
    body = {"model": a.model, "input": inp, "context_length": a.ctx, "max_output_tokens": max_out, "temperature": a.temp, "store": store}
    if a.reasoning != "none": body["reasoning"] = a.reasoning
    if prev: body["previous_response_id"] = prev
    req = urllib.request.Request(f"http://{a.host}/api/v1/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time(); d = json.load(urllib.request.urlopen(req, timeout=3600)); wall = time.time()-t0
    text = "".join(o.get("content","") for o in d.get("output",[]) if o.get("type")=="message")
    return d.get("stats") or {}, wall, text, d.get("response_id")
def rec(test, run, st, wall, extra=None, text=""):
    r = {"ts": time.strftime("%F %T"), "machine": a.machine, "model": a.model, "meta": meta, "params": {"ctx": a.ctx, "temperature": a.temp, "reasoning": a.reasoning},
         "test": test, "run": run, "tps": st.get("tokens_per_second"), "ttft_s": st.get("time_to_first_token_seconds"), "in_tok": st.get("input_tokens"),
         "out_tok": st.get("total_output_tokens"), "reason_tok": st.get("reasoning_output_tokens"), "wall_s": round(wall,2), "answer_head": text.strip()[:160]}
    if extra: r.update(extra)
    out.open("a").write(json.dumps(r, ensure_ascii=False)+"\n")
    print(f"[{a.machine}/{a.tag}] {test} r{run}: {r['tps'] and round(r['tps'],1)} t/s | ttft {r['ttft_s']} | in {r['in_tok']} out {r['out_tok']} | wall {r['wall_s']}s" + (f" | {extra}" if extra else ""), flush=True)
tests = a.tests.split(",")
if "short" in tests:
    for i in range(3): st,w,t,_ = call(PROMPTS["short"], 300); rec("short", i+1, st, w, text=t)
if "logic" in tests:
    st,w,t,_ = call(PROMPTS["logic"], 600 if a.reasoning in ("off","none") else 3000); rec("logic", 1, st, w, {"reasoning": a.reasoning, "answer_full": t.strip()}, t); print("   >>", t.strip()[:300].replace("\n"," "), flush=True)
if "code" in tests:
    st,w,t,_ = call(PROMPTS["code"], 700); rec("code", 1, st, w, text=t)
if "long50" in tests:
    doc = (R/"assets/text/honglou-60k.txt").read_text(encoding="utf-8"); st,w,t,_ = call(PROMPTS["long"]+doc, 400); rec("long50", 1, st, w, {"doc":"honglou-60k"}, t)
if "long100" in tests:
    doc = (R/f"assets/text/{a.doc}.txt").read_text(encoding="utf-8"); st,w,t,_ = call(PROMPTS["long"]+doc, 400); rec("long100", 1, st, w, {"doc":a.doc}, t)
if "turns" in tests:
    prev = None
    for k, p in enumerate(TURNS):
        st,w,t,rid = call(p, 500, prev, store=True); rec("turns", k+1, st, w, {"turn": k+1, "ctx_in": st.get("input_tokens")}, t); prev = rid
if "sustain" in tests:
    t_end = time.time()+a.sustain_sec; k = 0
    while time.time() < t_end:
        k += 1; st,w,t,_ = call(PROMPTS["code"], 600); rec("sustain", k, st, w, {"t_offset_s": round(a.sustain_sec-(t_end-time.time()),1)}, t)
print("done", out)
