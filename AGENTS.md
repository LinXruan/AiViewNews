# PDFAiReader 项目守则（B/S 课程作业）

## 0. Agent 守则

- 改动前先读本文件、[REQUIREMENT.md](REQUIREMENT.md) 与最近一份 PLAN（当前在 `PLAN/PLAN_11~20/PLAN_<n>.md`；1–10 归档在 `PLAN/PLAN_1~10/`）。
- 非平凡改动先写 `PLAN/PLAN_11~20/PLAN_<n>.md`：需求、方案、文件清单、验证、回退。序号递增，不复用；每 10 个计划一个目录。
- 阻塞或语义不确定时停下来问用户，不要猜；也不要顺手做没被要求的功能。
- 完成标准是可运行且对应场景验证通过，不是"代码写完"。

## 1. 项目概况

- **项目名**：AiViewNews；作业名仍是“新闻事件智能解析系统”（见 REQUIREMENT.md）。题目硬性要求 B/S 架构，前端必须是浏览器。
- **需求唯一来源**：REQUIREMENT.md。PPT 与本文件冲突时以 REQUIREMENT.md 为准；创新点不算需求。
- 项目当前状态以目录与 git 为准，本文件不复述架构细节。

## 2. 技术栈

- 后端 Python 3.11+ / FastAPI；前端原生 HTML + CSS + JS；数据库 SQLite。
- 文字模型统一用 **DeepSeek**（OpenAI 兼容 API）；`base_url`/`model`/`api_key` 走配置，不写死。
- 解释器统一用 `D:\Install\anaconda3\envs\deepseek\python.exe`。
- 依赖装在该环境内，不污染 base；不引入未记录在 `requirements.txt` 的包。**唯一例外是 mineru**：它必须装在独立的 Python 3.13 环境（本环境装不上），由 `MINERU_CMD` 调用，不进 `requirements.txt`。
- **换技术栈必须先改本节并在 PLAN 中写明理由**，否则视为超范围改动。

## 3. 常用命令

```bash
python -m pip install -r requirements.txt      # 装依赖（PyPI 直连不可用时加清华镜像）
python -m uvicorn app.main:app --reload       # 起服务，浏览器开 http://127.0.0.1:8000
python scripts/warmup.py                      # 演示前预热：配置/数据库/内存/mineru/模型
python -m pytest                              # 跑测试
```

（随实现补齐；新增脚本同步本节）

## 4. 硬性约束

- **B/S 边界**：解析、调模型、存数据全在服务端；浏览器只上传、展示、编辑。前端不得直连数据库或持有 API Key。
- **密钥只写不读**：API Key 默认走 `.env`，管理员可在界面写入数据库（`settings` 表）；`.env` 与 `*.db` 必须 gitignore，界面只回显掩码，日志、报告、导出文件都不得出现明文。代码里不出现任何明文 key。
- **模型输出不可信**：LLM 返回必须过 schema 校验 + 失败重试，禁止把原始输出直接塞进 DOM。
- **长任务异步**：解析与分析走后台任务，状态落库（`pending/parsing/analyzing/done/failed`），前端轮询；请求内不做长耗时操作。
- **数据库是唯一事实来源**：页面刷新、重启后数据不丢；报告编辑后必须持久化。
- **删除优先**：重构要删掉被取代的文件、字段、分支；不写 `_old` / `_v2` / 兼容壳，删完全库搜索确认无残留。
- **量级约束**：单文件 ≤300 行，单函数 ≤120 行；超了就拆，不继续堆。
- 代码与注释用英文，用户可见文案用中文。

## 5. 验收对齐

- 每条"基本要求"都要有可现场演示的路径，逐条对照 REQUIREMENT.md §4 自查。
- **演示机必须预热**：mineru 依赖与模型权重、示例 PDF、API Key 全部提前跑通；现场首次下载视为事故。
- 行为变化同步更新 PLAN 与 REQUIREMENT.md 的偏差记录；不在 README 里堆开发细节。

## 6. 提交

- 提交信息：`<范围>：<一句话变更>`（如 `backend：解析任务改为轮询状态`）。
- 不提交：`.env`、`*.db`、上传的 PDF、解析产物、模型权重、虚拟环境。
