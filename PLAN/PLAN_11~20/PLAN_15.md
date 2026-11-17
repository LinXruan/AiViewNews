# PLAN 15 — AiViewNews：修复交互缺陷、美化 UI、恢复管理员控制台

日期：2026-11-18　｜　状态：实施中

## 1. 目标

在 PLAN 14 的三栏工作台上修复 9 项交互/视觉问题，并恢复 PLAN 14 重写时被删除的管理员控制台。

1. 头像菜单 →「设置」打开新面板，内含「控制台」「账号设置」；管理员两条，普通用户/不登陆仅「账号设置」。控制台恢复旧版全功能（用户管理、任务/报告查看、LLM/mineru 设置）。
2. 登录页「不登陆」改为与登录按钮同级的大按钮（不同底色），底部加淡灰提示「不登陆系统会自动清理历史记录」。
3. 历史栏收起时头像固定在右下角；账户菜单移出历史栏，修复收起态弹窗错位。
4. 侧边栏 2 顶部「记录」改为右上角圆形时钟图标。
5. 简介框加强底色/边框分割；增加纵向拖拽调整高度；压缩顶部时间戳栏。
6. 简介框删除「来源」「原文」两行。
7. `users` 增加 `avatar_color`，创建用户时随机分配深色底色；预留后续修改能力（本期不做端点）。
8. 不登陆用户头像为纯白；点「账号设置」跳登录页并丢弃游客解析数据。
9. 正文顶部 PDF 栏超过上限时横向滚动；标签去掉 `.pdf` 后缀。

## 2. 方案

### 2.1 管理员控制台（最大工作量）

- 从 `git show fd7968c:web/views/admin.js` 与 `web/admin.css` 取回旧实现，适配当前 `index.html`。
- 新增独立全屏 `admin-screen`（与 `report-screen` 同级），带「← 返回」回工作台。
- 复用后端 `/api/admin/users`、`/api/admin/tasks`、`/api/admin/tasks/{id}`、`/api/admin/settings` 等现有接口。
- 功能全保留：用户列表/新增/角色调整、任务列表/详情（事件+报告）、LLM 与 mineru 设置、detect/test。
- 前端入口：头像菜单「设置」→ 设置面板「控制台」；`App.setUser` 记录 `role`，仅 admin 显示该条。

### 2.2 设置面板与账号设置

- 保留头像菜单「设置 / 退出」。
- 「设置」打开 `settings-panel`（小弹层），两条：
  - 控制台（仅 `role === "admin"`）
  - 账号设置（所有身份显示）
- 普通用户「账号设置」→ 现有 `account-modal`（改密码/注销）。
- 不登陆「账号设置」→ 新增 `POST /api/guest/discard`：删除 guest 的全部 histories/documents/tasks/events/reports 与解析产物，清 session；前端回登录页。

### 2.3 登录页

- `#guest-btn` 改为整宽大按钮，同 `.primary-btn` 尺寸，底色用中性石板色（`#eef1f6` 底 + 深色字 + 描边），下方淡灰小字提示。
- 「创建管理员」逻辑不动（无管理员且本机才显示）。

### 2.4 历史栏收起态

- `.account-box { margin-top: auto; }`，使头像恒贴底部。
- 把 `#account-menu` 从 `.history-rail` 移到 `body` 末尾，`position: fixed`，JS 按头像按钮 `getBoundingClientRect()` 定位（上方/下方自动翻转），最小宽度 170px。

### 2.5 侧边栏 2「记录」

- `#records-toggle` 改为圆形时钟图标按钮（内联 SVG：圆 + 时/分针），置于 `rail-head` 右侧、与收起按钮并列。
- 点击仍切换 `record-list`；收起态隐藏该按钮。

### 2.6 简介框

- `.summary-panel`：浅蓝底、2px 上边框、顶部内阴影，形成明确分割。
- 顶部加 `.summary-resize` 拖拽条；pointer 事件调整高度，范围 120px ~ 60vh，`flex: 0 0 auto`。
- `.summary-head` 压缩高度/内边距，时间戳用紧凑标签；关闭按钮缩小。

### 2.7 简介内容

- `showSummary` 只保留事件正文；删除来源/原文两行。
- 删除 `.summary-meta`、`.summary-date` 死样式。

### 2.8 头像底色

- `users` 增加 `avatar_color TEXT NOT NULL DEFAULT '#2563eb'`。
- `SCHEMA_VERSION` 升至 2：按用户确认，迁移直接清理旧历史/任务/事件/报告与解析产物（保留 users/settings）；再加列并给已有用户回填随机色。
- `auth.py` 新增 `AVATAR_COLORS` 深色池与 `random_avatar_color()`；创建用户/guest/首管时写入；`public_user`、`get_user_by_id`、`get_user_by_username` 返回 `avatar_color`。
- 前端 `App.setUser` 应用底色；guest 忽略底色用纯白。

### 2.9 PDF 栏

- `.doc-tabs` 加 `flex: 1; min-width: 0` 与显式横向滚动条样式。
- `renderDocTabs` 显示 `filename.replace(/\.pdf$/i, "")`。

### 2.10 缓存

- 所有静态资源 `?v=18` → `?v=19`。

## 3. 文件清单

新增：
- `PLAN/PLAN_11~20/PLAN_15.md`
- `web/views/admin.js`（由 git 102 适配）
- `web/admin.css`（由 git 102 适配）

修改：
- `app/schema.sql`、`app/db.py`（版本 2 + 加列回填）
- `app/services/auth.py`（颜色池、返回字段）
- `app/api/auth.py` 或新增 guest 丢弃端点（建议放 `app/api/account.py`）
- `web/index.html`、`web/app.js`、`web/style.css`、`web/history.css`、`web/layout.css`、`web/records.css`、`web/reader.css`
- `web/views/account.js`、`web/views/reader.js`

## 4. 验证

1. 管理员登录 → 设置 → 控制台：用户/任务/报告/设置四项可用；普通用户无「控制台」。
2. 「不登陆」为同级大按钮，底部提示可见；点击进入工作台。
3. 历史栏收起：头像仍在右下角；点头像菜单完整弹出且可点。
4. 侧栏 2 右上角时钟图标可展开/收起记录列表。
5. 简介框底色/边框明显；拖拽可拉长/收紧；时间戳栏紧凑。
6. 简介框不再出现来源/原文。
7. 新注册用户头像底色随机且为深色；管理员/演示账号迁移后也有颜色。
8. 不登陆头像纯白；点账号设置回登录页，游客历史/解析产物被清空。
9. 多 PDF 时顶部标签可横向滚动；标签无 `.pdf`。
10. `python -m pytest` 全绿；重启后数据与配色保持。

## 5. 回退

- 代码改动集中在单次提交，可 `git revert`。
- 数据库版本 2 会清空历史数据：回退需接受演示数据重建。

## 6. 实现备注与偏差

- 管理员控制台取自 `git fd7968c`（102_pl13）的 `web/views/admin.js` 与 `web/admin.css`，适配当前工作台：移除旧 `App.refreshSetupStatus()`，按钮改用当前 `.primary-btn` / `.ghost-btn`，新增独立 `admin-screen`。
- 头像菜单与设置面板移出 `.history-rail`，挂到 body 下，`position: fixed` + JS 按头像位置定位；收起态头像靠 `margin-top: auto` 固定在底部。
- 游客「账号设置」调用 `DELETE /api/me/guest-data`，删除该游客全部历史与解析产物并清 session，然后回登录页。
- 数据库 `SCHEMA_VERSION = 2`：初始化时清空旧 history/task/event/report 与解析产物（保留 users/settings），`users` 加 `avatar_color` 并对已有用户回填深色。
- 简介框增加 8px 拖拽条，高度限制 120px–60vh；删除来源/原文两行及死样式。
- PDF 标签去掉 `.pdf` 后缀，`.doc-tabs` 补 `flex:1/min-width:0` 与显式滚动条。
- 静态资源版本号统一到 `v=19`。
- 验证：`pytest` 23 passed；真实库迁移后 version=2、三个既有账号均有颜色；实机截图确认登录页、设置面板、控制台、收起态菜单、游客头像与简介框。
