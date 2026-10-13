#!/bin/zsh
# 模型下载队列（幂等：已存在的文件跳过；hf download 支持断点续传）。
# 用法：nohup zsh download-models.sh > /dev/null 2>&1 &   查看：zsh download-status.sh
set -u
unset HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy  # 直连，经路由器透明代理
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_DISABLE_TELEMETRY=1
[ -n "${HF_TOKEN:-}" ] && export HF_TOKEN
HF=/Users/iason/.local/bin/hf
ROOT=/Users/iason/Developer/python-ai-playground/DUAL-MAC-TEST-2026-10
LOG=$ROOT/logs/download-$(date +%Y%m%d).log
C=/Users/iason/ComfyUI-Shared/models
LM=/Users/iason/.lmstudio/models
STAGE=$C/_hf_staging
mkdir -p "$STAGE" "$ROOT/logs"
log(){ echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# 单文件 → 指定 Comfy 目录（扁平放置）
dl_file(){ # repo path target_dir [newname]
  local repo=$1 rpath=$2 tdir=$3 name=${4:-$(basename "$2")}
  if [ -s "$tdir/$name" ]; then log "SKIP  $tdir/$name 已存在"; return 0; fi
  log "START $repo :: $rpath"
  if "$HF" download "$repo" "$rpath" --local-dir "$STAGE/$repo" >> "$LOG" 2>&1; then
    mkdir -p "$tdir" && mv -f "$STAGE/$repo/$rpath" "$tdir/$name" && log "DONE  $tdir/$name ($(du -h "$tdir/$name" | cut -f1))"
  else
    log "FAIL  $repo :: $rpath（稍后重跑本脚本会续传）"
  fi
}
# 整仓 → 目录
dl_repo(){ # repo target_dir
  local repo=$1 tdir=$2
  if [ -f "$tdir/.download-complete" ]; then log "SKIP  $repo 已完整"; return 0; fi
  log "START repo $repo -> $tdir"
  if "$HF" download "$repo" --local-dir "$tdir" >> "$LOG" 2>&1; then touch "$tdir/.download-complete"; log "DONE  repo $repo ($(du -sh "$tdir" | cut -f1))"; else log "FAIL  repo $repo"; fi
}
# 整仓 → HF 缓存（mlx-audio 会自己找）
dl_cache(){ local repo=$1; log "START cache $repo"; if "$HF" download "$repo" >> "$LOG" 2>&1; then log "DONE  cache $repo"; else log "FAIL  cache $repo"; fi; }

log "===== 队列开始 ====="
# 1) 配音 / 字幕（小，先下）
dl_cache mlx-community/VoxCPM2-8bit
dl_cache mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit
dl_cache mlx-community/Qwen3-ASR-1.7B-8bit
dl_cache mlx-community/Qwen3-ForcedAligner-0.6B-8bit
# 2) Wan2.2 TI2V-5B（7 月同款三件，复跑对照）
dl_file Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors "$C/diffusion_models"
dl_file Comfy-Org/Wan_2.1_ComfyUI_repackaged  split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors "$C/text_encoders"
dl_file Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/vae/wan2.2_vae.safetensors "$C/vae"
# 3) MiniMax H3（ComfyUI 路线；pruned bf16 主用，int8 备用，编码器 int8）
dl_file Comfy-Org/MiniMax-H3 diffusion_models/minimax_h3_fl2va_pruned_bf16.safetensors "$C/diffusion_models"
dl_file Comfy-Org/MiniMax-H3 text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors "$C/text_encoders"
dl_file Comfy-Org/MiniMax-H3 diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors "$C/diffusion_models"
# 4) 只有主机能跑的那一档（LM Studio 目录，MLX）
dl_repo mlx-community/gpt-oss-120b-MXFP4-Q8 "$LM/mlx-community/gpt-oss-120b-MXFP4-Q8"
# 5) 两台并联才能跑的那一档
dl_repo mlx-community/Qwen3.8-Flash-Next-4bit "$LM/mlx-community/Qwen3.8-Flash-Next-4bit"
# 6) 追加段（由 download-extra.sh 写入后自动续跑）
[ -f "$ROOT/scripts/download-extra.sh" ] && { log "----- 追加段 -----"; source "$ROOT/scripts/download-extra.sh"; }
log "===== 队列结束 ====="
