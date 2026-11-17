# DEPENDLIST — AiViewNews 依赖、环境与交接清单

> 目标：任何人拿到本仓库后，能按本文档复现运行环境，完成「上传 PDF → mineru 解析 → DeepSeek 分析 → 时间线与报告」全流程。
> 核对日期：2026-11-18。核对环境：Windows 11 + Anaconda（本机）。

## 1. 组件总览

| 组件 | 版本 / 要求 | 用途 | 随仓库分发 |
| --- | --- | --- | --- |
| Python（主环境） | 3.11+（本机验证 3.15.2） | 后端 FastAPI | 否，按本文安装 |
| FastAPI / Uvicorn | 见 `requirements.txt` | Web 服务 | 否，pip 安装 |
| 前端 | 原生 HTML + CSS + JS | 浏览器界面 | 是（`web/`） |
| SQLite | Python 标准库 | 数据库 | 否，运行时生成 |
| DeepSeek API | OpenAI 兼容接口 | 事件抽取、时间线、报告 | 否，需 API Key |
| MinerU | 4.2.3（独立 Python 3.13.18 环境） | PDF → Markdown + 图片 | 否，需单独安装与模型 |
| Node.js | 可选 | 仅用于 `node --check` 语法检查 | 否，运行不依赖 |

## 2. Python 主环境

- 要求：Python 3.11 及以上；本机实测 **Python 3.15.2**。
- 建议使用 conda 独立环境，避免污染 base。

```bash
conda create -n deepseek python=3.11 -y
conda activate deepseek
python -m pip install -r requirements.txt
```

PyPI 直连不可用时改用清华镜像：

```bash
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

`requirements.txt` 内容与用途：

| 包 | 固定版本 | 用途 |
| --- | --- | --- |
| fastapi | 0.163.1 | Web 框架与依赖注入 |
| uvicorn[standard] | 0.54.0 | ASGI 服务器 |
| python-dotenv | 1.2.4 | 读取 `.env` |
| itsdangerous | 2.2.0 | 会话 Cookie 签名 |
| python-multipart | 0.0.34 | PDF 表单上传 |
| openai | 3.52.0 | DeepSeek OpenAI 兼容调用 |
| pymupdf | 1.28.2 | 读取 PDF 页数、预热样例 |
| python-docx | 1.2.0 | 报告导出 DOCX |
| httpx | 0.28.1 | 测试与 CDP 辅助（运行时不强依赖） |
| pytest | 9.2.0 | 测试 |

前端没有 npm / 构建步骤；Node.js 仅可选用于语法检查：

```bash
node --check web/app.js
node --check web/views/admin.js
```

## 3. 数据库

- SQLite，使用 Python 标准库 `sqlite3`，无需单独安装。
- 表结构见 `app/schema.sql`；启动时按 `app/db.py` 的 `SCHEMA_VERSION` 自动建表/迁移。
- 运行数据位于 `DATA_DIR`（默认项目下 `data/`）：
  - `data/db.sqlite3`：数据库（含用户密码哈希、系统设置；**不得提交或外发**）
  - `data/uploads/`：临时 PDF（解析后删除）
  - `data/parsed/<doc_id>/`：`full.md` 与图片
  - `data/logs/llm.jsonl`：模型调用审计日志（不含明文 Key）
  - `data/secret.key`：自动生成的会话密钥

## 4. 文字模型（DeepSeek）

- 协议：OpenAI 兼容 Chat Completions。
- 默认配置：
  - `base_url = https://api.deepseek.com`
  - `model = deepseek-chat`
- 需要自行申请 API Key，写入以下任一位置（优先级从高到低）：
  1. 管理员控制台「系统设置」（写入数据库 `settings` 表，界面只回显掩码）
  2. `.env` 的 `DEEPSEEK_API_KEY`
- 也可替换为任何 OpenAI 兼容服务，只需改 `base_url` / `model` / `api_key`。
- 单次分析 `max_tokens = 4096`，失败自动重试 3 次（429/5xx 可重试）。

## 5. MinerU（PDF 解析，独立环境）

MinerU 与主环境依赖冲突，必须装在**独立 Python 环境**，由程序以子进程方式调用，**不写入 `requirements.txt`**。

- 本机版本：**MinerU 4.2.3**，Python **3.13.18**。
- 本机可执行文件示例：
  `D:\Install\anaconda3\envs\mineru\Scripts\mineru.exe`
- 安装（版本按官方文档为准；本机为完整依赖，含 `mineru-llama-cpp`、`onnxruntime-directml`）：

```bash
conda create -n mineru python=3.13 -y
conda activate mineru
python -m pip install "mineru==4.2.3"
# 如官方要求 extras（如 mineru[core]），按其文档补齐
mineru --version
```

- 在 `.env` 或管理员控制台填写：

```text
MINERU_CMD=D:/Install/anaconda3/envs/mineru/Scripts/mineru.exe
MINERU_TIER=flash
```

- 解析档位：
  - `flash`：纯文本、低内存，默认
  - `basic` / `standard` / `advanced`：需要本地模型，占用更高
- 模型权重：**不随仓库分发**。首次解析或预热时由 MinerU 自动下载/加载。本机缓存位置与体积参考：
  - `C:\Users\<用户>\.cache\modelscope` ≈ 13 GB
  - `C:\Users\<用户>\.mineru` ≈ 0.24 GB（doclib 缓存）
- 程序解析后会调用 `mineru forget` 清理源文件记录，并删除 PDF 本体。

## 6. 环境变量

复制 `.env.example` 为 `.env` 后填写。`.env` 已被 `.gitignore` 忽略。

| 变量 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `DEEPSEEK_API_KEY` | 是 | 空 | 大模型密钥；也可在控制台写入 |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com` | OpenAI 兼容地址 |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat` | 模型名 |
| `DEEPSEEK_TEMPERATURE` | 否 | `0.2` | 采样温度 |
| `DEEPSEEK_TIMEOUT` | 否 | `60` | 请求超时（秒） |
| `MINERU_CMD` | 是 | 空 | mineru 可执行文件绝对路径 |
| `MINERU_TIER` | 否 | `flash` | 解析档位 |
| `ADMIN_USERNAME` | 否 | `admin` | 首次启动自动建管理员（需同时设密码） |
| `ADMIN_PASSWORD` | 否 | 空 | 为空则走本机「创建管理员」入口 |
| `DEMO_PASSWORD` | 否 | 空 | 设置后创建 `demo` 普通用户 |
| `SESSION_SECRET` | 否 | 自动生成 | 会话签名密钥，生成到 `data/secret.key` |
| `DATA_DIR` | 否 | `./data` | 可写数据目录 |

## 7. 启动与首次初始化

```bash
# 方式一：一键启动（Windows，自动打开浏览器）
tools\start.bat

# 方式二：手动启动
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000`。

首次使用：

1. 若无任何管理员，登录页显示「创建管理员」（仅本机回环地址可用）。
2. 登录后进入「设置 → 控制台」，填写 `MINERU_CMD`、模型地址/名称/API Key，保存。
3. 上传示例 PDF（`sources/testpdf/sample_*.pdf`）验证解析与查询。

## 8. 测试与演示前预热

```bash
python -m pytest          # 23 个测试
python scripts/warmup.py  # 配置/数据库/内存/mineru 实解析/大模型连通
```

`warmup.py` 会真实调用一次 mineru 与一次大模型，全部 PASS 后再现场演示；首次模型下载/加载较慢，必须提前完成。

## 9. 交接打包清单

### 必须包含

- `app/`、`web/`、`tests/`、`scripts/`、`tools/`
- `requirements.txt`、`.env.example`、`.gitignore`
- `DEPENDLIST.md`、`REQUIREMENT.md`、`AGENTS.md`、`PLAN/`
- `sources/testpdf/`（演示样例 PDF）
- `sources/103/`（界面参考图，可选）

### 禁止包含（已在 `.gitignore` 中，但打包时仍要人工确认）

- `.env`（真实 Key）
- `data/`（数据库、上传 PDF、解析产物、日志、secret.key）
- `*.db` / `*.sqlite3`
- `__pycache__/`、`*.py[cod]`、`.pytest_cache/`
- MinerU 模型缓存（`~/.cache/modelscope`、`~/.mineru` 等）
- 任何虚拟环境目录

### 建议清理

- `.tmp_slides/`：PPT 提取的临时图片，**当前仍在 git 中**，建议移除并加入 `.gitignore`
- `.vscode/`：个人 IDE 路径与终端配置，**当前仍在 git 中**，建议移除或改为通用配置
- 根目录课程 PPT（`.pptx`，5 MB）：已从工作区删除；若无需版本留存，可清理其历史

## 10. 已知限制

- 主打 Windows 10/11；MinerU 也支持 Linux/macOS，但 `tools/start.bat` 仅适用于 Windows。
- 单文件上限 50 MB，一次最多 10 个 PDF。
- 游客（不登陆）数据 24 小时后自动清理；游客点「账号设置」会立即清空并回登录页。
- 报告导出格式为 DOCX。
- `SCHEMA_VERSION` 变化时，历史数据会按迁移逻辑清理（PLAN 15 已执行一次）；升级前请备份 `data/`。
