---
name: blog-generator
displayName: Blog Generator
description: Analyzes journal entries and chat history to identify high-value topics and automatically generate structured blog posts with problem/solution format. Supports cron scheduling, configurable scoring weights, and JSON output.
version: 1.1.0
---

# Blog Generator

Automatically generates blog posts by analyzing journal entries, chat history, and recent activity to identify high-value, high-search-volume topics related to OpenClaw.

## What This Skill Does

- **Scans** journal entries from the last N days for interesting topics (discoveries, obstacles, solutions)
- **Scores** topics based on configurable keyword weights and content quality
- **Generates** structured blog posts with overview, problem, solution, and takeaways sections
- **Saves** posts to the blogs directory as timestamped markdown files
- **Supports** JSON output for pipeline integration and cron-based automation

## When to Use

- As a scheduled cron job to automatically generate blog content weekly or daily
- Manually to create blog posts from recent journal analysis
- To identify and document high-value solutions and discoveries

## Commands

```bash
# Generate blog posts from last 7 days of journal entries
python3 scripts/blog_generator.py

# Analyze last 14 days and generate up to 5 posts
python3 scripts/blog_generator.py --days 14 --max-topics 5

# Output JSON format (for pipelines)
python3 scripts/blog_generator.py --json

# Use a custom OpenClaw home directory
python3 scripts/blog_generator.py --openclaw-home /path/to/openclaw

# Backward-compatible cron wrapper
python3 scripts/generate_blog.py --days 7 --json
```

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--days` | 7 (configurable) | Days of journal history to scan |
| `--max-topics` | 3 (configurable) | Maximum blog posts to generate |
| `--json` | false | Output results as JSON |
| `--openclaw-home` | `$OPENCLAW_HOME` or `~/.openclaw` | OpenClaw home directory |

Defaults for `--days` and `--max-topics` are read from `config.json` when not specified on the command line.

## Configuration (config.json)

All scoring weights, paths, and template settings are configurable:

```json
{
  "paths": {
    "openclawHome": "~/.openclaw",
    "journalDir": "journal",
    "blogsDir": "blogs"
  },
  "scanning": {
    "defaultDaysBack": 7,
    "maxTopics": 3,
    "filePatterns": ["chat_analysis_*.md", "*.md"]
  },
  "scoring": {
    "weights": {
      "highValueKeyword": 2,
      "problemSolvingWord": 1,
      "contentDepthBonus": 1,
      "obstacleBonus": 2,
      "solutionBonus": 3
    },
    "highValueKeywords": ["openclaw gateway", "openclaw setup", "..."],
    "problemSolvingWords": ["error", "failed", "fix", "..."],
    "contentDepthMinLength": 100
  },
  "templates": {
    "sectionOrder": ["overview", "problem", "solution", "takeaways", "related"],
    "slugMaxLength": 50
  },
  "output": {
    "filenameFormat": "{date}_{slug}.md",
    "dateFormat": "%Y%m%d"
  }
}
```

### Configuration Keys

| Key | Description |
|-----|-------------|
| `paths.openclawHome` | Base OpenClaw directory (overridden by `$OPENCLAW_HOME` env var or `--openclaw-home` flag) |
| `paths.journalDir` | Subdirectory within OpenClaw home for journal files |
| `paths.blogsDir` | Subdirectory within OpenClaw home for generated blog posts |
| `scoring.weights.*` | Point values for different scoring factors |
| `scoring.highValueKeywords` | Keywords that boost topic score |
| `scoring.problemSolvingWords` | Problem-related words that boost topic score |
| `scoring.contentDepthMinLength` | Minimum content length for depth bonus |
| `templates.slugMaxLength` | Maximum length for filename slugs |
| `output.dateFormat` | strftime format for filename date prefix |

## Topic Scoring

Topics are scored based on configurable weights:

| Factor | Default Weight | Description |
|--------|---------------|-------------|
| High-value keyword match | +2 per keyword | OpenClaw-specific terms |
| Problem-solving word | +1 per word | Error/fix/troubleshoot language |
| Content depth | +1 | Content exceeds minimum length threshold |
| Obstacle type bonus | +2 | Problems users face (high search value) |
| Solution type bonus | +3 | How-to solutions (highest search value) |

## Integration as a Cron Job

```json
{
  "payload": {
    "kind": "agentTurn",
    "message": "Run blog-generator skill to analyze journal entries and generate high-value blog posts.",
    "model": "openrouter/google/gemini-2.5-flash",
    "thinking": "low",
    "timeoutSeconds": 300
  },
  "schedule": { "kind": "cron", "cron": "0 9 * * *" },
  "delivery": { "mode": "announce" },
  "sessionTarget": "isolated",
  "name": "Blog Post Generator"
}
```

## Output Format

Blog posts are saved to `$OPENCLAW_HOME/blogs/YYYYMMDD_slugified-title.md` with sections:

- **Title** -- Extracted or generated from topic content
- **Overview** -- Context about the topic
- **The Problem** -- Description of the issue or challenge
- **The Solution** -- Step-by-step solution guide
- **Key Takeaways** -- Summary points
- **Related Topics** -- Links to related content

## Directory Structure

```
blog-generator/
├── SKILL.md               # Skill specification
├── _meta.json             # Skill metadata
├── config.json            # Configuration (scoring, paths, templates)
├── README.md              # Quick-start guide
├── requirements.txt       # Python dependencies (none)
├── .gitignore             # Git ignore rules
└── scripts/
    ├── blog_generator.py  # Main entry point
    └── generate_blog.py   # Cron-compatible wrapper (delegates to blog_generator.py)
```

## Requirements

- **Python 3.8+** -- Runtime (no external packages needed)
- Journal entries in `$OPENCLAW_HOME/journal/`
- Writable blogs directory at `$OPENCLAW_HOME/blogs/`
