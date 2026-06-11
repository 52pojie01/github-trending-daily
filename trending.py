"""
GitHub Trending 爬虫模块

抓取 GitHub Trending 页面，提取热门仓库信息。
支持按编程语言和时间范围过滤。
"""

import re
import logging
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

GITHUB_TRENDING_URL = "https://github.com/trending"

# 请求头，模拟浏览器访问
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_trending(
    language: Optional[str] = None,
    since: str = "daily",
    spoken_language: Optional[str] = None,
    max_repos: int = 25,
    timeout: int = 30,
) -> List[Dict]:
    """
    抓取 GitHub Trending 页面，返回仓库列表。

    Args:
        language: 编程语言过滤，如 'python', 'javascript'。None 表示不限语言。
        since: 时间范围，可选 'daily', 'weekly', 'monthly'。
        spoken_language: 语言偏好，如 'zh' 表示中文。
        max_repos: 最多返回的仓库数量。
        timeout: 请求超时时间（秒）。

    Returns:
        List[Dict]: 仓库信息列表，每个 dict 包含:
            - name: 仓库全名 (owner/repo)
            - url: 仓库链接
            - description: 仓库描述
            - language: 编程语言
            - stars: 总星标数
            - forks: Fork 数
            - today_stars: 今日新增星标数
    """
    # 构建 URL
    if language:
        url = f"{GITHUB_TRENDING_URL}/{language}"
    else:
        url = GITHUB_TRENDING_URL

    params = {"since": since}
    if spoken_language:
        params["spoken_language"] = spoken_language

    logger.info(f"正在抓取 GitHub Trending: {url} (since={since})")

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"请求 GitHub Trending 失败: {e}")
        return []

    repos = _parse_trending_html(response.text, max_repos=max_repos)
    logger.info(f"成功获取 {len(repos)} 个仓库")
    return repos


def _parse_trending_html(html: str, max_repos: int = 25) -> List[Dict]:
    """
    解析 GitHub Trending 页面 HTML，提取仓库信息。

    Args:
        html: HTML 内容
        max_repos: 最多返回的仓库数量

    Returns:
        List[Dict]: 仓库信息列表
    """
    soup = BeautifulSoup(html, "html.parser")
    repos = []

    # 每个仓库在 <article class="Box-row"> 中
    articles = soup.select("article.Box-row")

    for article in articles[:max_repos]:
        try:
            repo = _parse_single_repo(article)
            if repo:
                repos.append(repo)
        except Exception as e:
            logger.warning(f"解析仓库条目时出错: {e}")
            continue

    return repos


def _parse_single_repo(article) -> Optional[Dict]:
    """
    解析单个仓库条目。

    Args:
        article: BeautifulSoup Tag 对象

    Returns:
        Dict: 仓库信息，或 None
    """
    # 仓库名和链接
    repo_link = article.select_one("h2 a")
    if not repo_link:
        return None

    href = repo_link.get("href", "").strip("/")
    repo_name = href  # 格式: owner/repo
    repo_url = f"https://github.com/{href}"

    # 描述
    desc_elem = article.select_one("p")
    description = desc_elem.get_text(strip=True) if desc_elem else ""

    # 编程语言
    lang_elem = article.select_one("[itemprop='programmingLanguage']")
    language = lang_elem.get_text(strip=True) if lang_elem else ""

    # 总星标数
    stars_elem = article.select("a.Link--muted")
    stars = 0
    forks = 0

    if len(stars_elem) >= 1:
        stars = _parse_number(stars_elem[0].get_text(strip=True))
    if len(stars_elem) >= 2:
        forks = _parse_number(stars_elem[1].get_text(strip=True))

    # 今日新增星标
    today_stars = 0
    today_elem = article.select_one("span.d-inline-block.float-sm-right")
    if today_elem:
        match = re.search(r"([\d,]+)\s+stars?\s+today", today_elem.get_text())
        if match:
            today_stars = _parse_number(match.group(1))

    return {
        "name": repo_name,
        "url": repo_url,
        "description": description,
        "language": language,
        "stars": stars,
        "forks": forks,
        "today_stars": today_stars,
    }


def _parse_number(text: str) -> int:
    """
    解析数字字符串，如 '1,234' -> 1234, '10.5k' -> 10500
    """
    text = text.strip().replace(",", "")
    if not text:
        return 0

    match = re.match(r"([\d.]+)([kKmM])?", text)
    if not match:
        return 0

    num = float(match.group(1))
    suffix = match.group(2)

    if suffix and suffix.lower() == "k":
        num *= 1000
    elif suffix and suffix.lower() == "m":
        num *= 1_000_000

    return int(num)


def fetch_all_trending(
    languages: Optional[List[str]] = None,
    since: str = "daily",
    spoken_language: Optional[str] = None,
    max_repos_per_lang: int = 25,
) -> List[Dict]:
    """
    抓取多个语言的 Trending 仓库并合并去重。

    Args:
        languages: 语言列表，None 表示不限语言。
        since: 时间范围。
        spoken_language: 语言偏好。
        max_repos_per_lang: 每种语言最多返回的仓库数。

    Returns:
        List[Dict]: 去重后的仓库列表，按今日星标数降序排列。
    """
    all_repos = {}
    seen_names = set()

    if languages:
        for lang in languages:
            repos = fetch_trending(
                language=lang,
                since=since,
                spoken_language=spoken_language,
                max_repos=max_repos_per_lang,
            )
            for repo in repos:
                if repo["name"] not in seen_names:
                    seen_names.add(repo["name"])
                    all_repos[repo["name"]] = repo
    else:
        repos = fetch_trending(
            since=since,
            spoken_language=spoken_language,
            max_repos=max_repos_per_lang,
        )
        for repo in repos:
            all_repos[repo["name"]] = repo

    # 按今日星标数降序排列
    sorted_repos = sorted(all_repos.values(), key=lambda x: x["today_stars"], reverse=True)
    return sorted_repos


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== GitHub Trending (Python, daily) ===")
    repos = fetch_trending(language="python", since="daily")
    for i, repo in enumerate(repos[:5], 1):
        print(f"\n{i}. {repo['name']}")
        print(f"   描述: {repo['description']}")
        print(f"   语言: {repo['language']}")
        print(f"   星标: {repo['stars']:,} | Fork: {repo['forks']:,} | 今日: +{repo['today_stars']}")
