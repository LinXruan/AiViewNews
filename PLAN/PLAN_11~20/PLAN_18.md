# PLAN 18 — Pandoc 导出 DOCX、各栏可伸缩

日期：2026-11-18　｜　状态：已完成

## 1. 需求

1. 用 **Pandoc** 把报告 Markdown 转 DOCX，可执行文件路径写进管理员控制台（与 mineru 一致的维护方式）。
2. 给各栏加拖拽伸缩，**正文顶部 PDF 标签栏除外**：
   - 历史侧边栏：横向
   - 侧边栏 2（记录/时间线）：横向
   - 侧边栏 2 内的询问框：纵向（替换 textarea 原生右下角手柄）
   - 报告页：编辑区与预览区之间的横向分隔
3. 询问框伸缩改为"顶部拖拽条"，解析按钮与右下角对齐。
4. 所有伸缩交互统一成"简介显示栏"那一套；同时修掉两个已知问题：
   - 拖拽时会意外选中文字；
   - 选中文字后触发的自动滚动（`reader.js:280` 的 `scrollIntoView`），拖拽期间不得被触发。

## 2. 环境

本机已存在两份 pandoc：`C:\Program Files\Pandoc\pandoc.exe`（3.9.0.2，独立安装）与 `D:\Install\anaconda3\Library\bin\pandoc.exe`（3.8，conda）。默认指向前者，不新增系统安装。

## 3. 方案

### 3.1 后端：配置与导出

- `app/services/settings.py`：新增 `export.pandoc` 默认空；`ENV_NAMES` 映射 `PANDOC_CMD`；`public()` 增加 `export.pandoc`。
- `app/config.py`：新增 `pandoc_cmd()`。
- `app/services/exporter.py`：
  - `export_docx(title, content_md)` 优先走 pandoc：`[pandoc, "-f", "markdown", "-t", "docx", "-o", <temp.docx>]`，正文经 stdin 传入；Markdown 开头若无 `# 标题` 则自动补一行；
  - pandoc 未配置 / 找不到 / 非零退出 → 回退现有 python-docx 实现（保留为 `_export_python_docx`），保证现场不会因为外部依赖崩掉；
  - 子进程 60s 超时，失败把 stderr 摘要打进日志（不含密钥）。
- `app/api/admin.py`：`SettingsPayload` 增加 `export`；`put_settings` 写 `export.pandoc`；新增 `GET /api/admin/settings/detect-pandoc`（配置值、`shutil.which`、`Program Files/Pandoc`、conda `Library/bin` 四类候选）。
- `.env.example` 增加 `PANDOC_CMD=`。
- `scripts/warmup.py`：加一项 pandoc 可用性检查。

### 3.2 前端：管理员面板

- `web/index.html` 系统设置区新增「Pandoc 可执行文件路径」输入 + 「自动探测 pandoc」按钮 + 候选列表。
- `web/views/admin.js`：`fillSettings` / `payload` 带上 `export.pandoc`，新增 `detectPandoc()`。

### 3.3 前端：统一伸缩组件

新增 `web/resize.js`：`App.resizer`，一个入口覆盖横向与纵向，行为与简介栏一致。

```
App.resizer.bind()   // 启动时调用一次，按 data-resize 属性挂载
```

- 手柄元素用 `data-resize="history|records|query|report|summary"`，目标元素由组件查表决定。
- `pointerdown`：`preventDefault()`、清空当前选区（`getSelection().removeAllRanges()`）、`setPointerCapture`、给 `body` 加 `is-resizing`。
- `pointermove`：按轴向改目标尺寸（`flex-basis` / `height` / `--editor-col`），夹在 min/max 之间；拖拽期间给目标加 `no-transition`。
- `pointerup / pointercancel`：解除捕获、移除 `is-resizing`、写 `localStorage`（键 `layout.history` 等）。
- `body.is-resizing { user-select: none; cursor: col-resize|row-resize }`：这是"拖拽时选中文字"的根治手段。
- 恢复：`bind()` 时读 localStorage 并应用；窗口 `resize` 只做上限夹取，不写回。
- **不注册任何与选区相关的滚动逻辑**；`reader.js:280` 的 `scrollIntoView` 增加守卫：`body.is-resizing` 时直接返回。

### 3.4 各栏接入

| 区域 | 手柄位置 | 轴 | 范围 | 存储键 |
| --- | --- | --- | --- | --- |
| 历史侧边栏 | 右边缘 6px | X | 220–420px | `layout.history` |
| 记录侧边栏 | 右边缘 6px | X | 260–520px | `layout.records` |
| 询问框 | textarea 上方 8px | Y | 96–320px | `layout.query` |
| 报告页 | 编辑区与预览区之间 6px | X | 320px–(宽-320) | `layout.reportEditor` |
| 简介显示栏 | 保持现状（改为走同一组件） | Y | 120–60vh | `layout.summary` |

- 侧边栏 `position: relative`，手柄 `.rail-resize` 绝对定位在右边缘，`cursor: col-resize`，hover 变色；收起态隐藏手柄。
- 询问框：`.query-form` 顶部加 `.query-resize`；textarea `resize: none`；高度用 `--query-h` 变量。
- 解析按钮：`right: 8px; bottom: 8px` 不变，改为 `display: grid; place-items: center` 并给 ▶ 加 `padding-left: 2px` 视觉居中，与右下角对齐。
- 报告页：`.report-grid` 由两列改为 `var(--editor-col, 1fr) 6px minmax(0, 1fr)`，中间插入 `.report-split`；编辑器/预览保持原有样式。

## 4. 文件清单

改动：
- `app/services/settings.py`、`app/config.py`、`app/services/exporter.py`、`app/api/admin.py`
- `scripts/warmup.py`、`.env.example`
- `web/index.html`、`web/style.css`、`web/layout.css`、`web/records.css`、`web/report.css`、`web/reader.css`
- `web/app.js`（挂载 resizer）、`web/views/admin.js`、`web/views/reader.js`（scrollIntoView 守卫）

新增：
- `web/resize.js`
- `PLAN/PLAN_11~20/PLAN_18.md`（本文件）

## 5. 验证（已完成）

- `pytest` 24 passed（导出用例改为两引擎兼容）；`node --check` 通过。
- Pandoc 实测：`C:\Program Files\Pandoc\pandoc.exe` 转换中文报告输出 11KB docx，标题/章节/列表/表格正确，表格是真正的 Word 表格（旧实现拍平成文本）。
- 控制台填入路径 → 保存 → 提示「已保存」，刷新后路径仍在。
- 浏览器实测四个手柄：历史栏、侧边栏 2、询问框、报告分栏均可拖动，刷新后尺寸保持；拖拽过程中不再选中正文。
- 询问框改为顶部 10px 拖拽条（带渐变提示），解析按钮保持在右下角。

### 5.1 实施中修正

- 手柄命中区从 6px 加宽到 10px（`right: -3px`）；`query-resize` 原本用绝对定位压不住 textarea，改为表单内常规流元素。
- 拖拽结束若落在按钮上会触发该按钮 click（实测会误开时间线简介），已在 `resize.js` 里用一次性捕获监听拦掉。
- 报告分栏的测量对象是 `#report-editor`，不是 grid 容器，否则起拖尺寸错误。

## 7. 回退

- Pandoc 相关为新增可选项，`export.pandoc` 清空即回到 python-docx；不改数据库结构。
- 伸缩为纯前端新增文件与样式，回退删除 `web/resize.js` 与手柄元素即可恢复固定布局。
