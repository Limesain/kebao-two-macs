# 克宝接管两台 Mac · 测试材料全公开

> 一个 AI（克宝 = Claude Fable 5.1，思考强度最高）全程主导两台 Mac 的本地 AI 测试：测试它跑、画面它画、配音它配、视频它剪。主人 炘宝 @Iason 全程围观不出力。
> 视频系列：EP.01 大语言模型 · EP.02 出图 · EP.03 生成视频（抖音 / 哔哩哔哩）。这个仓库放的是所有能自取的东西：原始数据、脚本、提示词、工作流、卡片、SVG。

## 两台机器

| | Mac Studio（2026） | MacBook Pro 16 英寸（2026-06） |
|---|---|---|
| 芯片 | M5 Ultra · 36 核 CPU / 80 核 GPU | M5 Max · 18 核 CPU / 40 核 GPU |
| 统一内存 | 96 GB | 48 GB |
| 内存带宽（实测） | 约 1,050 GB/s | 约 550 GB/s |
| SSD 顺序读 / 写（实测） | 6.8 / 13.9 GB/s | 4.6 / 7.2 GB/s |
| 系统 | macOS 27.0.1 | macOS 27.0.1 |
| 连接 | 雷雳 5 直连（TCP 62 Gbit/s，实拷 2 GB/s） | 合盖、接电源、不睡眠 |

推理栈：LM Studio 0.4.26 · MLX engine 1.13.1 · mlx 0.32.3 · mlx-lm 0.32.0。

## EP.01 大语言模型 · 结果摘要（2026-10-13 实测）

| 测试 | Mac Studio | MacBook Pro |
|---|---|---|
| Qwen3.5-9B（MLX 8bit，10.5 GB）短问答 | 102 t/s | 60 t/s |
| Qwen3.8-27B（MLX 8bit，29.5 GB）短问答 | 32.2 t/s · 首字 0.12 s | 19.0 t/s · 首字 0.26 s |
| 27B 读《红楼梦》前九回 50,240 token | 36 s | 76 s |
| 27B 读 100K token | 86 s（《三国》100,693 token） | 221 s（《红楼梦》100,600 token；《三国》同长度两次 Metal 显存不足） |
| 27B 六轮对话首字（上下文到 2,658 token） | 0.07–0.45 s | 0.14–0.61 s |
| gpt-oss-120b（MXFP4，63.4 GB） | 108.6 t/s | LM Studio 拒绝加载（内存不足） |
| 两台一起跑 gpt-oss-120b（MLX 张量并行，ring over Thunderbolt Bridge） | 每台 30.1 GiB · 34–36 t/s · 首字 3.0 s | |
| 读长文时 GPU 峰值 | 268 W · 79 ℃ · 风扇 2500/3625 | 100 W · 101 ℃ · 之后降频到 605 MHz / 7 W |

一道中文题「一个人是否能够同时拥有二伯和三叔？」：本地三个模型四种设置 16 次作答 15 次「可以」；DeepSeek-V4.1-Flash 关思考「可以」、低档思考「看家规」；GPT-6 Astra「看家规」；正确答案是「不能」，判法见 `s1-llm/data/claude_logic.md`。

「画一只骑自行车的鹈鹕」：九家同题（本地五张 + DeepSeek + GPT-6 Astra + Grok-4.7 + 克宝手画），另有六家 SMIL 动画版，见 `s1-llm/pelican/`。

## 目录

- `s1-llm/data/` 每条请求的 JSONL（t/s、首字、token 数、模型元数据、参数）、功耗 / 温度 / 风扇 CSV、汇总表 `summary.md`、逻辑题全文与各家答案、硬件实测 JSON
- `s1-llm/pelican/` SVG 原文件（静态 + 动画）与渲染 PNG
- `s1-llm/cards/` 视频里的所有图卡（1920×1080 PNG）；`s1-llm/web/` 画这些卡片和图表的网页源码
- `s1-llm/script/` 解说稿与配音分段文案；`s1-llm/text/` 长文测试用的《红楼梦》《三国演义》节选（公版）
- `s2-image/` 出图提示词、ComfyUI 工作流（API 格式）、原图与每张图的参数 JSON（EP.02 更新中）
- `tools/` 全部脚本：LM Studio 基准（`llm_bench2.py`）、两机并联（`pipeline_gen.py`）、功耗 / 温度记录、硬件实测、鹈鹕、无头 ComfyUI 出图（`comfy_gen.py`）、OpenRouter 出图、Playwright 录屏与卡片渲染、ffmpeg 成片拼装（`assemble.py`）

## 怎么复现

1. LM Studio 开服务：`lms server start`，`lms load <model> --context-length 32768 --gpu max --identifier bench -y`
2. 跑基准：`python3 tools/llm_bench2.py --machine studio --host 127.0.0.1:1234 --model bench --tag 27b --tests short,code,logic,long50,turns,sustain --reasoning off`
3. 两机并联：两台同路径装 mlx 0.32.3 + mlx-lm，`mlx.launch --hostfile hosts.json --backend ring -- tools/pipeline_gen.py --mode tp --model <本地模型目录>`
4. 功耗 / 温度：`tools/powerlog.sh`（需要 powermetrics 的 sudo）、`tools/templog.sh`（读 Stats.app 自带的 smc 工具，不需要 sudo）

## 制作说明

- 画面：不操作任何 App 界面，数据全走接口，画面是自绘网页经 Playwright 无头录制
- 配音：MiniMax speech-2.8-hd（声线 junlang_nanyou，API）；配乐：MiniMax-Music3 在 Mac Studio 上用 mlx-audio 本地生成
- 视频成片与音频不在仓库里（体积与版权）；模型权重请去各自的 Hugging Face 仓库下载

## 许可

代码 MIT；数据、卡片、SVG 与提示词 CC BY 4.0（署名「克宝 / @Iason」即可）。
