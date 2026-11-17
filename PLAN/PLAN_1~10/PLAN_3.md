# PLAN 3 — 用户、登录与角色

日期：2026-11-17　｜　阶段：M0

## 1. 需求

基本要求 §4.8 要求存储"其他用户数据"，选做 1 要求"特定用户设为管理员"。所以必须有最小用户体系：登录 + 角色，不做注册、不找回密码。

## 2. 方案

- 密码：`hashlib.pbkdf2_hmac('sha256', pwd, salt, 100_000)`，存 `salt_hex$hash_hex`，只用标准库。
- 会话：`starlette.middleware.sessions.SessionMiddleware`（签名 cookie）。`SESSION_SECRET` 优先读 `.env`；**缺失时自动生成并持久化**到 `<DATA_DIR>/secret.key`（首次启动写一次，之后复用）。既不因缺配置起不来，也不会每次重启把登录全踢掉——打包分发时 `.env` 本来就不存在，硬性要求会直接开不了机。
- 依赖注入：`require_user()` 返回当前用户，未登录 401；`require_admin()` 校验 `role='admin'`，否则 403。
- 播种顺序（**打包版没有 `.env`，必须留兜底，否则第一次运行就没有管理员、进不了设置页，直接死锁**）：
  1. `.env` 有 `ADMIN_USERNAME/ADMIN_PASSWORD` → 按它建。
  2. 没有 `.env` 但**没有任何管理员** → 允许 `/setup` **免登录创建首个管理员**（用户名 + 密码自己设）。
  3. 该免登录通道只在没有管理员账号时可用（`demo` 等普通用户不算），创建成功后立即关闭；且仅当请求来自本机时才启用——若绑定 `0.0.0.0` 必须禁用，否则等于把管理员创建权开放到局域网。
- **仅当 `DEMO_PASSWORD` 存在时**才建普通用户 `demo`（打包环境没有 `.env`，无密码的 demo 账号等于一个后门）。已存在则跳过。
- 新增用户入口放在管理员界面（PLAN 9），本计划只做登录与校验。

## 3. 文件

- 新增 `app/api/auth.py`、`app/services/auth.py`（哈希、校验、依赖）。
- 修改 `app/main.py`（挂 SessionMiddleware、注册路由）、`app/schema.sql` 不变、`.env.example` 增加 `SESSION_SECRET` 与 `DEMO_PASSWORD`。

## 4. 验证

1. 正确密码登录 200，错误密码 401；登出后访问 `/api/tasks` 也是 401。
2. 用 demo 访问 `/api/admin/users` 返回 403；用 admin 返回 200。
3. 重启服务后已登录会话仍有效（cookie 可验签）。
4. 删库重来且无 `.env`：首次访问 `/setup` 能创建管理员；创建完再访问该通道返回 403。
5. 有 `.env` 时不出现免登录创建通道。
4. 数据库里查不到明文密码。

## 5. 回退

删除 `app/api/auth.py` 与 `app/services/auth.py`，移除 SessionMiddleware，接口统一用假 user_id=1（会连带阻断选做 1，需同步改 PLAN 9）。