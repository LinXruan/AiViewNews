# AiViewNews

<p align="center">
  <img src="assets/icon.svg" alt="AiViewNews Logo" width="360" />
</p>

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-GPLv3-blue?style=flat-square" alt="License" />
  </a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/DeepSeek-LLM-4B6BFB?style=flat-square" alt="DeepSeek" />
</p>

<p align="center"><b>把新闻 PDF 变成一条可回溯的时间线，和一份可编辑的事件分析报告。</b></p>

上传 PDF，用一句自然语言提问；系统定位相关事件、按时间排好，再从原文里把这句话挖出来给你看。

> 课程设计作业项目，仅供学习与技术交流使用。

## 功能

- **批量上传**：一次最多 10 个 PDF（单个 ≤50MB），后台用 mineru 解析成 Markdown 与插图
- **自然语言检索**：在已解析文档里直接提问，抽取相关事件并去重合并
- **时间线摘要**：按时间顺序排布事件节点，点击节点回到正文对应位置并高亮原句
- **事件分析报告**：事件概述、关键节点、各方立场、影响分析、趋势预测、不确定性说明，分章节成文
- **边改边看**：报告左侧编辑、右侧实时渲染，保存即落库，一键导出 DOCX
- **任务历史**：每次提问都是一个分析任务，记录查询内容、事件数量、时间与状态，随时回看
- **账号体系**：注册 / 登录；也可以「不登录」直接试用，游客数据会被系统定期清理
- **管理控制台**：用户与任务总览、模型与 mineru 配置、接口连通性自检

## 亮点

- **长任务全异步**：解析与分析都在后台跑，状态落库（`pending / parsing / analyzing / done / failed`），前端轮询，刷新与重启都不丢进度
- **长文档拆分**：按章节切块抽取事件，再统一去重与归并，单任务调用次数可控
- **模型输出按不可信处理**：JSON 结构强校验 + 失败重试，校验不过的内容不会进页面
- **密钥只写不读**：API Key 存服务端，界面只回显掩码，日志与导出文件均不出现明文
- **纯本地运行**：数据落在本机 SQLite，无遥测、无外部分析服务
- **B/S 三层**：浏览器只负责上传与展示，解析、调模型、存数据全在服务端

## 快速开始

### 1. 准备环境

- Python 3.11+（后端与依赖）
- [mineru](https://github.com/opendatalab/MinerU)：需独立安装在 Python 3.13 环境中，装好后把可执行文件路径写进 `MINERU_CMD`
- 一个 DeepSeek API Key（OpenAI 兼容接口）

### 2. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 3. 配置

复制 `.env.example` 为 `.env`，按需填写：

```dotenv
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
MINERU_CMD=
```

也可以先留空，启动后在管理员控制台里填写（界面保存的配置优先于 `.env`）。

### 4. 启动

```bash
python -m uvicorn app.main:app --reload
```

Windows 下双击 `tools\start.bat` 可一键启动并打开浏览器。

打开 <http://127.0.0.1:8000>，首次访问会引导创建管理员账号。

### 5. 演示前预热

```bash
python scripts/warmup.py
```

会检查配置、数据库、mineru 与模型连通性，避免现场首次调用触发下载或超时。

## 说明

项目正在快速迭代，界面仍在调整，因此暂不提供界面截图。

## 许可证

本项目基于 [GNU General Public License v3.0](LICENSE) 发布，Copyright (C) 2026 LinXruan。

你可以自由使用、修改与分发，但衍生作品需以同一许可证开源，且不提供任何担保。
