#!/bin/zsh
# 主机 CPU 模式无头 ComfyUI（8201，只给 MPS 算坏的超分用）
cd /Users/iason/ComfyUI-Installs/Iason/ComfyUI && exec .venv/bin/python3 -s main.py --port 8201 --listen 127.0.0.1 --cpu --enable-cors-header --disable-auto-launch --extra-model-paths-config "/Users/iason/Library/Application Support/Comfy Desktop/instance-model-paths/inst-1783233783650.yaml" --input-directory /Users/iason/ComfyUI-Shared/input --output-directory /Users/iason/ComfyUI-Shared/output --user-directory /Users/iason/ComfyUI-Installs/Iason/ComfyUI/user
