#!/usr/bin/env python3
"""배경 사진 위에 카테고리, 계정 아이디, 두 줄 제목을 얹은 1080x1350 이미지를 만든다.

    python3 render_card.py --photo kane.jpg --tag 네이션스리그 \
        --headline "잉글랜드, 크로아티아에\\n[7-0] 대승" --out 1_잉글랜드.jpg \
        [--handle @pitchnote_] [--focus-y 0.12] [--focus-x 0.5] [--zoom 1.0]

제목의 \\n 은 줄바꿈, [ ] 로 감싼 부분은 강조색이다.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
W, H = 1080, 1350
MARGIN = 64
ACCENT = (61, 123, 255)
TEXT = (255, 255, 255)
HANDLE = (235, 235, 235)
MAX_HEADLINE = 104
MIN_HEADLINE = 72


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Pretendard-{weight}.otf"), size)


def cover(photo: Image.Image, focus_y: float, focus_x: float, zoom: float) -> Image.Image:
    scale = max(W / photo.width, H / photo.height) * zoom
    resized = photo.resize((round(photo.width * scale), round(photo.height * scale)), Image.LANCZOS)
    left = round((resized.width - W) * focus_x)
    top = round((resized.height - H) * focus_y)
    return resized.crop((left, top, left + W, top + H))


def shade(img: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(H):
        bottom = max(0.0, (y - H * 0.36) / (H * 0.5))
        top = max(0.0, (220 - y) / 220)
        alpha = int(255 * min(0.94, 0.94 * min(1.0, bottom) ** 0.9 + 0.45 * top))
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def segments(line: str) -> list[tuple[str, bool]]:
    return [(part, i % 2 == 1) for i, part in enumerate(re.split(r"\[|\]", line)) if part]


def plain(line: str) -> str:
    return line.replace("[", "").replace("]", "")


def render(photo: Path, tag: str, headline: str, out: Path, handle: str,
           focus_y: float, focus_x: float, zoom: float) -> None:
    img = shade(cover(Image.open(photo).convert("RGB"), focus_y, focus_x, zoom))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    draw.ellipse([MARGIN, 66, MARGIN + 12, 78], fill=ACCENT)
    draw.text((MARGIN + 26, 72), tag, font=font("Bold", 34), fill=TEXT, anchor="lm")

    lines = headline.split("\n")
    size = MAX_HEADLINE
    while size > MIN_HEADLINE and max(font("Black", size).getlength(plain(l)) for l in lines) > W - MARGIN * 2:
        size -= 2
    head = font("Black", size)
    line_h = int(size * 1.22)

    y = H - 96 - line_h * len(lines)
    if handle:
        draw.text((MARGIN, y - 24), handle, font=font("Bold", 32), fill=HANDLE, anchor="ls")
    for line in lines:
        x = MARGIN
        for text, accent in segments(line):
            draw.text((x, y), text, font=head, fill=ACCENT if accent else TEXT)
            x += head.getlength(text)
        y += line_h

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(layer.getchannel("A").point(lambda a: a * 0.6).filter(ImageFilter.GaussianBlur(10)))
    img = Image.alpha_composite(Image.alpha_composite(img, shadow), layer)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, "JPEG", quality=93)
    if size == MIN_HEADLINE and max(head.getlength(plain(l)) for l in lines) > W - MARGIN * 2:
        print("[warn] 제목이 너무 길어 화면 밖으로 나갑니다. 한 줄을 줄이세요.")
    print(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--photo", type=Path, required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--headline", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--handle", default="@pitchnote_")
    p.add_argument("--focus-y", type=float, default=0.15)
    p.add_argument("--focus-x", type=float, default=0.5)
    p.add_argument("--zoom", type=float, default=1.0)
    a = p.parse_args()
    render(a.photo, a.tag, a.headline.replace("\\n", "\n"), a.out, a.handle, a.focus_y, a.focus_x, a.zoom)


if __name__ == "__main__":
    main()
