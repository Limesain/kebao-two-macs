#!/usr/bin/env python3
"""按 s2/prompts_full.json 生成各条线的任务行：s2_jobs.py studio|mbp|cloud
每行要么是 `gen …`（comfy_gen.py 参数）/ `run …`（or_image.py 参数），要么是 `REC mp4|client|title|spec|prompt`（给下一条 gen 配录屏）。"""
import json, sys, shlex, pathlib
R = pathlib.Path(__file__).resolve().parent.parent; d = json.load(open(R / "s2/prompts_full.json", encoding="utf-8")); lane = sys.argv[1]; SEED = 20261013
Q = shlex.quote; new = [t for t in d["themes"] if not t.get("done")]
STUDIO = "Mac Studio M5 Ultra 96 GB"; MBP = "MacBook Pro M5 Max 48 GB"
def gen(**kw):
    parts = ["gen"]
    for k, v in kw.items():
        if v is None or v is False: continue
        if isinstance(v, (list, tuple)): parts.append(f"--{k} " + " ".join(Q(str(x)) for x in v))
        elif v is True: parts.append(f"--{k}")
        else: parts.append(f"--{k} {Q(str(v))}")
    return " ".join(parts)
def rec(mp4, client, title, spec, prompt):
    if (R / mp4).exists(): return "# REC skipped (exists) " + mp4
    return "REC " + "|".join([mp4, client, title, spec, prompt.replace("|", "／")])
out = []
if lane == "studio":
    for t in new:
        if t["id"] == "city": out.append(rec("assets/captures/s2/live-city-qwen.mp4", "liveq", "Qwen-Image 2.1 · " + t["title"], f"qwen_image_2.1_bf16 · 14.2 GB · 文本编码器 qwen3vl_8b_int8 · 25 步 · cfg 1 · euler / simple · {t['w']}×{t['h']} · 种子 {SEED} · {STUDIO}", t["zh"]))
        out.append(gen(engine="qwen", prompt=t["zh"], name=f"{t['id']}_qwen", w=t["w"], h=t["h"], seed=SEED, outdir="s2/images"))
    fb = d["flipbook"]; W, H = fb["w"], fb["h"]
    out.append(gen(engine="qwen", prompt=fb["anchor_zh"], name="fb_00", w=W, h=H, seed=SEED, outdir="s2/flipbook/local"))
    for i, m in enumerate(fb["motions_zh"], 1):
        instr = fb["frame_instruction_zh"].format(motion=m)
        if i == 3: out.append(rec("assets/captures/s2/live-flipbook-03.mp4", "livefb", "Qwen-Image 2.1 指令编辑 · 逐帧动图 · 第 3 帧", f"qwen_image_2.1_bf16 · 参考=基准帧 · 25 步 · cfg 1 · {W}×{H} · 种子 {SEED} · {STUDIO}", instr))
        out.append(gen(engine="qwen_edit", ref=["s2/flipbook/local/fb_00.png"], prompt=instr, name=f"fb_{i:02d}", w=W, h=H, seed=SEED, outdir="s2/flipbook/local"))
    for e in d["edits"]:
        if e["id"] == "edit_poster": out.append(rec("assets/captures/s2/live-edit-poster.mp4", "livee", "Qwen-Image 2.1 指令编辑 · 改海报文字", f"qwen_image_2.1_bf16 · 图1=原海报 · 25 步 · cfg 1 · {e['w']}×{e['h']} · 种子 {SEED} · {STUDIO}", e["zh"]))
        out.append(gen(engine="qwen_edit", ref=[e["ref"]], prompt=e["zh"], name=e["id"], w=e["w"], h=e["h"], seed=SEED, outdir="s2/edits"))
    for p in d["inpaints"]: out.append(gen(engine="zimage_inpaint", ref=[p["ref"]], mask=p["mask"], prompt=p["zh"], name=p["id"], seed=SEED, outdir="s2/inpaint"))
    u = d["upscale"]
    out.append(gen(engine="zimage", prompt=u["zh"], name=u["base_id"], w=u["w"], h=u["h"], seed=SEED, outdir="s2/upscale"))
    out.append(gen(engine="upscale", ref=[f"s2/upscale/{u['base_id']}.png"], upscaler=u["model"], name=u["x4_id"], outdir="s2/upscale"))
    s = d["shots"]
    for i, sh in enumerate(s["list_zh"], 1): out.append(gen(engine="qwen_edit", ref=["s2/flipbook/local/fb_00.png"], prompt=s["instruction_zh"].format(shot=sh), name=f"shot_{i}_qwen", w=W, h=H, seed=SEED, outdir="s2/storyboard"))
elif lane == "mbp":
    for t in new:
        if t["id"] == "city": continue  # 两机同题那一张已经出了
        out.append(gen(engine="zimage", prompt=t["zh"], name=f"{t['id']}_zimage", w=t["w"], h=t["h"], seed=SEED, outdir="s2/images"))
    for t in new:
        if t["id"] == "anime": out.append(rec("assets/captures/s2/live-anime-krea2-mbp.mp4", "livek", "Krea 2 Turbo · " + t["title"] + " · 笔记本", f"krea2_turbo_bf16 · 26.3 GB · 文本编码器 qwen3vl_4b_heretic_int8 · 8 步 · cfg 1 · {t['w']}×{t['h']} · 种子 {SEED} · {MBP}", t["zh"]))
        out.append(gen(engine="krea2", prompt=t["zh"], name=f"{t['id']}_krea2", w=t["w"], h=t["h"], seed=SEED, outdir="s2/images"))
elif lane == "cloud":
    def run(**kw):
        parts = ["run"]
        for k, v in kw.items():
            if v is None: continue
            parts.append(f"--{k} " + (" ".join(Q(str(x)) for x in v) if isinstance(v, (list, tuple)) else Q(str(v))))
        return " ".join(parts)
    for t in new:
        out.append(run(model="bytedance-seed/seedream-5-0-pro", prompt=t["zh"], out=f"{t['id']}_seedream", ar=t["ar"], res="2K"))
        ar2 = {"4:5": "3:4"}.get(t["ar"], t["ar"])  # Grok / GPT-Image 不收 4:5
        out.append(run(model="x-ai/grok-imagine-image-2.0", prompt=t["en"], out=f"{t['id']}_grok", ar=ar2, res="2K", quality="medium"))
        out.append(run(model="openai/gpt-image-2.5-flare", prompt=t["en"], out=f"{t['id']}_gptimage", ar=ar2, quality="high"))
    fb = d["flipbook"]
    out.append(run(model="bytedance-seed/seedream-5-0-pro", prompt=fb["anchor_zh"], out="fb_00", ar="16:9", res="2K", outdir="s2/flipbook/seedream"))
    for i, m in enumerate(fb["motions_zh"][: fb["seedream_frames"]], 1):
        out.append("CHAIN " + str(i) + "|" + fb["frame_instruction_zh"].format(motion=m))
print("\n".join(out))
