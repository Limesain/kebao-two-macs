#!/usr/bin/env python3
"""MiniMax T2A v2 配音：minimax_tts.py <text_file> <out.mp3> [voice_id] [speed]  （密钥只从环境变量读，不打印）"""
import os, sys, json, base64, urllib.request, pathlib
key = os.environ.get("MINIMAX_API_KEY") or sys.exit("MINIMAX_API_KEY missing")
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").strip(); out = sys.argv[2]
voice = sys.argv[3] if len(sys.argv) > 3 else "junlang_nanyou"; speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.15
gid = None
try:
    p = key.split(".")[1]; gid = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4))).get("GroupID")
except Exception: pass
body = {"model": "speech-2.8-hd", "text": text, "stream": False, "language_boost": "Chinese",
        "voice_setting": {"voice_id": voice, "speed": speed, "vol": 1.0, "pitch": 1, "emotion": "calm"},
        "pronunciation_dict": {"tone": ["Iason/(aɪˈeɪsən)"]},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 2}}
hosts = [h for h in os.environ.get("MINIMAX_HOSTS", "https://api.minimaxi.com,https://api.minimax.io").split(",") if h]
last = None
for h in hosts:
    url = f"{h}/v1/t2a_v2" + (f"?GroupId={gid}" if gid else "")
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=120))
    except Exception as e:
        last = f"{h}: {e}"; print("fail", last); continue
    br = d.get("base_resp", {})
    if br.get("status_code") == 0 and d.get("data", {}).get("audio"):
        pathlib.Path(out).write_bytes(bytes.fromhex(d["data"]["audio"]))
        ei = d.get("extra_info", {}); print(f"ok host={h} voice={voice} speed={speed} audio_ms={ei.get('audio_length')} chars={ei.get('usage_characters')} trace={d.get('trace_id')} -> {out}"); sys.exit(0)
    last = f"{h}: {br}"; print("fail", last)
sys.exit(f"all hosts failed: {last}")
