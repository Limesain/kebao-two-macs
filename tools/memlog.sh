#!/bin/zsh
# 内存记录：memlog.sh <秒数> <输出csv>   每秒一行：ts,comfy_rss_mb,free_mb,free_pct,swap_used_mb
set -u; SEC=${1:-60}; OUT=${2:-/tmp/memlog.csv}; echo "ts,comfy_rss_mb,free_mb,free_pct,swap_used_mb,wired_mb,compressed_mb" > "$OUT"
for ((i=0;i<SEC;i++)); do
  pid=$(pgrep -f "python3 -s main.py --port 8199" | head -1); rss=$(ps -o rss= -p ${pid:-0} 2>/dev/null | awk '{print int($1/1024)}'); free=$(vm_stat | awk '/Pages free/{f=$3} /Pages speculative/{s=$3} END{gsub(/\./,"",f);gsub(/\./,"",s); print int((f+s)*16384/1048576)}'); wired=$(vm_stat | awk '/Pages wired down/{w=$4} /Pages occupied by compressor/{c=$5} END{gsub(/\./,"",w);gsub(/\./,"",c); print int(w*16384/1048576)","int(c*16384/1048576)}')
  pf=$(memory_pressure 2>/dev/null | awk '/System-wide memory free percentage/{print $5}' | tr -d '%'); sw=$(sysctl -n vm.swapusage | awk '{print $6}' | tr -d 'M')
  echo "$(/bin/date +%H:%M:%S),${rss:-0},$free,${pf:-},${sw:-0},$wired" >> "$OUT"; sleep 1
done
