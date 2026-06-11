"""Docker trial management for GitHub trending projects."""

import atexit
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Global registry of active trial containers for cleanup
_active_trials: list[dict[str, Any]] = []
_lock = threading.Lock()
_base_port = 8080
_port_counter = 0


def _next_port() -> int:
    """Find an available port starting from _base_port."""
    import socket
    global _port_counter
    with _lock:
        for attempt in range(100):
            port = _base_port + _port_counter + attempt
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', port)) != 0:
                    _port_counter = _port_counter + attempt + 1
                    return port
        # fallback
        port = _base_port + _port_counter
        _port_counter += 1
        return port


def _run_cmd(cmd: list[str], cwd: str | None = None, timeout: int = 120) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def _detect_strategy(project: dict[str, Any], repo_dir: str) -> str:
    """Detect trial strategy based on repo contents."""
    if os.path.isfile(os.path.join(repo_dir, "Dockerfile")):
        return "dockerfile"
    if os.path.isfile(os.path.join(repo_dir, "requirements.txt")) or os.path.isfile(os.path.join(repo_dir, "setup.py")) or os.path.isfile(os.path.join(repo_dir, "pyproject.toml")):
        return "python"
    if os.path.isfile(os.path.join(repo_dir, "package.json")):
        return "node"
    return "clone"


def _detect_port(repo_dir: str) -> int:
    """Try to detect exposed port from Dockerfile or default to 8080."""
    dockerfile = os.path.join(repo_dir, "Dockerfile")
    if os.path.isfile(dockerfile):
        try:
            with open(dockerfile) as f:
                for line in f:
                    if line.strip().startswith("EXPOSE"):
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            return int(parts[1])
        except Exception:
            pass
    return 8080


def _schedule_cleanup(container_name: str, timeout: int):
    """Schedule container removal after timeout seconds."""
    def _cleanup():
        logger.info("Auto-cleaning container: %s", container_name)
        _run_cmd(["docker", "rm", "-f", container_name])
        with _lock:
            _active_trials[:] = [t for t in _active_trials if t.get("container") != container_name]
        logger.info("Cleaned up container: %s", container_name)

    timer = threading.Timer(timeout, _cleanup)
    timer.daemon = True
    timer.start()
    return timer


def trial(project: dict[str, Any], timeout: int = 300) -> dict[str, Any] | None:
    """Attempt to create a Docker trial for a project.

    Args:
        project: Project dict with at least 'url' and 'name'.
        timeout: Seconds before auto-cleaning the container.

    Returns:
        Dict with trial info (url, container, strategy) or None on failure.
    """
    repo_url = project.get("url", "")
    if not repo_url:
        logger.error("No URL in project data")
        return None

    import re as _re
    project_name = project.get("name", "unknown").replace("/", "_")
    # Docker container names must match [a-zA-Z0-9][a-zA-Z0-9_.-]
    project_name = _re.sub(r'[^a-zA-Z0-9_.-]', '', project_name)[:40]
    container_name = f"trending-trial-{project_name}".lower()

    tmpdir = tempfile.mkdtemp(prefix="trending-trial-")
    repo_dir = os.path.join(tmpdir, "repo")

    try:
        # Clone
        logger.info("Cloning %s ...", repo_url)
        rc, out, err = _run_cmd(["git", "clone", "--depth", "1", repo_url, repo_dir], timeout=60)
        if rc != 0:
            logger.error("Git clone failed: %s", err)
            return None

        strategy = _detect_strategy(project, repo_dir)
        host_port = _next_port()
        app_port = _detect_port(repo_dir)

        trial_info: dict[str, Any] = {
            "strategy": strategy,
            "container": container_name,
            "host_port": host_port,
            "app_port": app_port,
            "url": f"http://localhost:{host_port}",
        }

        if strategy == "dockerfile":
            image_name = f"{container_name}:latest"
            rc, _, err = _run_cmd(["docker", "build", "-t", image_name, repo_dir], timeout=180)
            if rc != 0:
                logger.error("Docker build failed: %s", err)
                return None
            rc, _, err = _run_cmd([
                "docker", "run", "-d",
                "--name", container_name,
                "-p", f"{host_port}:{app_port}",
                "--memory=256m", "--cpus=0.5",
                "--cap-drop=ALL", "--security-opt=no-new-privileges",
                "--network=bridge",
                "--label", "trending-trial=true",
                image_name,
            ])
            if rc != 0:
                logger.error("Docker run failed: %s", err)
                return None

        elif strategy == "python":
            rc, _, err = _run_cmd(["docker", "run", "-d",
                "--name", container_name,
                "-p", f"{host_port}:{app_port}",
                "-v", f"{repo_dir}:/app:ro",
                "-w", "/app",
                "--memory=256m", "--cpus=0.5",
                "--cap-drop=ALL", "--security-opt=no-new-privileges",
                "--network=none",
                "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                "--pids-limit=64",
                "--label", "trending-trial=true",
                "python:3.12-slim",
                "bash", "-c", "cp -r /app /tmp/app && cd /tmp/app && pip install -r requirements.txt 2>/dev/null && (python main.py || python app.py) || sleep infinity",
            ])
            if rc != 0:
                logger.error("Python trial failed: %s", err)
                return None

        elif strategy == "node":
            rc, _, err = _run_cmd(["docker", "run", "-d",
                "--name", container_name,
                "-p", f"{host_port}:{app_port}",
                "-v", f"{repo_dir}:/app:ro",
                "-w", "/app",
                "--memory=256m", "--cpus=0.5",
                "--cap-drop=ALL", "--security-opt=no-new-privileges",
                "--network=none",
                "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                "--pids-limit=64",
                "--label", "trending-trial=true",
                "node:20-slim",
                "bash", "-c", "cp -r /app /tmp/app && cd /tmp/app && npm install 2>/dev/null && npm start || sleep infinity",
            ])
            if rc != 0:
                logger.error("Node trial failed: %s", err)
                return None

        else:
            # clone only — no container to run
            trial_info["url"] = repo_url
            logger.info("Clone-only strategy for %s", project.get("name"))
            return trial_info

        # Register and schedule cleanup
        with _lock:
            _active_trials.append(trial_info)
        _schedule_cleanup(container_name, timeout)

        logger.info("Trial started: %s -> %s", container_name, trial_info["url"])

    except Exception as e:
        logger.error("Trial setup failed for %s: %s", project.get("name"), e)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None

    # Only delete tmpdir after container is running (it uses :ro mount)
    shutil.rmtree(tmpdir, ignore_errors=True)
    return trial_info


def cleanup():
    """Remove all active trial containers (also registered with atexit)."""
    with _lock:
        trials = list(_active_trials)

    for t in trials:
        name = t.get("container")
        if name:
            logger.info("Cleaning up container: %s", name)
            _run_cmd(["docker", "rm", "-f", name])

    with _lock:
        _active_trials.clear()

    logger.info("All trial containers cleaned up")


# Register cleanup on process exit
atexit.register(cleanup)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("docker_trial module loaded. Use trial() and cleanup() functions.")
