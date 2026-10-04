from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
POSTS_DIR = ROOT / "posts"
STATE_PATH = ROOT / "data" / "state.json"
PENDING_PATH = POSTS_DIR / "pending.json"

FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian", "https://www.theguardian.com/football/rss"),
    ("Sky Sports", "https://www.skysports.com/rss/11095"),
    ("ESPN", "https://www.espn.com/espn/rss/soccer/news"),
]

FRESH_HOURS = 24
MAX_CANDIDATES = 40
MAX_PUBLISH_ATTEMPTS = 3

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL") or "claude-opus-5-5"
BRAND_NAME = os.environ.get("BRAND_NAME") or "해외축구 브리핑"

IG_USER_ID = os.environ.get("IG_USER_ID") or ""
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN") or ""
IG_GRAPH_HOST = os.environ.get("IG_GRAPH_HOST") or "graph.instagram.com"
IG_API_VERSION = os.environ.get("IG_API_VERSION") or "v23.0"

USER_AGENT = "Mozilla/5.0 (compatible; card-news-bot/1.0)"
