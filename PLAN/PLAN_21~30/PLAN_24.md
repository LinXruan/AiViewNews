# PLAN 24 — 手机端 UI 适配（平板后续）

日期：2026-11-18　｜　状态：已完成

> 用真机 adb 调试手机端布局。只做手机（≤760px）；平板（761–1024px）另立 PLAN。
> 本批以 CSS 为主，不改任何 JS 交互逻辑、不新增接口、不动 DOM 结构。

## 1. 调试环境

- ADB：`C:\Users\Administrator\AppData\Local\Android\Sdk\platform-tools\adb.exe`（PATH 可用）。
- 设备：`192.168.1.101:5555`，型号 PJX110，Android 14，物理 1264×2780 / 560dpi（CSS viewport 约 361px）。
- 浏览器：默认 `com.jhaiian.clint`（ClintBrowser）；服务 `http://192.168.1.102:8000`（0.0.0.0:8000）。
- 截图：`adb exec-out screencap -p`，存于 `%LOCALAPPDATA%\Temp\aivn_mobile\phone_0*.png`。

## 2. 实机诊断（改前截图 phone_01 / 02 / 03 / 04 / 05 / 06 / 07）

1. **工作台三栏竖向无限堆叠**：历史栏 → 记录栏 → 正文依次铺在一个长页面里，正文要滚过两屏才能看到；区块之间无明确边界。
2. **时间线摘要被压成半行**：`layout.css` 的 760px 断点给 `.record-rail` 设 `max-height:40vh`，flex 子项被挤压，`.timeline-summary`（`max-height:110px; overflow-y:auto`）显示成上下裁切的残行。
3. **账户区位置尴尬**：`.account-box` 的 `margin-top:auto` 在自动高度下失效，头像/用户名夹在历史栏中间。
4. **正文嵌套滚动**：`.reader-body` 自身 `overflow-y:auto`，外层页面也在滚，手势容易被内层吃掉。
5. **触摸目标偏小**：运行按钮 30px、图标按钮 28px、文档标签、关闭 ×、主题分段按钮均低于 44px 建议值。
6. **文档标签行**有可见横向滚动条，`sample_energy_r…` 被截断；「报告」按钮与标签挤在一行。
7. **报告页**头部四个元素挤在一行、「下载 DOC」贴边；编辑区与预览区各自内部滚动（双滚动区）。
8. 设置弹窗、个性化面板本身居中完整、可用（phone_05/06），仅需加大控件与收紧留白。

## 3. 方案

### 3.1 集中管理手机样式（新增 `web/mobile.css`）

- 所有手机端规则集中在**一个新文件**内，用 `@media (max-width: 760px)` 包裹，链接放在样式表最后。
- 原因：现有多个 CSS 已接近 300 行上限（style 299、admin 297、records 250、report 246、settings 269），继续往各文件追加媒体查询会破约束；且平板后续可独立加 `tablet.css`，互不干扰。
- 删除 `layout.css` 里旧的 `@media (max-width: 760px)` 整段（保留 900px 断点，平板后续处理），避免两套手机规则互相覆盖。

### 3.2 工作台布局（核心）

- `.workspace`：竖向单列、`height:100vh; overflow-y:auto`——**整页只有一个滚动容器**。
- 三个区域各自限高、明确分隔（`border-bottom: 1px solid var(--line-strong)`）：
  - `.history-rail`：固定 `34vh`，flex column；`.history-list` 内部滚动，`.account-box` 固定到底部（`flex-shrink:0`），账户区不再夹在中间。
  - `.record-rail`：固定 `46vh`；`.record-list` 限高、`.query-form` 不收缩、**`.timeline-summary` 取消 max-height 完整显示**、`.timeline` 内部滚动。
  - `.reader`：`min-height:60vh`；**`.reader-body` 改为 `overflow:visible; flex:0 0 auto`**，正文随页面自然展开，消除嵌套滚动。
- 上传空状态、简介面板在手机端限高。

### 3.3 触摸与可读性

- `.icon-btn` 40px、`.run-btn` 44px、`.doc-tab` / `.new-history` / `.history-item` / `.record-item` / `.timeline-node` 增加纵向 padding 至 ≥44px 命中区。
- 输入框 `font-size:16px`（避免移动端浏览器自动缩放），主要按钮内边距加大。
- `.doc-tabs` 隐藏滚动条但保留横向滚动；`.timeline-summary` 不再裁切。
- 主题分段按钮、设置选项行、色块网格间距加大。

### 3.4 各页面窄屏收尾

- 报告页：头部 `flex-wrap`，操作按钮换行且加大；`.report-grid` 改 flex column 统一滚动，编辑区固定 `40vh`、预览区自然展开。
- 设置 / 个性化 / 账号弹窗：卡片 `max-width:100%`、padding 收紧、关闭按钮加大。
- 管理台：头部换行、卡片内边距收紧、表格保留横向滚动、控件加大。
- 登录页：留白收紧、输入框与按钮加大。
- 全站 `overflow-x:hidden` 兜底，避免横向溢出。

### 3.5 加载

- `web/index.html` 末尾引入 `mobile.css`；静态版本 `?v=30` → `?v=31`。

## 4. 文件清单

新增：

- `web/mobile.css`（手机端全部覆盖规则）
- `PLAN/PLAN_21~30/PLAN_24.md`（本文件）

改动：

- `web/layout.css`（删除旧 760px 断点）
- `web/index.html`（引入 mobile.css，版本号 → v31）

不动：所有 `.js`、`app/`、其余 CSS 内容、REQUIREMENT.md、README。

## 5. 验证结果（已完成）

- `pytest` 27 passed；`node --check` 通过；`web/mobile.css` 298 行，全站 CSS 均 ≤300。
- 真机（PJX110 / Android 14 / 1264×2780 / 暗色）adb 实机：
  - 首屏：历史栏 34vh、记录栏 52vh、正文依次排列，区块间有 1px 分隔；账户区固定在历史栏底部；时间线摘要两行完整显示，不再被挤压裁切。
  - 下滑：正文连续自然展开，整页只有一个滚动条，嵌套滚动消失。
  - 设置弹窗：三项完整、选项行与关闭按钮明显加大、卡片贴合屏幕。
  - 报告页：头部自动换行为「返回 + 标题」「保存 + 下载 DOC」两行，不再拥挤；编辑区 40vh 内部滚动、预览区自然展开。
  - 无横向溢出、无文字重叠。
- 桌面端（1536px）：`.workspace` 仍为 row、overflow hidden，mobile.css 媒体查询未生效，布局不受影响。

### 5.1 实施中修正

- mobile.css 首版 329 行，超出 300；把 12 处简单规则压成单行后为 298 行。
- 删除 layout.css 里旧的 760px 断点，手机布局统一由 mobile.css 管理，避免两套规则互相覆盖。

## 6. 回退

`git revert` 本提交即可（纯 CSS + 一行 link + 版本号）；或删除 `web/mobile.css` 并恢复 `layout.css` 的 760px 断点。无数据与接口影响。

## 7. 本期不做

- 平板（761–1024px）与横屏专门布局（后续 PLAN）。
- 手机端专门的视图切换 / 底部导航（需要 JS，超出本批范围）。
- 任何交互逻辑、DOM 结构、接口变更。
