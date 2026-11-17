# PLAN 2 — 项目骨架与配置

日期：2026-11-17　｜　阶段：M0

## 1. 需求

服务能起来、能建库、能托管前端静态页，且所有密钥走配置。这一份只搭地基，不含业务。

## 2. 方案

- FastAPI + `uvicorn app.main:app --reload`，开发期固定 127.0.0.1:8000；打包后改为**扫空闲端口**再打开浏览器，并加单实例锁（PLAN.md §12）。
- **路径统一走 `app/paths.py`**：`DATA_DIR` 默认项目下 `data/`，打包后可切到 `%LOCALAPPDATA%`。所有可写目录（DB、uploads、parsed、logs）都从这个模块取，代码里不出现 `Path(__file__).parent` 硬拼——这是为将来打包留的口子（PLAN.md §12）。
- 配置分层：`settings` 表 > `.env` > 内置默认值，统一由 `app/config.py` 暴露（见 PLAN_12）。`.env` + `python-dotenv` 只作初始播种，读取值如下：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`ADMIN_USERNAME`、`ADMIN_PASSWORD`、`DATA_DIR`、`MINERU_CMD`。
- 启动时（FastAPI `lifespan` 钩子，不用已废弃的 `on_event`）：建 `data/` 目录 → 执行 `app/schema.sql` 幂等建表 → 播种管理员账号 → 重置中断状态。
- **SQLite 必须开并发参数**：`journal_mode=WAL`、`busy_timeout=5000`、`foreign_keys=ON`；连接按线程隔离（`threading.local`），不共享全局 connection。后台解析线程与 Web 请求会同时写库，不开 WAL 迟早撞 `database is locked`，而且这种错在演示时最容易被撞上。
- 静态文件：`/` 映射 `web/index.html`，`/static` 映射 `web/`；上传目录不进静态路由，只能走接口。
- 只有一份 `requirements.txt`，**不记录 mineru**——它装在独立 Python 3.13 环境，用一条 conda + pip 命令安装，App 只通过 `MINERU_CMD` 调它。以前写的 `requirements-mineru.txt` 是自相矛盾的（一个文件喂两个环境），删掉。
- 依赖克制：**不装 pdfplumber**。应用只需要 `pymupdf`（页数、文本、图片）；pdfplumber 是我读 PPT 用的工具，不进运行时，省 10MB 与一层 pdfminer 依赖。
- **mineru 走独立环境（不是兜底，是主路径）**：`deepseek` 环境是 Python 3.15.2，装不上 mineru。实测其 `requires-python` 有**上界**——4.2.3 为 `>=3.11,<3.15`，2.x 系列为 `>=3.10,<3.14`。因此单独建一个 **Python 3.13** 的 conda 环境（`conda create -n mineru python=3.13`，4.x 支持、离上界 3.15 有余量），装 `mineru[core]`，`MINERU_CMD` 指向该环境的 `python.exe`。解析只走子进程 CLI，业务代码零感知。
- 题目 PPT 写的 "Python 版本：3.10" 是当年验证过的规格条目，不是硬性等值要求；选 3.13 的原因写在此处，答辩被问时照此解释。

## 3. 目录

```
app/    main.py  config.py  paths.py  db.py  schema.sql  models.py  errors.py
        api/     auth.py documents.py tasks.py reports.py admin.py settings.py
        services/ parser.py analyzer.py chunker.py exporter.py settings.py
        workers.py
web/    index.html app.js style.css
data/   uploads/ parsed/ db.sqlite3   （gitignore）
tests/
```

## 4. 文件

新建上表全部骨架文件（业务函数留空或抛 NotImplemented）、`requirements.txt`、`.env.example`、`.gitignore`。

## 5. 验证

1. `python -m uvicorn app.main:app --reload` 无报错。
2. 浏览器打开 `http://127.0.0.1:8000` 返回首页；`GET /api/health` 返回 200。
3. `data/db.sqlite3` 生成，**七张表**齐全（users / documents / tasks / task_documents / events / reports / settings），`users` 里有管理员。
4. 重启两次不报错（建表幂等）。

## 6. 回退

删除 `app/`、`web/`、两份 requirements、`.env.example`，项目回到只有文档的状态。