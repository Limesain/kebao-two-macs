#!/usr/bin/env python3
"""汇总 data/s1v2/*.jsonl → data/s1v2/summary.md + summary.json"""
import json, glob, pathlib, statistics as st, collections
R = pathlib.Path(__file__).resolve().parent.parent; D = R/"data/s1v2"
rows=[]
for f in sorted(D.glob("*.jsonl")):
    for l in open(f,encoding="utf-8"):
        if l.strip(): r=json.loads(l); r["src"]=f.stem; rows.append(r)
def name(r): m=r.get("meta") or {}; q=(m.get("quantization") or {}).get("name") if isinstance(m.get("quantization"),dict) else m.get("quantization"); return f"{m.get('path') or r['model']} ({q})"
groups=collections.defaultdict(list)
for r in rows:
    if r.get("tps") is None: continue
    groups[(r["machine"], name(r), r["test"], r.get("params",{}).get("reasoning"), r.get("doc",""), r["src"] if r["test"]=="sustain" else "")].append(r)
out=["| 机器 | 模型 | 测试 | 思考 | n | 出字 t/s | 首字 s | 输入 tok | 输出 tok | 墙钟 s |","|---|---|---|---|---|---|---|---|---|---|"]
summ=[]
order={"short":0,"code":1,"logic":2,"long50":3,"long100":4,"turns":5,"sustain":6}
for k in sorted(groups, key=lambda k:(k[0],k[1],order.get(k[2],9),k[3] or "",k[4])):
    g=groups[k]; tps=st.mean(x["tps"] for x in g); ttft=st.mean(x["ttft_s"] for x in g); wall=st.mean(x["wall_s"] for x in g)
    it=g[0]["in_tok"] if k[2] not in ("turns","sustain") else f"{g[0]['in_tok']}→{g[-1]['in_tok']}"; ot=round(st.mean(x["out_tok"] or 0 for x in g))
    label=k[2]+(f" · {k[4]}" if k[4] else "")+(f" · {k[5]}" if k[5] else "")
    out.append(f"| {'主机 M5 Ultra' if k[0]=='studio' else '笔记本 M5 Max'} | {k[1]} | {label} | {k[3]} | {len(g)} | {tps:.1f} | {ttft:.2f} | {it} | {ot} | {wall:.1f} |")
    summ.append({"machine":k[0],"model":k[1],"test":k[2],"reasoning":k[3],"doc":k[4],"src":k[5],"n":len(g),"tps":round(tps,2),"ttft":round(ttft,3),"wall":round(wall,2),"runs":[{kk:x.get(kk) for kk in ("run","tps","ttft_s","in_tok","out_tok","wall_s","turn","t_offset_s")} for x in g]})
md="# S1 v2 实测汇总（2026-10-13）\n\n"+"\n".join(out)+"\n\n## 逻辑题答案（前 400 字）\n"
for r in rows:
    if r["test"]=="logic": md+=f"\n### {('主机' if r['machine']=='studio' else '笔记本')} · {name(r)} · 思考={r.get('params',{}).get('reasoning')} · {r['tps'] and round(r['tps'],1)} t/s · {r['wall_s']} s\n{r['answer_head']}\n"
(D/"summary.md").write_text(md,encoding="utf-8"); (D/"summary.json").write_text(json.dumps(summ,ensure_ascii=False,indent=1),encoding="utf-8")
print(md[:3000])
