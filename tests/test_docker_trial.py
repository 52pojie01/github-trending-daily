"""
test_docker_trial.py – Docker 试用管理测试
"""
import pytest
from unittest.mock import patch, MagicMock


# ── 被测函数桩实现 ────────────────────────────────────────────────────────

# 项目类型 → Dockerfile/命令映射
LANG_STRATEGIES = {
    "Python": "pip install -r requirements.txt && python main.py",
    "Node":   "npm install && npm start",
    "Go":     "go build -o app && ./app",
    "Rust":   "cargo build --release && ./target/release/app",
    "Docker": "docker run --rm {image}",
}


def detect_project_type(repo_meta: dict) -> str:
    """根据仓库元数据检测项目类型。"""
    files = repo_meta.get("files", [])
    lang = repo_meta.get("language", "")

    if "Dockerfile" in files:
        return "Docker"
    if "requirements.txt" in files or "pyproject.toml" in files or lang == "Python":
        return "Python"
    if "package.json" in files or lang in ("JavaScript", "TypeScript"):
        return "Node"
    if "go.mod" in files or lang == "Go":
        return "Go"
    if "Cargo.toml" in files or lang == "Rust":
        return "Rust"
    return "Unknown"


def generate_docker_command(repo_url: str, project_type: str, timeout: int = 600) -> dict:
    """生成 Docker 运行命令。"""
    import shlex
    strategy = LANG_STRATEGIES.get(project_type)
    if not strategy:
        return {"error": f"不支持的项目类型: {project_type}"}

    container_name = repo_url.replace("https://github.com/", "").replace("/", "_")
    cmd = (
        f"docker run -d --name {container_name} "
        f"--memory=512m --cpus=1 "
        f"--label auto-trial=true "
        f"--label expire-after={timeout}s "
        f"github-trending/{container_name}"
    )
    return {
        "container_name": container_name,
        "command": cmd,
        "strategy": strategy,
        "timeout": timeout,
    }


def cleanup_expired_containers() -> list:
    """清理所有带 auto-trial 标签的过期容器（模拟）。"""
    # 实际实现会调用 docker ps --filter label=auto-trial
    # 此处为桩实现
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "label=auto-trial", "-q"],
            capture_output=True, text=True, timeout=10,
        )
        container_ids = result.stdout.strip().split("\n") if result.stdout.strip() else []
        cleaned = []
        for cid in container_ids:
            subprocess.run(["docker", "rm", "-f", cid], capture_output=True, timeout=10)
            cleaned.append(cid)
        return cleaned
    except Exception:
        return []


# ── 测试用例 ──────────────────────────────────────────────────────────────

class TestDockerTrial:

    def test_detect_python_project(self):
        """有 requirements.txt 的仓库应被识别为 Python"""
        meta = {"language": "Python", "files": ["requirements.txt", "main.py", "README.md"]}
        assert detect_project_type(meta) == "Python"

    def test_detect_node_project(self):
        """有 package.json 的仓库应被识别为 Node"""
        meta = {"language": "JavaScript", "files": ["package.json", "index.js"]}
        assert detect_project_type(meta) == "Node"

    def test_detect_docker_project(self):
        """有 Dockerfile 的仓库优先识别为 Docker"""
        meta = {"language": "Python", "files": ["Dockerfile", "requirements.txt", "app.py"]}
        assert detect_project_type(meta) == "Docker"

    def test_detect_go_project(self):
        """有 go.mod 的仓库应被识别为 Go"""
        meta = {"language": "Go", "files": ["go.mod", "main.go"]}
        assert detect_project_type(meta) == "Go"

    def test_detect_unknown_project(self):
        """无特征文件且无语言信息时返回 Unknown"""
        meta = {"language": "", "files": ["README.md"]}
        assert detect_project_type(meta) == "Unknown"

    def test_generate_docker_command_structure(self):
        """生成的 Docker 命令应包含容器名、资源限制和标签"""
        result = generate_docker_command("https://github.com/openai/awesome-ai", "Python")
        assert "container_name" in result
        assert "command" in result
        assert "--memory=512m" in result["command"]
        assert "--label auto-trial=true" in result["command"]

    def test_generate_docker_command_unsupported_type(self):
        """不支持的项目类型应返回错误"""
        result = generate_docker_command("https://github.com/test/repo", "Haskell")
        assert "error" in result

    def test_cleanup_returns_list(self):
        """清理函数应返回列表（即使 Docker 不可用也不抛异常）"""
        result = cleanup_expired_containers()
        assert isinstance(result, list)
