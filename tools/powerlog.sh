#!/bin/zsh
# 功耗/温度压力记录：powerlog.sh <秒数> <输出csv>   每秒一行：ts,cpu_mW,gpu_mW,ane_mW,combined_mW,gpu_mhz,gpu_idle_pct,pressure
set -u; SEC=${1:-60}; OUT=${2:-/tmp/powerlog.csv}
echo "ts,cpu_mW,gpu_mW,ane_mW,combined_mW,gpu_mhz,gpu_idle_pct,pressure" > "$OUT"
sudo -n /usr/bin/powermetrics -i 1000 -n $SEC --samplers cpu_power,gpu_power,ane_power,thermal 2>/dev/null | /usr/bin/awk -v out="$OUT" '
/^\*\*\* Sampled/ { cpu=gpu=ane=comb=mhz=idle=""; pres=""; gpuseen=0 }
/^CPU Power:/ { cpu=$3 }
/^GPU Power:/ { if(!gpuseen){gpu=$3; gpuseen=1} }
/^ANE Power:/ { ane=$3 }
/^Combined Power/ { comb=$(NF-1) }
/^Current pressure level:/ { pres=$4 }
/^GPU HW active frequency:/ { mhz=$5 }
/^GPU idle residency:/ { idle=$4; sub("%","",idle); cmd="date +%H:%M:%S"; cmd | getline ts; close(cmd); print ts","cpu","gpu","ane","comb","mhz","idle","pres >> out; fflush(out) }'
