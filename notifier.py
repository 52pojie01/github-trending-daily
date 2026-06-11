"""Push notifications via hermes send."""

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

DEFAULT_TARGET = "weixin"


def send(message: str, target: str = DEFAULT_TARGET, dry_run: bool = False) -> bool:
    """Send a message via hermes send.

    Args:
        message: The message content (supports Markdown).
        target: The target platform (default: weixin).
        dry_run: If True, only print the message without sending.

    Returns:
        True if sent successfully, False otherwise.
    """
    if dry_run:
        print(f"[DRY RUN] Would send to {target}:\n")
        print(message)
        logger.info("[DRY RUN] Message printed to stdout")
        return True

    if not message or not message.strip():
        logger.error("Cannot send empty message")
        return False

    try:
        cmd = ["hermes", "send", "--to", target, "-"]
        logger.info("Sending message to %s (length=%d)", target, len(message))

        result = subprocess.run(
            cmd,
            input=message,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            logger.info("Message sent successfully to %s", target)
            if result.stdout:
                logger.debug("hermes stdout: %s", result.stdout.strip())
            return True
        else:
            logger.error(
                "hermes send failed (code=%d): %s",
                result.returncode,
                result.stderr.strip() if result.stderr else "no error output",
            )
            return False

    except FileNotFoundError:
        logger.error("'hermes' command not found. Is hermes-agent installed?")
        return False
    except subprocess.TimeoutExpired:
        logger.error("hermes send timed out after 60s")
        return False
    except Exception as e:
        logger.error("Unexpected error sending message: %s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_msg = "# Test\n\nHello from GitHub Trending Daily!"
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        send(test_msg, dry_run=True)
    else:
        send(test_msg)
