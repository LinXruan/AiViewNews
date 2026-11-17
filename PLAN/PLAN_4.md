# PLAN 4 — 文档上传与 mineru 解析

日期：2026-11-17　｜　阶段：M1

## 1. 需求

基本要求 §4.2：支持不少于 3 个 PDF 同时上传。上传后要变成可检索的纯文本（`parsed_md`），供后续分析使用。解析只做一次，与查询解耦（见 PLAN.md §4）。

## 2. 方案

- 接口 `POST /api/documents`：multipart 多文件，校验扩展名 + `%PDF` 魔数 + 单文件 ≤50MB，落盘为 `data/uploads/<uuid>.pdf`，插库 `pending`。
- **并发策略**：允许 3 个文件同时上传并各自返回，但解析走单线程队列（`ThreadPoolExecutor(max_workers=1)`）。mineru 单进程就要吃掉大半内存（本机 15.8GB，当前仅余 4.2GB），并发解析必崩。
- 解析器 `services/parser.py`：调 mineru CLI（命令、后端与设备均从设置读取，见 PLAN_12；`.env` 只作兜底）产出到 `data/parsed/<doc_id>/`；把 `*.md` 按文件名排序拼接后**写成 `full.md` 落盘**，库里只存 `md_path`，不把全文塞进数据库。
- 图片统一落到 `data/parsed/<doc_id>/images/`，md 中的引用改写为 `/api/documents/<id>/assets/<name>`，前端不直连文件系统。
- 用 `pymupdf` 取 `page_count`，并在拼接 full.md 时**逐页记录区间**，落 `page_offsets`（`[[start,end],…]`）。不靠模型猜页码、也不靠解析器给的不可靠分页标记——这是页码的唯一来源。
- 子进程必须设超时（600s）并在超时后**杀进程树**：Windows 上 `process.kill()` 只杀父进程，mineru 的子进程会残留吃内存，要用 `taskkill /T /F`。解析前先检查是否已有残留 mineru 进程。
- 状态：进入队列前 `parsing`，成功 `parsed`，异常 `failed` 并把 stderr 尾部写 `parse_error`。
- 启动时把所有 `parsing` 重置为 `pending` 重新入队（进程被杀不留僵尸状态）。

**风险与取舍**：mineru 的具体调用方式以任务书附录示例为准，版本差异只影响 `parser.py` 一个文件；不在业务代码里直接引用 mineru 的 Python API，统一走 CLI 子进程，便于换版本和隔离环境。

## 3. 文件

- 新增 `app/api/documents.py`、`app/services/parser.py`、`app/workers.py`（队列与状态重置）。
- 修改 `app/main.py`（注册路由、启动钩子）。

## 4. 验证

1. 一次选 3 个不同排版的 PDF 上传：三个文档依次从 pending → parsing → parsed，页面可轮询看到。
2. `full.md` 非空且含正文，`md_path` 可读；抽出的图片通过 `/api/documents/{id}/assets/...` 能打开；`page_count` 与 PDF 实际页数一致。
3. 上传一个非 PDF（改后缀）返回 400；上传 60MB 文件返回 413。
4. 解析中途 `Ctrl+C` 杀进程再启动，该文档回到 pending 并被重新解析，最终 parsed。
5. `page_offsets` 长度等于 `page_count`，且首尾连续无缝、无重叠；构造一篇 5 页 PDF 验证第 3 页的首字符偏移落在该页区间内。
6. 构造超时场景（把 `MINERU_CMD` 指向一个 `timeout` 脚本）→ 600s 后任务 failed，任务管理器里无残留 mineru 进程。

## 5. 回退

删除 `documents.py`、`parser.py`、`workers.py`，上传接口下线，`documents` 表保留但不再推进状态。