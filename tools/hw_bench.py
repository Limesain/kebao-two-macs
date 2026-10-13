#!/usr/bin/env python3
"""硬盘顺序读写 + 统一内存带宽（MLX GPU）实测：hw_bench.py [--gb 8] [--out json]"""
import os, time, json, argparse, fcntl, pathlib, platform, subprocess
ap = argparse.ArgumentParser(); ap.add_argument("--gb", type=int, default=8); ap.add_argument("--out", default=None); a = ap.parse_args()
res = {"host": platform.node(), "when": time.strftime("%Y-%m-%d %H:%M:%S")}
# --- SSD：F_NOCACHE 绕过页缓存，1 MiB 块顺序写/读 ---
path = pathlib.Path.home() / "_hwbench.tmp"; n = a.gb * 1024; buf = os.urandom(1 << 20)
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC); fcntl.fcntl(fd, fcntl.F_NOCACHE, 1)
t0 = time.time()
for _ in range(n): os.write(fd, buf)
os.fsync(fd); os.close(fd); tw = time.time() - t0
fd = os.open(path, os.O_RDONLY); fcntl.fcntl(fd, fcntl.F_NOCACHE, 1); t0 = time.time(); got = 0
while True:
    b = os.read(fd, 1 << 20)
    if not b: break
    got += len(b)
tr = time.time() - t0; os.close(fd); path.unlink(missing_ok=True)
res["ssd_write_MBps"] = round(n / tw, 0); res["ssd_read_MBps"] = round(got / 2**20 / tr, 0); res["ssd_test_GiB"] = a.gb
# --- 内存带宽：MLX GPU 上 2 GiB float32 数组复制（读 2 + 写 2 = 4 GiB/次），取最好一次 ---
import mlx.core as mx
x = mx.ones((512, 1024, 1024), dtype=mx.float32); mx.eval(x)   # 2 GiB
best = 0.0
for i in range(6):
    mx.synchronize(); t0 = time.time(); y = x * 1.0; mx.eval(y); mx.synchronize(); dt = time.time() - t0
    best = max(best, 4.0 / dt)   # GiB/s（读+写）
res["mem_bw_copy_GBps"] = round(best * 1.0737, 0)  # 换算成十进制 GB/s
# 只读带宽：求和
best = 0.0
for i in range(6):
    mx.synchronize(); t0 = time.time(); s = mx.sum(x); mx.eval(s); mx.synchronize(); dt = time.time() - t0
    best = max(best, 2.0 / dt)
res["mem_bw_read_GBps"] = round(best * 1.0737, 0)
res["chip"] = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
print(json.dumps(res, ensure_ascii=False))
if a.out: open(a.out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
