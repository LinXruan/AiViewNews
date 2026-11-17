# PLAN 1 — 数据模型与接口契约（v2，已评审修订）

日期：2026-11-17　｜　阶段：M0

> 2026-11-18 PLAN 14 变更：新增 `histories`；`documents/tasks` 增加 `history_id`；建任务改为传 `history_id`；PDF 解析后删除。本文旧表结构以 PLAN_14 为准。

## 1. 需求

写业务代码之前先把三件事定死：表结构、两套状态机、DeepSeek 的 JSON 契约。后续所有计划按本文件实现；改契约必须先改这里并通知。

## 2. 表结构（SQLite）

```sql
users(id INTEGER PK, username TEXT UNIQUE, password_hash TEXT,
      role TEXT CHECK(role IN ('user','admin')), created_at TEXT)

documents(id INTEGER PK, user_id INTEGER, filename TEXT, stored_path TEXT,
          md_path TEXT, page_count INTEGER, char_count INTEGER, page_offsets TEXT,
          parse_status TEXT CHECK(parse_status IN ('pending','parsing','parsed','failed')),
          parse_error TEXT, created_at TEXT)

tasks(id INTEGER PK, user_id INTEGER, query TEXT,
      status TEXT CHECK(status IN ('pending','analyzing','done','partial','failed')),
      timeline_summary TEXT, error TEXT, created_at TEXT, finished_at TEXT)

task_documents(task_id INTEGER, doc_id INTEGER, PRIMARY KEY(task_id, doc_id))

events(id INTEGER PK, task_id INTEGER, doc_id INTEGER, eid TEXT,
       event_text TEXT, event_time TEXT, page INTEGER,
       source_offset TEXT, source_quote TEXT, order_index INTEGER, created_at TEXT)

reports(id INTEGER PK, task_id INTEGER UNIQUE, title TEXT,
        content_md TEXT, created_at TEXT, edited_at TEXT)

settings(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT, updated_by INTEGER)
```

三条落库决定：

- **解析全文不入库**：`parsed_md` 存 `data/parsed/<doc_id>/full.md`，库里只存 `md_path`。理由：一篇新闻 PDF 可能几十万字符，塞进 TEXT 会让 `SELECT * FROM documents` 把整个正文拖进列表接口，越用越慢。
- `source_offset` 存 JSON `{"start":n,"end":n}`，基准是 `full.md`，不是源 PDF 字节。
- `eid` 由**后端**生成（`<doc_id>-<块序号>-<块内序号>`），模型只给内容不给 id。理由：模型编的 id 跨块必然重复，合并时无法去重。

时间统一 TEXT + ISO8601（SQLite 无 datetime 类型）。

外键列建索引：`documents(user_id)`、`tasks(user_id)`、`events(task_id)`、`events(doc_id)`、`task_documents(doc_id)`。选做 2 把"良好的数据库设计"列为加分项，报告里要附这张 ER 图。

## 3. 状态机

```
documents: pending -> parsing -> parsed | failed
tasks:     pending -> analyzing -> done | partial | failed
```

两套独立。建任务前必须校验所选文档全部 `parsed`，否则 409。进程重启时把所有 `parsing` / `analyzing` 重置为 `pending`。

`partial` = 大部分分块成功、少数块放弃（见 PLAN_11 §4）。前端按"成功但可能不全"展示，不能当失败处理——否则一次局部漂移会让整条任务看起来挂了。

## 4. LLM JSON 契约

事件抽取（对单个分块）：
```json
{"events":[{"event_text":"...","event_time":"2024-03-05","source_quote":"逐字原文片段，不超过120字"}]}
```
时间线摘要与报告：
```json
{"timeline_summary":"不超过300字"}
{"title":"...","sections":[{"heading":"事件概述","content":"..."}]}
```

**关键决定：页码也不让模型输出。** 模型看到的只是某个分块的文字，它无从知道这是第几页——让它填 page 只会得到编造值。正确做法：解析时生成 `page_offsets`（`[[start,end],…]`，每页在 full.md 中的区间），事件定位到偏移后用二分查表反查页码。模型只负责 `source_quote` 与 `event_time`。

**关键决定：不让模型输出 offset。** 模型给 `source_quote` + `page`，后端在 full.md 里检索 quote 定位并算 offset；检索不到则 offset 置 null，前端降级为只显示 quote。

**报告章节固定为六段**，既满足选做 4 的结构化，也顺手拿下选做 5：
`事件概述 / 关键节点 / 各方立场 / 影响分析 / 趋势预测 / 不确定性说明`。
预测段在 prompt 中强制要求"基于事实、标注为推断"，避免模型编造确定结论。

## 5. HTTP 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /api/health | 存活检查 |
| POST | /api/login · /api/logout | 会话 |
| GET | /api/me | 当前用户与角色 |
| POST | /api/documents | 多文件上传，返回文档列表 |
| GET | /api/documents | 文档列表 + parse_status |
| GET | /api/documents/{id}/text | 解析全文分页切片（溯源视图用） |
| GET | /api/documents/{id}/assets/{name} | mineru 抽出的图片 |
| POST | /api/tasks | 建分析任务（doc_ids + query） |
| GET | /api/tasks | 任务列表，每条附 `event_count` 与 `event_titles`（前 3 条摘要） |
| GET | /api/tasks/{id} | 任务详情 + 状态（轮询） |
| GET | /api/tasks/{id}/events | 事件列表 |
| GET/PUT | /api/tasks/{id}/report | 报告读取 / 保存 |
| GET | /api/tasks/{id}/report.docx | 导出 DOC |
| POST | /api/render | Markdown → 清洗后的 HTML（报告实时预览） |
| GET | /api/admin/users | 管理员：用户列表与计数 |
| POST/PATCH | /api/admin/users · /api/admin/users/{id} | 新建用户 / 改角色 |
| GET | /api/admin/tasks | 管理员：全量任务 |
| GET/PUT | /api/admin/settings | 运行时配置读写（key 只写不读，见 PLAN_12） |
| POST | /api/admin/settings/test-llm · test-parse | 连通性测试 |
| GET | /api/admin/settings/detect-mineru | 扫描 PATH 与 conda 环境中的 mineru |
| GET | /api/admin/tasks/{id} | 管理员只读查看单个任务、事件与报告 |
| GET | /api/setup/status | 引导状态（三个布尔值） |
| GET/POST | /api/setup/admin | 首个管理员的状态查询与创建（仅本机、仅 `users` 表为空时，见 PLAN_3） |

两条约定：

- 除 `/api/admin/*` 外，所有查询默认限定当前用户，`user_id` 从会话取，**不接受前端传入**。建任务时还要逐个校验 `doc_ids` 全部属于当前用户，否则 403——只靠列表过滤挡不住直接构造 doc_id 的越权请求。
- `/api/render` 也要求登录（`require_user`），不开匿名入口。
- `event_titles` 由 `events.event_text` 截断 30 字派生，不新增字段——需求里的"事件名称"就是事件的一句话摘要。

## 6. 错误约定

统一 `{"error":{"code":"...","message":"..."}}`；4xx 客户端错，5xx 服务端错；后台任务失败原因落 `tasks.error`。

## 7. 文件

纯文档改动。落地时对应 `app/schema.sql` 与 `app/models.py`。

## 8. 验证

- 六字段下限与 REQUIREMENT §6.1 对齐：`id`↔event_id、`doc_id`、`eid`、`event_text`、`source_offset`、`created_at`↔create_time。
- 需求 §4.4 的五个任务字段全部有来源：查询内容（tasks.query）、事件数量（count）、事件名称（event_titles）、查询时间（created_at）、任务状态（status）。
- 每个状态转换都有触发它的接口或后台动作，无孤立状态。

## 9. 回退

纯文档，无需回退；契约变更时在 PLAN 中追加勘误段，不覆盖历史。