# GitHub Trending 自动日报 + 一键试用

每天自动抓取 GitHub Trending，AI 筛选值得 Star 的项目，生成中文简报推送到微信。

## 功能

- 🔄 **自动抓取** - 每天抓取 GitHub Trending（支持多语言）
- 🤖 **AI 筛选** - OpenAI 评分筛选，无 API 时自动降级为规则评分
- 📝 **中文简报** - 自动生成中文日报，包含推荐理由
- 📱 **微信推送** - 通过 Hermes 推送到微信
- 🐳 **一键试用** - Docker 容器限时运行，10 分钟自动清理

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置（可选，有 OpenAI API Key 时效果更好）
cp config.yaml.example ~/.github-trending/config.yaml
# 编辑 ~/.github-trending/config.yaml 填入 OpenAI API Key

# 3. 手动运行测试
python main.py --dry-run --limit 3

# 4. 正式运行（推送到微信）
python main.py --limit 5

# 5. 启用 Docker 试用（可选）
python main.py --limit 3 --trial
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config` | 配置文件路径 | `~/.github-trending/config.yaml` |
| `--language` | 按语言过滤 | python, javascript, go, rust |
| `--since` | 时间范围 | daily |
| `--limit` | 最大项目数 | 10 |
| `--trial` | 启用 Docker 试用 | False |
| `--trial-timeout` | 试用容器超时（秒） | 600 |
| `--dry-run` | 只生成不推送 | False |
| `--output` | 保存到文件 | stdout |
| `--target` | 推送目标 | weixin |

## 配置文件

```yaml
# GitHub Trending
languages: [python, javascript, go, rust]
spoken_language: zh
max_repos: 10

# AI 筛选
openai_api_key: sk-xxx  # 或设置环境变量 OPENAI_API_KEY
openai_model: gpt-4o-mini
min_score: 3  # 1-5 评分，>=3 的项目进入日报

# Docker 试用
trial_timeout: 600  # 10 分钟
trial_ports: [8080, 8000, 3000]

# 推送
notify_target: weixin
```

## 定时任务

已配置 Hermes CronJob：
- **名称**: github-trending-daily
- **时间**: 每天 09:00
- **推送**: 微信

```bash
# 查看任务状态
hermes cron list

# 手动触发一次
hermes cron run 38d839d816a7
```

## 项目结构

```
github-trending-daily/
├── main.py              # 主入口
├── config.py            # 配置管理
├── trending.py          # GitHub Trending 爬虫
├── summarizer.py        # AI 筛选器
├── renderer.py          # Jinja2 模板渲染
├── docker_trial.py      # Docker 试用管理
├── notifier.py          # 推送通知
├── requirements.txt     # 依赖
├── config.yaml.example  # 配置模板
├── PRD.md               # 产品需求文档
└── tests/               # 测试套件 (29 个测试)
    ├── conftest.py
    ├── test_config.py
    ├── test_trending.py
    ├── test_summarizer.py
    ├── test_renderer.py
    └── test_docker_trial.py
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 爬虫 | requests + BeautifulSoup |
| AI 筛选 | OpenAI API (gpt-4o-mini) |
| 模板 | Jinja2 |
| 容器 | Docker |
| 推送 | Hermes CLI |
| 调度 | Hermes CronJob |

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_trending.py -v
```

## License

MIT
