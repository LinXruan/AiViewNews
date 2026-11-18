# PLAN 17 — 修复正文路径丢失、报告页改为 Obsidian 式实时预览编辑

日期：2026-11-18　｜　状态：3.1 / 3.2 已完成；3.3（报告页三模式）已按用户要求回退

## 1. 需求

1. **Bug**：登录后打开历史，正文区显示「正文加载失败：文档尚未解析完成」，但时间线与报告页正常。
2. 正文页右上角按钮「保存」改名「报告」。
3. 报告页取消「左编辑 + 右预览」分栏，改为单栏 Obsidian 式编辑器，三模式切换：
   - **实时预览**（默认）：整篇按渲染结果展示，光标进入哪一块，哪一块退回源码（块级标记淡化），失焦即复原；
   - **源码模式**：全文原始 Markdown，可编辑；
   - **渲染模式**：全文渲染，不可编辑。
4. 保存方式沿用现状：手动点「保存」落库，有未保存修改时离开需确认。
5. 许可证、README 等文档层不动。

## 2. 根因

`documents.md_path` 存的是绝对路径。项目目录由 `PDFAiReader` 改名为 `AiViewNews` 后，库里三条记录仍指向旧目录：

```
C:\...\Assignment\PDFAiReader\data\parsed\<id>\full.md   （不存在）
```

真实文件在 `data/parsed/<id>/full.md`。`read_markdown` 直接 `Path(md_path).read_text()` → `FileNotFoundError` → `api/documents.py:128` 转成 409「文档尚未解析完成」。时间线与报告读 `events` / `reports` 表，不受影响。

## 3. 方案

### 3.1 正文路径改为按 doc_id 推导（不再入库）

- `app/schema.sql`：删除 `documents.md_path` 列。
- `app/db.py`：新增 `_drop_md_path(conn)`，用 `PRAGMA table_info` 判存在再 `ALTER TABLE documents DROP COLUMN md_path`，在 `init_db` 两个分支都调用（幂等，不升 SCHEMA_VERSION、不删数据）。
- `app/services/documents.py`：
  - `mark_parsed(doc_id, page_count, char_count, page_offsets)`（去掉 md_path 参数与 SQL 字段）；
  - `read_markdown(doc_id)` → `paths.PARSED_DIR / str(doc_id) / "full.md"`，文件不存在仍抛 `FileNotFoundError`；
  - 新增 `markdown_path(doc_id)` 供 `read_markdown` 与测试共用。
- 调用点同步：`app/services/parser.py:180`、`app/api/documents.py:126`、`app/services/analyzer.py:76`、`app/services/histories.py:64`。
- `app/api/documents.py` 的 409 文案改为「正文文件缺失，请重新上传该 PDF」，与"尚未解析"区分开。
- `web/views/reader.js`：`loadDoc` 失败只替换正文区文字，不再让整页不可用；文档 tab 保留，可切到其他文档。

### 3.2 stored_path 兜底（可选，3 行）

读取处统一 `paths.UPLOAD_DIR / Path(stored).name`：新记录写相对文件名，旧记录取 basename 自动兼容，不动表结构、不加迁移。改 `parser.py` 与 `histories.py` 两处取路径的位置。

### 3.3 报告页三模式编辑器

**结构**（`web/index.html`）

- `header.report-head`：← 返回 ｜ 分析报告 ｜ 分段控件「实时预览 / 源码 / 渲染」 ｜ 保存 ｜ 下载 DOC。
- 主体由 `.report-grid` 改为单栏 `#report-doc`（正文容器）+ 渲染模式的 `#report-source`（textarea，默认 hidden）。
- 状态条 `#report-status` 保留。

**模型**（新增 `web/markdown.js`，纯前端，不含业务）

- `MD.splitBlocks(text)`：按空行切块，返回 `[{start, end, raw}]`；表格、围栏代码块、连续列表项各视为一块（与空行语义一致，不重排原文）。
- `MD.joinBlocks(blocks, text)`：按偏移把改动块写回整篇字符串，保持未改动区域字节不变。
- `MD.visibleIndex(raw, visibleOffset)`：把点击处的可见字符偏移映射回 raw 偏移（跳过 `#`、`- `、`> `、`| ` 等块级标记），用于定位光标。

**渲染**（新增接口，避免前后端两套 Markdown）

- `POST /api/render/blocks`：入参 `{blocks: [string]}`（≤200 块，单块 ≤20000 字符），返回 `{html: [string]}`，逐块调用 `markdown_renderer.render`。
- 现有 `POST /api/render` 保留（管理台在用）。

**交互**（`web/views/report.js`）

- 打开：拉 `GET /api/tasks/{id}/report` → 切块 → 批量渲染 → 每块 `div.md-block[contenteditable]`，`data-index` 记块号。
- 聚焦（`focusin`/`mousedown`）：`caretRangeFromPoint` 取可见偏移 → `MD.visibleIndex` → 该块 `textContent = raw`（`is-editing` 类，`##` 等块级标记用 `.md-mark` 包裹淡化）→ 光标落到映射位置。
- 失焦：写回模型 → 只重渲染该块（单块请求），恢复渲染态。
- 回车：拦截 `keydown`，在光标处把该块拆成两块（`\n\n` 分隔），渲染新块并把光标放到新块开头。
- 块首 Backspace 且块非空首行：与上一块合并。
- 源码模式：`#report-source` 展示整篇 raw，等宽字体，`input` 同步模型；切回实时预览时重新切块渲染。
- 渲染模式：`POST /api/render` 整篇渲染写入 `#report-doc`，去 `contenteditable`，只读。
- 保存：手动；成功后状态条显示「已保存 · 时间」；切模式不触发保存；有未保存改动时「返回」仍确认。

**样式**（`web/report.css`）

- 正文列 `max-width: 880px` 居中、白底、行高 1.8，与现有 `.report-preview` 视觉一致。
- `.md-block` 悬停淡底、`is-editing` 时保留块级排版（标题仍是大字），`.md-mark` 用 `--muted`。
- 分段控件沿用 `.auth-tabs` 的胶囊风格（同一套变量：`--accent`、`--line`、`--surface`）。

### 3.4 其他

- `web/index.html` 静态资源版本 `?v=19` → `?v=20`，并引入 `/static/markdown.js`。
- 单文件 ≤300 行、单函数 ≤120 行：`report.js` 按「模式 / 块操作 / 保存」拆内部对象，超限则再拆 `web/views/report-blocks.js`。

## 4. 文件清单

改动：
- `app/schema.sql`、`app/db.py`、`app/services/documents.py`、`app/services/parser.py`、`app/services/analyzer.py`、`app/services/histories.py`
- `app/api/documents.py`、`app/api/reports.py`
- `web/index.html`、`web/report.css`、`web/views/report.js`
- `tests/test_histories.py`（不再写 md_path；新增 `read_markdown` / `upload_path` 断言）

注：`web/views/reader.js` 未改——`loadDoc` 失败时本来就只替换正文区文字、文档 tab 保留，实测行为符合预期。

新增：
- `web/markdown.js`（切块 / 偏移写回 / 点击偏移映射）
- `web/views/report-blocks.js`（块编辑、回车拆块、退格合并；以 mixin 方式并入 `App.report`）
- `PLAN/PLAN_11~20/PLAN_17.md`（本文件）

## 5. 验证（已完成）

1. **真实库迁移**：`init_db()` 后 `PRAGMA table_info(documents)` 已无 `md_path`；`read_markdown(1)` 返回 582 字符（改前抛 `FileNotFoundError`）。
2. **改名不再复发**：新增单测断言 `read_markdown` 只依赖 doc_id，且 `upload_path` 取 basename。
3. `python -m pytest` → 24 passed（原 23 + 新增路径用例）；`node --check` 三个前端文件语法通过。
4. **浏览器手测**（临时 `DATA_DIR` 起 8011，Edge 实机）：
   - 正文正常加载，右上角按钮显示「报告」；
   - 实时预览：点块出源码（`##` 淡化）、失焦复原、回车拆块、三种模式互切；
   - 源码模式：全文原始 Markdown；渲染模式：全渲染且点击不进编辑；
   - 保存后状态条显示时间，行内 `**加粗**` 在多次进出编辑后未丢失。
5. 文档流回归：管理台任务详情仍走 `/api/render`，接口未改动。

## 6. 回退

- 3.1/3.2 为后端独立改动，`git revert` 该提交即可；旧 `md_path` 列已删，回退需重新解析文档（PDF 已 purge，故回退后旧正文不可读，属预期）。
- 3.3 为前端重写，回退到分栏版即恢复旧 `report-grid`；按"删除优先"不保留双实现。

## 7. 修订记录

**2026-11-18 回退 3.3**：Obsidian 式三模式编辑实测在 contenteditable + innerText 回写链路上有多处操作缺陷（标记丢失、光标跳位、跨块选区与撤销失效），根因是缺少统一文本模型，修补无底。经确认放弃该路线，报告页恢复为「左编辑、右预览」两栏：

- 删除 `web/markdown.js`、`web/views/report-blocks.js`；
- `web/views/report.js`、`web/report.css` 回退到 3.3 之前版本；
- `web/index.html` 恢复 `.report-grid` + `#report-editor` / `#report-preview`，移除模式控件与两个脚本引用；
- 删除随之无用的接口 `POST /api/render/blocks` 与 `BlocksPayload`；
- 3.1（正文路径）与 3.2（upload_path）保留，正文页「报告」按钮保留。

## 8. 本期不做

- 报告自动保存（按用户决定保持手动）。
- 图片 / 链接 / 嵌套列表的实时预览编辑（当前渲染器也不支持，保持现状）。
- 表格的单元格级编辑：表格整块视为一个块，编辑时显示整张表的源码。
