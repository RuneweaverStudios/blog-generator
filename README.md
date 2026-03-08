# Blog Generator

Automatically generates blog posts by analyzing journal entries and chat history to identify high-value topics. Produces structured posts in a problem/solution format.

## Quick Start

```bash
# Generate blog posts from the last 7 days of journal entries
python3 scripts/blog_generator.py

# Analyze last 14 days, generate up to 5 posts
python3 scripts/blog_generator.py --days 14 --max-topics 5

# Output as JSON (for automation pipelines)
python3 scripts/blog_generator.py --json
```

## Requirements

- **Python 3.8+** (no external packages)
- Journal entries in `$OPENCLAW_HOME/journal/` (defaults to `~/.openclaw/journal/`)

## Installation

```bash
git clone https://github.com/RuneweaverStudios/blog-generator.git
cd blog-generator
python3 scripts/blog_generator.py --help
```

No `pip install` step needed -- the skill uses only the Python standard library.

## Configuration

Edit `config.json` to customize:

- **Scoring weights** -- How much different factors contribute to topic ranking
- **High-value keywords** -- OpenClaw-specific terms that boost topic scores
- **Output paths** -- Where journal files are read from and blogs are saved to
- **Template settings** -- Slug length, date format, section order

The OpenClaw home directory is resolved in this order:
1. `--openclaw-home` CLI flag
2. `$OPENCLAW_HOME` environment variable
3. `paths.openclawHome` in config.json
4. `~/.openclaw` (default)

## How It Works

1. Scans journal directory for markdown files from the last N days
2. Extracts topics from discoveries, obstacles, and solutions sections
3. Scores topics based on configurable keyword weights and content quality
4. Selects the top N highest-scoring unique topics
5. Generates structured blog posts with problem/solution format
6. Saves posts to the blogs directory with timestamped filenames

## Cron Scheduling

Set up as an OpenClaw cron job to run daily or weekly. See `SKILL.md` for example cron configurations.

```bash
# Quick cron test
python3 scripts/generate_blog.py --days 7 --json
```

## Output

Blog posts are saved as markdown files at `$OPENCLAW_HOME/blogs/YYYYMMDD_slug.md`. Each post includes an overview, problem description, solution guide, key takeaways, and related topics.

See `SKILL.md` for full configuration reference and scoring details.
