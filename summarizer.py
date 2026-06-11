"""
AI 项目筛选与摘要模块

使用 OpenAI API 对 GitHub Trending 仓库进行智能筛选和中文摘要。
"""

import json
import logging
from typing import List, Dict, Optional, Tuple

import requests

from config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位资深的 GitHub 项目推荐专家和技术分析师。

你的任务是分析 GitHub 上的热门开源项目，并用中文为每个项目提供简洁、有价值的评价。

你需要：
1. 用 1-2 句话简要介绍项目的功能和价值（中文）
2. 给出推荐理由，说明为什么这个项目值得关注（中文）
3. 给出 1-5 分的评分：
   - 5分：革命性项目，强烈推荐关注
   - 4分：非常优秀，值得尝试
   - 3分：质量不错，可以了解
   - 2分：一般，看个人需求
   - 1分：不推荐

评分标准：
- 创新性和实用性
- 社区活跃度（star 增长速度、fork 数量）
- 代码质量和文档完善度
- 对开发者社区的潜在影响力

你必须严格按照 JSON 格式输出结果，不要输出任何其他内容。"""


def build_user_prompt(repos: List[Dict]) -> str:
    """构建发送给 AI 的用户提示词"""
    lines = ["请分析以下 GitHub Trending 项目并给出评价：\n"]

    for i, repo in enumerate(repos, 1):
        lines.append(f"【{i}. {repo['name']}】")
        lines.append(f"- 描述: {repo.get('description', '无')}")
        lines.append(f"- 语言: {repo.get('language', '未知')}")
        lines.append(f"- 总星标: {repo.get('stars', 0):,}")
        lines.append(f"- Fork: {repo.get('forks', 0):,}")
        lines.append(f"- 今日新增星标: +{repo.get('today_stars', 0)}")
        lines.append(f"- 链接: {repo.get('url', '')}")
        lines.append("")

    lines.append("""
请以如下 JSON 格式输出（严格 JSON，不要多余内容）：
{
  "results": [
    {
      "name": "owner/repo",
      "summary": "项目简介（中文）",
      "reason": "推荐理由（中文）",
      "score": 4
    }
  ]
}
""")
    return "\n".join(lines)


def call_openai(
    prompt: str,
    config: Config,
    timeout: int = 120,
) -> Optional[Dict]:
    """
    调用 OpenAI Chat Completions API。

    Args:
        prompt: 用户提示词
        config: 配置对象
        timeout: 请求超时时间

    Returns:
        API 响应的 JSON 内容，失败返回 None
    """
    if not config.openai_api_key:
        logger.warning("未设置 OpenAI API Key，跳过 AI 筛选")
        return None

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.openai_api_key}",
    }
    payload = {
        "model": config.openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }

    try:
        logger.info(f"调用 OpenAI API (model={config.openai_model})...")
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        logger.info("AI 响应获取成功")

        return json.loads(content)

    except requests.RequestException as e:
        logger.error(f"调用 OpenAI API 失败: {e}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"解析 AI 响应失败: {e}")
        return None


def summarize_and_filter(
    repos: List[Dict],
    config: Config,
) -> Tuple[List[Dict], List[Dict]]:
    """
    对仓库列表进行 AI 筛选和摘要。

    Args:
        repos: 仓库信息列表
        config: 配置对象

    Returns:
        Tuple[List[Dict], List[Dict]]:
            - 推荐列表（评分 >= min_score），每个 repo 增加 summary, reason, score 字段
            - 所有结果（含低分）
    """
    if not repos:
        logger.warning("没有仓库需要筛选")
        return [], []

    # 分批处理，每批最多 10 个（避免 prompt 过长）
    batch_size = 10
    all_results = []

    for i in range(0, len(repos), batch_size):
        batch = repos[i : i + batch_size]
        logger.info(f"处理第 {i // batch_size + 1} 批（{len(batch)} 个仓库）...")

        prompt = build_user_prompt(batch)
        ai_response = call_openai(prompt, config)

        if ai_response and "results" in ai_response:
            all_results.extend(ai_response["results"])
        else:
            logger.warning(f"第 {i // batch_size + 1} 批 AI 处理失败，跳过")
            # 为失败的仓库生成默认结果
            for repo in batch:
                all_results.append({
                    "name": repo["name"],
                    "summary": repo.get("description", ""),
                    "reason": "AI 分析不可用",
                    "score": config.min_score - 1,  # 低于阈值，不会被推荐
                })

    # 将 AI 结果与原始数据合并
    result_map = {r["name"]: r for r in all_results if "name" in r}

    recommended = []
    all_merged = []

    for repo in repos:
        ai_info = result_map.get(repo["name"], {})
        merged = {
            **repo,
            "summary": ai_info.get("summary", repo.get("description", "")),
            "reason": ai_info.get("reason", ""),
            "score": ai_info.get("score", 3),
        }

        all_merged.append(merged)

        if merged["score"] >= config.min_score:
            recommended.append(merged)

    # 推荐列表按评分降序排列
    recommended.sort(key=lambda x: (-x["score"], -x["today_stars"]))
    all_merged.sort(key=lambda x: (-x["score"], -x["today_stars"]))

    logger.info(
        f"AI 筛选完成: 总计 {len(all_merged)} 个, "
        f"推荐 {len(recommended)} 个 (评分 >= {config.min_score})"
    )

    return recommended, all_merged


def summarize_without_ai(repos: List[Dict]) -> List[Dict]:
    """
    在没有 AI API Key 的情况下，基于规则进行简单评分。
    用作降级方案。返回新列表，不修改输入。
    """
    import copy
    repos = copy.deepcopy(repos)
    for repo in repos:
        score = 3  # 基础分

        # 根据今日星标加分
        today = repo.get("today_stars", 0)
        if today >= 500:
            score += 2
        elif today >= 200:
            score += 1
        elif today >= 50:
            pass
        else:
            score -= 1

        # 根据总星标加分
        total = repo.get("stars", 0)
        if total >= 50000:
            score += 1
        elif total >= 10000:
            pass
        elif total < 1000:
            score -= 1

        # 限制在 1-5 范围
        score = max(1, min(5, score))

        repo["score"] = score
        repo["summary"] = repo.get("description", "")
        repo["reason"] = _generate_rule_reason(repo)

    return repos


def _generate_rule_reason(repo: Dict) -> str:
    """基于规则生成推荐理由"""
    reasons = []

    today = repo.get("today_stars", 0)
    if today >= 500:
        reasons.append(f"今日爆火（+{today}⭐）")
    elif today >= 200:
        reasons.append(f"今日热门（+{today}⭐）")

    total = repo.get("stars", 0)
    if total >= 50000:
        reasons.append("成熟项目，社区基础扎实")
    elif total >= 10000:
        reasons.append("社区活跃，有一定影响力")

    lang = repo.get("language", "")
    if lang:
        reasons.append(f"{lang} 生态")

    if not reasons:
        reasons.append("Trending 上榜项目")

    return "；".join(reasons)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 测试用例
    test_repos = [
        {
            "name": "test/repo1",
            "url": "https://github.com/test/repo1",
            "description": "A test repository for AI summarizer",
            "language": "Python",
            "stars": 15000,
            "forks": 500,
            "today_stars": 300,
        },
    ]

    config = Config.load()

    if config.openai_api_key:
        recommended, all_results = summarize_and_filter(test_repos, config)
        for r in recommended:
            print(f"\n{r['name']} (⭐{r['score']})")
            print(f"  简介: {r['summary']}")
            print(f"  理由: {r['reason']}")
    else:
        print("未设置 OPENAI_API_KEY，使用规则评分：")
        results = summarize_without_ai(test_repos)
        for r in results:
            print(f"\n{r['name']} (⭐{r['score']})")
            print(f"  理由: {r['reason']}")
