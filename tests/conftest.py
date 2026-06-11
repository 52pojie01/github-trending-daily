"""
公共 fixtures，供所有测试模块复用。
"""
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Optional


# ── 模拟数据结构 ──────────────────────────────────────────────────────────

@dataclass
class RepoInfo:
    """模拟 trending.py 中的仓库信息结构"""
    name: str
    owner: str
    description: str
    language: Optional[str]
    stars: int
    forks: int
    today_stars: int
    url: str = ""


@dataclass
class SummaryResult:
    """模拟 summarizer.py 中的 AI 摘要结果"""
    name: str
    chinese_summary: str
    reason: str
    score: int  # 1-5
    tryable: bool = False


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_repos() -> List[RepoInfo]:
    """提供一组样例仓库数据"""
    return [
        RepoInfo(
            name="awesome-ai",
            owner="openai",
            description="A collection of AI tools and resources",
            language="Python",
            stars=12000,
            forks=500,
            today_stars=350,
            url="https://github.com/openai/awesome-ai",
        ),
        RepoInfo(
            name="fast-api-kit",
            owner="devguy",
            description="Toolkit for FastAPI microservices",
            language="Python",
            stars=800,
            forks=40,
            today_stars=120,
            url="https://github.com/devguy/fast-api-kit",
        ),
        RepoInfo(
            name="tiny-go-server",
            owner="gopher",
            description="Minimal HTTP server in Go",
            language="Go",
            stars=200,
            forks=10,
            today_stars=30,
            url="https://github.com/gopher/tiny-go-server",
        ),
    ]


@pytest.fixture
def sample_summaries() -> List[SummaryResult]:
    """提供一组样例 AI 摘要结果"""
    return [
        SummaryResult(
            name="openai/awesome-ai",
            chinese_summary="一个精选的 AI 工具和资源合集，涵盖多个领域",
            reason="内容全面，持续更新，社区活跃",
            score=5,
            tryable=False,
        ),
        SummaryResult(
            name="devguy/fast-api-kit",
            chinese_summary="FastAPI 微服务开发工具包，提供常用中间件和模板",
            reason="实用性强，适合快速搭建后端服务",
            score=4,
            tryable=True,
        ),
        SummaryResult(
            name="gopher/tiny-go-server",
            chinese_summary="用 Go 编写的极简 HTTP 服务器",
            reason="代码量小，适合学习，但实用性有限",
            score=2,
            tryable=False,
        ),
    ]


@pytest.fixture
def mock_openai_response():
    """构造一个模拟的 OpenAI chat completion 响应"""
    def _make(content: str):
        mock_message = MagicMock()
        mock_message.content = content
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        return mock_resp
    return _make


@pytest.fixture
def trending_html():
    """返回一段模拟的 GitHub Trending 页面 HTML"""
    return """
    <html>
    <body>
    <article class="Box-row">
        <h2><a href="/openai/awesome-ai">openai / awesome-ai</a></h2>
        <p class="col-9 color-fg-muted my-1 pr-4">
            A collection of AI tools and resources
        </p>
        <span itemprop="programmingLanguage">Python</span>
        <a href="/openai/awesome-ai/stargazers" class="Link--muted d-inline-block mr-3">
            <svg aria-label="stars">star</svg> 12,000
        </a>
        <a href="/openai/awesome-ai/network/members" class="Link--muted d-inline-block mr-3">
            <svg aria-label="forks">fork</svg> 500
        </a>
        <span class="d-inline-block float-sm-right">
            <svg aria-label="stars today">star</svg> 350 stars today
        </span>
    </article>
    <article class="Box-row">
        <h2><a href="/devguy/fast-api-kit">devguy / fast-api-kit</a></h2>
        <p class="col-9 color-fg-muted my-1 pr-4">
            Toolkit for FastAPI microservices
        </p>
        <span itemprop="programmingLanguage">Python</span>
        <a href="/devguy/fast-api-kit/stargazers" class="Link--muted d-inline-block mr-3">
            <svg aria-label="stars">star</svg> 800
        </a>
        <a href="/devguy/fast-api-kit/network/members" class="Link--muted d-inline-block mr-3">
            <svg aria-label="forks">fork</svg> 40
        </a>
        <span class="d-inline-block float-sm-right">
            <svg aria-label="stars today">star</svg> 120 stars today
        </span>
    </article>
    </body>
    </html>
    """


@pytest.fixture
def empty_trending_html():
    """返回一个空的 GitHub Trending 页面 HTML（无项目）"""
    return """
    <html>
    <body>
    <div class="Box">
        <div class="Box-row">
            <p>Trending repositories are not available.</p>
        </div>
    </div>
    </body>
    </html>
    """


@pytest.fixture
def yaml_config():
    """返回一份样例 YAML 配置"""
    return {
        "languages": ["Python", "Go", "TypeScript"],
        "max_repos": 10,
        "score_threshold": 3,
        "openai_api_key": "sk-test-key-12345",
        "openai_model": "gpt-4o-mini",
        "docker_timeout": 600,
        "wechat_webhook": "https://example.com/webhook",
    }
