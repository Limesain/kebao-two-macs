#!/bin/zsh
# 第二批下载（可独立运行，也会被 download-models.sh 末尾 source；幂等）
set -u
unset HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy  # 直连，经路由器透明代理
export HF_HUB_DISABLE_TELEMETRY=1
HF=/Users/iason/.local/bin/hf
ROOT=/Users/iason/Developer/python-ai-playground/DUAL-MAC-TEST-2026-10
LOG=$ROOT/logs/download-$(date +%Y%m%d).log
C=/Users/iason/ComfyUI-Shared/models
STAGE=$C/_hf_staging
mkdir -p "$STAGE" "$ROOT/logs"
log(){ echo "[$(date '+%F %T')] [extra] $*" >> "$LOG"; }
dl_file(){ local repo=$1 rpath=$2 tdir=$3 name=${4:-$(basename "$2")}
  if [ -s "$tdir/$name" ]; then log "SKIP  $tdir/$name 已存在"; return 0; fi
  log "START $repo :: $rpath"
  if "$HF" download "$repo" "$rpath" --local-dir "$STAGE/$repo" >> "$LOG" 2>&1; then
    mkdir -p "$tdir" && mv -f "$STAGE/$repo/$rpath" "$tdir/$name" && log "DONE  $tdir/$name ($(du -h "$tdir/$name" | cut -f1))"
  else log "FAIL  $repo :: $rpath"; fi; }

log "===== 第二批开始 ====="
# A) Qwen-Image-2.1（主机 bf16 / 笔记本 int8 / Turbo 两档 / 官方模板用的 PE 编码器）
Q=Comfy-Org/Qwen-Image-2.1
dl_file $Q vae/qwen_image_2.1_vae_bf16.safetensors "$C/vae"
dl_file $Q diffusion_models/qwen_image_2.1_bf16.safetensors "$C/diffusion_models"
dl_file $Q text_encoders/qwen3vl_8b_bf16.safetensors "$C/text_encoders"
dl_file $Q diffusion_models/qwen_image_2.1_turbo_bf16.safetensors "$C/diffusion_models"
dl_file $Q loras/qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors "$C/loras"
dl_file $Q diffusion_models/qwen_image_2.1_int8_convrot.safetensors "$C/diffusion_models"
dl_file $Q text_encoders/qwen3vl_8b_int8_convrot.safetensors "$C/text_encoders"
dl_file $Q diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors "$C/diffusion_models"
dl_file $Q text_encoders/qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors "$C/text_encoders"
# B) MiniMax H3 配件（VAE 两种精度、音频 VAE、Turbo LoRA）
H=Comfy-Org/MiniMax-H3
dl_file $H vae/minimax_h3_video_vae_fp16.safetensors "$C/vae"
dl_file $H vae/minimax_h3_video_vae_int8_convrot.safetensors "$C/vae"
dl_file $H vae/minimax_h3_audio_vae_fp32.safetensors "$C/vae"
dl_file $H loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors "$C/loras"
dl_file $H loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors "$C/loras"
# C) FastH3 8 步蒸馏版（官方模板 video_fastvideo_fasth3_t2v 用）
dl_file FastVideo/FastVideo-FastH3-Comfy diffusion_models/fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors "$C/diffusion_models"
# D) LTX-2.5 官方仓库是 gated（需 HF 账号点同意 + hf auth login）；有 token 才下，否则留提示
GEMMA_E2B="text_encoders/gemma4_e2b_it_int8_convrot.safetensors"
if "$HF" auth whoami >/dev/null 2>&1; then
  L=Lightricks/LTX-2.5
  dl_file $L vae/ltx-2.5-video-vae-bf16.safetensors "$C/vae"
  dl_file $L vae/ltx-2.5-audio-vae-bf16.safetensors "$C/vae"
  dl_file $L diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors "$C/diffusion_models"
  dl_file $L text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors "$C/text_encoders"
  dl_file $L latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors "$C/latent_upscale_models"
  dl_file $L latent_upscale_models/ltx-2.5-latent-temporal-upscaler-x2-bf16-1.0.safetensors "$C/latent_upscale_models"
  dl_file $L model_patches/ltx-2.5-duration-head-bf16.safetensors "$C/model_patches"
  [ -n "$GEMMA_E2B" ] && dl_file Comfy-Org/gemma-4 "$GEMMA_E2B" "$C/text_encoders"
else
  log "LTX-2.5 跳过：未登录 Hugging Face（需要在 huggingface.co/Lightricks/LTX-2.5 点同意后执行 hf auth login）"
fi
log "===== 第二批结束 ====="
