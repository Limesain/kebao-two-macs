#!/bin/zsh
set -u
R=/Users/iason/Developer/python-ai-playground/DUAL-MAC-TEST-2026-10; LMS=/Users/iason/.lmstudio/bin/lms; B="/opt/homebrew/bin/python3 -I $R/scripts/llm_bench.py"
LOG=$R/logs/s1-studio.log; DOC=$R/assets/text/honglou-60k.txt; H=127.0.0.1:1234
log(){ echo "[$(/bin/date '+%T')] $*" >> "$LOG"; }
export HOME=/Users/iason; unset HTTPS_PROXY HTTP_PROXY ALL_PROXY
log "== S1 Studio start =="; $LMS server start --port 1234 >> "$LOG" 2>&1; $LMS unload --all >> "$LOG" 2>&1
run(){ local key=$1 tag=$2 ctx=$3; log "load $key ctx=$ctx"; $LMS load "$key" --context-length $ctx --gpu max --identifier bench -y >> "$LOG" 2>&1 || { log "LOAD FAIL $key"; return 1; }
  $LMS ps >> "$LOG" 2>&1
  ${=B} --host $H --model bench --label studio_$tag --machine studio --prompt-set short --repeat 3 --ctx $ctx >> "$LOG" 2>&1
  ${=B} --host $H --model bench --label studio_$tag --machine studio --prompt-set medium --max-out 700 --ctx $ctx >> "$LOG" 2>&1
  return 0; }
run qwen/qwen3.5-9b 9b 32768; $LMS unload --all >> "$LOG" 2>&1
run qwen/qwen3.8-27b 27b 65536 && { ${=B} --host $H --model bench --label studio_27b --machine studio --prompt-set short --reasoning low --max-out 1500 --ctx 65536 --note "thinking=low" >> "$LOG" 2>&1; ${=B} --host $H --model bench --label studio_27b --machine studio --prompt-set long --doc "$DOC" --max-out 400 --ctx 65536 --note "honglou-60k" >> "$LOG" 2>&1; }; $LMS unload --all >> "$LOG" 2>&1
run gpt-oss-120b 120b 32768; $LMS unload --all >> "$LOG" 2>&1
log "== S1 Studio done =="
