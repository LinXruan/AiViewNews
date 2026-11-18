# PLAN 23 — 跟随系统的暗夜模式（白天 / 黑夜 / 系统）

日期：2026-11-18　｜　状态：已完成

> 全站视觉基线已完成（PLAN 20–22）。本计划只增加主题切换，不改既有业务交互。

## 1. 需求

- 新增暗夜模式，默认跟随系统。
- 入口放在「个性化」面板：白天 / 黑夜 / 系统三选一。
- 偏好存浏览器 localStorage；没有该值时按「系统」处理。
- 选「系统」时随操作系统明暗实时切换；选白天/黑夜则固定。

## 2. 现状

- 全站颜色已集中在 :root 令牌（style.css），并有少量硬编码的浅色（危险按钮、状态徽标、认证页底纹、hover 洗色等）。
- 个性化面板目前只有「更改头像背景色」；游客看不到个性化（PLAN 19 的决定）。
- 没有任何主题/外观代码。

## 3. 方案

### 3.1 主题模型与存储

- localStorage 键：theme.mode，值 light | dark | system。
- 缺失或非法值 → system。
- system 通过 matchMedia('(prefers-color-scheme: dark)') 解析为 light/dark；监听其 change，仅在当前为 system 时重绘。
- 在 html 上写 data-theme="light|dark"（用于 CSS）与 data-theme-mode（当前选择，便于调试）。

### 3.2 无闪烁加载（新增 web/theme.js）

- 脚本放在 head 中、样式表之前同步执行：先根据 localStorage + matchMedia 设置 data-theme，再加载 CSS，避免暗色用户看到白屏闪烁。
- 暴露 window.AppTheme = { get, set, resolved }：get 返回原始选择，set 写入存储并重绘，resolved 返回当前生效值。
- 不使用内联脚本，保持与现有外链脚本一致。

### 3.3 暗色令牌（新增 web/theme.css）

- :root 补充浅色默认的辅助令牌：wash / wash-soft / wash-strong / ring / focus-ring / selection / card-mark / dot-border。
- :root[data-theme="dark"] 重定义全部主令牌：纸面 #121418、表面 #191c21、浅表面 #1f2329、墨色 #e8eaee、线 #292e35、强调浅蓝 #8db0d8 等；同步 color-scheme: dark，让原生下拉/滚动条/取色器跟随。
- 暗色下的组件修正：
  - 主按钮与运行按钮改用深蓝填充（浅蓝文字令牌不适合当白字按钮底色），running 态反转；
  - 危险按钮、状态徽标四组语义色改深底浅字；
  - 认证页横线底纹改白色低透明度；
  - 游客头像、模态遮罩、分段控件选中态、滚动条做暗色适配。

### 3.4 接入现有样式

把散落的浅色硬编码换成辅助令牌，保证暗色下 hover、焦点环、选中仍然可见：

- style.css：selection、focus-visible、输入焦点环；
- history.css / records.css：条目与时间线 hover 洗色；
- report.css：编辑器焦点环；
- settings.css：头像色点描边、色块外描边。

### 3.5 个性化面板 UI

- 在「个性化」标题下、头像色行上方新增「主题」块：
  - 标题「主题」+ 说明「跟随系统时随系统切换」；
  - 三段式控件：白天 / 黑夜 / 系统，当前项高亮（aria-pressed）。
- 交互：点击即写入 localStorage 并立即切换，不需要额外保存。

### 3.6 游客

- 主题是浏览器本地偏好，与账号无关；为了让「不登陆」也能自主切换，个性化对游客可见，但游客只看到主题块，隐藏「更改头像背景色」（头像色仍仅登录用户可改，后端也拒绝游客写入）。

### 3.7 加载

- index.html：head 引入 theme.js（样式表之前）、样式表末尾引入 theme.css；静态版本 ?v=29 → ?v=30。

## 4. 文件清单

新增：

- web/theme.js
- web/theme.css
- PLAN/PLAN_21~30/PLAN_23.md（本文件）

改动：

- web/index.html（脚本/样式引入、个性化主题块、版本号 → v30）
- web/views/personal.js（主题按钮绑定、打开时同步选中态、游客支持）
- web/app.js（个性化对游客可见）
- web/settings.css（主题块样式 + 两处硬编码描边换令牌）
- web/style.css / web/history.css / web/records.css / web/report.css（把 rgba 洗色/焦点环换成辅助令牌，不改变数值）

不动：后端、数据库、其余 JS 逻辑、REQUIREMENT.md、README。

## 5. 验证结果（已完成）

- pytest 27 passed；node --check theme.js / personal.js / app.js 通过。
- 本机系统偏好为暗色，因此「无存储」默认解析为 dark，符合跟随系统预期。
- 主题切换（实机）：
  - 无 theme.mode → AppTheme.get()=system、html[data-theme]=dark、个性化选中「系统」；
  - 白天 → attr=light、存储 light、body rgb(242,243,245)、选中「白天」；刷新后仍为 light；
  - 黑夜 → attr=dark、存储 dark、body rgb(18,20,24)、卡片 rgb(25,28,33)；
  - 系统 → attr=dark（当前系统值）、存储 system、选中「系统」；
  - 删除存储并刷新 → 回到 system/dark，未写入新键。
- 游客：设置里可见「注销与密码 / 个性化」；个性化面板仅主题块，头像色行与调色盘隐藏；白天/黑夜切换正常。
- 暗色抽查（计算值）：登录页 body rgb(18,20,24)、卡片 rgb(25,28,33)；工作台 surface rgb(25,28,33)、侧栏 rgb(21,24,28)；时间线选中 rgb(34,44,56)+浅蓝边；mark 底色 rgb(90,77,36)+浅字；管理台卡片 rgb(25,28,33)、输入 rgb(31,35,41)、done 徽标 rgb(27,42,35)/rgb(127,191,158)、failed rgb(42,30,29)/rgb(224,139,128)；报告编辑区 rgb(31,35,41)、预览 rgb(25,28,33)、代码块 rgb(34,44,56)；主题选中 accent-soft + accent-dark。均无横向溢出。
- 行数：theme.js 56、theme.css 132、settings.css 269、style.css 299、personal.js 141，均 ≤300。

### 5.1 实施中修正

- 游客原本看不到个性化；主题是浏览器本地偏好，改为对游客开放，面板内隐藏头像色行（头像色仍需登录，后端亦拒绝游客）。
- 暗色下浅蓝强调色不适合作为白字按钮底色，主按钮/运行按钮单独用深蓝填充；danger、状态徽标、认证页底纹、滚动条另做暗色覆盖。
- 原散落的 rgba 洗色/焦点环改为辅助令牌（--wash / --ring / --selection 等），浅色数值保持不变。

## 6. 回退

删除 theme.js / theme.css 与 index.html 的引入、personal.js 的主题绑定即可回到单主题；localStorage 残留的 theme.mode 不影响浅色使用。无后端与数据影响。

## 7. 本期不做

- 跟随时间的自动切换（如日落到黑夜）。
- 按用户账号同步主题（按需求只存浏览器本地）。
- 自定义主题色 / 高对比度模式。
