#!/usr/bin/env python3
"""Main entry point for GitHub Trending Daily."""

import argparse
import logging
import sys

from config import Config
from trending import fetch_trending, fetch_all_trending
from summarizer import summarize_and_filter, summarize_without_ai
from renderer import render
from notifier import send
from docker_trial import trial, cleanup


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Trending Daily - Generate and deliver trending project reports"
    )
    parser.add_argument("--config", default=None, help="Path to config file (default: ~/.github-trending/config.yaml)")
    parser.add_argument("--language", default=None, help="Filter by programming language")
    parser.add_argument("--since", default=None, choices=["daily", "weekly", "monthly"], help="Time range")
    parser.add_argument("--limit", type=int, default=None, help="Max number of projects in report")
    parser.add_argument("--trial", action="store_true", help="Enable Docker trial for top projects")
    parser.add_argument("--trial-timeout", type=int, default=None, help="Trial container lifetime in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Generate report but don't send notification")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level")
    parser.add_argument("--target", default=None, help="Notification target platform")
    parser.add_argument("--output", default=None, help="Save report to file instead of stdout")

    args = parser.parse_args()
    setup_logging(args.log_level)

    try:
        # 1. Load config
        logger.info("Loading config from %s", args.config or "default path")
        cfg = Config.load(args.config)
        logger.info("Config loaded: languages=%s, max_repos=%d", cfg.languages, cfg.max_repos)

        # CLI args override config
        limit = args.limit if args.limit is not None else cfg.max_repos
        since = args.since or "daily"
        trial_timeout = args.trial_timeout or cfg.trial_timeout
        target = args.target or cfg.notify_target

        # 2. Fetch trending for each configured language
        if args.language:
            languages = [args.language]
        else:
            languages = cfg.languages

        logger.info("Fetching trending projects (languages=%s, since=%s)", languages, since)
        projects = fetch_all_trending(
            languages=languages,
            since=since,
            spoken_language=cfg.spoken_language,
            max_repos_per_lang=cfg.max_repos,
        )
        logger.info("Total unique projects: %d", len(projects))

        if not projects:
            logger.warning("No trending projects found. Exiting.")
            return

        # 3. Summarize and filter with AI (or fallback to rule-based)
        logger.info("Summarizing and filtering projects...")
        if cfg.openai_api_key:
            recommended, all_results = summarize_and_filter(projects, cfg)
        else:
            logger.info("No OpenAI API key, using rule-based summarizer")
            recommended = summarize_without_ai(projects)
            all_results = recommended

        # Limit results
        filtered = recommended[:limit] if recommended else all_results[:limit]
        logger.info("Selected %d projects for report", len(filtered))

        # 4. Docker trials (optional)
        if args.trial:
            logger.info("Starting Docker trials for top projects...")
            for p in filtered[:3]:  # Trial top 3
                try:
                    trial_info = trial(p, timeout=trial_timeout)
                    if trial_info:
                        p["trial_url"] = trial_info.get("url", "")
                        logger.info("Trial for %s: %s", p.get("name"), p["trial_url"])
                    else:
                        logger.warning("Trial setup returned None for %s", p.get("name"))
                except Exception as e:
                    logger.warning("Trial failed for %s: %s", p.get("name"), e)

        # 5. Normalize field names for renderer
        for p in filtered:
            p.setdefault("total_stars", p.get("stars", 0))
            p.setdefault("stars_today", p.get("today_stars", 0))

        # 6. Render report
        logger.info("Rendering report...")
        report = render(filtered)

        # 7. Output
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info("Report saved to %s", args.output)
        else:
            print(report)

        # 8. Send notification
        success = send(report, target=target, dry_run=args.dry_run)
        if success:
            logger.info("Notification %s", "simulated (dry-run)" if args.dry_run else "sent successfully")
        else:
            logger.error("Failed to send notification")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        cleanup()
        sys.exit(130)
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        if args.trial:
            logger.info("Cleaning up trial containers...")
            cleanup()


if __name__ == "__main__":
    main()
