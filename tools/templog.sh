#!/bin/zsh
# 温度/风扇记录（无需 root，读 Stats.app 自带的 smc 工具）：templog.sh <秒数> <输出csv>
# 每秒一行：ts,cpu_max,cpu_avg,gpu_max,gpu_avg,mem_max,fan0_rpm,fan1_rpm
#   cpu=Tp*（Stats 对 M5 的映射：CPU 核心） gpu=Tg*（GPU 核心） mem=Tm*（内存）
#   注：Tf?6 一组 86/93 ℃ 的键空载与满载读数完全不变，是常量（阈值类），不是传感器，已排除
set -u; SEC=${1:-60}; OUT=${2:-/tmp/templog.csv}; SMC=/Applications/Stats.app/Contents/Resources/smc
echo "ts,cpu_max,cpu_avg,gpu_max,gpu_avg,mem_max,fan0_rpm,fan1_rpm" > "$OUT"
for ((i=0;i<SEC;i++)); do
  T=$($SMC list -t 2>/dev/null | /usr/bin/awk '/^\[T/ {k=substr($1,2,4); v=$2+0; if (v<=0||v>150) next;
      if(k~/^Tp/){if(v>cm)cm=v; cs+=v; cn++} else if(k~/^Tg/){if(v>gm)gm=v; gs+=v; gn++} else if(k~/^Tm/){if(v>mm)mm=v}}
      END{printf "%.1f,%.1f,%.1f,%.1f,%.1f", cm, (cn?cs/cn:0), gm, (gn?gs/gn:0), mm}')
  F=$($SMC fans 2>/dev/null | /usr/bin/awk '/^Actual speed:/ {printf "%s%d", (n++?",":""), $3} END{for(;n<2;n++)printf "%s0",(n?",":"")}')
  echo "$(/bin/date +%H:%M:%S),$T,$F" >> "$OUT"; sleep 1
done
