#!/bin/zsh
ROOT=/Users/iason/Developer/python-ai-playground/DUAL-MAC-TEST-2026-10
for w in w1 w2 w3 w4; do
  st=$(launchctl print gui/$(id -u)/com.iason.dlq-$w 2>/dev/null | grep -E '^\s*state = ' | head -1 | sed 's/.*= //'); [ -z "$st" ] && st="未托管/已结束"
  echo "== $w [$st] =="; grep -E 'START|DONE|SKIP|FAIL|=====' "$ROOT/logs/worker-$w.log" 2>/dev/null | tail -3 | cut -c1-140
done
echo; echo "hf 进程: $(pgrep -f 'hf download' | wc -l | tr -d ' ')   staging: $(du -sh /Users/iason/ComfyUI-Shared/models/_hf_staging 2>/dev/null | cut -f1)   LM Studio/mlx-community: $(du -sh /Users/iason/.lmstudio/models/mlx-community 2>/dev/null | cut -f1)"
