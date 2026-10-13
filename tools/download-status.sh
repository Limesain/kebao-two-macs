#!/bin/zsh
ROOT=/Users/iason/Developer/python-ai-playground/DUAL-MAC-TEST-2026-10
LOG=$(ls -t $ROOT/logs/download-*.log 2>/dev/null | head -1)
echo "日志: $LOG"; echo
grep -E 'START|DONE|SKIP|FAIL|=====|-----' "$LOG" | tail -25
echo; echo "正在下载的进程: $(pgrep -f 'download-(models|extra).sh' | wc -l | tr -d ' ') 个"
echo "staging 占用: $(du -sh /Users/iason/ComfyUI-Shared/models/_hf_staging 2>/dev/null | cut -f1)"
echo "LM Studio 目录: $(du -sh /Users/iason/.lmstudio/models/mlx-community 2>/dev/null | cut -f1)"
echo "HF 缓存: $(du -sh ~/.cache/huggingface/hub 2>/dev/null | cut -f1)"
