#!/usr/bin/env python3
"""本地出图（无头 ComfyUI API）：comfy_gen.py --engine zimage|qwen|qwen_turbo|krea2 --prompt "..." --name xxx [--w 2048 --h 1152] [--seed N] [--steps N] [--enhance] [--outdir s2/images] [--server http://127.0.0.1:8199]
产出：<outdir>/<name>.png + <name>.json（模型/量化/采样/步数/cfg/种子/尺寸/提示词/耗时/机器）+ <name>.api.json（实际提交的工作流）"""
import argparse, json, time, uuid, urllib.request, urllib.parse, pathlib, shutil, copy, platform, random
R = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--engine", required=True); ap.add_argument("--prompt", required=True); ap.add_argument("--name", required=True)
ap.add_argument("--w", type=int, default=1024); ap.add_argument("--h", type=int, default=1024); ap.add_argument("--seed", type=int, default=None); ap.add_argument("--steps", type=int, default=None)
ap.add_argument("--enhance", action="store_true"); ap.add_argument("--client-id", default=None); ap.add_argument("--outdir", default="s2/images"); ap.add_argument("--server", default="http://127.0.0.1:8199"); ap.add_argument("--negative", default="")
a = ap.parse_args(); seed = a.seed if a.seed is not None else random.randrange(1, 2**48)
def load(name): return json.load(open(R / "s2/workflows" / name, encoding="utf-8"))
def find(g, cls): return [k for k, v in g.items() if v["class_type"] == cls]
meta = {}
if a.engine == "zimage":
    g = load("image_z_image_turbo.api.json"); k = find(g, "CLIPTextEncode")[0]; g[k]["inputs"]["text"] = a.prompt
    lat = find(g, "EmptySD3LatentImage")[0]; g[lat]["inputs"].update(width=a.w, height=a.h)
    ks = find(g, "KSampler")[0]; g[ks]["inputs"].update(seed=seed, steps=a.steps or 9)
    meta = {"model": "Z-Image Turbo", "file": g[find(g,"UNETLoader")[0]]["inputs"]["unet_name"], "quant": "bf16", "text_encoder": "qwen_3_4b", "shift": g[find(g,"ModelSamplingAuraFlow")[0]]["inputs"]["shift"]}
elif a.engine in ("qwen", "qwen_turbo"):
    g = load("image_qwen_image_2_1_t2i.api.json")
    sw = find(g, "ComfySwitchNode")[0]; tg = find(g, "TextGenerate")[0]; pa = find(g, "PreviewAny")[0]
    if a.enhance:
        g[sw]["inputs"]["switch"] = True; g[tg]["inputs"]["prompt"] = a.prompt; g[sw]["inputs"]["on_false"] = a.prompt
    else:
        g.pop(tg)
        pe = [k for k in find(g, "CLIPLoader") if "pe_" in g[k]["inputs"]["clip_name"]]; [g.pop(k) for k in pe]
        g[sw]["inputs"].update(switch=False, on_false=a.prompt, on_true=a.prompt)
    rs = find(g, "ResolutionSelector")[0]; g.pop(rs); lat = find(g, "EmptyLatentImage")[0]; g[lat]["inputs"].update(width=a.w, height=a.h)
    te = find(g, "TextEncodeQwenImage21")[0]; g[te]["inputs"].update(resolution=max(a.w, a.h), negative_prompt=a.negative)
    un = find(g, "UNETLoader")[0]; g[un]["inputs"]["unet_name"] = "qwen_image_2.1_turbo_bf16.safetensors" if a.engine == "qwen_turbo" else "qwen_image_2.1_bf16.safetensors"
    ks = find(g, "KSampler")[0]; g[ks]["inputs"].update(seed=seed, steps=a.steps or (8 if a.engine == "qwen_turbo" else 25))
    meta = {"model": "Qwen-Image 2.1" + (" Turbo" if a.engine == "qwen_turbo" else ""), "file": g[un]["inputs"]["unet_name"], "quant": "bf16", "text_encoder": "qwen3vl_8b_int8", "prompt_enhancer": a.enhance}
elif a.engine == "krea2":
    g = load("image_krea2_turbo_t2i.api.json")
    # 去掉提示词改写与风格后缀、去掉缺失的 darkbrush LoRA，直接喂提示词
    ct = find(g, "CLIPTextEncode")[0]; g[ct]["inputs"]["text"] = a.prompt
    for cls in ("TextGenerate", "StringConcatenate", "PrimitiveStringMultiline", "PreviewAny", "ComfySwitchNode", "PrimitiveBoolean", "ResolutionSelector"):
        for k in find(g, cls): g.pop(k)
    lora = find(g, "LoraLoaderModelOnly")[0]; un = find(g, "UNETLoader")[0]; ks = find(g, "KSampler")[0]
    g[ks]["inputs"]["model"] = [un, 0]; g.pop(lora)
    g[un]["inputs"]["unet_name"] = "krea2_turbo_bf16.safetensors"; cl = find(g, "CLIPLoader")[0]; g[cl]["inputs"]["clip_name"] = "qwen3vl_4b_heretic_int8convrot.safetensors"
    lat = find(g, "EmptyLatentImage")[0]; g[lat]["inputs"].update(width=a.w, height=a.h); g[ks]["inputs"].update(seed=seed, steps=a.steps or 8)
    meta = {"model": "Krea 2 Turbo", "file": "krea2_turbo_bf16.safetensors", "quant": "bf16", "text_encoder": "qwen3vl_4b_heretic_int8"}
else: raise SystemExit("unknown engine")
# 大于 2.5 MP 时改用 VAEDecodeTiled（输入项按服务端 object_info 的默认值填）
if a.w * a.h > 2_500_000:
    info = json.load(urllib.request.urlopen(f"{a.server}/object_info/VAEDecodeTiled", timeout=30))["VAEDecodeTiled"]["input"]
    for k in find(g, "VAEDecode"):
        node = g[k]; node["class_type"] = "VAEDecodeTiled"
        for name, spec in info.get("required", {}).items():
            if name in ("samples", "vae"): continue
            node["inputs"][name] = (spec[1].get("default") if len(spec) > 1 and isinstance(spec[1], dict) else None)
        node["inputs"]["tile_size"] = 1024; node["inputs"]["overlap"] = 96
# 统一保存节点前缀
for k in find(g, "SaveImage") + find(g, "SaveImageAdvanced"): g[k]["inputs"]["filename_prefix"] = f"s2/{a.name}"
ks = find(g, "KSampler")[0]; ksi = g[ks]["inputs"]
cid = a.client_id or uuid.uuid4().hex; t0 = time.time()
try:
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"{a.server}/prompt", data=json.dumps({"prompt": g, "client_id": cid}).encode(), headers={"Content-Type": "application/json"}), timeout=60))
except urllib.error.HTTPError as e:
    body = e.read().decode(errors="replace")
    try:
        d = json.loads(body); msg = d.get("error", {}).get("message"); errs = {k: [(x.get("message"), x.get("details")) for x in v.get("errors", [])] for k, v in (d.get("node_errors") or {}).items()}
        raise SystemExit(f"submit {e.code}: {msg} | node_errors: {json.dumps(errs, ensure_ascii=False)[:1500]}")
    except SystemExit: raise
    except Exception: raise SystemExit(f"submit {e.code}: {body[:800]}")
if "prompt_id" not in r: raise SystemExit("submit failed: " + json.dumps(r)[:800])
pid = r["prompt_id"]
while True:
    time.sleep(1.0); h = json.load(urllib.request.urlopen(f"{a.server}/history/{pid}", timeout=30))
    if pid in h:
        st = h[pid].get("status", {}); 
        if st.get("status_str") == "error": raise SystemExit("comfy error: " + json.dumps(st)[:1200])
        outs = h[pid].get("outputs", {}); imgs = [im for o in outs.values() for im in o.get("images", [])]
        if imgs: break
wall = time.time() - t0; im = imgs[0]
q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
data = urllib.request.urlopen(f"{a.server}/view?{q}", timeout=120).read()
out = R / a.outdir; out.mkdir(parents=True, exist_ok=True); (out / f"{a.name}.png").write_bytes(data)
rec = {"name": a.name, "engine": a.engine, **meta, "sampler": ksi["sampler_name"], "scheduler": ksi["scheduler"], "steps": ksi["steps"], "cfg": ksi["cfg"], "seed": ksi["seed"], "width": a.w, "height": a.h, "prompt": a.prompt, "negative": a.negative, "wall_s": round(wall, 1), "machine": platform.node(), "server": a.server, "when": time.strftime("%Y-%m-%d %H:%M:%S")}
(out / f"{a.name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8"); (out / f"{a.name}.api.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: rec[k] for k in ("name", "model", "steps", "seed", "width", "height", "wall_s")}, ensure_ascii=False))
