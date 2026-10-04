#!/usr/bin/env python3
"""최근 축구 기사 후보를 RSS에서 모아 출력한다.

    python3 fetch_news.py [--hours 24]
"""
from __future__ import annotations

import argparse
import calendar
import html
import re
import sys
import time
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests

FEEDS = [
    ("연합뉴스", "https://www.yna.co.kr/rss/sports.xml"),
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian", "https://www.theguardian.com/football/rss"),
    ("Sky Sports", "https://www.skysports.com/rss/11095"),
    ("ESPN", "https://www.espn.com/espn/rss/soccer/news"),
]
UA = {"User-Agent": "Mozilla/5.0 (compatible; card-news/1.0)"}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def normalize(link: str) -> str:
    parts = urlsplit(link)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    cutoff = time.time() - args.hours * 3600
    seen, rows = set(), []
    for source, url in FEEDS:
        try:
            resp = requests.get(url, headers=UA, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[warn] {source} 수집 실패: {e}", file=sys.stderr)
            continue
        for e in feedparser.parse(resp.content).entries:
            stamp = e.get("published_parsed") or e.get("updated_parsed")
            if not stamp or not e.get("link"):
                continue
            published = calendar.timegm(stamp)
            link = normalize(e["link"])
            if published < cutoff or link in seen:
                continue
            seen.add(link)
            rows.append((published, source, clean(e.get("title", "")), clean(e.get("summary", ""))[:160], link))

    rows.sort(reverse=True)
    for published, source, title, summary, link in rows:
        when = time.strftime("%m-%d %H:%M", time.localtime(published))
        print(f"{when} | {source} | {title} | {summary} | {link}")


if __name__ == "__main__":
    main()
