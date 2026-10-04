from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from . import config

KST = timezone(timedelta(hours=9))


def load_state() -> dict:
    if config.STATE_PATH.exists():
        return json.loads(config.STATE_PATH.read_text(encoding="utf-8"))
    return {"posted": []}


def save_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_caption(cards: dict, link: str) -> str:
    tags = " ".join("#" + re.sub(r"[\s#]+", "", t) for t in cards["hashtags"] if t.strip())
    return f"{cards['headline']}\n\n{cards['caption']}\n{link}\n\n{tags}"


def prepare() -> int:
    from .feeds import fetch_articles, fetch_body
    from .render import render_all
    from .writer import select_article, write_cards

    if config.PENDING_PATH.exists():
        print("[prepare] 게시 대기 중인 카드뉴스가 있어 새로 만들지 않습니다")
        return 0

    state = load_state()
    used = {p["link"] for p in state["posted"]}
    candidates = [a for a in fetch_articles() if a.link not in used][: config.MAX_CANDIDATES]
    if not candidates:
        print("[prepare] 새 기사가 없습니다")
        return 0

    recent = [p["headline"] for p in state["posted"][-20:]]
    article = select_article(candidates, recent)
    if article is None:
        print("[prepare] 게시할 만한 기사가 없습니다")
        return 0

    cards = write_cards(article, fetch_body(article.link))
    now = datetime.now(KST)
    slug = now.strftime("%Y%m%d-%H%M")
    out_dir = config.POSTS_DIR / slug
    images = render_all(cards, article.source, out_dir, now)
    save_json(out_dir / "cards.json", {"article": article.__dict__, "cards": cards})
    save_json(config.PENDING_PATH, {
        "slug": slug,
        "link": article.link,
        "headline": cards["headline"],
        "images": [p.relative_to(config.ROOT).as_posix() for p in images],
        "caption": build_caption(cards, article.link),
        "attempts": 0,
    })
    print(f"[prepare] {out_dir.relative_to(config.ROOT)} 에 카드 {len(images)}장 생성")
    return 0


def raw_base_url() -> str:
    if os.environ.get("RAW_BASE_URL"):
        return os.environ["RAW_BASE_URL"].rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY 또는 RAW_BASE_URL 환경변수가 필요합니다")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=config.ROOT, text=True).strip()
    return f"https://raw.githubusercontent.com/{repo}/{sha}"


def publish() -> int:
    from .instagram import publish_carousel

    if not config.PENDING_PATH.exists():
        print("[publish] 게시할 카드뉴스가 없습니다")
        return 0
    pending = json.loads(config.PENDING_PATH.read_text(encoding="utf-8"))
    base = raw_base_url()
    urls = [f"{base}/{path}" for path in pending["images"]]
    state = load_state()

    try:
        media_id = publish_carousel(urls, pending["caption"])
    except Exception as e:
        pending["attempts"] += 1
        print(f"[publish] 실패 ({pending['attempts']}/{config.MAX_PUBLISH_ATTEMPTS}회): {e}", file=sys.stderr)
        if pending["attempts"] >= config.MAX_PUBLISH_ATTEMPTS:
            state["posted"].append({
                "link": pending["link"],
                "headline": pending["headline"],
                "slug": pending["slug"],
                "media_id": None,
                "posted_at": None,
            })
            save_json(config.STATE_PATH, state)
            config.PENDING_PATH.unlink()
            print("[publish] 재시도 한도를 넘어 이 기사는 건너뜁니다", file=sys.stderr)
        else:
            save_json(config.PENDING_PATH, pending)
        return 1

    state["posted"].append({
        "link": pending["link"],
        "headline": pending["headline"],
        "slug": pending["slug"],
        "media_id": media_id,
        "posted_at": datetime.now(KST).isoformat(timespec="seconds"),
    })
    state["posted"] = state["posted"][-300:]
    save_json(config.STATE_PATH, state)
    config.PENDING_PATH.unlink()
    print(f"[publish] 게시 완료: media_id={media_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m bot")
    parser.add_argument("command", choices=["prepare", "publish"])
    args = parser.parse_args()
    return prepare() if args.command == "prepare" else publish()


if __name__ == "__main__":
    sys.exit(main())
