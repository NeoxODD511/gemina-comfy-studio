# 🧩 推荐安装插件与扩展清单（Recommended Plugins）

> 本清单专为 **ODD 出图 · Studio（`gemina-comfy-studio`）** 以及 **Anima 二次元出图 / 6GB 显存轻量配置** 精选整理，由 **Antigravity（天才美少女 AIGC 设计师洁美奈 / Gemina）** 测试筛选。
>
> 💡 **小白提示**：基础出图（`server.py` + `web/index.html`）**零插件也能直接用**；以下插件按「强烈推荐 / 前端联动」和「进阶可选」分类，按需安装即可，切忌一次性装几十个大杂烩包导致依赖打架。

---

## ⭐ 一、与 ODD 前端深度联动的核心插件（强烈推荐）

| 插件名称 | 作用（人话版） | 联动 ODD 前端功能 | 仓库地址 |
| :--- | :--- | :--- | :--- |
| **ComfyUI-Impact-Pack** + **Impact-Subpack** | 全自动 **FaceDetailer 修脸**，画全身图、双人分区图时自动框出每张脸单独高清重绘，彻底告别糊脸/眼歪 | 右栏 **`✨ 自动修脸 (FaceDetailer)`** 开关 | [Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) · [Subpack](https://github.com/ltdrdata/ComfyUI-Impact-Subpack) |
| **ComfyUI-WD14-Tagger** | 本地离线反推参考图提示词，支持只抄服装与构图、自动剔除原图角色名 | 中栏 **`🖼️ 拖图反推`**（支持拖拽与 `Ctrl+V` 粘贴） | [ComfyUI-WD14-Tagger](https://github.com/pythongosssss/ComfyUI-WD14-Tagger) · [WD14 模型库](https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3) |
| **comfyui-pose-gallery** + **comfyui_controlnet_aux** | 1,439 张高清姿势原图包（~675 MB，288 组多视角）+ 动漫线稿提取，配合 Anima LLLite 精准锁姿势 | 左栏 **姿势图库** + 右栏 **`🕺 姿势图控图`** | [comfyui-pose-gallery](https://github.com/wangweihong/comfyui-pose-gallery) · [原图库 ai-pose-gallery-zh](https://github.com/wangweihong/ai-pose-gallery-zh) · [controlnet_aux](https://github.com/Fannovel16/comfyui_controlnet_aux) |

> **联动模型与素材直链**：
> - **自动修脸人脸模型（`face_yolov8m.pt`，~49.6 MB）**：放到 `<ComfyUI目录>\models\ultralytics\bbox\face_yolov8m.pt`  
>   直链：`https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt`
> - **WD14 反推模型（`wd-swinv2-tagger-v3`，~467 MB）**：放到 `<ComfyUI目录>\custom_nodes\ComfyUI-WD14-Tagger\models\`  
>   模型仓库：`https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3`（需下载 `model.onnx` → 改名 `wd-swinv2-tagger-v3.onnx`，以及 `selected_tags.csv` → 改名 `wd-swinv2-tagger-v3.csv`）
> - **姿势图原图包（~675 MB）**：随 [wangweihong/comfyui-pose-gallery](https://github.com/wangweihong/comfyui-pose-gallery) 仓库或上游 [wangweihong/ai-pose-gallery-zh](https://github.com/wangweihong/ai-pose-gallery-zh) 获取。

---

## ✨ 二、通用必备 & 轻量画质效率插件

| 插件名称 | 作用（人话版） | 显存开销 | 仓库地址 |
| :--- | :--- | :---: | :--- |
| **ComfyUI-Manager** | ComfyUI 插件大管家：一键安装缺失节点、统一更新插件，新手必备 | 极低 | [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager) |
| **ComfyUI-Detail-Daemon** | 细节恶魔：在采样中途微调噪声曲线，显著提升眼睛高光、发丝与布料细节 | 几乎为 0 | [ComfyUI-Detail-Daemon](https://github.com/Jonseed/ComfyUI-Detail-Daemon) |
| **rgthree-comfy** | 效率神装：单节点叠挂多个 LoRA（Power Lora Loader）、快捷开关组、工作流导航 | 极低 | [rgthree-comfy](https://github.com/rgthree/rgthree-comfy) |
| **ComfyUI-Easy-Use** | 简化常用节点连线，社区大量整合工作流的通用依赖 | 极低 | [ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use) |
| **ComfyUI-Custom-Scripts** | 原生界面增强（自动补全、图像对比、快捷菜单等） | 极低 | [ComfyUI-Custom-Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts) |

### 💾 三、按需选装（6GB 显存尝鲜超大底模）

- **ComfyUI-GGUF**（[city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF)）：如果你后续想玩 **Flux / Qwen-Image / Wan 视频** 等超大模型，装它就能直接跑 `Q4/Q6/Q8` 量化版（`.gguf`），6GB 显存也能流畅运行。

---

## 🚀 最简单安装方式（二选一）

### 方式 A：交给你的 AI Agent 全自动安装（推荐电脑小白）
把下面这段话直接发给你的 AI 助手（Antigravity / Claude Code / Cursor）：
```text
请按 https://github.com/NeoxODD511/gemina-comfy-studio 仓库里的 RECOMMENDED_PLUGINS.md，
帮我探测本机 ComfyUI 的 custom_nodes 和内置 Python，自动安装推荐的核心插件（Manager、Impact-Pack、Impact-Subpack、Detail-Daemon、rgthree-comfy），
装好缺失的 Python 依赖，并下载 face_yolov8m.pt 到 models/ultralytics/bbox/，最后重启 ComfyUI 验证节点加载正常。
```

### 方式 B：Windows PowerShell 一键安装脚本
把下面脚本里的 `F:\ComfyUI` 改成你电脑上实际的 ComfyUI 路径，在 PowerShell 中直接粘贴运行即可：

```powershell
$COMFY_ROOT = "F:\ComfyUI"
$PY = "$COMFY_ROOT\python_embeded\python.exe"
$NODES = "$COMFY_ROOT\ComfyUI\custom_nodes"
$BBOX = "$COMFY_ROOT\ComfyUI\models\ultralytics\bbox"

$repos = @(
  "https://github.com/ltdrdata/ComfyUI-Manager.git",
  "https://github.com/ltdrdata/ComfyUI-Impact-Pack.git",
  "https://github.com/ltdrdata/ComfyUI-Impact-Subpack.git",
  "https://github.com/Jonseed/ComfyUI-Detail-Daemon.git",
  "https://github.com/rgthree/rgthree-comfy.git"
)

foreach ($url in $repos) {
  $name = [IO.Path]::GetFileNameWithoutExtension($url)
  $dst = Join-Path $NODES $name
  if (!(Test-Path $dst)) {
    git clone --depth 1 $url $dst
  }
  $req = Join-Path $dst "requirements.txt"
  if (Test-Path $req) {
    & $PY -m pip install -r $req
  }
}

# 下载人脸检测模型（约 6MB），用于自动修脸 FaceDetailer
New-Item -ItemType Directory -Force -Path $BBOX | Out-Null
$yolo = Join-Path $BBOX "face_yolov8m.pt"
if (!(Test-Path $yolo)) {
  Invoke-WebRequest -Uri "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt" -OutFile $yolo
}
Write-Host "全部推荐插件安装完成！请重启 ComfyUI 即可生效。" -ForegroundColor Green
```

---

> ⚠️ **避坑提示**：
> - 安装 `Impact-Pack` / `Impact-Subpack` 时，请务必使用 **ComfyUI 自带的 `python_embeded\python.exe`** 执行 `pip install`，不要装到系统全局 Python 里；
> - 6GB 显存笔记本开启 **`✨ 自动修脸`** 时，建议先关掉二段高清精绘（HiRes Fix）或保持修脸重绘幅度 `0.35~0.45`，既稳又清晰！
