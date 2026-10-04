from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config

W, H = 1080, 1350
MARGIN = 80
BG_TOP = (13, 38, 28)
BG_BOTTOM = (5, 16, 11)
ACCENT = (200, 255, 61)
TEXT = (255, 255, 255)
MUTED = (157, 181, 168)
LINE = (255, 255, 255, 18)


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(config.FONTS_DIR / f"Pretendard-{weight}.otf"), size)


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            candidate = f"{line} {word}".strip()
            if font.getlength(candidate) <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
            line = ""
            for ch in word:
                if font.getlength(line + ch) > width:
                    lines.append(line)
                    line = ""
                line += ch
        lines.append(line)
    return lines


def _fit(text: str, weight: str, size: int, min_size: int, width: int, max_height: int, spacing: float):
    while True:
        font = _font(weight, size)
        lines = _wrap(text, font, width)
        line_h = int(size * spacing)
        if len(lines) * line_h <= max_height or size <= min_size:
            return font, lines, line_h
        size -= 2


def _background() -> Image.Image:
    img = Image.new("RGB", (W, H), BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        color = tuple(int(BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=color)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pitch = ImageDraw.Draw(overlay)
    pitch.line([(0, H // 2), (W, H // 2)], fill=LINE, width=4)
    pitch.ellipse([W // 2 - 260, H // 2 - 260, W // 2 + 260, H // 2 + 260], outline=LINE, width=4)
    pitch.rectangle([W // 2 - 300, -4, W // 2 + 300, 220], outline=LINE, width=4)
    pitch.rectangle([W // 2 - 300, H - 220, W // 2 + 300, H + 4], outline=LINE, width=4)
    img.paste(overlay, (0, 0), overlay)
    return img


def _header(draw: ImageDraw.ImageDraw, right: str) -> None:
    font = _font("Medium", 32)
    draw.text((MARGIN, 72), config.BRAND_NAME, font=font, fill=MUTED)
    draw.text((W - MARGIN, 72), right, font=font, fill=MUTED, anchor="ra")


def _footer(draw: ImageDraw.ImageDraw, source: str, hint: str) -> None:
    font = _font("Medium", 28)
    draw.text((MARGIN, H - 72), f"출처 {source}", font=font, fill=MUTED, anchor="ls")
    if hint:
        draw.text((W - MARGIN, H - 72), hint, font=font, fill=ACCENT, anchor="rs")


def render_cover(cards: dict, source: str, date: datetime) -> Image.Image:
    img = _background()
    draw = ImageDraw.Draw(img)
    _header(draw, date.strftime("%Y.%m.%d"))
    width = W - MARGIN * 2

    sub_font, sub_lines, sub_h = _fit(cards["subhead"], "Medium", 44, 34, width, 180, 1.4)
    head_font, head_lines, head_h = _fit(cards["headline"], "Black", 104, 72, width, 520, 1.22)

    y = H - 200 - len(sub_lines) * sub_h
    for line in sub_lines:
        draw.text((MARGIN, y), line, font=sub_font, fill=MUTED)
        y += sub_h

    y = H - 200 - len(sub_lines) * sub_h - 48 - len(head_lines) * head_h
    head_top = y
    for line in head_lines:
        draw.text((MARGIN, y), line, font=head_font, fill=TEXT)
        y += head_h

    tag_font = _font("Bold", 34)
    tag_w = int(tag_font.getlength(cards["tag"]))
    tag_top = head_top - 100
    draw.rounded_rectangle([MARGIN, tag_top, MARGIN + tag_w + 48, tag_top + 62], radius=31, fill=ACCENT)
    draw.text((MARGIN + 24, tag_top + 31), cards["tag"], font=tag_font, fill=BG_BOTTOM, anchor="lm")

    _footer(draw, source, "넘겨보기 →")
    return img


def render_slide(slide: dict, number: int, total: int, source: str) -> Image.Image:
    img = _background()
    draw = ImageDraw.Draw(img)
    _header(draw, f"{number} / {total}")
    width = W - MARGIN * 2

    y = 260
    draw.text((MARGIN, y), f"{number - 1:02d}", font=_font("Black", 120), fill=ACCENT)
    y += 180
    draw.rectangle([MARGIN, y, MARGIN + 72, y + 8], fill=ACCENT)
    y += 56

    title_font, title_lines, title_h = _fit(slide["title"], "Bold", 68, 52, width, 260, 1.3)
    for line in title_lines:
        draw.text((MARGIN, y), line, font=title_font, fill=TEXT)
        y += title_h
    y += 40

    body_font, body_lines, body_h = _fit(slide["body"], "Medium", 46, 34, width, H - 200 - y, 1.6)
    for line in body_lines:
        draw.text((MARGIN, y), line, font=body_font, fill=(225, 235, 229))
        y += body_h

    _footer(draw, source, "" if number == total else "→")
    return img


def render_all(cards: dict, source: str, out_dir: Path, date: datetime) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(cards["slides"]) + 1
    images = [render_cover(cards, source, date)]
    images += [render_slide(s, i + 2, total, source) for i, s in enumerate(cards["slides"])]
    paths = []
    for i, img in enumerate(images, start=1):
        path = out_dir / f"{i:02d}.jpg"
        img.save(path, "JPEG", quality=92)
        paths.append(path)
    return paths
