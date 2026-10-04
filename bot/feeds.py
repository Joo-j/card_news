from __future__ import annotations

import calendar
import html
import re
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests

from . import config


@dataclass
class Article:
    source: str
    title: str
    summary: str
    link: str
    published: float


def normalize_link(link: str) -> str:
    parts = urlsplit(link)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def fetch_articles() -> list[Article]:
    cutoff = time.time() - config.FRESH_HOURS * 3600
    articles: list[Article] = []
    for source, url in config.FEEDS:
        try:
            resp = requests.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[warn] {source} 피드 수집 실패: {e}", file=sys.stderr)
            continue
        for entry in feedparser.parse(resp.content).entries:
            stamp = entry.get("published_parsed") or entry.get("updated_parsed")
            if not stamp or not entry.get("link"):
                continue
            published = calendar.timegm(stamp)
            if published < cutoff:
                continue
            articles.append(
                Article(
                    source=source,
                    title=_clean(entry.get("title", "")),
                    summary=_clean(entry.get("summary", "")),
                    link=normalize_link(entry["link"]),
                    published=published,
                )
            )
    articles.sort(key=lambda a: a.published, reverse=True)
    return articles


class _ParagraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.skip = 0
        self.current: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "aside", "figure", "nav", "footer"):
            self.skip += 1
        elif tag == "p":
            self.depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "aside", "figure", "nav", "footer"):
            self.skip = max(0, self.skip - 1)
        elif tag == "p" and self.depth:
            self.depth -= 1
            if not self.depth:
                text = re.sub(r"\s+", " ", "".join(self.current)).strip()
                if len(text) > 40:
                    self.paragraphs.append(text)
                self.current = []

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.current.append(data)


def fetch_body(link: str) -> str:
    try:
        resp = requests.get(link, headers={"User-Agent": config.USER_AGENT}, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[warn] 기사 본문 수집 실패 ({link}): {e}", file=sys.stderr)
        return ""
    parser = _ParagraphParser()
    parser.feed(resp.text)
    return "\n".join(parser.paragraphs)[:20000]
