"""Jinja2 template renderer for GitHub Trending daily report."""

import logging
from datetime import datetime
from typing import Any

from jinja2 import Environment, BaseLoader

logger = logging.getLogger(__name__)

# Cached Jinja2 Environment
_jinja_env = Environment(loader=BaseLoader(), autoescape=False)

# Markdown template for the daily report
REPORT_TEMPLATE = """# 🔥 GitHub Trending 日报 - {{ date }}

> 数据来源：GitHub Trending | 自动生成时间：{{ generated_at }}

---

{% for project in projects %}
## {{ loop.index }}. {{ project.name }}

| 属性 | 值 |
|------|-----|
| **描述** | {{ project.get('description', '暂无描述') }} |
| **语言** | {{ project.get('language', '未知') }} |
| **今日 Star** | ⭐ +{{ project.get('stars_today', 0) }} |
| **总 Star** | ⭐ {{ project.get('total_stars', 0) }} |
| **Fork** | 🍴 {{ project.get('forks', 0) }} |
| **链接** | [GitHub]({{ project.get('url', '#') }}) |
{% if project.get('trial_url') %}| **🚀 在线试用** | [{{ project.trial_url }}]({{ project.trial_url }}) |{% endif %}

**💡 推荐理由：** {{ project.get('reason', '该项目近期在 GitHub 上获得大量关注，值得关注。') }}

---

{% endfor %}

*本报告由 GitHub Trending Daily 自动生成*
"""


def render(projects: list[dict[str, Any]], template: str | None = None) -> str:
    """Render projects into a Markdown report.

    Args:
        projects: List of project dicts with keys like name, description, url, etc.
        template: Optional custom Jinja2 template string. Uses default if None.

    Returns:
        Rendered Markdown string.
    """
    if not projects:
        logger.warning("No projects to render, generating empty report")
        projects = []

    tmpl = _jinja_env.from_string(template or REPORT_TEMPLATE)

    context = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "projects": projects,
    }

    try:
        result = tmpl.render(**context)
        logger.info("Rendered report with %d projects", len(projects))
        return result
    except Exception as e:
        logger.error("Template rendering failed: %s", e)
        raise


if __name__ == "__main__":
    # Quick test
    sample = [
        {
            "name": "example/repo",
            "description": "A cool project",
            "language": "Python",
            "stars_today": 500,
            "total_stars": 10000,
            "forks": 1200,
            "url": "https://github.com/example/repo",
            "reason": "快速上升的新项目",
        }
    ]
    print(render(sample))
