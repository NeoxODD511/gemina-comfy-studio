# ODD 出图 · Studio（ComfyUI 独立轻量化出图工作台）

> ✨ **项目说明**：本项目的赛博极光磨砂玻璃前端重塑、交互架构（UX）、一条龙工作流引擎、双人分区域独立提示词（防光环串台）、Anima LLLite 姿势图控图联动、WD14 拖图反推集成、实时进度条与队列控制等核心功能，均由 **Antigravity（天才美少女 AIGC 设计师洁美奈 / Gemina）** 完整设计与编写实现。

---

## 🤖 AI Agent 一键全自动部署（推荐小白直接复制！）

把下面这段话直接复制发给你的 AI 编程助手（**Antigravity / Claude Code / Codex / Cursor** 均可），它会自动帮你克隆代码、探测本机 ComfyUI 路径、配置环境变量、启动服务并验收：

```text
请帮我部署这个 ComfyUI 前端项目：https://github.com/NeoxODD511/gemina-comfy-studio.git
1. 先克隆仓库到本地合适目录（如 F:\ComfyUI_Frontend 或我本机 ComfyUI 同级目录）；
2. 严格按照仓库里的 AGENT_DEPLOY.md 全自动探测我电脑上的 ComfyUI 路径、内置 Python 和 LoRA 目录；
3. 配好环境变量、检查/适配可选依赖（WD14 拖图反推、姿势图库等）并在桌面生成一键启动脚本；
4. 启动 8189 前端服务并验证 http://127.0.0.1:8189/api/status 显示 ComfyUI 在线，完成后告诉我打开链接。
```

如果你习惯在终端直接一条命令拉取运行（PowerShell）：
```powershell
git clone https://github.com/NeoxODD511/gemina-comfy-studio.git; Set-Location gemina-comfy-studio; python server.py
```

*(Agent 详细操作手册见 **[AGENT_DEPLOY.md](./AGENT_DEPLOY.md)**)*

---

## 📦 依赖项一览（分清「必须」和「可选」）

### 1. 基础运行（开箱即用，零第三方依赖！）
| 模块 | 依赖项 | 说明 |
| :--- | :--- | :--- |
| **前端 (`web/index.html`)** | **无任何依赖** | 纯原生 HTML / CSS / JS，无需 Node.js、无需 npm、无需联网加载 CDN |
| **后端 (`server.py` 等)** | **Python 3.10+ 标准库** | 直接用 ComfyUI 自带的 `python_embeded\python.exe` 即可运行，无需额外装包 |
| **生图引擎** | **本机 ComfyUI**（`8188` 端口） | 只通过 ComfyUI 原生 API / WebSocket 通信，不改 ComfyUI 任何源码 |

### 2. 可选进阶功能依赖（按需开启，不装不影响基础出图）
| 进阶功能 | 所需依赖 / 模型 |
| :--- | :--- |
| **🖼️ WD14 本地拖图反推** | Python 包见 [requirements-optional.txt](./requirements-optional.txt)（`onnxruntime`、`pillow`、`numpy`，ComfyUI 内置 Python 通常自带）；模型文件 `wd-swinv2-tagger-v3.onnx` + `wd-swinv2-tagger-v3.csv` |
| **🕺 姿势图 LLLite 控图** | ComfyUI 节点：`comfyui-pose-gallery`、`comfyui_controlnet_aux`、Anima LLLite 节点 + `ab1_lineart.safetensors` |
| **⚡ 一条龙工作流预设** | `workflows/presets.json` 中配置的 Anima 底模及对应画风/画质 LoRA（可按自己本机模型自由编辑） |

---

## 🚀 3 步快速启动

1. **先启动你电脑上的 ComfyUI**（确认 `http://127.0.0.1:8188` 可访问）。
2. **在本项目目录下运行**：
   ```bash
   python server.py
   ```
   *(如果电脑没全局装 Python，直接用 ComfyUI 自带的内置 Python：`F:\ComfyUI\python_embeded\python.exe server.py`)*
3. **浏览器打开**：**`http://127.0.0.1:8189/`**，看到左上角绿灯亮起 **`ComfyUI 在线`** 即可开始画图！

### 可选环境变量（适配不同盘符与目录）
| 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `COMFY_URL` | `http://127.0.0.1:8188` | ComfyUI 服务地址 |
| `FRONTEND_PORT` | `8189` | ODD 出图台网页端口 |
| `LORA_DIR` | `F:\ComfyUI_Models\loras` | 本地 LoRA 目录（重建索引时扫描） |
| `COMFY_UI_DIR` | `F:\ComfyUI\app\comfyui-master` | ComfyUI 主目录（用于读取姿势图库） |
| `DESKTOP_OUT_DIR` | `C:\Users\Administrator\Desktop\CpmfyUI出图` | 出图完成后自动镜像保存的文件夹 |

---

## 📖 新手使用指南（一分钟上手）

### 1. 左栏：挑底模 & 挑素材
- **底模引擎**：切换你本机 `models/diffusion_models` 里的底模（如 `anima_aestheticV11`、`one_obsession_animaV5turbo`、`anima-base-v1.0`）。
- **姿势（2 列高清画廊）**：默认勾选 **`仅看带图`**，点击任意姿势卡片弹出**高清大图 + 多视角切换窗口**（支持键盘 `←` / `→` 切视角）；点 **`✓ 选用当前视角`** 后会自动绑定到右栏的 **`🕺 姿势图控图 (LLLite)`**。
- **服装（子分类精准筛选）**：支持 **`全部 / 上装 / 下装 / 鞋袜 / ★ 角色专属 / 连衣裙 / 制服 / 配饰`**；角色专属服装按人气降序展示，并清清楚楚标出了 **`角色中文名 · 服装名 [所属作品]`**，搜索框支持直接搜中文角色名或作品名。
- **角色（中文系列筛选）**：70+ 热门作品已全面汉化并合并中英文重名系列（如 `赛马娘`、`原神`、`崩坏：星穹铁道`、`东方Project`、`Fate / FGO` 等）。

### 2. 中栏：灵感一键搭配 + 提示词 + LoRA
- **🎲 灵感一键搭配**：
  - 支持 Lv0 ~ Lv4 五档分级，默认勾选 **`✨ 附带自然语言`**，会把英文电影感场景段落一起写入正面提示词，画面感大幅提升；
  - 抽到多人场景自动切人数锁（双女主自动抽 `角色 2`），场景自带体位时自动跳过姿势控图防冲突；
  - **每个槽位（场景 / 角色 / 服装 / 姿势 / 画风）均可独立微调**：
    - `🔒 / 🔓` 锁定或解锁（整套重抽时保留锁住的项）
    - `🎲` 单独重抽这一项（遇到场景和姿势冲突一秒换掉！）
    - `✏️` 弹窗搜索自主替换（支持点 **`📥 使用左栏已选`**）
    - `×` 直接移除此项
- **提示词编排**：
  - 顶部实时展示彩色 **「已选素材」条**，点 `×` 随时取消；
  - 下方自带快捷美学芯片（`+ 全身`、`+ 强制换装`、`+ 双女主`、`+ 丁达尔神光`、`+ 大仰拍张力`）、**`📋 复制`** 与 **`🖼️ 拖图反推`**（把参考图拖进去或直接 `Ctrl + V` 粘贴截图，默认勾选「排除原图角色名」只抄衣服/构图不夺舍）；
  - **👯 双人独立提示词（防光环/发色串台）**：基于 Anima 5D Latent 原生 `ConditioningSetAreaPercentageVideo` + `ConditioningCombine` 做物理左右/上下分区；一方含 `halo`（如蔚蓝档案角色）时另一方自动补 `no halo` 护盾，同时自动压制第 3 人影分身。
- **LoRA 工作室**：
  - 支持按底模和分类筛选；已挂 LoRA 支持滑块调权重，**滑杆 LoRA（Slider LoRA）自动解锁 `-3 ~ +3` 负值反向调节**。

### 3. 右栏：出图与控制（两个出图按钮的区别！）
- **紫粉渐变 `✦ 立即生成`**（或任意位置按 **`Ctrl + Enter`**）：**完全按你当前自选的底模、已挂 LoRA 和参数出图**。
- **琥珀金 `⚡ 一条龙出图`**：自动套用上方选中的预设工作流（切换底模 + 挂好画风/画质 LoRA + 保留你已挂的角色 LoRA + 开启二段高清精绘）并立刻出图。
- **顶栏实时掌控**：
  - 出图时顶栏与右栏画廊同步显示 **实时步数 & 百分比进度条**；
  - 点击 **`📋 队列 X 运行 / Y 等待`** 可查看排队明细并取消指定任务；
  - 觉得卡顿或点错重型工作流，随时点顶栏 **`⏹ 停止当前`** 或 **`🧹 清显存`**。
- **6 GB 显存笔记本推荐甜点参数**：`832×1216` · 步数 `18~20`（Turbo 底模 `12` 步） · CFG `4` · `euler` · `FP8 极速` · 抽卡阶段关闭二段高清精绘。

---

## 📁 目录结构

```text
ComfyUI_Frontend/
├── README.md                    # 人类用户文档与使用指南
├── AGENT_DEPLOY.md              # AI Agent 自动化安装、配置与验收 SOP
├── requirements-optional.txt    # 可选扩展依赖（仅 WD14 反推需要）
├── server.py                    # 独立 HTTP 服务、ComfyUI API/WS 代理、WD14 反推、自动落盘
├── combo.py                     # 灵感一键搭配引擎（单人/多人/自然语言/锁槽重抽）
├── lora_index.py                # 本地 LoRA 索引与分类器
├── web/
│   └── index.html               # ODD 出图 · Studio 单页前端（零外部 CDN 依赖）
├── workflows/
│   ├── presets.json             # 一条龙工作流预设配置
│   └── raw/                     # 归档的 ComfyUI 工作流 JSON
├── data/assets/                 # 角色 / 服装 / 姿势 / 场景 / 画风结构化词库
└── tools/                       # 索引标注、下载修复与控图辅助脚本
```

---

## ⚠️ 已知问题与常见避坑说明（Known Issues）

1. **6 GB 显存 / 16 GB 内存设备开启「1.5× 二段高清精绘」会明显变慢**：
   - `1024×1536` 经 `1.5×` 放大后达到 `1536×2304`，容易触发 6 GB 显存溢出回落系统内存（单步耗时飙升至数十秒）。
   - **建议**：日常抽卡关闭二段精绘，采用 `832×1216` + `FP8 极速` + `18~20 步`（或选 `Aesthetic V11 · 省显存精修一条龙`）；若误点重型任务，直接点顶栏 **`⏹ 停止当前`** 与 **`🧹 清显存`**。
2. **报错 `Error while deserializing header: incomplete metadata, file not fully covered`**：
   - 表示当前挂载的某个 `.safetensors` LoRA/底模文件下载中断损坏。卸载对应 LoRA 即可恢复，或使用 `tools/fix_broken_loras.py` 校验文件头并重下补全。
3. **跨角色换装被原皮压制 / 残留上个角色饰品（如光环、帽子）**：
   - 热门角色原皮先验较强，换装时建议配合 `+ 强制换装`（`alternate costume`）并用自然语言写清服装版型与配色；
   - 在「一键搭配」中单独更换 **`角色`** 后，记得顺手点一下 **`服装`** 上的 **`🎲`**，以免保留上一个角色官方服装里的光环/发饰导致“串台”。
4. **场景自带体位与「姿势图控图」冲突**：
   - 若场景词包含 `standing` 等强动作词，同时开启不同动作的 LLLite 姿势图会导致肢体扭曲。一键搭配已内置 `pose_conflict` 自动防呆跳过控图；手动组合时请删除正面提示词里的冲突动作词，或取消勾选 **`🕺 姿势图控图`**。
5. **上游词库少量历史瑕疵**：
   - 词库源自多个开源项目合并，极少数角色可能存在发色/瞳色错标（例如已修复的无声铃鹿因 `white hairband` 被误提取为 `white hair`），`styles.json` 画风建议池中也混有少量杂项标签（仅作参考不写入正面提示词，点 `🎲` 换掉即可）。
6. **大体积离线资源未随 Git 仓库打包**：
   - 因 GitHub 单文件 100 MB 限制，姿势图原图包（~675 MB）与 WD14 反推模型（~467 MB）未包含在仓库内，缺失时基础出图与词库功能完全正常，按需安装对应节点与模型即可解锁。

---

## 🙏 致谢
- 感谢 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 及相关开源节点社区（`ComfyUI-WD14-Tagger`、`comfyui-pose-gallery`、`Comfyui-Anima-Wardrobe-V5`、`prompt-workbench` 等）。
- 前端视觉、交互设计与工程化整理：**Antigravity · 洁美奈 (Gemina)** 🐾✨
