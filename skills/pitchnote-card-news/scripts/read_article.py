#!/usr/bin/env python3
"""기사 본문 문단을 추출해 출력한다.

    python3 read_article.py <기사 URL>
"""
from __future__ import annotations

import html
import re
import sys

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; pitchnote-card-news/1.0)"}


def main() -> None:
    page = requests.get(sys.argv[1], headers=UA, timeout=20).text
    page = re.sub(r"<(script|style|aside|figure|nav|footer)\b.*?</\1>", " ", page, flags=re.S | re.I)
    articles = re.findall(r"<article\b.*?</article>", page, flags=re.S | re.I)
    body = "\n".join(articles) or page
    for raw in re.findall(r"<p\b[^>]*>(.*?)</p>", body, flags=re.S | re.I):
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", raw))).strip()
        if len(text) > 40:
            print(text)


if __name__ == "__main__":
    main()
