"""
test_config.py – 配置加载、环境变量覆盖、默认值测试
"""
import os
import pytest
from unittest.mock import patch


# ── 被测函数桩实现 ────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "languages": [],
    "max_repos": 25,
    "score_threshold": 3,
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "docker_timeout": 600,
    "wechat_webhook": "",
    "trending_period": "daily",
}


def load_config(config_path: str = None) -> dict:
    """加载 YAML 配置文件，合并默认值。"""
    import yaml
    config = dict(DEFAULT_CONFIG)
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        config.update(user_config)
    return config


def apply_env_overrides(config: dict) -> dict:
    """用环境变量覆盖配置。"""
    env_map = {
        "GITHUB_TRENDING_LANGUAGES": ("languages", lambda v: [x.strip() for x in v.split(",")]),
        "GITHUB_TRENDING_MAX_REPOS": ("max_repos", int),
        "GITHUB_TRENDING_SCORE_THRESHOLD": ("score_threshold", int),
        "OPENAI_API_KEY":             ("openai_api_key", str),
        "OPENAI_MODEL":               ("openai_model", str),
        "DOCKER_TIMEOUT":             ("docker_timeout", int),
        "WECHAT_WEBHOOK":             ("wechat_webhook", str),
    }
    for env_var, (key, converter) in env_map.items():
        value = os.environ.get(env_var)
        if value is not None:
            try:
                config[key] = converter(value)
            except (ValueError, TypeError):
                pass  # 忽略格式错误的环境变量
    return config


def get_config(config_path: str = None) -> dict:
    """完整配置加载流程：YAML → 环境变量覆盖。"""
    config = load_config(config_path)
    config = apply_env_overrides(config)
    return config


# ── 测试用例 ──────────────────────────────────────────────────────────────

class TestConfig:

    def test_default_values(self):
        """无配置文件时应返回全部默认值"""
        config = load_config(None)
        assert config["max_repos"] == 25
        assert config["score_threshold"] == 3
        assert config["openai_model"] == "gpt-4o-mini"
        assert config["docker_timeout"] == 600
        assert config["trending_period"] == "daily"

    def test_load_yaml_config(self, tmp_path, yaml_config):
        """YAML 配置文件应正确覆盖默认值"""
        import yaml
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(yaml_config), encoding="utf-8")

        config = load_config(str(config_file))
        assert config["max_repos"] == 10
        assert config["score_threshold"] == 3
        assert "Python" in config["languages"]
        assert config["openai_api_key"] == "sk-test-key-12345"

    def test_env_override(self):
        """环境变量应覆盖配置文件中的值"""
        config = {"max_repos": 25, "openai_api_key": "", "openai_model": "gpt-4o-mini"}
        with patch.dict(os.environ, {
            "GITHUB_TRENDING_MAX_REPOS": "50",
            "OPENAI_API_KEY": "sk-env-key",
            "OPENAI_MODEL": "gpt-4",
        }):
            config = apply_env_overrides(config)
        assert config["max_repos"] == 50
        assert config["openai_api_key"] == "sk-env-key"
        assert config["openai_model"] == "gpt-4"

    def test_env_languages_parsing(self):
        """环境变量中的语言列表应正确解析为 list"""
        config = {"languages": []}
        with patch.dict(os.environ, {"GITHUB_TRENDING_LANGUAGES": "Python, Go, TypeScript"}):
            config = apply_env_overrides(config)
        assert config["languages"] == ["Python", "Go", "TypeScript"]

    def test_partial_yaml_preserves_defaults(self, tmp_path):
        """部分配置文件应保留其余默认值"""
        import yaml
        partial = {"max_repos": 5}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(partial), encoding="utf-8")

        config = load_config(str(config_file))
        assert config["max_repos"] == 5
        assert config["score_threshold"] == 3  # 保留默认
        assert config["openai_model"] == "gpt-4o-mini"  # 保留默认

    def test_missing_config_file_uses_defaults(self):
        """指定不存在的配置文件路径应返回默认值"""
        config = load_config("/nonexistent/path/config.yaml")
        assert config == DEFAULT_CONFIG
