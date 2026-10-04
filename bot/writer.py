from __future__ import annotations

import json
from datetime import datetime, timezone

import anthropic

from . import config
from .feeds import Article

SYSTEM = """당신은 한국 해외축구 팬을 위한 인스타그램 카드뉴스 편집자입니다.
영문 기사를 바탕으로 사실만 한국어로 전달합니다. 기사에 없는 내용(추측, 루머 확대, 수치)은 만들지 않습니다.
선수·감독·구단 이름은 국내 언론에서 통용되는 한글 표기를 씁니다(예: 손흥민, 맨체스터 유나이티드, 레알 마드리드)."""

SELECT_SCHEMA = {
    "type": "object",
    "properties": {
        "index": {"type": "integer"},
        "reason": {"type": "string"},
    },
    "required": ["index", "reason"],
    "additionalProperties": False,
}

CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "tag": {"type": "string"},
        "headline": {"type": "string"},
        "subhead": {"type": "string"},
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["title", "body"],
                "additionalProperties": False,
            },
        },
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["tag", "headline", "subhead", "slides", "caption", "hashtags"],
    "additionalProperties": False,
}

_client = anthropic.Anthropic()


def _ask(prompt: str, schema: dict, effort: str) -> dict:
    resp = _client.beta.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        output_config={
            "effort": effort,
            "format": {"type": "json_schema", "schema": schema},
        },
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Claude가 요청을 거절했습니다: {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("Claude 응답이 max_tokens에서 잘렸습니다")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


def select_article(candidates: list[Article], recent_headlines: list[str]) -> Article | None:
    lines = []
    for i, a in enumerate(candidates):
        when = datetime.fromtimestamp(a.published, timezone.utc).strftime("%m-%d %H:%M UTC")
        lines.append(f"[{i}] ({a.source}, {when}) {a.title} — {a.summary}")
    recent = "\n".join(f"- {h}" for h in recent_headlines) or "(없음)"
    prompt = f"""아래는 최근 해외축구 기사 목록입니다. 한국 팬이 가장 관심을 가질 만한 기사 하나를 고르세요.

기준:
- 이적, 경기 결과, 감독 교체, 부상, 한국 선수 소식 등 화제성이 큰 사실 보도를 우선합니다
- 라이브 중계 페이지, 퀴즈, 칼럼·의견 글, 팟캐스트, 하위리그 단신은 피합니다
- 이미 다룬 주제와 같은 사건이면 고르지 않습니다
- 고를 만한 기사가 없으면 index에 -1을 넣으세요

이미 다룬 주제:
{recent}

기사 목록:
{chr(10).join(lines)}"""
    result = _ask(prompt, SELECT_SCHEMA, "low")
    index = result["index"]
    if index < 0 or index >= len(candidates):
        return None
    print(f"[select] {candidates[index].title} — {result['reason']}")
    return candidates[index]


def write_cards(article: Article, body: str) -> dict:
    prompt = f"""아래 기사로 인스타그램 캐러셀 카드뉴스를 만드세요.

형식:
- tag: 리그·대회 이름 짧게 (예: 프리미어리그, 라리가, 챔피언스리그, 이적시장)
- headline: 표지 제목. 공백 포함 24자 이내, 핵심 사실이 드러나게
- subhead: 표지 부제. 40자 이내
- slides: 본문 카드 3~5장. 각 title은 18자 이내, body는 90자 이내의 1~2문장. 기사 흐름대로 사실 → 배경 → 의미 순서
- caption: 인스타그램 본문. 3~5문장 요약 후 마지막 줄에 "출처: {article.source}"
- hashtags: 5~10개, # 없이 단어만

기사 출처: {article.source}
제목: {article.title}
요약: {article.summary}
본문:
{body or "(본문을 가져오지 못했습니다. 제목과 요약에 있는 사실만 쓰세요.)"}"""
    cards = _ask(prompt, CARD_SCHEMA, "medium")
    if len(cards["slides"]) < 2:
        raise RuntimeError("본문 카드가 2장 미만으로 생성되었습니다")
    cards["slides"] = cards["slides"][:5]
    return cards
