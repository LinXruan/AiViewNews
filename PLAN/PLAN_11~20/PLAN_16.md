# PLAN 16 — 面向用户的 README、Logo 与 GPLv3 许可证

日期：2026-11-18　｜　状态：已完成

## 1. 需求

1. 补一份面向用户的项目说明（README），排版参考 `LinXruan/YuYin` 的 README：居中 Logo、徽章、一句话简介、功能、亮点。
2. 项目正在快速迭代，README 不放界面截图。
3. Logo 暂用登录页 `AiViewNews` 字标的样式（首字母蓝色 + 深色字）。
4. 整个项目补齐 GPLv3 许可证。

## 2. 方案

- **README.md**：新增，中文；结构为 标题 + 居中 Logo + 徽章（License / Python / FastAPI / SQLite / DeepSeek）+ 一句话简介 + 功能 + 亮点 + 快速开始 + 许可证声明。功能条目只写已在代码中落地的能力（上传 ≤10 个 PDF、mineru 解析、事件抽取、时间线溯源、报告实时编辑与 DOCX 导出、任务历史、游客模式、管理员控制台）。
- **assets/icon.svg**：按 `web/style.css` 的登录页字标复刻——圆角卡片（`#ffffff` 底、`#e3e7ee` 描边、圆角 18）内居中排 `AiViewNews`，字号 48 / 字重 700；首字母 `A` 用 `--accent` `#2563eb`，其余用 `--ink` `#1f2937`。文字用 `text-anchor="middle"` 居中，字体回退时不裁切。透明外底，浅色/深色主题下都靠卡片底色保证可读。
- **LICENSE**：写入 GPLv3 官方全文（675 行），版权声明集中在 README 的许可证小节，不给每个源文件加头部注释（改动面过大且无必要）。

## 3. 文件清单

新增：
- `README.md`
- `assets/icon.svg`
- `LICENSE`
- `PLAN/PLAN_11~20/PLAN_16.md`

不改动：`web/**`、`app/**`、`tests/**`、`.gitignore`。

## 4. 验证

- SVG 用 Edge 无头渲染截图核对：字标居中、首字母蓝色、卡片边框完整、无裁切。
- `LICENSE` 首行 `GNU GENERAL PUBLIC LICENSE` / `Version 3, 29 June 2007`，末尾为 "How to Apply These Terms" 段，行数与官方文本一致。
- README 中引用的文件（`assets/icon.svg`、`LICENSE`、`.env.example`、`tools/start.bat`、`requirements.txt`）均存在。
- `python -m pytest` 全绿（不改代码，作为回归确认）。

## 5. 回退

纯新增文档与静态资源，回退即删除上述 4 个文件；不影响运行时行为。
