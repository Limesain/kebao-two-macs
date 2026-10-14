#!/usr/bin/env python3
"""从 data/s2/{power,temp,mem}_gen_studio.csv + s2/profile/*.json 算三模型的功耗/温度/内存峰值 → data/s2/profile_summary.json"""
import json, csv, pathlib, datetime as dt
R = pathlib.Path(__file__).resolve().parent.parent; D = R / "data/s2"
def rows(n): return list(csv.DictReader(open(D / n, encoding="utf-8")))
def sec(t): h, m, s = map(int, t.split(":")); return h * 3600 + m * 60 + s
pw, tp, mm = rows("power_gen_studio.csv"), rows("temp_gen_studio.csv"), rows("mem_gen_studio.csv")
models = {}; starts = []
for k in ("zimage", "krea2", "qwen"):
    j = R / f"s2/profile/profile_{k}.json"
    if not j.exists(): continue
    d = json.load(open(j)); end = sec(d["when"].split(" ")[1]); start = end - int(round(d["wall_s"])); starts.append(start)
    win = lambda rs: [r for r in rs if start <= sec(r["ts"]) <= end + 2]
    P, Tt, Mm = win(pw), win(tp), win(mm)
    gw = [float(r["gpu_mW"]) / 1000 for r in P if r["gpu_mW"]]; pk = [float(r["combined_mW"]) / 1000 for r in P if r["combined_mW"]]
    gt = [float(r["gpu_max"]) for r in Tt if r["gpu_max"] not in ("", "0.0")]; fan = [float(r["fan0_rpm"]) for r in Tt if r["fan0_rpm"]]
    wired = [(float(r["wired_mb"]) + float(r.get("compressed_mb") or 0)) / 1024 for r in Mm if r.get("wired_mb")]
    models[k] = {"start": dt.datetime.utcfromtimestamp(start).strftime("%H:%M:%S") if False else f"{start//3600:02d}:{start%3600//60:02d}:{start%60:02d}", "end": f"{end//3600:02d}:{end%3600//60:02d}:{end%60:02d}", "wall_s": d["wall_s"],
        "gpu_w_peak": round(max(gw), 0) if gw else None, "gpu_w_avg": round(sum(gw) / len(gw), 0) if gw else None, "pkg_w_peak": round(max(pk), 0) if pk else None,
        "gpu_temp_peak": round(max(gt), 0) if gt else None, "fan_peak": round(max(fan)) if fan else None, "wired_peak_gb": round(max(wired), 1) if wired else None}
idle = [r for r in mm if sec(r["ts"]) < min(starts) - 5][-60:] if starts else []
idle_gb = round(sum((float(r["wired_mb"]) + float(r.get("compressed_mb") or 0)) / 1024 for r in idle) / len(idle), 1) if idle else None
w0 = min(starts) - 8 if starts else 0; w1 = max(sec(m["end"]) for m in models.values()) + 8 if models else 0
out = {"window": {"start": f"{w0//3600:02d}:{w0%3600//60:02d}:{w0%60:02d}", "end": f"{w1//3600:02d}:{w1%3600//60:02d}:{w1%60:02d}"}, "idle_wired_gb": idle_gb, "models": models}
hi = max((m["wired_peak_gb"] or 0) for m in models.values()) if models else 0
out["verdict"] = f"三个模型里最吃内存的也只用到 <em>{hi:.0f} GB</em>，96 GB 里还剩 {96-hi:.0f} GB：出图的同时再跑一个 27B 的大语言模型（29.5 GB）绰绰有余。GPU 功耗峰值 {max((m['gpu_w_peak'] or 0) for m in models.values()):.0f} W、温度 {max((m['gpu_temp_peak'] or 0) for m in models.values()):.0f} ℃，风扇最高 {max((m['fan_peak'] or 0) for m in models.values())} rpm——桌上听不见。"
(D / "profile_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"); print(json.dumps(out, ensure_ascii=False)[:600])
