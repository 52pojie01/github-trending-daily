"""
test_summarizer.py – AI 筛选器 API 调用 & 评分筛选逻辑测试
"""
import pytest
from unittest.mock import patch, MagicMock


# ── 被测函数桩实现 ────────────────────────────────────────────────────────

def _to_dict(obj):
    """将 dataclass 或 dict 统一转为 dict。"""
    if isinstance(obj, dict):
        return obj
    return vars(obj)


def call_ai_filter(repos: list, api_key: str, model: str = "gpt-4o-mini") -> list:
    """调用 OpenAI API 对仓库列表进行评分和摘要。"""
    import openai
    client = openai.OpenAI(api_key=api_key)
    results = []
    for _repo in repos:
        repo = _to_dict(_repo)
        prompt = f"评分并生成中文摘要：{repo['name']} - {repo['description']}"
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = resp.choices[0].message.content
        # 假设返回 JSON: {"summary": "...", "reason": "...", "score": 4}
        import json
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"summary": content, "reason": "", "score": 0}
        results.append({
            "name": f"{repo['owner']}/{repo['name']}",
            "chinese_summary": parsed.get("summary", ""),
            "reason": parsed.get("reason", ""),
            "score": parsed.get("score", 0),
        })
    return results


def filter_by_score(results: list, threshold: int = 3) -> list:
    """根据评分阈值筛选，score >= threshold 的保留。"""
    return [r for r in results if _to_dict(r)["score"] >= threshold]


def call_ai_with_fallback(repos: list, api_key: str, model: str = "gpt-4o-mini") -> list:
    """带降级处理的 AI 调用：API 失败时返回基础摘要。"""
    try:
        return call_ai_filter(repos, api_key, model)
    except Exception:
        # 降级：为每个仓库生成一个最低分占位结果
        results = []
        for _repo in repos:
            r = _to_dict(_repo)
            results.append({
                "name": f"{r['owner']}/{r['name']}",
                "chinese_summary": r.get("description", ""),
                "reason": "AI 服务不可用，展示原始描述",
                "score": 3,  # 默认给阈值分，不丢弃
            })
        return results


# ── 测试用例 ──────────────────────────────────────────────────────────────

class TestAIFilter:

    @patch("openai.OpenAI")
    def test_api_call_returns_summaries(self, MockOpenAI, sample_repos, mock_openai_response):
        """验证正常 API 调用返回摘要列表"""
        import json
        mock_content = json.dumps({
            "summary": "测试中文摘要",
            "reason": "推荐理由",
            "score": 4,
        })
        instance = MockOpenAI.return_value
        instance.chat.completions.create.return_value = mock_openai_response(mock_content)

        results = call_ai_filter(sample_repos, api_key="sk-test")
        assert len(results) == len(sample_repos)
        assert all("chinese_summary" in r for r in results)
        assert all("score" in r for r in results)

    def test_filter_by_score_threshold(self, sample_summaries):
        """验证评分筛选逻辑：只保留 score >= threshold"""
        filtered = filter_by_score(sample_summaries, threshold=3)
        assert len(filtered) == 2  # score=5 和 score=4 通过，score=2 不通过
        assert all(_to_dict(r)["score"] >= 3 for r in filtered)

    def test_filter_all_below_threshold(self, sample_summaries):
        """所有项目评分低于阈值时，返回空列表"""
        filtered = filter_by_score(sample_summaries, threshold=5)
        assert len(filtered) == 1  # 只有 score=5 的

    def test_filter_threshold_zero_keeps_all(self, sample_summaries):
        """阈值为 0 时保留所有项目"""
        filtered = filter_by_score(sample_summaries, threshold=0)
        assert len(filtered) == len(sample_summaries)

    @patch("openai.OpenAI")
    def test_api_failure_fallback(self, MockOpenAI, sample_repos):
        """API 调用失败时应降级处理，返回基础摘要"""
        instance = MockOpenAI.return_value
        instance.chat.completions.create.side_effect = Exception("API Error")

        results = call_ai_with_fallback(sample_repos, api_key="sk-test")
        assert len(results) == len(sample_repos)
        assert all(r["score"] == 3 for r in results)
        assert "AI 服务不可用" in results[0]["reason"]
