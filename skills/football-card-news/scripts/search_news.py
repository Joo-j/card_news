#!/usr/bin/env python3
"""뉴스 검색에서 키워드별 최신 축구 기사 제목과 첫 보도 시각(한국 시간)을 출력한다. 속보 후보를 찾을 때 쓴다.

    python3 search_news.py 오피셜 경질 은퇴 --hours 12
    python3 search_news.py sacked confirmed official --lang en --hours 12
"""
from __future__ import annotations

import argparse
import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; card-news/1.0)"}
KST = timezone(timedelta(hours=9))
LANG = {"ko": ("ko", "KR", "KR:ko", "축구"), "en": ("en-GB", "GB", "GB:en", "(\"Premier League\" OR LaLiga OR Bundesliga OR \"Serie A\" OR \"Champions League\" OR \"Nations League\") -NFL")}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("keywords", nargs="+")
    p.add_argument("--lang", choices=LANG, default="ko")
    p.add_argument("--hours", type=int, default=12)
    a = p.parse_args()
    hl, gl, ceid, sport = LANG[a.lang]
    cutoff = datetime.now(KST) - timedelta(hours=a.hours)
    rows = {}
    for kw in a.keywords:
        r = requests.get("https://news.google.com/rss/search", headers=UA, timeout=20,
                         params={"q": f"{sport} {kw} when:1d", "hl": hl, "gl": gl, "ceid": ceid})
        for title, date in re.findall(r"<item><title>(.*?)</title>.*?<pubDate>(.*?)</pubDate>", r.text, re.S):
            when = parsedate_to_datetime(date).astimezone(KST)
            if when >= cutoff:
                rows[html.unescape(title)] = when
    for title, when in sorted(rows.items(), key=lambda kv: kv[1], reverse=True):
        print(f"{when:%m-%d %H:%M} | {title}")


if __name__ == "__main__":
    main()
