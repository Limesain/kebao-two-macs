#!/usr/bin/env python3
"""两机流水线推理（mlx-lm sharded_load + pipeline_group）。由 mlx.launch 启动，每个 rank 跑一份。
用法：mlx.launch --hostfile hosts.json --backend ring --python ~/.venvs/mlx/bin/python -- scripts/pipeline_gen.py --model <本地目录> --prompt "..." --max-tokens 300 [--split 20,16] [--log out.jsonl]
"""
import argparse, json, time, sys, os
import mlx.core as mx
from mlx_lm import stream_generate
from mlx_lm.utils import sharded_load

ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--prompt", default="用三句话介绍一下你自己。"); ap.add_argument("--max-tokens", type=int, default=300)
ap.add_argument("--split", default=None, help="每个 rank 的层数，逗号分隔（rank0 在后：rank0 拿最后的层）"); ap.add_argument("--log", default=None); ap.add_argument("--tag", default=""); ap.add_argument("--mode", default="pp", choices=["pp","tp"]); ap.add_argument("--stream", default=None, help="rank0 把实时状态写到这个 json（给 cluster.html 画面用）")
a = ap.parse_args()
group = mx.distributed.init(backend="ring" if os.environ.get("MLX_HOSTFILE") else "any")
rank, size = group.rank(), group.size()
t0 = time.time()
if a.split:
    # 自定义不均分：先 lazy 加载拿到层数，再按 split 切
    from mlx_lm.utils import load_model, load_tokenizer, _download
    from mlx.utils import tree_flatten
    split = [int(x) for x in a.split.split(",")]
    model_path = _download(a.model, allow_patterns=["*.json", "*.py", "tokenizer.model", "*.tiktoken", "*.txt", "*.jsonl", "*.jinja"])
    model, config = load_model(model_path, lazy=True, strict=False)
    tokenizer = load_tokenizer(model_path, {"trust_remote_code": True}, eos_token_ids=config.get("eos_token_id"))
    model.model.pipeline(group, split=split)
    mx.eval(model.parameters())
    mx.eval(mx.distributed.all_sum(mx.array(1.0), stream=mx.cpu))
elif a.mode == "tp":
    model, tokenizer = sharded_load(a.model, tensor_group=group)
else:
    model, tokenizer = sharded_load(a.model, pipeline_group=group)
load_s = time.time() - t0
mem = mx.get_active_memory() / 2**30
msgs = [{"role": "user", "content": a.prompt}]
prompt = tokenizer.apply_chat_template(msgs, add_generation_prompt=True)
sys.stderr.write(f"[rank {rank}/{size}] loaded in {load_s:.1f}s, active mem {mem:.1f} GiB, mode {a.mode} layers {getattr(getattr(model,'model',None),'start_idx',None)}-{getattr(getattr(model,'model',None),'end_idx',None)}\n"); sys.stderr.flush()
mems = mx.distributed.all_gather(mx.array([mem]), group=group); mx.eval(mems); mems = [round(float(x), 1) for x in mems.tolist()]
def emit(status, extra=None):
    if rank != 0 or not a.stream: return
    d = {"status": status, "mode": a.mode, "ranks": size, "mems": mems, "model": os.path.basename(a.model.rstrip("/")), "prompt": a.prompt, "text": text, "n": n, "t": round(time.time() - t1, 2), "ttft": first, "tag": a.tag}
    if extra: d.update(extra)
    tmp = a.stream + ".tmp"; open(tmp, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False)); os.replace(tmp, a.stream)
t1 = time.time(); first = None; n = 0; text = ""; emit("loaded")
for r in stream_generate(model, tokenizer, prompt, max_tokens=a.max_tokens):
    if first is None: first = time.time() - t1
    n += 1; text += r.text
    if rank == 0: print(r.text, end="", flush=True)
    if n % 2 == 0: emit("generating", {"tps": round((n - 1) / max(1e-6, time.time() - t1 - first), 1)})
wall = time.time() - t1
if rank == 0:
    print(); tps = (n - 1) / max(1e-6, wall - first)
    rec = {"tag": a.tag, "mode": a.mode, "model": a.model, "ranks": size, "split": a.split, "load_s": round(load_s, 1), "mem_rank0_GiB": round(mem, 1), "ttft_s": round(first, 3), "out_tok": n, "tps": round(tps, 2), "wall_s": round(wall, 2), "prompt": a.prompt, "answer": text}
    emit("done", {"tps": round(tps, 1), "wall": round(wall, 2)})
    print(json.dumps({k: v for k, v in rec.items() if k != "answer"}, ensure_ascii=False), file=sys.stderr)
    if a.log:
        with open(a.log, "a", encoding="utf-8") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
