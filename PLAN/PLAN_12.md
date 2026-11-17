# PLAN 12 — 运行时配置：管理员设置页与首次引导

日期：2026-11-17　｜　阶段：M0–M5（骨架期先建表与读取层，页面在管理端补齐）

## 1. 需求

解析与调用所需的参数（本地解析模型、OpenAI 兼容大模型的地址/名称/Key）不能只在 `.env` 里改——打包成安装包后，用户没有终端也没有编辑器。因此在管理员界面提供配置入口，并配一个首次引导流程。

**范围限定**：只支持 OpenAI 兼容接口（`openai` SDK + 自定义 `base_url`）。不做 Anthropic / Gemini / Ollama 专用适配器——兼容接口已覆盖 DeepSeek、通义千问、智谱、vLLM 等绝大多数服务。

## 2. 存储：设置项入表

```sql
settings(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT, updated_by INTEGER)
```

| key | 默认值 | 说明 |
| --- | --- | --- |
| `llm.base_url` | `https://api.deepseek.com` | OpenAI 兼容入口 |
| `llm.model` | `deepseek-chat` | 模型名 |
| `llm.api_key` | 空 | **只写不读**，见 §5 |
| `llm.temperature` | `0.2` | 抽取用；报告可单独抬高 |
| `llm.timeout` | `60` | 秒 |
| `parse.mineru_cmd` | 空 | mineru 可执行文件完整路径 |
| `parse.backend` | `pipeline` | mineru 解析后端（`pipeline` / `vlm`） |
| `parse.device` | `auto` | `auto` / `cuda` / `cpu` |
| `parse.model_dir` | 空 | 权重目录，留空用 mineru 默认 |
| `ui.first_run_done` | `false` | 引导是否完成 |

**读取优先级**：`settings` 表 > 环境变量 > 内置默认值。`.env` 只作为初始播种，界面改过的值以库为准，不需要重启。

## 3. 接口（全部 `require_admin`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /api/admin/settings | 返回全部配置；`api_key` 以 `sk-****abcd` 形式返回，另附 `api_key_set: true/false` |
| PUT | /api/admin/settings | 保存；`api_key` 传空字符串表示**不修改**，传 `null` 表示清空 |
| POST | /api/admin/settings/test-llm | 用当前配置发一次最小请求，返回耗时与模型回显 |
| GET | /api/admin/settings/detect-mineru | 扫 PATH 与常见 conda 目录，返回候选路径列表 |
| POST | /api/admin/settings/test-parse | 用**内置样例 PDF**（随包分发，1 页）跑一次真实解析，返回耗时、版本、设备 |
| GET | /api/setup/status | 任意登录用户可读，仅返回 `{llm_ok, parse_ok, first_run_done}` 布尔值 |

## 4. 首次引导流程

1. 启动后若 `llm.api_key` 为空或 `parse.mineru_cmd` 为空 → 首页顶部显示一条提示条。
2. 管理员点击进入 `/setup`，三步：**① 填大模型**（base_url / model / key + 测试连接）→ **② 检测解析器**（点「自动探测」扫 PATH 与常见 conda 目录下的 `mineru.exe`，探测不到再手填路径；点检测显示版本与 GPU 是否可用）→ **③ 完成**。
   - 让用户手填 `conda 环境\Scripts\mineru.exe` 的完整路径是不现实的；能自动探测就别让人找。
3. 完成时写 `ui.first_run_done=true`，提示条消失。
4. 非管理员看到的是「请联系管理员完成系统配置」，不渲染任何配置字段。
5. 引导可重复进入（`/admin#settings`），不强制一次性。

## 5. 安全约定（比功能更重要）

- **Key 只写不读**：GET 永远返回掩码 + 是否已设置，前端拿不到明文；前端不存 localStorage。
- **不落日志**：`llm.jsonl` 只记 `scheme+host` 与 `model`。整条 `base_url` 也不记——有的服务把 token 放在 URL 查询串里，记全 URL 等于记 key。
- **不存提示词之外的地方**：key 只出现在 `settings` 表与进程内存，不进报告、不进任务记录、不进导出文件。
- **CSRF 与越权**：写操作要求同源 + 有效会话 + `role=admin`；普通用户 403。
- **`.env` 仍可用**：优先读库，库为空回落到 `.env`，两者都没有则判定未配置并触发引导。

## 6. 对其它计划的影响

- PLAN_1：新增 `settings` 表与上表 5 个接口。
- PLAN_2：`config.py` 改为「库 > env > 默认」的分层读取，带 1 秒进程内缓存。
- PLAN_4：`parser.py` 的 `MINERU_CMD` / 设备 / 后端改从设置读，不再直接读环境变量。
- PLAN_5：`analyzer.py` 每次任务开始时取一次配置快照，任务中途改配置只影响新任务。
- PLAN_9：管理端增加「系统设置」页，含两个测试按钮。
- PLAN_10：warmup 增加「配置完整性」检查，直接复用 `test-llm` 与 `test-parse`。

## 7. 文件

- 新增 `app/api/settings.py`、`app/services/settings.py`、`web/views/settings.js`、`web/setup.html`。
- 修改 `app/config.py`、`app/schema.sql`、`app/main.py`、`app/api/admin.py`。

## 8. 验证

1. 空库启动 → 首页出现提示条，非管理员点击提示「请联系管理员」。
2. admin 填错 key → 测试连接返回明确错误；填对 → 返回模型名与耗时。
3. 保存后不重启，直接发起查询 → 使用新配置生效。
4. GET 设置 → key 显示为掩码；`api_key_set=true`；响应体全文搜索不到明文 key。
5. `PUT` 时把 `api_key` 传空字符串 → 原 key 保留；传 `null` → 清空并触发引导。
6. 普通用户 `PUT /api/admin/settings` → 403。
7. 检查 `llm.jsonl` → 无任何 key 片段。

## 9. 回退

删 `settings.py`、设置页与 `/setup`，`config.py` 回落为纯 `.env` 读取；`settings` 表保留但不再被读取，不影响既有功能。