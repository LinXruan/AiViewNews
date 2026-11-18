# PLAN 19 — 设置页居中、注销与密码改名、头像背景色调色盘

日期：2026-11-18　｜　状态：已完成

> **编号说明**：`PLAN/PLAN_11~20/PLAN_18.md` 已存在且标记「已完成」（Pandoc 导出 DOCX、各栏可伸缩，见提交 `5b63798`）。按 AGENTS.md「序号递增，不复用」，本计划顺延为 **PLAN 19**，不覆盖 18。若确需以 18 编号，由用户明确指定后再调整。

## 1. 需求

1. **左下角头像的一级点击逻辑保持正确、不动**：单击头像 → 在头像旁弹出「设置」「退出」（`web/views/account.js:15-22` 的 `place()` 定位）。
2. **一级「设置」的次级页面改为屏幕中央**：目前点「设置」会在左下角贴着头像弹出 `#settings-panel`（控制台 / 账号设置），这是要改掉的唯一位置问题。设置页面应当水平+垂直居中，像真正的设置页，而不是贴边小菜单。
3. **改名**：选项「账号设置」→「注销与密码」，对应弹窗标题同步改名。
4. **设置界面（管理员）三个选项**：`控制台`、`注销与密码`、`个性化`（新增）。
5. **新增「个性化」面板**：当前仅有一条「更改头像背景色」；点击后展开「调色盘」，可在其中取色，选色后左下角头像背景色立即变化并持久化（刷新/重登不丢）。

## 2. 现状与根因

- `web/index.html:126-133`：一级 `#account-menu`（设置/退出）与次级 `#settings-panel`（控制台/账号设置）都是 `position: fixed` 浮层；`web/history.css:164-191` 给两者同一套贴边菜单样式。
- `web/views/account.js:24-29`：点「设置」后 `this.place(panel, avatar)`，把次级面板按头像坐标摆到左下角，即需求 2 的成因。
- `web/index.html:269-284` 的 `#account-modal`（改密码 / 注销账号）本身已是居中模态（`web/style.css:251-261` 的 `.modal`），只是 `align-items: flex-start` + `padding: 9vh` 偏上，未垂直居中。
- `users.avatar_color` 列已存在（`app/schema.sql:7`，迁移在 `app/db.py:57-71`），`/api/me` 与 `/api/admin/users` 均已回传；`App.setUser` 已把它应用到头像（`web/app.js:106`）。**缺的只是一个写入端点与前端取色 UI，不需要改表结构、不需要迁移。**
- `app/services/auth.py:22-36` 的 `AVATAR_COLORS` 是 12 个深色预设（保证白色首字母可读），前端可调色盘复用这 12 个值。

## 3. 方案

### 3.1 交互层级（核心）

| 层级 | 触发 | 呈现 | 变化 |
| --- | --- | --- | --- |
| L1 | 单击左下角头像 | `#account-menu`：设置 / 退出，头像旁 | **不变** |
| L2 | 点「设置」 | `#settings-modal`：**屏幕中央**的设置对话框，选项列表 | **由贴边面板改为居中对话框**，不再调用 `place()` |
| L3 | 点 L2 选项 | 三个去向，见下 | 新增「个性化」 |

L2 选项及去向：

- **控制台**（仅管理员可见）→ 关闭 L2，`App.admin.open()` 全屏控制台（现状不变，返回仍回工作台）。
- **注销与密码**（原「账号设置」）→ 关闭 L2，打开 `#account-modal`（已是居中模态）；游客仍走 `discardGuest()` 清理游客数据并回登录页（`web/views/account.js:31-38`，保持）。
- **个性化**（新增）→ 关闭 L2，打开新增的居中 `#personal-modal`。

L2 可见性（`App.setUser` 控制）：

- 管理员：3 项；普通登录用户：2 项（控制台隐藏）；游客：1 项（仅「注销与密码」）。

### 3.2 L2 居中对话框

- 把 `#settings-panel` 整块替换为 `#settings-modal`，复用 `.modal` 遮罩 + `.modal-card` 卡片，但加修饰类 `.modal.center` 使其**水平+垂直居中**（`align-items: center; padding: 24px 16px`），覆盖 `style.css:256` 的 `flex-start`。
- 卡片结构：标题「设置」+ 关闭 ×；下面三个 `.settings-option` 行按钮（标签 + 一句说明 + 右箭头），视觉上是设置页而非小菜单。
- 关闭方式统一：× 按钮、点击遮罩（`event.target === modal`）、`Esc`。`#account-modal` 与 `#personal-modal` 同样加 `.center` 并支持这三种关闭方式，整条设置流位置一致。
- `document` 点击处理器（`account.js:45-54`）改为**只收起 L1 菜单**；居中模态由自身遮罩/×/Esc 负责，避免点模态内部误关。
- `window.resize` 只收起 L1 菜单；居中模态由 CSS 自动保持居中，不再强制关闭。
- `App.showAuth()`（`web/app.js:81-82`）退出登录时同步隐藏三个模态，避免登录页上残留弹窗。

### 3.3 「个性化」面板与调色盘

`#personal-modal`（居中）内容：

```
个性化                                    ×
┌──────────────────────────────────────────┐
│ 更改头像背景色        [当前色块]  ›      │  ← 一行，点击展开/收起调色盘
└──────────────────────────────────────────┘
  调色盘（展开后）：
  · 12 个预设色块网格（值同 auth.AVATAR_COLORS，深色保证白字可读）
  · 「自定义颜色」<input type="color">（不限制色域，自由自选）
  · 实时预览：圆形头像（首字母）+ 当前 #RRGGBB 文本
  · 状态行：已保存 / 失败原因
```

- **取色即保存**，不设额外「保存」按钮：点预设色块或改变自定义色 → `PATCH /api/me/avatar-color` → 成功后更新 `App.state.user.avatar_color`、`#avatar.style.background`、面板色块与预览，状态行提示「已保存」；失败显示错误且不改本地状态。
- 不引入任何前端取色库，用原生 `<input type="color">`；`requirements.txt` 不动。
- 前端 12 个预设值以常量写死在 `web/views/account.js`，注释标明与 `app/services/auth.py:AVATAR_COLORS` 保持一致（纯静态值，不为此新增 API）。
- 保存成功后 `web/views/admin.js:187` 的用户表色点会在下次加载时自动取到新颜色，无需改动。

### 3.4 后端写入端点

`app/api/account.py`（`router` 前缀 `/api/me`）新增：

```
PATCH /api/me/avatar-color
body: { "avatar_color": "#1d4ed8" }
→ 200 { "ok": true, "avatar_color": "#1d4ed8" }
```

- `AvatarColorPayload(BaseModel)`：字段 `avatar_color: str`。
- 严格校验 `re.fullmatch(r"#[0-9a-fA-F]{6}", value.strip())`，非法 → `ApiError(400, "invalid_color", "颜色格式应为 #RRGGBB")`（系统边界校验，避免任意字符串进 `style.background`）。
- 游客 → `ApiError(400, "guest_color", "不登陆模式不能保存个性化设置")`，与现有 `guest_password` / `guest_delete` 一致。
- 统一转小写入库：`UPDATE users SET avatar_color = ? WHERE id = ?`。
- `/api/me`（`auth.current_user` → `public_user`）与 `/api/admin/users` 已回传该列，**无需改 `app/services/auth.py`、`app/schema.sql`、`app/db.py`**。

## 4. 决策记录（请一并确认）

1. **L2 采用「居中对话框 + 三个选项各自打开独立面板」**，不改成左右分栏设置页：可保留现有 `#account-modal` 与全屏控制台，改动最小，符合「删除优先、不做没要求的功能」。
2. **游客隐藏「个性化」**：游客头像是固定白色 `.avatar.guest` 样式（`web/history.css:152-156`），且数据定期清理，改色无可见效果；同时后端也拒绝游客写入。若希望游客也能改，请指出。
3. **取色即保存**，不设「保存」按钮。
4. **点「控制台」后不自动重开设置对话框**，返回控制台时回到工作台。
5. **自定义颜色不限制色域**（用户「自选」），仅预设色块沿用深色系；浅色下白色首字母可读性下降属用户自选结果。
6. **三个模态统一垂直居中**（给 `#account-modal` 也加 `.center`），整条设置流位置一致；这是唯一对现有账号弹窗的视觉改动。

## 5. 文件清单

改动：

- `app/api/account.py`：新增 `PATCH /api/me/avatar-color`。
- `tests/test_account.py`：新增 3 个用例（合法色持久化、非法色 400、游客 400）。
- `web/index.html`：`#settings-panel` → `#settings-modal`；新增 `#personal-modal`；「账号设置」→「注销与密码」；三个模态加 `.center`；引入 `settings.css`；静态资源 `?v=24` → `?v=25`。
- `web/app.js`：`showAuth()` 隐藏新模态；`setUser()` 按角色/游客控制 L2 三项可见性；`startSession()` 挂载 `App.personal.bind()`。
- `web/views/account.js`：L2 居中与三选项路由、× / 遮罩 / Esc 关闭逻辑；`place()` 仍只服务 L1。个性化逻辑拆到 `web/views/personal.js`——首版并入后实测 315 行，超出「单文件 ≤300 行」，故按文件拆分。
- `web/history.css`：删除 `.settings-panel` 及其按钮样式，保留 `.account-menu` 一套。

新增：

- `web/views/personal.js`：`App.personal`——调色盘渲染、取色即保存、预览与状态行（与 `account.js` 分文件维护）。
- `web/settings.css`：L2 选项行、`.modal.center`、个性化行、调色盘网格/色块/预览/状态行样式。**单独建文件**的原因：`web/style.css` 已 299 行，再追加会突破「单文件 ≤300 行」硬约束。
- `PLAN/PLAN_11~20/PLAN_19.md`（本文件）。

明确不动：`app/schema.sql`、`app/db.py`、`app/services/auth.py`、`app/api/admin.py`、`web/views/admin.js`、`App.admin.open/close`、`.env.example`、`requirements.txt`、`REQUIREMENT.md`、README。

## 6. 验证

1. `python -m pytest`：基线 24 passed → 预期 27 passed；`node --check` 检查 `web/app.js`、`web/views/account.js`。
2. 浏览器实测，分别用**管理员 / 普通用户 / 游客**三种身份：
   - 点头像 → 左下角仍弹「设置 / 退出」；
   - 点「设置」→ **屏幕正中央**出现设置对话框；管理员 3 项、普通用户 2 项、游客 1 项；
   - 「注销与密码」→ 居中弹窗标题已改名；改密码、注销账号、游客清理数据流程回归通过；
   - 「控制台」→ 全屏控制台，「← 返回」回工作台；
   - 「个性化」→ 居中面板，点「更改头像背景色」展开调色盘；点预设 / 自定义取色 → 左下角头像立即变色、状态行「已保存」；
   - **刷新页面、重新登录**后颜色保持；管理台「用户管理」色点同步；
   - × / 点遮罩 / Esc 均可关闭；退出登录后无残留模态；
   - 回归：拖拽伸缩、时间线、报告编辑/导出不受影响。
3. 边界：提交 `red`、`#12345`、`javascript:...` 均返回 400 `invalid_color`；游客提交返回 400 `guest_color`。
4. 全库搜索确认 `settings-panel`、`账号设置` 无残留（`app.js` / `index.html` / `account.js` / `history.css`）。

## 7. 验证结果（已完成）

- python -m pytest：27 passed（原 24 + 背景色 3 例）；node --check 三个前端脚本通过。
- 真实浏览器（临时 DATA_DIR + 8019 端口，Edge 实机）逐项：
  1. 点头像 → 左下角弹「设置 / 退出」，未变；
  2. 点「设置」→ 设置卡片 460×314，中心 (768, 396) 与视口中心 (768, 395.5) 一致，水平+垂直居中；管理员 3 项；
  3. 普通用户（demo）→ 2 项（注销与密码 / 个性化），控制台隐藏；游客 → 1 项（注销与密码），个性化隐藏；
  4. 「注销与密码」弹窗标题正确，Esc 可关闭；
  5. 「控制台」全屏打开，「← 返回」回工作台；
  6. 「个性化」→ 点「更改头像背景色」展开 12 个预设色块 + 自定义颜色；点 #7c3aed 后头像变 rgb(124, 58, 237)、状态行「已保存」；刷新后仍为 rgb(124, 58, 237)；
  7. 游客点「注销与密码」→ 清理游客数据并回登录页（原有行为）；
  8. 退出登录后无残留模态。
- 全库搜索 settings-panel、账号设置 零残留；account.js 204 行、personal.js 119 行、settings.css 195 行，均 ≤300。
- 边界：red / #12345 / #gggggg / javascript:alert(1) → 400 invalid_color；游客写入 → 400 guest_color。

## 8. 回退

- 后端：新端点为独立新增，`git revert` 对应提交即可；不动表结构、不删数据、无迁移。
- 前端：删除 `web/settings.css` 与 `#personal-modal`，恢复 `#settings-panel` 及 `history.css` 中其样式、还原 `?v` 号即可恢复旧贴边菜单；`app.js` 的 `showAuth` / `setUser` 改动随提交一并回退。
- 已写入的 `avatar_color` 值仍在库中（合法 `#RRGGBB`，旧逻辑同样读取），回退后不影响任何功能。

## 9. 本期不做

- 头像上传图片 / 首字母字体自定义 / 主题配色（仅头像背景色）。
- 游客的个性化设置持久化。
- 控制台内嵌进设置对话框（保持全屏独立页）。
- 报告、解析、模型相关任何改动。
