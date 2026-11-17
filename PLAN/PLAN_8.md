# PLAN 8 — 报告编辑、预览与 DOC 导出

日期：2026-11-17　｜　阶段：M4　｜　状态：已实现

## 1. 需求

基本要求 §4.6：报告内容可实时编辑，保存后实时在预览区看到编辑结果。§4.7：报告可下载保存为 DOC 等格式。选做 4：报告要有清晰的结构化标题。

## 2. 方案

- 报告以 Markdown 为唯一存储格式（`reports.content_md`），标题层级来自分析阶段的 `sections`。
- 界面左右分栏：左侧 textarea 编辑、右侧预览；输入防抖 300ms 后请求 `POST /api/render`（服务端 markdown → HTML + 白名单清洗），避免前端引入第三方渲染库。
- 保存：`PUT /api/tasks/{id}/report`，落库并更新 `edited_at`；页面顶部显示"已保存 / 未保存"。
- 导出：`GET /api/tasks/{id}/report.docx`，用 python-docx 按 `#`/`##` 层级生成标题与段落，文件名 `<查询摘要>_分析报告.docx`。中文文件名必须用 RFC 5987 的 `filename*=UTF-8''...` 形式，否则浏览器下载会变成乱码。
- md → docx 只处理标题、段落、有序/无序列表、加粗；表格降级为逐行文本，不为导出单独实现表格布局。
- **中文字体要显式设置**：python-docx 默认 Calibri，中文会走 fallback，标题容易变成宋体/等线混排。每个 style 与 run 都要写 `w:eastAsia`（微软雅黑或宋体），否则导出的 DOC 打开像草稿。
- **重新生成不能默默覆盖编辑**：报告被人工改过（`edited_at` 非空）时，「重新生成」必须二次确认，并保留旧版本到 `reports_history` 或直接提示不可恢复。不然后台一重跑，用户半小时的修改就没了。
- 清洗白名单：`h1-h4, p, ul, ol, li, strong, em, blockquote, table, th, td, code, pre`；去掉 `script/style/iframe/on*`。

## 3. 文件

- 新增 `app/api/reports.py`、`app/services/exporter.py`、`web/views/report.js`。
- 修改 `app/main.py`、`web/index.html`、`web/style.css`。

## 4. 验证

1. 编辑后保存 → 刷新页面内容还在；`edited_at` 变化。
2. 预览区在输入后 300ms 内更新，标题层级正确显示。
3. 在编辑区输入 `<script>alert(1)</script>`，预览与导出都不执行，标签被转义。
4. 导出的 DOCX 用 Word 打开：标题层级、列表、段落正常，中文不乱码。
5. 报告为空时导出不报 500，得到一个只含标题的空文档。

## 5. 回退

报告改为只读（隐藏编辑区与保存按钮），导出保留；删除 `web/views/report.js` 的编辑逻辑。