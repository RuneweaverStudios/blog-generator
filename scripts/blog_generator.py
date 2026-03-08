#!/usr/bin/env python3
"""
Blog Generator - Analyzes journal entries and chat history to identify high-value
topics and generate structured blog posts.

Scans journal entries, scores topics using configurable weights, and produces
blog posts in a problem/solution format. Designed to run standalone or as a
cron job via OpenClaw.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

SKILL_DIR = Path(__file__).parent.parent
CONFIG_PATH = SKILL_DIR / "config.json"


def load_config() -> dict:
    """Load configuration from config.json, falling back to defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            print(f"Warning: Invalid JSON in config.json: {exc}. Using defaults.", file=sys.stderr)
    return {}


def validate_config(config: dict) -> list:
    """Validate that required config keys exist. Returns list of warnings."""
    warnings = []
    required_sections = ["paths", "scanning", "scoring"]
    for section in required_sections:
        if section not in config:
            warnings.append(f"Missing config section: {section} (using defaults)")
    paths = config.get("paths", {})
    if "openclawHome" not in paths and "journalDir" not in paths:
        warnings.append("No paths configured; using defaults (~/.openclaw/journal)")
    scoring = config.get("scoring", {})
    if "weights" not in scoring:
        warnings.append("No scoring weights configured; using built-in defaults")
    return warnings


class BlogGenerator:
    """Generates blog posts from journal entries and chat history analysis."""

    def __init__(self, openclaw_home: Path, config: Optional[dict] = None):
        self.config = config or load_config()
        self.openclaw_home = openclaw_home
        paths_cfg = self.config.get("paths", {})
        self.journal_dir = openclaw_home / paths_cfg.get("journalDir", "journal")
        self.blogs_dir = openclaw_home / paths_cfg.get("blogsDir", "blogs")
        self.blogs_dir.mkdir(parents=True, exist_ok=True)

        # Load scoring configuration
        scoring_cfg = self.config.get("scoring", {})
        self.weights = scoring_cfg.get("weights", {})
        self.high_value_keywords = scoring_cfg.get("highValueKeywords", [
            "openclaw gateway", "openclaw setup", "openclaw configuration",
            "openclaw skills", "openclaw troubleshooting", "gateway auth",
            "gateway restart", "gateway disconnected", "agent swarm",
            "subagent", "cursor chat history", "openclaw cron", "openclaw automation",
        ])
        self.problem_solving_words = scoring_cfg.get("problemSolvingWords", [
            "error", "failed", "issue", "problem", "fix",
            "solution", "how to", "troubleshoot", "resolve", "workaround",
        ])
        self.content_depth_min = scoring_cfg.get("contentDepthMinLength", 100)

    def scan_journal_entries(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """Scan journal entries from the last N days for interesting topics."""
        topics: List[Dict[str, Any]] = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        if not self.journal_dir.exists():
            return topics

        # Scan chat analysis files first
        for journal_file in self.journal_dir.glob("chat_analysis_*.md"):
            try:
                file_time = self._extract_timestamp_from_filename(journal_file.name)
                if file_time and file_time >= cutoff_date:
                    content = journal_file.read_text()
                    extracted = self._extract_topics_from_content(content, journal_file.name)
                    topics.extend(extracted)
            except Exception as exc:
                print(f"Error reading {journal_file}: {exc}", file=sys.stderr)

        # Scan other markdown files
        for journal_file in self.journal_dir.rglob("*.md"):
            if "chat_analysis" in journal_file.name:
                continue
            try:
                stat = journal_file.stat()
                file_time = datetime.fromtimestamp(stat.st_mtime)
                if file_time >= cutoff_date:
                    content = journal_file.read_text()
                    extracted = self._extract_topics_from_content(content, journal_file.name)
                    topics.extend(extracted)
            except Exception:
                continue

        return topics

    def _extract_timestamp_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract timestamp from filename like chat_analysis_2026-02-17_123045.md."""
        match = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{6})", filename)
        if not match:
            return None
        try:
            date_str = match.group(1)
            time_str = match.group(2)
            dt_str = f"{date_str} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    def _extract_topics_from_content(self, content: str, source: str) -> List[Dict[str, Any]]:
        """Extract topics from journal content by section type."""
        topics: List[Dict[str, Any]] = []

        section_patterns = {
            "discovery": r"##\s*(?:Key\s*Discoveries|Discoveries)\s*\n(.*?)(?=##|$)",
            "obstacle": r"##\s*(?:Obstacles\s*Encountered|Obstacles)\s*\n(.*?)(?=##|$)",
            "solution": r"##\s*(?:Solutions\s*Found|Solutions)\s*\n(.*?)(?=##|$)",
        }

        type_bonus = {
            "discovery": 0,
            "obstacle": self.weights.get("obstacleBonus", 2),
            "solution": self.weights.get("solutionBonus", 3),
        }

        for topic_type, pattern in section_patterns.items():
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for section_text in matches:
                for line in section_text.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        topics.append({
                            "type": topic_type,
                            "content": line[:500],
                            "source": source,
                            "value_score": self._score_topic_value(line) + type_bonus[topic_type],
                        })

        return topics

    def _score_topic_value(self, content: str) -> int:
        """Score a topic based on keyword relevance and content quality."""
        score = 0
        content_lower = content.lower()

        kw_weight = self.weights.get("highValueKeyword", 2)
        for keyword in self.high_value_keywords:
            if keyword.lower() in content_lower:
                score += kw_weight

        ps_weight = self.weights.get("problemSolvingWord", 1)
        for word in self.problem_solving_words:
            if word in content_lower:
                score += ps_weight

        if len(content) > self.content_depth_min:
            score += self.weights.get("contentDepthBonus", 1)

        return score

    def identify_high_value_topics(
        self, topics: List[Dict[str, Any]], max_topics: int = 5
    ) -> List[Dict[str, Any]]:
        """Select the highest-scoring unique topics for blog posts."""
        sorted_topics = sorted(topics, key=lambda x: x.get("value_score", 0), reverse=True)

        unique: List[Dict[str, Any]] = []
        seen: set = set()

        for topic in sorted_topics:
            signature = topic["content"][:100].lower().strip()
            if signature not in seen:
                seen.add(signature)
                unique.append(topic)
                if len(unique) >= max_topics:
                    break

        return unique

    def research_keyword(self, keyword: str) -> Dict[str, Any]:
        """Heuristic keyword research (placeholder for API integration)."""
        keyword_lower = keyword.lower()
        search_volume_score = 0

        if any(kw in keyword_lower for kw in ["how to", "tutorial", "guide", "setup", "install"]):
            search_volume_score += 3
        if any(kw in keyword_lower for kw in ["error", "fix", "troubleshoot"]):
            search_volume_score += 2
        if "openclaw" in keyword_lower:
            search_volume_score += 1

        return {
            "keyword": keyword,
            "estimated_volume": "medium" if search_volume_score >= 3 else "low",
            "competition": "low",
            "value_score": search_volume_score,
        }

    def generate_blog_post(self, topic: Dict[str, Any]) -> str:
        """Generate a structured blog post from a topic."""
        content_type = topic.get("type", "general")
        content = topic.get("content", "")
        title = self._extract_title_from_content(content, content_type)

        return f"""# {title}

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Overview

{self._generate_overview(content, content_type)}

## The Problem

{self._generate_problem_section(content, content_type)}

## The Solution

{self._generate_solution_section(content, content_type)}

## Key Takeaways

{self._generate_takeaways(content, content_type)}

## Related Topics

{self._generate_related_topics(content)}

---

*This post was automatically generated from journal analysis. Source: {topic.get('source', 'unknown')}*
"""

    def _extract_title_from_content(self, content: str, content_type: str) -> str:
        """Extract or generate a title from content."""
        for line in content.split("\n")[:3]:
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^\d+\.\s*", "", line)
            line = re.sub(r"\*\*", "", line)
            line = re.sub(r"`", "", line)
            if 20 < len(line) < 100:
                title = line[0].upper() + line[1:] if line else "OpenClaw Topic"
                if not title.endswith((".", "!", "?")):
                    title += ": A Practical Guide"
                return title

        fallbacks = {
            "obstacle": "Common OpenClaw Issues and How to Resolve Them",
            "solution": "Solving OpenClaw Configuration Challenges",
            "discovery": "OpenClaw Tips and Best Practices",
        }
        return fallbacks.get(content_type, "OpenClaw Insights and Solutions")

    def _generate_overview(self, content: str, content_type: str) -> str:
        overviews = {
            "obstacle": "In this post, we explore a common issue encountered with OpenClaw and provide practical solutions. Based on recent analysis, this problem appears frequently and has a clear resolution path.",
            "solution": "This guide walks through a proven solution for an OpenClaw configuration or usage challenge. The approach has been tested and documented from real-world usage.",
        }
        return overviews.get(
            content_type,
            "This post covers an interesting discovery or insight about using OpenClaw effectively. The information comes from analyzing recent usage patterns and journal entries.",
        )

    def _generate_problem_section(self, content: str, content_type: str) -> str:
        if content_type == "obstacle":
            problem_lines = [line.strip() for line in content.split("\n")[:3] if line.strip()]
            problem_text = " ".join(problem_lines[:2])
            return f"{problem_text}\n\nThis issue can be frustrating and may prevent you from using OpenClaw effectively. Understanding the root cause is the first step toward resolution."
        return "While working with OpenClaw, users may encounter various challenges related to configuration, gateway connectivity, or skill management. This post addresses one such challenge."

    def _generate_solution_section(self, content: str, content_type: str) -> str:
        if content_type == "solution":
            solution_lines = [line.strip() for line in content.split("\n")[:5] if line.strip()]
            solution_text = "\n\n".join(solution_lines[:3])
            return f"{solution_text}\n\n### Step-by-Step Guide\n\n1. Identify the specific issue you're experiencing\n2. Follow the solution approach outlined above\n3. Verify the fix works as expected\n4. Document any additional steps needed for your setup"
        return "To resolve this issue, follow these steps:\n\n1. Check your OpenClaw configuration\n2. Review recent logs for error messages\n3. Consult the relevant skill documentation\n4. If needed, restart the gateway or relevant services\n\nFor specific guidance, refer to the OpenClaw documentation or community resources."

    def _generate_takeaways(self, content: str, content_type: str) -> str:
        takeaways = [
            "Always check logs when encountering issues",
            "Keep your OpenClaw installation updated",
            "Review skill documentation for best practices",
            "Consider using gateway-guard for automatic recovery",
        ]
        return "\n".join(f"- {t}" for t in takeaways)

    def _generate_related_topics(self, content: str) -> str:
        related: List[str] = []
        content_lower = content.lower()

        if "gateway" in content_lower:
            related.extend(["- [Gateway Configuration Guide](#)", "- [Troubleshooting Gateway Issues](#)"])
        if "skill" in content_lower or "agent" in content_lower:
            related.extend(["- [OpenClaw Skills Overview](#)", "- [Creating Custom Skills](#)"])
        if "cron" in content_lower or "schedule" in content_lower:
            related.extend(["- [Setting Up Cron Jobs](#)", "- [Automation Best Practices](#)"])
        if not related:
            related = ["- [OpenClaw Documentation](#)", "- [Community Resources](#)"]

        return "\n".join(related[:4])

    def save_blog_post(self, blog_post: str, topic: Dict[str, Any]) -> Path:
        """Save blog post to the blogs directory with a timestamped filename."""
        title = blog_post.split("\n")[0].replace("# ", "").strip()
        slug = self._slugify(title)
        output_cfg = self.config.get("output", {})
        date_fmt = output_cfg.get("dateFormat", "%Y%m%d")
        timestamp = datetime.now().strftime(date_fmt)
        blog_file = self.blogs_dir / f"{timestamp}_{slug}.md"

        counter = 1
        while blog_file.exists():
            blog_file = self.blogs_dir / f"{timestamp}_{slug}_{counter}.md"
            counter += 1

        blog_file.write_text(blog_post)
        return blog_file

    def _slugify(self, text: str) -> str:
        """Convert text to a URL-friendly slug."""
        templates_cfg = self.config.get("templates", {})
        max_len = templates_cfg.get("slugMaxLength", 50)
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        return text[:max_len]


def _resolve_openclaw_home(args_home: Optional[str], config: dict) -> Path:
    """Resolve the OpenClaw home directory from CLI args, env var, config, or default."""
    if args_home:
        return Path(os.path.expanduser(args_home))
    env_home = os.environ.get("OPENCLAW_HOME")
    if env_home:
        return Path(os.path.expanduser(env_home))
    cfg_home = config.get("paths", {}).get("openclawHome")
    if cfg_home:
        return Path(os.path.expanduser(cfg_home))
    return Path.home() / ".openclaw"


def main():
    config = load_config()
    config_warnings = validate_config(config)
    for w in config_warnings:
        print(f"Config warning: {w}", file=sys.stderr)

    parser = argparse.ArgumentParser(
        description="Generate blog posts from journal entries and chat history."
    )
    parser.add_argument("--days", type=int, default=None, help="Days of journal history to analyze (default: from config or 7)")
    parser.add_argument("--max-topics", type=int, default=None, help="Maximum topics to generate (default: from config or 3)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--openclaw-home", type=str, default=None, help="OpenClaw home directory (default: $OPENCLAW_HOME or ~/.openclaw)")
    args = parser.parse_args()

    scanning_cfg = config.get("scanning", {})
    days_back = args.days if args.days is not None else scanning_cfg.get("defaultDaysBack", 7)
    max_topics = args.max_topics if args.max_topics is not None else scanning_cfg.get("maxTopics", 3)

    openclaw_home = _resolve_openclaw_home(args.openclaw_home, config)
    generator = BlogGenerator(openclaw_home, config=config)

    try:
        topics = generator.scan_journal_entries(days_back=days_back)

        if not topics:
            if args.json:
                print(json.dumps({"status": "no_topics", "message": "No topics found in journal entries"}))
            else:
                print("No topics found in journal entries from the specified time period.")
            return

        high_value_topics = generator.identify_high_value_topics(topics, max_topics=max_topics)

        if not high_value_topics:
            if args.json:
                print(json.dumps({"status": "no_high_value_topics", "message": "No high-value topics identified"}))
            else:
                print("No high-value topics identified.")
            return

        generated_posts = []
        for topic in high_value_topics:
            try:
                blog_post = generator.generate_blog_post(topic)
                blog_file = generator.save_blog_post(blog_post, topic)
                generated_posts.append({
                    "topic": topic,
                    "blog_file": str(blog_file),
                    "title": blog_post.split("\n")[0].replace("# ", ""),
                })
            except Exception as exc:
                print(f"Error generating blog post: {exc}", file=sys.stderr)
                continue

        if args.json:
            print(json.dumps({
                "status": "success",
                "topics_found": len(topics),
                "high_value_topics": len(high_value_topics),
                "blog_posts_generated": len(generated_posts),
                "posts": generated_posts,
            }, indent=2))
        else:
            print("=" * 70)
            print("BLOG POST GENERATION REPORT")
            print("=" * 70)
            print(f"\nTopics analyzed: {len(topics)}")
            print(f"High-value topics identified: {len(high_value_topics)}")
            print(f"Blog posts generated: {len(generated_posts)}\n")

            for i, post in enumerate(generated_posts, 1):
                print(f"{i}. {post['title']}")
                print(f"   Saved to: {post['blog_file']}\n")

            print("=" * 70)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
