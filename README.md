# ODD 出图 · Studio（ComfyUI 独立轻量化出图工作台）

> ✨ **项目说明**：本项目的赛博极光磨砂玻璃前端重塑、交互架构（UX）、一条龙工作流引擎、Anima LLLite 姿势图控图联动、WD14 拖图反推集成、实时进度条与队列控制等核心功能，均由 **Antigravity（天才美少女 AIGC 设计师洁美奈 / Gemina）** 在与项目发起人的协作中完整设计与编写实现。

一个**零第三方前端依赖、纯 Python 标准库 + 单页 HTML/CSS/JS** 驱动的 ComfyUI 专属出图工作台（默认端口 `8189`），只通过 ComfyUI 原生 HTTP / WebSocket API（`8188`）通信，不修改 ComfyUI 任何核心源码。

---

## 🎨 核心亮点

### 1. 赛博极光磨砂玻璃 UI（Cyber Atelier）
- 动态极光深空背景 + 悬浮磨砂玻璃三栏布局，告别呆板切豆腐竖线与原生大白条滚动条。
- 顶部悬浮导航栏集成 **ComfyUI 在线状态**、**可点击队列明细**、**实时步数/百分比流光进度条**、**⏹ 停止当前**、**🧹 一键清显存/内存** 与 `Ctrl + Enter` 全局出图快捷键。

### 2. 左栏：素材与模型库（分段式大 Tab）
- **姿势画廊**：2 列高清竖版画廊卡片（默认开启「仅看带图」），点击弹出**高清原图 + 多视角切换弹窗**（支持 `←`/`→` 键切换视角），选中后自动绑定右栏 **🕺 Anima LLLite 线稿控图**（支持单人 & 双人姿势图）。
- **服装库**：细分 **`全部 / 上装 / 下装 / 鞋袜 / ★ 角色专属 / 连衣裙 / 制服 / 配饰`** 快捷子分类；所有角色专属服装清晰标注 **「角色中文名 · 服装名 [所属作品]」** 并按人气排序，支持直接搜中文角色名或作品名。
- **角色库**：70+ 热门作品全面汉化并合并中英文重名系列（如 `赛马娘`、`原神`、`崩坏：星穹铁道`、`东方Project`、`Fate / FGO` 等）。

### 3. 中栏：灵感一键搭配 + 提示词编排 + LoRA 工作室
- **可自主修改的「灵感一键搭配」**：
  - 支持 Lv0 ~ Lv4 五档分级，内置 **✨ 附带自然语言描述**（融合 Wardrobe V5 英文电影感场景段落，大幅提升 Anima / Qwen 画面感）；
  - 智能区分单人、男女互动（`1girl, 1boy`）与双女主（自动抽取 `角色 2`），自动检测场景与姿势冲突；
  - 场景 / 角色 / 服装 / 姿势 / 画风每个槽位均支持 **`🔒 锁定`**、**`🎲 单独重抽`**、**`✏️ 弹窗搜索替换 / 同步左栏`**、**`× 单项移除`**。
- **提示词编排**：顶部实时展示彩色 **「已选素材」汇总条**；下方自带 **快捷美学芯片**（`+ 全身`、`+ 强制换装`、`+ 双女主`、`+ 丁达尔神光`、`+ 大仰拍张力`）、**一键复制** 与 **🖼️ WD14 本地拖图反推弹窗**（支持拖拽 / 选图 / `Ctrl + V` 粘贴截图，默认勾选「排除原图角色名防夺舍」）。
- **LoRA 工作室**：按底模（Anima / MOSS / Krea 2）与类别筛选；已挂 LoRA 支持滑动条双向微调，**滑杆 LoRA（Slider LoRA）自动解锁 `-3 ~ +3` 负值反向调节**。

### 4. 右栏：成图画廊 + ⚡ 一条龙工作流 + 生成参数
- **成图画廊**：宽屏实时百分比进度条、出图点击全屏灯箱预览、会话历史缩略图条、后台 WebSocket 自动将成图镜像保存到指定桌面目录。
- **⚡ 一条龙工作流**：支持加载 `workflows/presets.json` 预设，一键切换底模 + 挂载画风/画质 LoRA（同时保留已挂角色 LoRA）+ 开启 **二段高清精绘（LatentUpscaleBy + 二次 KSampler）** 直接出图。

---

## 🚀 快速开始（3 步启动）

### 前置条件
1. 已安装并运行 **ComfyUI**（默认地址 `http://127.0.0.1:8188`）。
2. Python 3.10+（可直接使用 ComfyUI 自带的 `python_embeded\python.exe`）。
3. （可选）如需使用 **WD14 拖图反推**，请安装 `ComfyUI-WD14-Tagger` 并将 `wd-swinv2-tagger-v3.onnx` 与 `wd-swinv2-tagger-v3.csv` 放至其 `models/` 目录；如需使用 **姿势图控图**，请安装 `comfyui-pose-gallery`、`comfyui_controlnet_aux` 及 Anima LLLite 控图模型。

### 启动命令
```bash
# 直接使用 ComfyUI 内置 Python 启动（默认监听 127.0.0.1:8189）
python server.py
```
随后在浏览器打开：**`http://127.0.0.1:8189/`**

### 可选环境变量（适配你自己的本机路径）
| 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `COMFY_URL` | `http://127.0.0.1:8188` | ComfyUI 后端地址 |
| `FRONTEND_PORT` | `8189` | ODD 出图前端监听端口 |
| `LORA_DIR` | `F:\ComfyUI_Models\loras` | 本地 LoRA 目录（用于重建索引） |
| `COMFY_UI_DIR` | `F:\ComfyUI\app\comfyui-master` | ComfyUI 主目录（用于读取姿势图库） |
| `DESKTOP_OUT_DIR` | `C:\Users\Administrator\Desktop\CpmfyUI出图` | 出图自动镜像保存目录 |

---

## 📁 目录结构

```text
ComfyUI_Frontend/
├── server.py          # 独立 HTTP 服务、ComfyUI API/WS 代理、WD14 反推、自动落盘
├── combo.py           # 灵感一键搭配引擎（单人/多人/自然语言/锁槽重抽）
├── lora_index.py      # 本地 LoRA 索引与分类器
├── web/
│   └── index.html     # ODD 出图 · Studio 单页前端（零外部 CDN 依赖）
├── workflows/
│   ├── presets.json   # 一条龙工作流预设配置
│   └── raw/           # 归档的 ComfyUI 工作流 JSON
├── data/assets/       # 角色 / 服装 / 姿势 / 场景 / 画风结构化词库
└── tools/             # 索引标注、下载修复与控图辅助脚本
```

---

## 🙏 致谢
- 感谢 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 及相关开源节点社区（`ComfyUI-WD14-Tagger`、`comfyui-pose-gallery`、`Comfyui-Anima-Wardrobe-V5`、`prompt-workbench` 等）提供的生态与词库灵感。
- 前端视觉与工程实现：**Antigravity · 洁美奈 (Gemina)** 🐾✨
