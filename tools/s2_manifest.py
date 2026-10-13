#!/usr/bin/env python3
"""汇总 s2/ 下所有 sidecar JSON → s2/manifest.json（画廊/图表页读取）"""
import json, pathlib, time
R = pathlib.Path(__file__).resolve().parent.parent; d = json.load(open(R / "s2/prompts_full.json", encoding="utf-8"))
ENG = {"zimage": ("Z-Image Turbo", "local"), "qwen": ("Qwen-Image 2.1", "local"), "krea2": ("Krea 2 Turbo", "local"), "seedream": ("Seedream 5.0 Pro", "cloud"), "grok": ("Grok Imagine Image 2.0", "cloud"), "gptimage": ("GPT-Image 2.5 Flare", "cloud")}
items = []
for sub, kind in [("images", "t2i"), ("cloud", "cloud"), ("edits", "edit"), ("inpaint", "inpaint"), ("upscale", "upscale"), ("flipbook/local", "flipbook"), ("flipbook/seedream", "flipbook"), ("storyboard", "storyboard"), ("duel", "duel")]:
    for j in sorted((R / "s2" / sub).glob("*.json")):
        if j.name.startswith("_") or j.name.endswith(".api.json"): continue
        try: rec = json.load(open(j, encoding="utf-8"))
        except Exception: continue
        name = j.stem; img = next((p for p in [j.with_suffix(".png"), j.with_suffix(".jpg"), j.with_suffix(".webp")] if p.exists()), None)
        if not img: continue
        theme, eng = (name.rsplit("_", 1) + [""])[:2] if kind in ("t2i", "cloud") else (None, None)
        if kind == "cloud":
            m = rec.get("model", ""); eng = "seedream" if "seedream" in m else "grok" if "grok" in m else "gptimage" if "gpt-image" in m else eng
        label, where = ENG.get(eng, (rec.get("model", ""), "local" if kind != "cloud" else "cloud"))
        items.append({"name": name, "kind": kind, "theme": theme, "engine": eng, "model": label, "where": where, "file": str(img.relative_to(R)), "json": str(j.relative_to(R)), "wall_s": rec.get("wall_s"), "cost_usd": rec.get("cost_usd"), "width": rec.get("width"), "height": rec.get("height"), "steps": rec.get("steps"), "seed": rec.get("seed"), "machine": rec.get("machine"), "quant": rec.get("quant"), "model_file": rec.get("file") if kind != "cloud" else rec.get("model"), "prompt": rec.get("prompt")})
out = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "themes": d["themes"], "edits": d["edits"], "inpaints": d["inpaints"], "upscale": d["upscale"], "flipbook": {k: v for k, v in d["flipbook"].items() if k != "frame_instruction_en"}, "shots": d["shots"], "items": items}
(R / "s2/manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(items), "items")
