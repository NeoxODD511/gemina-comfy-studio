# 🧩 推荐安装插件与扩展清单（Recommended Plugins）

> 本清单专为 **ODD 出图 · Studio（`gemina-comfy-studio`）** 以及 **Anima 二次元出图 / 6GB 显存轻量配置** 精选整理，由 **Antigravity（天才美少女 AIGC 设计师洁美奈 / Gemina）** 测试筛选。
>
> 💡 **小白提示**：基础出图（`server.py` + `web/index.html`）**零插件也能直接用**；以下插件按「强烈推荐 / 前端联动」和「进阶可选」分类，按需安装即可，切忌一次性装几十个大杂烩包导致依赖打架。

---

## ⭐ 一、与 ODD 前端深度联动的核心插件（强烈推荐）

| 插件名称 | 作用（人话版） | 联动 ODD 前端功能 | 仓库地址 / 获取方式 |
| :--- | :--- | :--- | :--- |
| **ComfyUI-Anima29-LegacyLoRA** *(仓库内置精简增强版)* | **Anima 2.9B (40层) 跨代 LoRA 智能桥接器**：将普通 28 层 Anima LoRA 实时重映射至 40 层 `29B` 扩容底模，对原生 40 层 LoRA 自动直通（已剔除无用 52L/3.8B 代码） | 左栏选用任意 **`29B` 底模**（如 `NovaAnimeAMV70_29B` / `mature29B`）时，后端**全自动无感启用桥接**并按角色/画风分流最优锐度参数 | 随本仓库内置于 [`tools/ComfyUI-Anima29-LegacyLoRA`](./tools/ComfyUI-Anima29-LegacyLoRA)（上游：[Civitai #2857927](https://civitai.com/models/2857927)） |
| **ComfyUI-Impact-Pack** + **Impact-Subpack** | 全自动 **FaceDetailer 修脸 & 修手**，自动框出每张脸和每只手单独高清重绘，专治糊脸、眼歪、6指/4指 | 右栏 **`✨ 自动修脸`** + **`🖐️ 自动修手`** 开关 | [Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) · [Subpack](https://github.com/ltdrdata/ComfyUI-Impact-Subpack) |
| **ComfyUI-WD14-Tagger** | 本地离线反推参考图提示词，支持只抄服装与构图、自动剔除原图角色名 | 中栏 **`🖼️ 拖图反推`**（支持拖拽与 `Ctrl+V` 粘贴） | [ComfyUI-WD14-Tagger](https://github.com/pythongosssss/ComfyUI-WD14-Tagger) · [WD14 模型库](https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3) |
| **comfyui-pose-gallery** + **comfyui_controlnet_aux** | 1,439 张高清姿势原图包（~675 MB，288 组多视角）+ 动漫线稿提取，配合 Anima LLLite 精准锁姿势 | 左栏 **姿势图库** + 右栏 **`🕺 姿势图控图`** | [comfyui-pose-gallery](https://github.com/wangweihong/comfyui-pose-gallery) · [原图库 ai-pose-gallery-zh](https://github.com/wangweihong/ai-pose-gallery-zh) · [controlnet_aux](https://github.com/Fannovel16/comfyui_controlnet_aux) |
| **comfyui-krea2-controlnet** *(多底模选装)* | 为 `Krea2` 底模提供深度/结构控图扩展，配合 `Anima / Krea2 / MOSS` 三底模隔离架构使用 | 多底模切换与扩展控图预留 | 按需放入 `custom_nodes/comfyui-krea2-controlnet` |

> **联动模型与素材直链**：
> - **自动修脸模型（`face_yolov8m.pt`，~49.6 MB）**：放到 `<ComfyUI目录>\models\ultralytics\bbox\face_yolov8m.pt`  
>   直链：`https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt`
> - **自动修手模型（`hand_yolov8s.pt`，~21.4 MB）**：放到 `<ComfyUI目录>\models\ultralytics\bbox\hand_yolov8s.pt`  
>   直链：`https://huggingface.co/Bingsu/adetailer/resolve/main/hand_yolov8s.pt`
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

## 🆕 四、近期架构升级与推荐配置补充

1. **Anima-2.9B (40L) 全自动无感桥接**：前端选择任何文件名含 `29B` / `2.9B` 的 Anima 底模时，`server.py` 自动将 LoRA 链切换为 `Anima29LegacyLoRALoaderSharp`，并针对角色类（`copy_prev / 0.18 / attn_only`）与画风类（`sharp_blend / 0.20 / attn_and_mlp`）自动匹配最佳层间补偿策略。
2. **隐藏触发词自动补全与三底模隔离索引**：`lora_index.py` 原生兼容 `char` / `character` 双目录命名，支持 `Anima / Krea2 / MOSS` 三大纯血架构物理隔离，并在生图时自动向正面提示词补全名家画风与新角色的显式触发词（如 `@syjt`、`4s4n4g1sknsfw`、`xiaoxingchen` 等）。
3. **本机私有预设分离（`workflows/presets.local.json`）**：支持在本机创建不随 Git 提交的 `presets.local.json` 存放个人定制一条龙预设，与仓库公共 `presets.json` 自动合并加载。
4. **全量词库扩充与安全护盾**：大幅扩充角色、专属服装、多视角姿势、场景、道具与外貌结构化词库；内置纯女性场景防串台护盾及 Anima 5D Latent 双人独立分区（防光环/发色串台）。

---

## 🚀 最简单安装方式（二选一）

### 方式 A：交给你的 AI Agent 全自动安装（推荐电脑小白）
把下面这段话直接发给你的 AI 助手（Antigravity / Claude Code / Codex / Cursor）：
```text
请按 https://github.com/NeoxODD511/gemina-comfy-studio 仓库里的 RECOMMENDED_PLUGINS.md，
帮我探测本机 ComfyUI 的 custom_nodes 和内置 Python：
1. 将仓库内置的 tools/ComfyUI-Anima29-LegacyLoRA 复制到 custom_nodes/ 以启用 Anima 2.9B 自动桥接；
2. 自动安装推荐的核心插件（Manager、Impact-Pack、Impact-Subpack、Detail-Daemon、rgthree-comfy）并装好 Python 依赖；
3. 下载 face_yolov8m.pt（自动修脸）和 hand_yolov8s.pt（自动修手）到 models/ultralytics/bbox/，最后重启 ComfyUI 验证节点加载正常。
```

### 方式 B：Windows PowerShell 一键安装脚本
把下面脚本里的 `F:\ComfyUI` 和 `F:\ComfyUI_Frontend` 改成你电脑上实际的路径，在 PowerShell 中直接粘贴运行即可：

```powershell
$COMFY_ROOT = "F:\ComfyUI"
$FRONTEND_ROOT = "F:\ComfyUI_Frontend"
$PY = "$COMFY_ROOT\python_embeded\python.exe"
$NODES = "$COMFY_ROOT\app\comfyui-master\custom_nodes"
$BBOX = "$COMFY_ROOT\app\comfyui-master\models\ultralytics\bbox"

# 1. 安装仓库内置精简版 Anima 2.9B (28L->40L) 智能桥接插件
Copy-Item -Path "$FRONTEND_ROOT\tools\ComfyUI-Anima29-LegacyLoRA" -Destination "$NODES\ComfyUI-Anima29-LegacyLoRA" -Recurse -Force

# 2. 克隆通用核心插件
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

# 3. 下载自动修脸 (face_yolov8m.pt) 与自动修手 (hand_yolov8s.pt) 检测模型
New-Item -ItemType Directory -Force -Path $BBOX | Out-Null
foreach ($fn in @("face_yolov8m.pt", "hand_yolov8s.pt")) {
  $out = Join-Path $BBOX $fn
  if (!(Test-Path $out)) {
    Invoke-WebRequest -Uri "https://huggingface.co/Bingsu/adetailer/resolve/main/$fn" -OutFile $out
  }
}
Write-Host "全部推荐插件（含 Anima 2.9B 桥接与修脸修手模型）安装完成！请重启 ComfyUI 即可生效。" -ForegroundColor Green
```

---

> ⚠️ **避坑提示**：
> - 安装 `Impact-Pack` / `Impact-Subpack` 时，请务必使用 **ComfyUI 自带的 `python_embeded\python.exe`** 执行 `pip install`，不要装到系统全局 Python 里；
> - 6GB 显存笔记本开启 **`✨ 自动修脸`** 时，建议先关掉二段高清精绘（HiRes Fix）或保持修脸重绘幅度 `0.35~0.45`，既稳又清晰！
