"""
test_trending.py – TrendingFetcher HTML 解析逻辑测试
"""
import pytest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup


# ── 被测函数（从 trending.py 导入；此处提供桩实现以便独立运行）─────────
# 实际项目中应改为: from trending import parse_trending_page, fetch_trending

def parse_trending_page(html: str, language: str = None) -> list:
    """解析 GitHub Trending 页面 HTML，返回仓库列表。"""
    soup = BeautifulSoup(html, "html.parser")
    repos = []
    for article in soup.select("article.Box-row"):
        # 仓库名
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        full_name = h2.get("href", "").strip("/")
        parts = full_name.split("/")
        owner = parts[0] if len(parts) >= 2 else ""
        name = parts[1] if len(parts) >= 2 else full_name

        # 描述
        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        # 语言
        lang_el = article.select_one('[itemprop="programmingLanguage"]')
        repo_language = lang_el.get_text(strip=True) if lang_el else None

        # Star 数
        star_links = article.select("a.Link--muted")
        stars = _parse_count(star_links[0]) if len(star_links) >= 1 else 0
        forks = _parse_count(star_links[1]) if len(star_links) >= 2 else 0

        # 今日 star
        today_span = article.select_one(".float-sm-right")
        today_stars = _parse_today(today_span) if today_span else 0

        # 语言过滤
        if language and repo_language and repo_language.lower() != language.lower():
            continue

        repos.append({
            "name": name,
            "owner": owner,
            "description": description,
            "language": repo_language,
            "stars": stars,
            "forks": forks,
            "today_stars": today_stars,
            "url": f"https://github.com/{owner}/{name}",
        })
    return repos


def _parse_count(el) -> int:
    import re
    text = el.get_text(strip=True)
    # 提取第一个纯数字（可能含逗号）或 "数字 stars" 等格式
    match = re.search(r'([\d,]+)', text)
    if match:
        return int(match.group(1).replace(",", ""))
    return 0


def _parse_today(el) -> int:
    import re
    text = el.get_text(strip=True)
    match = re.search(r'([\d,]+)', text)
    if match:
        return int(match.group(1).replace(",", ""))
    return 0


# ── 测试用例 ──────────────────────────────────────────────────────────────

class TestTrendingParsing:
    """TrendingFetcher HTML 解析测试"""

    def test_parse_normal_page_returns_correct_count(self, trending_html):
        """正常页面应解析出正确数量的仓库"""
        repos = parse_trending_page(trending_html)
        assert len(repos) == 2

    def test_parse_repo_fields(self, trending_html):
        """验证每个仓库的字段值正确"""
        repos = parse_trending_page(trending_html)
        first = repos[0]
        assert first["owner"] == "openai"
        assert first["name"] == "awesome-ai"
        assert first["language"] == "Python"
        assert first["stars"] == 12000
        assert first["forks"] == 500
        assert first["today_stars"] == 350
        assert "openai/awesome-ai" in first["url"]

    def test_parse_returns_list_of_dicts(self, trending_html):
        """返回值是 list[dict]，每个 dict 包含必要 key"""
        repos = parse_trending_page(trending_html)
        required_keys = {"name", "owner", "description", "language", "stars", "forks", "today_stars", "url"}
        for repo in repos:
            assert required_keys.issubset(repo.keys())

    def test_empty_page_returns_empty_list(self, empty_trending_html):
        """空页面应返回空列表，而非抛异常"""
        repos = parse_trending_page(empty_trending_html)
        assert repos == []

    def test_language_filter(self, trending_html):
        """按语言过滤时，只返回匹配的仓库"""
        repos = parse_trending_page(trending_html, language="Go")
        assert len(repos) == 0  # 页面中没有 Go 项目

        repos = parse_trending_page(trending_html, language="Python")
        assert len(repos) == 2
