#!/usr/bin/env python3
"""위키미디어 공용에서 출처 표기만으로 쓸 수 있는 사진을 찾고 내려받는다.

    python3 find_photo.py search "Harry Kane England"
    python3 find_photo.py download "Harry Kane England v Panama 27 June 26-184.jpg" --out <폴더>

download 는 사진(.jpg)과 같은 이름의 .json(작가, 라이선스, 원본 주소)을 함께 저장한다.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "card-news/1.0 (https://github.com/Joo-j/card_news)"}
ALLOWED = re.compile(r"^(CC BY(-SA)? [0-9.]+|CC0|Public domain)$", re.I)


def _meta(info: dict) -> dict:
    m = info["extmetadata"]
    get = lambda k: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.get(k, {}).get("value", ""))).strip()
    return {"artist": get("Artist"), "license": get("LicenseShortName"),
            "date": get("DateTimeOriginal")[:10], "page": info["descriptionurl"]}


def search(query: str) -> None:
    data = requests.get(API, headers=UA, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrlimit": 20, "gsrsearch": f"{query} filetype:bitmap",
        "prop": "imageinfo", "iiprop": "size|url|extmetadata"}).json()
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for p in pages:
        info = p["imageinfo"][0]
        meta = _meta(info)
        if not ALLOWED.match(meta["license"]):
            continue
        print(f"{info['width']}x{info['height']} | {meta['license']} | {meta['date']} | {p['title'][5:]}")


def download(title: str, out: Path) -> None:
    data = requests.get(API, headers=UA, timeout=30, params={
        "action": "query", "format": "json", "titles": f"File:{title}",
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1600}).json()
    info = next(iter(data["query"]["pages"].values()))["imageinfo"][0]
    meta = _meta(info)
    if not ALLOWED.match(meta["license"]):
        raise SystemExit(f"쓸 수 없는 라이선스입니다: {meta['license']}")
    out.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w]+", "_", Path(title).stem).strip("_")
    photo = out / f"{stem}.jpg"
    photo.write_bytes(requests.get(info["thumburl"], headers=UA, timeout=60).content)
    meta["title"] = title
    photo.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(photo)
    print(f"사진: {meta['artist']} / {meta['license']} (위키미디어 공용)")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    d = sub.add_parser("download")
    d.add_argument("title")
    d.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "search":
        search(args.query)
    else:
        download(args.title, args.out)


if __name__ == "__main__":
    main()
