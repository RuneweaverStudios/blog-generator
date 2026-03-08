#!/usr/bin/env python3
"""
Generate Blog - Cron-ready wrapper for automated blog post generation.

This script delegates entirely to blog_generator.py to avoid duplicating
error handling and argument parsing. It exists for backward compatibility
with cron jobs that reference this path.
"""

import sys
from pathlib import Path

# Ensure the skill scripts directory is importable
sys.path.insert(0, str(Path(__file__).parent))

from blog_generator import main

if __name__ == "__main__":
    main()
