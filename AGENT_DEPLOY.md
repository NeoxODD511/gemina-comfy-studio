# AGENT_DEPLOY.md — AI Agent 自动化安装与部署指南

> 本文档专供 **AI Coding Agent（如 Antigravity / Claude Code / Codex / Cursor 等）** 阅读执行。人类用户请直接阅读 [README.md](./README.md)。
>
> **官方仓库**：`https://github.com/NeoxODD511/gemina-comfy-studio.git`  
> **架构作者**：Antigravity（天才美少女 AIGC 设计师洁美奈 / Gemina）

---

## 0. Agent 一键拉取与快速启动命令

```powershell
# Windows PowerShell 一键拉取（可按用户盘符调整目标目录）
git clone https://github.com/NeoxODD511/gemina-comfy-studio.git "F:\ComfyUI_Frontend"
Set-Location "F:\ComfyUI_Frontend"

# 使用 ComfyUI 自带嵌入式 Python 启动（免全局装 Python，按实际路径替换）
$env:COMFY_URL = "http://127.0.0.1:8188"
$env:FRONTEND_PORT = "8189"
& "F:\ComfyUI\python_embeded\python.exe" "F:\ComfyUI_Frontend\server.py"
```

---

## 1. 系统架构与零依赖原则

- **前端**：`web/index.html` 为单文件原生 HTML/CSS/JS，**零 npm、零打包构建、零外部 CDN**。
- **后端**：`server.py`、`combo.py`、`lora_index.py` 仅依赖 **Python 3.10+ 标准库**，通过 HTTP/WebSocket 与用户本机的 ComfyUI（默认 `http://127.0.0.1:8188`）通信，**禁止修改 ComfyUI 核心源码**。
- **可选能力依赖**：
  - **WD14 拖图反推**（`POST /api/tagger`）：需要 `onnxruntime`、`pillow`、`numpy`（见 `requirements-optional.txt`）以及 `wd-swinv2-tagger-v3.onnx` + `wd-swinv2-tagger-v3.csv`。
  - **姿势图 LLLite 控图**（`pose_ctrl`）：需要 ComfyUI 已安装 `comfyui-pose-gallery`、`comfyui_controlnet_aux`、Anima LLLite 节点，以及 `ab1_lineart.safetensors`。
  - **一条龙预设**（`workflows/presets.json`）：需要对应底模与 LoRA 存在；如果用户本机 LoRA 路径不同，Agent 应扫描用户 `models/loras` 目录并重写 `workflows/presets.json` 中的相对路径。

---

## 2. Agent 部署标准操作流程（SOP）

### Step 1：探测用户本机环境
在执行任何修改前，先探测以下路径与端口：
1. 找到用户本机 ComfyUI 根目录（记为 `<COMFY_ROOT>`）与内置 Python（通常为 `<COMFY_ROOT>\python_embeded\python.exe`）。
2. 检查 `http://127.0.0.1:8188/system_stats` 是否在线；若未启动，定位用户的 ComfyUI 启动命令（例如 `python.exe -s <COMFY_ROOT>\ComfyUI\main.py --disable-auto-launch`）。
3. 探测 `<COMFY_ROOT>\ComfyUI\models\loras`（或 `extra_model_paths.yaml` 中的真实 LoRA 目录，记为 `<LORA_DIR>`）。
4. 探测 `<COMFY_ROOT>\ComfyUI\custom_nodes\` 中是否已存在 `ComfyUI-WD14-Tagger`、`comfyui-pose-gallery`、`comfyui_controlnet_aux`。

### Step 2：配置环境变量（不要硬改源码默认路径）
启动 `server.py` 时，通过环境变量传入用户本机的真实路径：

| 环境变量 | 必填 | 示例值 | 用途 |
| :--- | :---: | :--- | :--- |
| `COMFY_URL` | 否 | `http://127.0.0.1:8188` | ComfyUI 服务地址 |
| `FRONTEND_PORT` | 否 | `8189` | ODD 出图台监听端口 |
| `LORA_DIR` | 推荐 | `D:\ComfyUI\models\loras` | 本地 LoRA 扫描根目录 |
| `COMFY_UI_DIR` | 推荐 | `D:\ComfyUI\ComfyUI` | 用于读取 `custom_nodes/comfyui-pose-gallery/library/` |
| `DESKTOP_OUT_DIR` | 否 | `C:\Users\<User>\Desktop\ComfyUI出图` | 出图完成后自动镜像保存的本地目录 |

> 注意：`server.py` 中 `WD14_MODEL_DIR` 指向 `ComfyUI-WD14-Tagger\models`，若用户的 `ComfyUI` 不在 `F:\ComfyUI\ComfyUI`，Agent 需将其更新为 `<COMFY_UI_DIR>\custom_nodes\ComfyUI-WD14-Tagger\models`。

### Step 3：安装可选扩展（按用户需求执行）

#### A. 启用 WD14 本地拖图反推（`POST /api/tagger`）
1. 检查 Python 依赖：
   ```bash
   <PYTHON_EXE> -c "import onnxruntime, PIL, numpy; print('OK')"
   ```
   若缺失，安装 `requirements-optional.txt`：
   ```bash
   <PYTHON_EXE> -m pip install -r requirements-optional.txt
   ```
2. 克隆节点并下载 `wd-swinv2-tagger-v3`（约 `467 MB`）：
   ```bash
   git clone --depth 1 https://github.com/pythongosssss/ComfyUI-WD14-Tagger.git "<COMFY_UI_DIR>\custom_nodes\ComfyUI-WD14-Tagger"
   ```
   下载以下两个文件到 `<COMFY_UI_DIR>\custom_nodes\ComfyUI-WD14-Tagger\models\`：
   - `wd-swinv2-tagger-v3.csv` ← `https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3/resolve/main/selected_tags.csv`
   - `wd-swinv2-tagger-v3.onnx` ← `https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3/resolve/main/model.onnx`

#### B. 校准一条龙预设（`workflows/presets.json`）
- 扫描用户 `<LORA_DIR>` 和 `GET http://127.0.0.1:8188/object_info/UNETLoader`、`LoraLoader`。
- 将 `workflows/presets.json` 中不存在的 LoRA 自动移除或映射为本机真实相对路径，确保用户在前端点选预设时 0 报错。

### Step 4：启动服务与生成一键启动器
1. 启动前端服务（建议作为独立守护进程运行）：
   ```bash
   cd <REPO_DIR>
   <PYTHON_EXE> server.py
   ```
2. 建议在用户桌面生成 `启动 ODD出图.bat`：
   - 检测 `8188` 是否运行，未运行则最小化启动 ComfyUI 并轮询等待就绪；
   - 检测 `8189` 是否运行，未运行则启动 `server.py`；
   - 自动 `start "" "http://127.0.0.1:8189/"`。

---

## 3. 核心 HTTP API 契约（供调试与二次开发）

| 方法与路径 | 说明 |
| :--- | :--- |
| `GET /api/status` | 检查 ComfyUI 在线状态与硬件信息 |
| `GET /api/models` | 读取 ComfyUI `UNETLoader` 可用底模列表 |
| `GET /api/loras` | 读取并结合 `data/lora-index.json` 返回分类 LoRA 列表 |
| `GET /api/reindex` | 重新扫描 `LORA_DIR` 重建本地 LoRA 索引 |
| `GET /api/assets` | 分页/搜索/分组查询姿势、服装、角色词库（支持 `cat`, `q`, `group`, `part`, `collapsed`, `offset`, `limit`） |
| `GET /api/combo/options?level=X` | 返回指定分级下的全部场景与画风列表 |
| `POST /api/combo` | 智能生成或局部重抽搭配（支持 `locked` 与 `disabled` 槽位控制） |
| `GET /api/workflows` | 读取 `workflows/presets.json` 一条龙工作流预设 |
| `POST /api/tagger` | 接收 base64 图片，本地 ONNX 推理返回 WD14 通用标签与角色标签 |
| `POST /api/generate` | 构造 ComfyUI Workflow（支持 LoRA 链、LLLite 姿势控图、二段 HiRes Fix）并提交 `/prompt` |
| `GET /api/queue` | 返回 ComfyUI 队列状态及后端 WS 监听线程实时采集的 `progress` |
| `POST /api/interrupt` | 立即中断当前正在运行的 ComfyUI 任务 |
| `POST /api/free` | 调用 ComfyUI `/free` 卸载闲置模型释放显存与物理内存 |
| `POST /api/queue/clear` | 清空等待队列或按 `delete: [pid]` 取消指定排队任务 |

---

## 4. 部署后自动化验收 Checklist

Agent 在向用户汇报部署完成前，**必须逐项验证**：
- [ ] `GET http://127.0.0.1:8189/api/status` 返回 `{"comfy": "online", ...}`。
- [ ] `GET http://127.0.0.1:8189/api/workflows` 返回 HTTP 200 且预设 LoRA 均存在于本机。
- [ ] `POST http://127.0.0.1:8189/api/combo` 返回 HTTP 200 且包含 `prompt`、`scene_nl`。
- [ ] `GET http://127.0.0.1:8189/api/queue` 返回 HTTP 200 且包含 `progress` 字段。
- [ ] 浏览器打开 `http://127.0.0.1:8189/`，控制台 **0 JS Errors**，网络请求 **0 HTTP >= 400**。
- [ ] （可选）校验用户 `<LORA_DIR>` 内所有 `.safetensors` 文件头完整性，避免损坏文件导致 `Error while deserializing header`。

---

## 5. 已知问题与排障速查（供 Agent 快速定位）

1. **`POST /interrupt` 或 `/free` 报 JSON 解析错误**：ComfyUI 这些控制接口成功时返回空响应体 `""`，已在 `server.py` 的 `comfy_post()` 中兼容空响应返回 `{"ok": True}`，二次开发时勿回退为直接 `json.loads()`。
2. **前端进度条不显示**：浏览器直连 `ws://127.0.0.1:8188/ws` 易受跨源策略或多标签页同 `clientId` 互顶影响；当前已改为由 `server.py` 后台线程 `_ws_progress_loop()` 统一监听并通过 `GET /api/queue` 附带 `progress` 字段返回。
3. **出图后未自动保存到桌面目录**：已通过 `_ws_progress_loop()` 监听 `executed` / `executing(node=None)` 自动镜像保存，不受前端刷新影响；若用户未启用该目录，可通过环境变量 `DESKTOP_OUT_DIR` 调整。
4. **旧 ComfyUI 工作流 JSON 报 LoRA 缺失**：用户重整 `models/loras` 子目录后，旧 JSON 扁平路径会失效；Agent 应查询 `GET /object_info/LoraLoader` 按文件名 basename 批量重映射并更新 `workflows/presets.json`。
5. **模型加载报 `Error while deserializing header: incomplete metadata, file not fully covered`**：说明对应 `.safetensors` 文件下载截断，需校验文件头 `8 + hdr_len + max_offset <= file_size` 并重新下载。
6. **默认正负面质量词兜底**：`server.py` 的 `build_prompt_payload()` 会自动通过 `_append_tags()` 追加 `DEFAULT_POSITIVE` 与 `DEFAULT_NEGATIVE`，用户留空负面框时仍会有保底负面词生效。

