# PLAN 5 — DeepSeek 分析与事件抽取

日期：2026-11-17　｜　阶段：M2　｜　状态：已实现

## 1. 需求

基本要求 §4.3 / §4.5：按查询从已解析文档中抽取事件，并生成时间线摘要。输出必须结构化、可校验、可重试。

## 2. 方案

> 调用形态、上下文预算与格式失败处理见 [PLAN_11](PLAN_11.md)，本文只写业务编排。

**实现偏差**：配置快照暂从 `.env` 读取（PLAN_12 落地后切到 `settings` 表）；分块并发 4 路与局部重试已实现；单任务 10 分钟硬超时未单独计时，依赖单块 60 秒超时与 60 个分块预算（局部重试的额外调用另计）。

- 接口 `POST /api/tasks`：校验 doc 全部 `parsed` → 建 task(`pending`) → 入后台队列。
- **配置快照**：任务开始时从 `settings` 取一次 `base_url / model / api_key / temperature / timeout`，整个任务用同一份；中途改配置只影响新任务（PLAN_12）。
- **分块**（`services/chunker.py`）：按 md 标题切，单片 ≤6000 字符；超长段落用 200 字符重叠滑动窗口。每块记录起始偏移，用于回推全文位置。
- **调用**（`services/analyzer.py`）：OpenAI SDK 指向 `DEEPSEEK_BASE_URL`，`model` 取配置，`response_format={"type":"json_object"}`，`temperature=0.2`，超时 60s。
- **并发**：同一任务内分块并发 4 路（`asyncio.gather` + `Semaphore(4)`），耗时从 N×t 降到约 N/4×t；遇 429 指数退避后重试。
- **Prompt**：system 段固定 schema + 四条硬要求——只输出 JSON、时间必须是绝对日期（无法确定填 null）、`source_quote` 必须逐字来自给定文本、不得编造。user 段给查询 + 分块正文。
- **相关性筛选**：prompt 明确"只抽与查询相关的事件，无关返回空数组"。不加这条，一次查询会把全文事件全抽出来，任务列表的"事件数量"就没有意义了。
- **校验与重试**：按 PLAN_11 §4 的五层防御执行——约束 → 解析容错 → 字段归一化 → 局部重试（最多 2 次）→ 降级。**局部成功要保住**：只重试不合格的条目，不整块重来。
- **eid 后端生成**：`<doc_id>-<块序号>-<块内序号>`，不使用模型返回的 id（跨块必重复）。
- **合并去重**：按 `归一化(event_text) + event_time` 组合键去重，保留最先出现的 offset；`order_index` 按 `event_time` 升序重排。
- **定位**：先在该分块自己的偏移区间内找 `source_quote`，**找不到再扩到全文找**；全文里同一句话可能出现多次，先按块范围找才不会指到别的页。定位用归一化文本（去空白、统一全半角）再回查真实偏移。仍找不到就丢弃该事件并计数——编造引用比少一条事件更伤（PLAN_11 §5）。
- **页码反查**：用 `source_offset` 在 `page_offsets` 里二分，得到真实页码写入 `events.page`。模型不参与页码。
- **时间线摘要**：把合并后的事件（只给时间 + 一句话）再调一次，产出 `timeline_summary`。
- **报告**：再调一次生成 `title + sections`（固定六段，见 PLAN_1 §4），落 `reports.content_md`。事件超过 40 条时先压缩成 20 条再送模型，避免超出上下文。
- 全流程结束 task → `done`，写 `finished_at`。

## 3. 文件

- 新增 `app/api/tasks.py`、`app/services/chunker.py`、`app/services/analyzer.py`、`app/services/prompts.py`。
- 修改 `app/main.py`、`app/workers.py`。

## 4. 验证

1. 单文档 + 查询"能源价格波动"，产出 ≥5 条带时间的事件，时间升序排列。
2. 故意传错 API Key：task 变 failed，`error` 有可读原因，页面不白屏。
3. 重复建两个任务查同一文档，事件不串（各自 task_id 隔离）。
4. 模型返回裹了 ```json 代码块时仍能解析（剥壳逻辑生效）。
5. 某事件 `source_quote` 被模型改写导致定位失败时，接口返回 offset=null 且不报错。

## 5. 回退

删除 `tasks.py`、`chunker.py`、`analyzer.py`、`prompts.py`，`tasks` 保持 pending；前端任务列表仍可展示。