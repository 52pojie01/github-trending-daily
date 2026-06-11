"""
test_renderer.py – Jinja2 模板渲染 & Markdown 输出测试
"""
import pytest
from datetime import date


# ── 被测函数桩实现 ────────────────────────────────────────────────────────

MARKDOWN_TEMPLATE = """# GitHub Trending 日报 – {{ date }}

{% for repo in repos %}
## {{ loop.index }}. [{{ repo.name }}]({{ repo.url }})

{{ repo.chinese_summary }}

> 推荐理由：{{ repo.reason }}

| 指标 | 值 |
|------|----|
| ⭐ Stars | {{ repo.stars }} |
| 🔀 Forks | {{ repo.forks }} |
| 📈 今日 | +{{ repo.today_stars }} |
| 🏷️ 语言 | {{ repo.language }} |
| 🎯 评分 | {{ repo.score }}/5 |

{% if repo.tryable %}
> 🚀 **一键试用**: [点击在 Docker 中试用]({{ repo.try_url }})
{% endif %}

---

{% endfor %}

_由 Hermes Agent 自动生成_
"""


def render_markdown(repos: list, report_date: str = None) -> str:
    """使用 Jinja2 渲染 Markdown 日报。"""
    from jinja2 import Template
    if report_date is None:
        report_date = date.today().isoformat()
    template = Template(MARKDOWN_TEMPLATE)
    return template.render(repos=repos, date=report_date)


# ── 测试用例 ──────────────────────────────────────────────────────────────

class TestRenderer:

    def test_render_contains_header(self, sample_summaries):
        """渲染结果包含日报标题和日期"""
        repos = [vars(r) for r in sample_summaries]
        for r in repos:
            r.setdefault("stars", 1000)
            r.setdefault("forks", 50)
            r.setdefault("today_stars", 100)
            r.setdefault("url", "https://github.com/test/repo")
            r.setdefault("language", "Python")
            r.setdefault("tryable", False)
            r.setdefault("try_url", "")

        output = render_markdown(repos, report_date="2026-06-10")
        assert "GitHub Trending 日报" in output
        assert "2026-06-10" in output

    def test_render_contains_all_repos(self, sample_summaries):
        """所有仓库都应出现在输出中"""
        repos = [vars(r) for r in sample_summaries]
        for r in repos:
            r.setdefault("stars", 1000)
            r.setdefault("forks", 50)
            r.setdefault("today_stars", 100)
            r.setdefault("url", "https://github.com/test/repo")
            r.setdefault("language", "Python")
            r.setdefault("tryable", False)
            r.setdefault("try_url", "")

        output = render_markdown(repos)
        assert "awesome-ai" in output
        assert "fast-api-kit" in output
        assert "tiny-go-server" in output

    def test_render_markdown_table_format(self, sample_summaries):
        """验证 Markdown 表格格式正确"""
        repos = [vars(r) for r in sample_summaries]
        for r in repos:
            r.setdefault("stars", 1000)
            r.setdefault("forks", 50)
            r.setdefault("today_stars", 100)
            r.setdefault("url", "https://github.com/test/repo")
            r.setdefault("language", "Python")
            r.setdefault("tryable", False)
            r.setdefault("try_url", "")

        output = render_markdown(repos)
        assert "| 指标 | 值 |" in output
        assert "| ⭐ Stars |" in output

    def test_render_empty_list(self):
        """空列表应正常渲染，不抛异常"""
        output = render_markdown([])
        assert "GitHub Trending 日报" in output
        assert "由 Hermes Agent 自动生成" in output

    def test_render_tryable_button(self):
        """可试用的项目应包含试用按钮"""
        repos = [{
            "name": "test/repo",
            "chinese_summary": "测试项目",
            "reason": "测试",
            "score": 4,
            "stars": 100,
            "forks": 10,
            "today_stars": 5,
            "url": "https://github.com/test/repo",
            "language": "Python",
            "tryable": True,
            "try_url": "http://localhost:8080/try/test/repo",
        }]
        output = render_markdown(repos)
        assert "一键试用" in output
        assert "localhost:8080" in output
