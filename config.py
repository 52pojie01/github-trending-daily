import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    # GitHub Trending
    languages: List[str] = field(default_factory=lambda: ['python', 'javascript', 'go', 'rust'])
    spoken_language: str = 'zh'
    max_repos: int = 10

    # AI
    openai_api_key: str = ''
    openai_model: str = 'gpt-4o-mini'
    min_score: int = 3

    # Docker Trial
    trial_timeout: int = 600  # 10 minutes
    trial_ports: List[int] = field(default_factory=lambda: [8080, 8000, 3000])

    # Notification
    notify_target: str = 'weixin'

    @classmethod
    def load(cls, config_path: str = None) -> 'Config':
        if config_path is None:
            config_path = os.path.expanduser('~/.github-trending/config.yaml')

        config = cls()
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                    else:
                        import logging
                        logging.getLogger(__name__).warning("Unknown config key ignored: %s", key)

        # 环境变量覆盖
        if os.getenv('OPENAI_API_KEY'):
            config.openai_api_key = os.getenv('OPENAI_API_KEY')

        return config

    def save(self, config_path: str = None):
        """将当前配置保存到 YAML 文件"""
        if config_path is None:
            config_path = os.path.expanduser('~/.github-trending/config.yaml')

        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'languages': self.languages,
            'spoken_language': self.spoken_language,
            'max_repos': self.max_repos,
            'openai_model': self.openai_model,
            'min_score': self.min_score,
            'trial_timeout': self.trial_timeout,
            'trial_ports': self.trial_ports,
            'notify_target': self.notify_target,
        }

        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
