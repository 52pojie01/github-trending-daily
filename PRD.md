# PRD: GitHub Trending 自动日报 + 一键试用

## Problem Statement

开发者每天想了解 GitHub 热门项目，但：
1. 手动刷 Trending 费时间
2. 看到好项目"收藏了=学了"，实际从不试用
3. 缺乏中文筛选，英文描述理解成本高

## Solution

自动化流水线：抓取 → AI 筛选 → 中文摘要 → 推送 → 一键试用

## User Stories

1. 作为用户，我希望每天收到 GitHub Trending 中文简报，不用自己刷
2. 作为用户，我希望 AI 帮我筛选出真正值得 Star 的项目，过滤噪音
3. 作为用户，我希望点击"试用"按钮就能在隔离环境跑起来，10 分钟自动清理
4. 作为用户，我希望通过微信收到推送，不离开常用工具

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  GitHub      │────▶│  AI 筛选     │────▶│  模板渲染    │
│  Trending    │     │  + 摘要生成  │     │  (Markdown)  │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                    ┌──────────────┐     ┌──────▼───────┐
                    │  Docker 试用  │◀────│  推送通知    │
                    │  (限时容器)  │     │  (微信)      │
                    └──────────────┘     └──────────────┘
```

## 模块设计

### 1. Trending 爬虫 (`trending.py`)
- 抓取 GitHub Trending 页面（daily/weekly/monthly）
- 提取：repo name, description, language, stars, forks, today stars
- 支持按语言过滤

### 2. AI 筛选器 (`summarizer.py`)
- 调用 OpenAI API（或本地模型）
- 输入：项目描述 + README 摘要
- 输出：中文简介 + 推荐理由 + 试用价值评分 (1-5)
- 筛选阈值：评分 ≥ 3 的项目进入日报

### 3. 模板渲染 (`renderer.py`)
- Jinja2 模板生成 Markdown 日报
- 每个项目包含：名称、描述、推荐理由、Star 数、试用按钮链接

### 4. Docker 试用管理 (`docker_trial.py`)
- 根据项目类型自动选择试用策略：
  - Python: pip install + 运行 demo
  - Node: npm install + npm start
  - Docker: 直接 docker run
  - Go/Rust: 编译运行
- 容器限时 10 分钟，自动清理
- 暴露端口映射，生成访问链接

### 5. 推送通知 (`notifier.py`)
- 通过 hermes send 推送到微信
- 支持 Markdown 格式

### 6. 配置管理 (`config.py`)
- 支持语言过滤、每日数量限制、API Key 配置
- YAML 配置文件

### 7. 主入口 (`main.py`)
- 串联所有模块
- 支持命令行参数
- 支持 cron 定时任务

## 技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 爬虫方式 | requests + BeautifulSoup | 简单可靠，GitHub Trending 页面结构稳定 |
| AI 模型 | OpenAI gpt-4o-mini | 性价比高，中文能力强 |
| 模板引擎 | Jinja2 | Python 标准，灵活 |
| 容器运行时 | Docker | 安全隔离，资源限制方便 |
| 推送链路 | hermes send | 已有基础设施 |
| 配置格式 | YAML | 可读性好 |

## Testing Decisions

- 爬虫：mock HTTP 响应，验证解析逻辑
- AI 筛选：mock API 调用，验证筛选逻辑
- 模板渲染：验证输出格式
- Docker 试用：验证容器创建/清理
- 集成测试：端到端流程

## Out of Scope

- Web UI（只做 CLI + 推送）
- 多用户支持（自用）
- 项目详情页深度分析
- 自动 Star 功能

## 部署方式

1. 克隆仓库
2. 配置 `.env`（API Key、推送目标）
3. `pip install -r requirements.txt`
4. `python main.py` 手动运行
5. 配置 Hermes cronjob 每日自动运行
