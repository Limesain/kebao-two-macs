#!/usr/bin/env python3
"""本地出图（无头 ComfyUI API，只用标准库）
文生图   comfy_gen.py --engine zimage|qwen|qwen_turbo|krea2 --prompt "…" --name N [--w --h --seed --steps --enhance]
指令编辑 comfy_gen.py --engine qwen_edit --ref 图1.png [图2.png] --prompt "指令" --name N [--w --h]   # 输出尺寸 = 图1 缩放到 w×h
局部重绘 comfy_gen.py --engine zimage_inpaint --ref 原图.png --mask x,y,w,h（0–1 比例）--prompt "整图描述" --name N [--blur 24]
超分     comfy_gen.py --engine upscale --ref 原图.png --name N [--upscaler 4x-UltraSharp.pth] [--down 0.5]
通用     [--server http://127.0.0.1:8199] [--client-id ID] [--outdir s2/images] [--negative ""] [--unet 文件名]
产出：<outdir>/<name>.png + <name>.json（模型/量化/采样/步数/cfg/种子/尺寸/提示词/耗时/机器）+ <name>.api.json（实际提交的工作流）"""
import argparse, json, time, uuid, urllib.request, urllib.parse, pathlib, random, re, subprocess
R = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--engine", required=True); ap.add_argument("--prompt", default=""); ap.add_argument("--name", required=True)
ap.add_argument("--w", type=int, default=1024); ap.add_argument("--h", type=int, default=1024); ap.add_argument("--seed", type=int, default=None); ap.add_argument("--steps", type=int, default=None)
ap.add_argument("--enhance", action="store_true"); ap.add_argument("--client-id", default=None); ap.add_argument("--outdir", default="s2/images"); ap.add_argument("--server", default="http://127.0.0.1:8199"); ap.add_argument("--negative", default="")
ap.add_argument("--ref", nargs="*", default=[]); ap.add_argument("--mask", default=None); ap.add_argument("--blur", type=int, default=24); ap.add_argument("--upscaler", default="4x-UltraSharp.pth"); ap.add_argument("--down", type=float, default=None); ap.add_argument("--unet", default=None)
a = ap.parse_args(); seed = a.seed if a.seed is not None else random.randrange(1, 2**48)
host = urllib.parse.urlparse(a.server).hostname or ""; machine = "Mac Studio M5 Ultra 96GB" if host in ("127.0.0.1", "localhost") else "MacBook Pro M5 Max 48GB"
def load(name): return json.load(open(R / "s2/workflows" / name, encoding="utf-8"))
def find(g, cls): return [k for k, v in g.items() if v["class_type"] == cls]
def imsize(p):
    o = subprocess.check_output(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(p)]).decode()
    return int(re.search(r"pixelWidth: (\d+)", o).group(1)), int(re.search(r"pixelHeight: (\d+)", o).group(1))
def upload(p, sub="s2refs"):
    p = pathlib.Path(p); data = p.read_bytes(); b = uuid.uuid4().hex; mt = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{p.name}\"\r\nContent-Type: {mt}\r\n\r\n").encode() + data + (f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}\r\nContent-Disposition: form-data; name=\"subfolder\"\r\n\r\n{sub}\r\n--{b}--\r\n").encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"{a.server}/upload/image", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=300))
    return (r["subfolder"] + "/" if r.get("subfolder") else "") + r["name"]
meta = {}; pixels = a.w * a.h; new = iter(str(i) for i in range(9001, 9100))
if a.engine == "zimage":
    g = load("image_z_image_turbo.api.json"); k = find(g, "CLIPTextEncode")[0]; g[k]["inputs"]["text"] = a.prompt
    lat = find(g, "EmptySD3LatentImage")[0]; g[lat]["inputs"].update(width=a.w, height=a.h)
    ks = find(g, "KSampler")[0]; g[ks]["inputs"].update(seed=seed, steps=a.steps or 9)
    meta = {"model": "Z-Image Turbo", "file": g[find(g,"UNETLoader")[0]]["inputs"]["unet_name"], "quant": "bf16", "text_encoder": "qwen_3_4b", "shift": g[find(g,"ModelSamplingAuraFlow")[0]]["inputs"]["shift"]}
elif a.engine == "zimage_inpaint":
    g = load("image_z_image_turbo.api.json"); k = find(g, "CLIPTextEncode")[0]; g[k]["inputs"]["text"] = a.prompt
    W, H = imsize(a.ref[0]); pixels = W * H; fx, fy, fw, fh = map(float, a.mask.split(","))
    mx, my, mw, mh = int(W * fx), int(H * fy), max(8, int(W * fw)), max(8, int(H * fh))
    li = next(new); g[li] = {"class_type": "LoadImage", "inputs": {"image": upload(a.ref[0])}}
    vae = find(g, "VAELoader")[0]; ve = next(new); g[ve] = {"class_type": "VAEEncode", "inputs": {"pixels": [li, 0], "vae": [vae, 0]}}
    base = next(new); g[base] = {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": W, "height": H}}
    rect = next(new); g[rect] = {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": mw, "height": mh}}
    comp = next(new); g[comp] = {"class_type": "MaskComposite", "inputs": {"destination": [base, 0], "source": [rect, 0], "x": mx, "y": my, "operation": "add"}}
    m2i = next(new); g[m2i] = {"class_type": "MaskToImage", "inputs": {"mask": [comp, 0]}}
    prev = m2i  # ImageBlur 半径上限 31、sigma 上限 10：羽化宽度大于 31 时串联多遍
    for _ in range(max(1, -(-a.blur // 31))):
        bl = next(new); g[bl] = {"class_type": "ImageBlur", "inputs": {"image": [prev, 0], "blur_radius": min(31, a.blur), "sigma": min(10.0, max(1.0, a.blur / 2))}}; prev = bl
    i2m = next(new); g[i2m] = {"class_type": "ImageToMask", "inputs": {"image": [prev, 0], "channel": "red"}}
    if W * H > 2_500_000:  # MPS 上 VAEEncode 也有 INT_MAX 上限 → 分块编码
        g[ve] = {"class_type": "VAEEncodeTiled", "inputs": {"pixels": [li, 0], "vae": [vae, 0], "tile_size": 1024, "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}}
    nm = next(new); g[nm] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": [ve, 0], "mask": [i2m, 0]}}
    ks = find(g, "KSampler")[0]; g[ks]["inputs"].update(seed=seed, steps=a.steps or 9, latent_image=[nm, 0]); g.pop(find(g, "EmptySD3LatentImage")[0])
    vd = find(g, "VAEDecode")[0]; cm = next(new); g[cm] = {"class_type": "ImageCompositeMasked", "inputs": {"destination": [li, 0], "source": [vd, 0], "x": 0, "y": 0, "resize_source": False, "mask": [i2m, 0]}}
    for s in find(g, "SaveImage") + find(g, "SaveImageAdvanced"): g[s]["inputs"]["images"] = [cm, 0]
    meta = {"model": "Z-Image Turbo（局部重绘）", "file": g[find(g,"UNETLoader")[0]]["inputs"]["unet_name"], "quant": "bf16", "text_encoder": "qwen_3_4b", "ref": a.ref[0], "mask": a.mask, "mask_px": [mx, my, mw, mh], "mask_blur": a.blur, "method": "VAEEncode → SetLatentNoiseMask → KSampler(denoise 1.0) → ImageCompositeMasked"}
    a.w, a.h = W, H
elif a.engine in ("qwen", "qwen_turbo"):
    g = load("image_qwen_image_2_1_t2i.api.json")
    sw = find(g, "ComfySwitchNode")[0]; tg = find(g, "TextGenerate")[0]
    if a.enhance:
        g[sw]["inputs"]["switch"] = True; g[tg]["inputs"]["prompt"] = a.prompt; g[sw]["inputs"]["on_false"] = a.prompt
    else:
        g.pop(tg); [g.pop(k) for k in [k for k in find(g, "CLIPLoader") if "pe_" in g[k]["inputs"]["clip_name"]]]
        g[sw]["inputs"].update(switch=False, on_false=a.prompt, on_true=a.prompt)
    g.pop(find(g, "ResolutionSelector")[0]); lat = find(g, "EmptyLatentImage")[0]; g[lat]["inputs"].update(width=a.w, height=a.h)
    te = find(g, "TextEncodeQwenImage21")[0]; g[te]["inputs"].update(resolution=max(a.w, a.h), negative_prompt=a.negative)
    un = find(g, "UNETLoader")[0]; g[un]["inputs"]["unet_name"] = a.unet or ("qwen_image_2.1_turbo_bf16.safetensors" if a.engine == "qwen_turbo" else "qwen_image_2.1_bf16.safetensors")
    ks = find(g, "KSampler")[0]; g[ks]["inputs"].update(seed=seed, steps=a.steps or (8 if a.engine == "qwen_turbo" else 25))
    meta = {"model": "Qwen-Image 2.1" + (" Turbo" if a.engine == "qwen_turbo" else ""), "file": g[un]["inputs"]["unet_name"], "quant": "int8" if "int8" in g[un]["inputs"]["unet_name"] else "bf16", "text_encoder": "qwen3vl_8b_int8", "prompt_enhancer": a.enhance}
elif a.engine == "qwen_edit":
    g = load("image_qwen_image_2_1_image_edit.api.json")
    for cls in ("TextGenerate", "PrimitiveStringMultiline", "BatchImagesNode", "ImageCompare"):
        for k in find(g, cls): g.pop(k)
    [g.pop(k) for k in [k for k in find(g, "CLIPLoader") if "pe_" in g[k]["inputs"]["clip_name"]]]
    sw = [k for k in find(g, "ComfySwitchNode") if isinstance(g[k]["inputs"].get("on_false"), str)][0]; g[sw]["inputs"].update(switch=False, on_false=a.prompt, on_true=a.prompt)
    te = find(g, "TextEncodeQwenImage21")[0]; g[te]["inputs"]["negative_prompt"] = a.negative
    loads = sorted(find(g, "LoadImage")); names = [upload(p) for p in a.ref]
    g[loads[0]]["inputs"]["image"] = names[0]; sc = next(new); g[sc] = {"class_type": "ImageScale", "inputs": {"image": [loads[0], 0], "upscale_method": "lanczos", "width": a.w, "height": a.h, "crop": "center"}}; g[te]["inputs"]["images.image_1"] = [sc, 0]
    if len(names) > 1:
        g[loads[1]]["inputs"]["image"] = names[1]; sc2 = next(new); g[sc2] = {"class_type": "ImageScale", "inputs": {"image": [loads[1], 0], "upscale_method": "lanczos", "width": a.w, "height": a.h, "crop": "center"}}; g[te]["inputs"]["images.image_2"] = [sc2, 0]
    else:
        g.pop(loads[1]); g[te]["inputs"].pop("images.image_2", None)
    un = find(g, "UNETLoader")[0]; g[un]["inputs"]["unet_name"] = a.unet or "qwen_image_2.1_bf16.safetensors"
    ks = find(g, "KSampler")[0]; g[ks]["inputs"].update(seed=seed, steps=a.steps or 25)
    meta = {"model": "Qwen-Image 2.1（指令编辑）", "file": g[un]["inputs"]["unet_name"], "quant": "int8" if "int8" in g[un]["inputs"]["unet_name"] else "bf16", "text_encoder": "qwen3vl_8b_int8", "refs": a.ref}
elif a.engine == "krea2":
    g = load("image_krea2_turbo_t2i.api.json")
    ct = find(g, "CLIPTextEncode")[0]; g[ct]["inputs"]["text"] = a.prompt
    for cls in ("TextGenerate", "StringConcatenate", "PrimitiveStringMultiline", "PreviewAny", "ComfySwitchNode", "PrimitiveBoolean", "ResolutionSelector"):
        for k in find(g, cls): g.pop(k)
    lora = find(g, "LoraLoaderModelOnly")[0]; un = find(g, "UNETLoader")[0]; ks = find(g, "KSampler")[0]
    g[ks]["inputs"]["model"] = [un, 0]; g.pop(lora)
    g[un]["inputs"]["unet_name"] = a.unet or "krea2_turbo_bf16.safetensors"; cl = find(g, "CLIPLoader")[0]; g[cl]["inputs"]["clip_name"] = "qwen3vl_4b_heretic_int8convrot.safetensors"
    lat = find(g, "EmptyLatentImage")[0]; g[lat]["inputs"].update(width=a.w, height=a.h); g[ks]["inputs"].update(seed=seed, steps=a.steps or 8)
    meta = {"model": "Krea 2 Turbo", "file": g[un]["inputs"]["unet_name"], "quant": "bf16", "text_encoder": "qwen3vl_4b_heretic_int8"}
elif a.engine == "upscale":
    W, H = imsize(a.ref[0]); pixels = 0
    g = {"1": {"class_type": "LoadImage", "inputs": {"image": upload(a.ref[0])}}, "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": a.upscaler}},
         "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}}}
    last = "3"
    if a.down: g["4"] = {"class_type": "ImageScaleBy", "inputs": {"image": ["3", 0], "upscale_method": "lanczos", "scale_by": a.down}}; last = "4"
    g["5"] = {"class_type": "SaveImage", "inputs": {"images": [last, 0], "filename_prefix": "x"}}
    meta = {"model": f"超分 {a.upscaler}", "file": a.upscaler, "quant": "fp32", "ref": a.ref[0], "ref_size": [W, H], "down": a.down}
else: raise SystemExit("unknown engine")
# 大于 2.5 MP 时改用 VAEDecodeTiled（输入项按服务端 object_info 的默认值填）
if pixels > 2_500_000:
    info = json.load(urllib.request.urlopen(f"{a.server}/object_info/VAEDecodeTiled", timeout=30))["VAEDecodeTiled"]["input"]
    for k in find(g, "VAEDecode"):
        node = g[k]; node["class_type"] = "VAEDecodeTiled"
        for name, spec in info.get("required", {}).items():
            if name in ("samples", "vae"): continue
            node["inputs"][name] = (spec[1].get("default") if len(spec) > 1 and isinstance(spec[1], dict) else None)
        node["inputs"]["tile_size"] = 1024; node["inputs"]["overlap"] = 96
for k in find(g, "SaveImage") + find(g, "SaveImageAdvanced"): g[k]["inputs"]["filename_prefix"] = f"s2/{a.name}"
ksl = find(g, "KSampler"); ksi = g[ksl[0]]["inputs"] if ksl else {}
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
        st = h[pid].get("status", {})
        if st.get("status_str") == "error": raise SystemExit("comfy error: " + json.dumps(st, ensure_ascii=False)[:1500])
        outs = h[pid].get("outputs", {}); imgs = [im for o in outs.values() for im in o.get("images", []) if im.get("type", "output") == "output"]
        if imgs: break
wall = time.time() - t0; im = imgs[0]
q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
data = urllib.request.urlopen(f"{a.server}/view?{q}", timeout=600).read()
out = R / a.outdir; out.mkdir(parents=True, exist_ok=True); png = out / f"{a.name}.png"; png.write_bytes(data)
try: ow, oh = imsize(png)
except Exception: ow, oh = a.w, a.h
rec = {"name": a.name, "engine": a.engine, **meta, "sampler": ksi.get("sampler_name"), "scheduler": ksi.get("scheduler"), "steps": ksi.get("steps"), "cfg": ksi.get("cfg"), "seed": ksi.get("seed"), "denoise": ksi.get("denoise"), "width": ow, "height": oh, "prompt": a.prompt, "negative": a.negative, "wall_s": round(wall, 1), "machine": machine, "server": a.server, "when": time.strftime("%Y-%m-%d %H:%M:%S")}
(out / f"{a.name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8"); (out / f"{a.name}.api.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: rec[k] for k in ("name", "model", "steps", "seed", "width", "height", "wall_s", "machine")}, ensure_ascii=False))
