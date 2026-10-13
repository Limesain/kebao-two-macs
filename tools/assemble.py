#!/usr/bin/env python3
"""把「场景 + 配音段」拼成成片（ffmpeg）：assemble.py <scenes.json> <out.mp4>
scenes.json: {"gap":0.45,"lead":0.35,"tail":0.7,"xfade":0.6,"scenes":[{"type":"video|image","src":"...","segs":["s0a"],"start":0,"speed":1.0,"hold":0}]}
配音段文件 assets/voice2/seg_<id>_000.wav，文案 script/S1-tts-segments.txt（字幕用）。"""
import json, subprocess, sys, pathlib, re
R = pathlib.Path(__file__).resolve().parent.parent
cfg = json.load(open(sys.argv[1], encoding="utf-8")); out = sys.argv[2]
GAP, LEAD, TAIL, XF = cfg.get("gap", .45), cfg.get("lead", .35), cfg.get("tail", .7), cfg.get("xfade", .6)
OW, OH = int(cfg.get("width", 1920)), int(cfg.get("height", 1080)); SUBSCALE = max(1, round(OW / 1920))
def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))
texts = {l.split("|", 1)[0]: l.split("|", 1)[1].strip() for l in open(R / cfg.get("segments", "script/S1-tts-segments.txt"), encoding="utf-8") if "|" in l and not l.startswith("#")}
seg_path = lambda s: R / cfg.get("voice_dir", "assets/voice2") / f"seg_{s}_000.wav"
# 时间轴：场景 k 的起点 = 前面场景时长之和 - k*XF
scenes = cfg["scenes"]; t = 0.0; audio = []; subs = []; sdur = []
for k, sc in enumerate(scenes):
    segs = sc.get("segs", []); d = LEAD
    for i, s in enumerate(segs):
        sd = dur(seg_path(s)); audio.append((t + d, seg_path(s)))
        # 字幕按句切分，时长按字数分配
        sents = []
        for x in [y for y in re.split(r"(?<=[。！？；])", texts[s]) if y.strip()]:
            if len(x) <= 30: sents.append(x); continue
            parts = [y for y in re.split(r"(?<=[，、：])", x) if y.strip()]; buf = ""
            for y in parts:
                if buf and len(buf) + len(y) > 26: sents.append(buf); buf = y
                else: buf += y
            if buf: sents.append(buf)
        n = sum(len(x) for x in sents); cur = t + d
        for x in sents:
            L = sd * len(x) / n; subs.append((cur, cur + L, x.strip())); cur += L
        d += sd + (GAP if i < len(segs) - 1 else 0)
    d += TAIL + sc.get("hold", 0); sdur.append(d); t += d - (XF if k < len(scenes) - 1 else 0)
total = t
starts = []; _t = 0.0
for k, sc in enumerate(scenes):
    starts.append(_t); _t += sdur[k] - (XF if k < len(scenes) - 1 else 0)
chap = [f"{int(st//60):02d}:{int(st%60):02d} {sc['label']}" for st, sc in zip(starts, scenes) if sc.get("label")]
pathlib.Path(out).with_suffix(".chapters.txt").write_text("\n".join(chap) + "\n", encoding="utf-8")
# 视频输入与滤镜
inputs = []; vf = []; 
for k, sc in enumerate(scenes):
    D = sdur[k]
    if sc["type"] == "image":
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{D:.3f}", "-i", str(R / sc["src"])]
        vf.append(f"[{k}:v]scale={OW}:{OH},fps=30,trim=duration={D:.3f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{k}]")
    else:
        src = R / sc["src"]; st = sc.get("start", 0); sp = sc.get("speed", 1.0); clip = (dur(src) - st) / sp
        inputs += ["-ss", f"{st}", "-i", str(src)]
        pad = max(0.0, D - clip + 0.05)
        vf.append(f"[{k}:v]setpts=PTS/{sp},scale={OW}:{OH},fps=30,tpad=stop_mode=clone:stop_duration={pad:.3f},trim=duration={D:.3f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{k}]")
# xfade 链
chain = "[v0]"; off = 0.0
for k in range(1, len(scenes)):
    off += sdur[k - 1] - XF
    vf.append(f"{chain}[v{k}]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}]"); chain = f"[x{k}]"
for _start, _p in audio: inputs += ["-i", str(_p)]
# 字幕：每句一张透明 PNG，按时间叠加
subdir = R / cfg.get("subs_dir", "assets/captures/v2/_subs"); cues = [{"i": i, "text": x} for i, (_, _, x) in enumerate(subs)]
(subdir.parent / "_cues.json").write_text(json.dumps(cues, ensure_ascii=False), encoding="utf-8")
subprocess.run(["/Users/iason/.local/share/uv/tools/playwright/bin/python", str(R / "scripts/sub_png.py"), str(subdir.parent / "_cues.json"), str(subdir), str(SUBSCALE)], check=True)
nsc = len(scenes); naud = len(audio)
for i, (a, b, _) in enumerate(subs):
    inputs += ["-loop", "1", "-framerate", "30", "-t", f"{b - a + 0.1:.3f}", "-i", str(subdir / f"cue_{i:03d}.png")]
    idx = nsc + naud + i; src = chain if i == 0 else f"[o{i-1}]"
    vf.append(f"[{idx}:v]setpts=PTS+{a:.3f}/TB[s{i}]"); vf.append(f"{src}[s{i}]overlay=eof_action=pass:enable='between(t,{a:.3f},{b:.3f})'[o{i}]")
chain = f"[o{len(subs)-1}]" if subs else chain
vf.append(f"{chain}copy[vout]")
# 音频：绝对位置 adelay + amix（音频输入已在字幕之前加入）
n0 = len(scenes); af = []
for j, (start, p) in enumerate(audio):
    af.append(f"[{n0 + j}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={int(start*1000)}|{int(start*1000)}[a{j}]")
music = cfg.get("music")
if music:
    mi = len(inputs) // 2  # placeholder, recomputed below
    inputs += ["-stream_loop", "-1", "-i", str(R / music)]
    midx = sum(1 for k in range(0, len(inputs)) if inputs[k] == "-i") - 1
    af.append("".join(f"[a{j}]" for j in range(len(audio))) + f"amix=inputs={len(audio)}:normalize=0:dropout_transition=0,volume={cfg.get('gain', 2.2)},alimiter=limit=0.95[voice]")
    mode = cfg.get("music_mode", "full")
    if mode == "transitions":
        # 只在转场与无解说段落响起：每个场景边界 ±1.2 s、无配音场景整段、片头片尾
        wins = []; st0 = 0.0
        for k, sc in enumerate(scenes):
            if k > 0: wins.append((st0 - 1.2, st0 + XF + 1.2))
            if not sc.get("segs"): wins.append((st0, st0 + sdur[k]))
            st0 += sdur[k] - (XF if k < len(scenes) - 1 else 0)
        if audio: wins.append((0.0, audio[0][0] + 0.3)); wins.append((total - 6.0, total))
        r = 0.8; terms = [f"min(max((t-{a:.3f})/{r},0),1)*min(max(({b:.3f}-t)/{r},0),1)" for a, b in wins]
        expr = terms[0]
        for tm in terms[1:]: expr = f"max({expr},{tm})"
        af.append(f"[{midx}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={total:.3f},volume={cfg.get('music_gain', 0.09)},volume='{expr}':eval=frame,afade=t=out:st={total-4:.3f}:d=4[bgm]")
    else:
        af.append(f"[{midx}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={total:.3f},volume={cfg.get('music_gain', 0.09)},afade=t=in:d=2.5,afade=t=out:st={total-4:.3f}:d=4[bgm]")
    af.append(f"[voice][bgm]amix=inputs=2:normalize=0:dropout_transition=0,apad=whole_dur={total:.3f},atrim=duration={total:.3f}[aout]")
else:
    af.append("".join(f"[a{j}]" for j in range(len(audio))) + f"amix=inputs={len(audio)}:normalize=0:dropout_transition=0,volume={cfg.get('gain', 2.2)},alimiter=limit=0.95,apad=whole_dur={total:.3f},atrim=duration={total:.3f}[aout]")
cmd = ["ffmpeg", "-y", "-v", "warning", "-nostats", *inputs, "-filter_complex", ";".join(vf + af), "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", cfg.get("preset", "medium"), "-crf", str(cfg.get("crf", 18)), "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", out]
print(f"scenes={len(scenes)} total={total:.1f}s subs={len(subs)}"); r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode: print("FFMPEG ERROR:", r.stderr[-3000:]); sys.exit(1)
print("wrote", out)
