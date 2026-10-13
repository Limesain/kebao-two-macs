#!/bin/zsh
set -u
R=/Users/iason/Developer/python-ai-playground/DUAL-MAC-TEST-2026-10; B="/opt/homebrew/bin/python3 -I $R/scripts/llm_bench.py"
LOG=$R/logs/s1-mbp.log; DOC=$R/assets/text/honglou-60k.txt; H="$(/usr/bin/ssh -o BatchMode=yes -F /Users/iason/.ssh/config mbp ipconfig getifaddr bridge0):1234"
SSH="/usr/bin/ssh -o BatchMode=yes -o ConnectTimeout=10 -F /Users/iason/.ssh/config mbp"; LMS='/Users/iason/.lmstudio/bin/lms'
log(){ echo "[$(/bin/date '+%T')] $*" >> "$LOG"; }
export HOME=/Users/iason; unset HTTPS_PROXY HTTP_PROXY ALL_PROXY
log "== S1 MBP start =="; ${=SSH} "$LMS unload --all" >> "$LOG" 2>&1
run(){ local key=$1 tag=$2 ctx=$3; log "load $key ctx=$ctx"; ${=SSH} "$LMS load $key --context-length $ctx --gpu max --identifier bench -y" >> "$LOG" 2>&1 || { log "LOAD FAIL $key"; return 1; }
  ${=SSH} "$LMS ps" >> "$LOG" 2>&1
  ${=B} --host $H --model bench --label mbp_$tag --machine mbp --prompt-set short --repeat 3 --ctx $ctx >> "$LOG" 2>&1
  ${=B} --host $H --model bench --label mbp_$tag --machine mbp --prompt-set medium --max-out 700 --ctx $ctx >> "$LOG" 2>&1
  return 0; }
run qwen/qwen3.5-9b 9b 32768; ${=SSH} "$LMS unload --all" >> "$LOG" 2>&1
run qwen3.8-27b-mlx 27b 65536 && { ${=B} --host $H --model bench --label mbp_27b --machine mbp --prompt-set short --reasoning low --max-out 1500 --ctx 65536 --note "thinking=low" >> "$LOG" 2>&1; ${=B} --host $H --model bench --label mbp_27b --machine mbp --prompt-set long --doc "$DOC" --max-out 400 --ctx 65536 --note "honglou-60k" >> "$LOG" 2>&1; }; ${=SSH} "$LMS unload --all" >> "$LOG" 2>&1
log "try load gpt-oss-120b on MBP (expect guardrail refusal)"; ${=SSH} "$LMS load gpt-oss-120b --gpu max --identifier bench -y" >> "$LOG" 2>&1; log "gpt-oss load exit=$?"; ${=SSH} "$LMS ps; $LMS unload --all" >> "$LOG" 2>&1
log "== S1 MBP done =="
