#!/usr/bin/env python3
"""캐러셀 2장째부터 쓰는 내용 장(1080x1350)을 만든다. 1장째 표지는 render_card.py 로 만든다.

    python3 render_slide.py info --photo kane.jpg \
        --body "체코전 3골 모두 케인이 만들었다\\n전반 27분 케인의 크로스, 상대 자책골\\n전반 40분 로저스 패스 받아 오른발 골" \
        --out 1_케인_02.jpg [--handle @pitchnote_] [--focus-y 0.15] [--focus-x 0.5] [--zoom 1.0]

    python3 render_slide.py quote --photo kane.jpg --quote "꿈도 꾸지 못했던 일입니다.\\n정말 큰 영광입니다." \
        --who "해리 케인" --out 1_케인_05.jpg

info 는 본문 여러 줄을 화면 아래쪽에 가운데 정렬로 쓴다.
quote 는 인용문을 “ ” 로 감싸 가운데 정렬로 쓰고, 맨 아래에 말한 사람을 쓴다. 따옴표는 직접 넣지 않아도 된다.
두 모양 모두 계정 아이디를 오른쪽 위에 둔다. \\n 은 줄바꿈이다.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from render_card import H, TEXT, W, cover, draw_text, finish, font, text_length

SIDE = 80
WHO = (200, 200, 200)


def shade(img: Image.Image, start: float) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(H):
        bottom = max(0.0, (y - H * start) / (H * (0.95 - start)))
        top = max(0.0, (160 - y) / 160) * 0.35
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, int(255 * min(0.92, 0.92 * min(1.0, bottom) ** 0.85 + top))))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def warn_wide(lines: list[str], f, limit: int) -> None:
    for line in lines:
        if text_length(line, f) > limit:
            print(f"[warn] 화면 밖으로 나가는 줄이 있습니다. 줄여 쓰세요: {line}")


def info(img: Image.Image, body: str, handle: str) -> tuple[Image.Image, Image.Image]:
    img = shade(img, 0.38)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    body_font, body_h = font("Bold", 38), 64
    lines = body.split("\n")
    warn_wide(lines, body_font, W - SIDE * 2)
    y = H - 110 - body_h * len(lines)
    for i, line in enumerate(lines):
        draw_text(draw, (W / 2, y + i * body_h), line, body_font, TEXT, anchor="mm")
    if handle:
        draw.text((W - 56, 70), handle, font=font("Bold", 30), fill=TEXT, anchor="rm")
    return img, layer


def quote(img: Image.Image, text: str, who: str, handle: str) -> tuple[Image.Image, Image.Image]:
    img = shade(img, 0.42)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    quote_font, line_h = font("Bold", 46), 70
    lines = text.split("\n")
    if not lines[0].startswith(('"', "“")):
        lines[0], lines[-1] = "“" + lines[0], lines[-1] + "”"
    warn_wide(lines, quote_font, W - SIDE * 2)
    y = H - 150 - line_h * len(lines)
    for i, line in enumerate(lines):
        draw_text(draw, (W / 2, y + i * line_h), line, quote_font, TEXT, anchor="mm")
    draw.text((W / 2, H - 95), who, font=font("Bold", 32), fill=WHO, anchor="mm")
    if handle:
        draw.text((W - 56, 70), handle, font=font("Bold", 30), fill=TEXT, anchor="rm")
    return img, layer


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("style", choices=["info", "quote"])
    p.add_argument("--photo", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--body", help="info: 본문 줄")
    p.add_argument("--quote", help="quote: 인용문")
    p.add_argument("--who", help="quote: 말한 사람")
    p.add_argument("--handle", default="@pitchnote_")
    p.add_argument("--focus-y", type=float, default=0.15)
    p.add_argument("--focus-x", type=float, default=0.5)
    p.add_argument("--zoom", type=float, default=1.0)
    a = p.parse_args()
    if a.style == "info" and not a.body:
        p.error("info 에는 --body 가 필요합니다")
    if a.style == "quote" and not (a.quote and a.who):
        p.error("quote 에는 --quote 와 --who 가 필요합니다")
    base = cover(Image.open(a.photo).convert("RGB"), a.focus_y, a.focus_x, a.zoom)
    if a.style == "info":
        img, layer = info(base, a.body.replace("\\n", "\n"), a.handle)
    else:
        img, layer = quote(base, a.quote.replace("\\n", "\n"), a.who, a.handle)
    finish(img, layer, a.out)
    print(a.out)


if __name__ == "__main__":
    main()
