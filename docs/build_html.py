#!/usr/bin/env python3
"""docs/ 의 마크다운 문서를 단일 HTML로 묶는다.

    python3 docs/build_html.py
"""

from __future__ import annotations

import base64
import html
import html as html_mod
import os
import re

DOCUMENTS = [
    'card-news-spec.md',
]

OUTPUT_FILENAME = '피치노트-카드뉴스-스펙.html'
PAGE_TITLE = '피치노트 축구 카드뉴스 스펙'

_CODE_TOKEN = '\x00CODE{}\x00'
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
_FENCE_RE = re.compile(r'^```')
_HR_RE = re.compile(r'^(-{3,}|\*{3,})\s*$')
_TABLE_DIVIDER_RE = re.compile(r'^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$')
_UL_RE = re.compile(r'^(\s*)[-*]\s+(.*)$')
_OL_RE = re.compile(r'^(\s*)(\d+)\.\s+(.*)$')
_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)\)')
_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)\s]+)\)')
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_STRIKE_RE = re.compile(r'~~(.+?)~~')


_MIME_BY_EXT = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml'}


MISSING_IMAGES: list = []


def _embed_image(src: str):
    """이미지를 base64로 묻어 HTML 한 파일로 유지한다. 없으면 None을 준다."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = src if os.path.isabs(src) else os.path.join(base_dir, src)
    ext = os.path.splitext(path)[1].lower()
    if not os.path.exists(path) or ext not in _MIME_BY_EXT:
        MISSING_IMAGES.append(src)
        return None
    with open(path, 'rb') as handle:
        payload = base64.b64encode(handle.read()).decode('ascii')
    return 'data:{};base64,{}'.format(_MIME_BY_EXT[ext], payload)


def doc_anchor(filename: str) -> str:
    return 'doc-' + os.path.splitext(os.path.basename(filename))[0]


def render_inline(text: str) -> str:
    """인라인 서식을 HTML로 바꾼다. 코드 스팬은 먼저 빼 두고 마지막에 되돌린다."""
    codes: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        codes.append(match.group(1))
        return _CODE_TOKEN.format(len(codes) - 1)

    text = re.sub(r'`([^`]+)`', stash_code, text)
    text = html.escape(text, quote=False)
    text = _BOLD_RE.sub(r'<strong>\1</strong>', text)
    text = _STRIKE_RE.sub(r'<del>\1</del>', text)

    def to_image(match: re.Match[str]) -> str:
        alt, src = match.group(1), match.group(2)
        # 설명 끝에 {넓게}를 붙이면 본문 폭을 꽉 채운다.
        wide = alt.endswith('{넓게}')
        if wide:
            alt = alt[:-len('{넓게}')].rstrip()
        data = _embed_image(src)
        if data is None:
            return '<figure class="missing"><div class="ph">이미지 없음 · {}</div>' \
                   '<figcaption>{}</figcaption></figure>'.format(
                       html.escape(src, quote=False), alt)
        return '<figure{}><img src="{}" alt="{}"><figcaption>{}</figcaption></figure>'.format(
            ' class="wide"' if wide else '',
            html.escape(data, quote=True), html.escape(alt, quote=True), alt)

    text = _IMAGE_RE.sub(to_image, text)

    def to_link(match: re.Match[str]) -> str:
        label, href = match.group(1), match.group(2)
        if href.endswith('.md') or '.md#' in href:
            href = '#' + doc_anchor(href.split('#')[0])
        return '<a href="{}">{}</a>'.format(html.escape(href, quote=True), label)

    text = _LINK_RE.sub(to_link, text)

    for index, code in enumerate(codes):
        text = text.replace(
            _CODE_TOKEN.format(index),
            '<code>{}</code>'.format(html.escape(code, quote=False)),
        )
    return text


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split('|')]


def is_block_start(line: str) -> bool:
    text = line.strip()
    if not text:
        return True
    return bool(
        _HEADING_RE.match(line)
        or _FENCE_RE.match(text)
        or _HR_RE.match(text)
        or _UL_RE.match(line)
        or _OL_RE.match(line)
        or text.startswith('>')
        or text.startswith('|')
    )


def render_blocks(lines: list[str], heading_ids: dict[str, str] | None = None) -> str:
    """블록 단위로 마크다운을 렌더한다. 인용·목록은 내용을 재귀 처리한다."""
    out: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if _FENCE_RE.match(stripped):
            index += 1
            body: list[str] = []
            while index < len(lines) and not _FENCE_RE.match(lines[index].strip()):
                body.append(lines[index])
                index += 1
            index += 1
            out.append('<pre><code>{}</code></pre>'.format(
                html.escape('\n'.join(body), quote=False)))
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            raw = heading.group(2).strip()
            collapsible = raw.endswith(_COLLAPSE_MARK)
            if collapsible:
                raw = raw[:-len(_COLLAPSE_MARK)].rstrip()
            text = render_inline(raw)
            attr = ''
            if heading_ids is not None and raw in heading_ids:
                attr = ' id="{}"'.format(heading_ids[raw])
            if collapsible:
                attr += ' class="collapsible"'
            out.append('<h{level}{attr}>{text}</h{level}>'.format(
                level=min(level + 1, 6), attr=attr, text=text))
            index += 1
            continue

        if _HR_RE.match(stripped):
            out.append('<hr>')
            index += 1
            continue

        if stripped.startswith('>'):
            quoted: list[str] = []
            while index < len(lines) and lines[index].strip().startswith('>'):
                content = lines[index].strip()[1:]
                quoted.append(content[1:] if content.startswith(' ') else content)
                index += 1
            inner = render_blocks(quoted)
            kind = ' class="warn"' if '⚠️' in inner else ''
            out.append('<blockquote{}>{}</blockquote>'.format(kind, inner))
            continue

        if stripped.startswith('|') and index + 1 < len(lines) \
                and _TABLE_DIVIDER_RE.match(lines[index + 1].strip()):
            header = split_table_row(lines[index])
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                rows.append(split_table_row(lines[index]))
                index += 1
            head = ''.join('<th>{}</th>'.format(render_inline(cell)) for cell in header)
            body_html: list[str] = []
            for row in rows:
                cells = ''.join('<td>{}</td>'.format(render_inline(cell)) for cell in row)
                body_html.append('<tr>{}</tr>'.format(cells))
            out.append(
                '<div class="table-wrap"><table><thead><tr>{}</tr></thead>'
                '<tbody>{}</tbody></table></div>'.format(head, ''.join(body_html)))
            continue

        list_match = _UL_RE.match(line) or _OL_RE.match(line)
        if list_match:
            ordered = bool(_OL_RE.match(line))
            base_indent = len(list_match.group(1))
            items: list[list[str]] = []
            while index < len(lines):
                current = lines[index]
                match = _OL_RE.match(current) if ordered else _UL_RE.match(current)
                other = _UL_RE.match(current) if ordered else _OL_RE.match(current)
                if match and len(match.group(1)) == base_indent:
                    items.append([match.group(3) if ordered else match.group(2)])
                    index += 1
                    continue
                if not current.strip():
                    if index + 1 < len(lines) and lines[index + 1].startswith(' ' * (base_indent + 2)):
                        items[-1].append('')
                        index += 1
                        continue
                    break
                if items and current.startswith(' ' * (base_indent + 2)):
                    items[-1].append(current[base_indent + 2:])
                    index += 1
                    continue
                if other and len(other.group(1)) > base_indent:
                    items[-1].append(current[base_indent + 2:])
                    index += 1
                    continue
                break
            rendered: list[str] = []
            for item in items:
                if len(item) == 1:
                    rendered.append('<li>{}</li>'.format(render_inline(item[0])))
                else:
                    inner = render_blocks([item[0]] + item[1:])
                    inner = re.sub(r'^<p>(.*?)</p>', r'\1', inner, count=1, flags=re.S)
                    rendered.append('<li>{}</li>'.format(inner))
            tag = 'ol' if ordered else 'ul'
            out.append('<{tag}>{items}</{tag}>'.format(tag=tag, items=''.join(rendered)))
            continue

        paragraph = [stripped]
        index += 1
        while index < len(lines) and not is_block_start(lines[index]):
            paragraph.append(lines[index].strip())
            index += 1
        rendered_para = render_inline(' '.join(paragraph))
        if rendered_para.startswith('<figure>') and rendered_para.endswith('</figure>'):
            out.append(rendered_para)
        else:
            out.append('<p>{}</p>'.format(rendered_para))

    return '\n'.join(out)


def collect_headings(filename: str, lines: list[str]) -> tuple[str, list[tuple[str, str]], dict[str, str]]:
    """문서 제목과 h2 목록, 그리고 제목 → id 매핑을 만든다."""
    stem = doc_anchor(filename)
    title = os.path.splitext(filename)[0]
    sections: list[tuple[str, str]] = []
    heading_ids: dict[str, str] = {}
    counter = 0

    for line in lines:
        match = _HEADING_RE.match(line)
        if not match:
            continue
        text = match.group(2).strip()
        if text.endswith(_COLLAPSE_MARK):
            text = text[:-len(_COLLAPSE_MARK)].rstrip()
        if len(match.group(1)) == 1:
            # 목록과 이동 버튼에는 URL을 뺀 짧은 제목을 쓴다.
            title = re.sub(r'\s*\(`?/[^)]*\)', '', re.sub(r'[*`]', '', text))
            heading_ids[text] = stem
        elif len(match.group(1)) == 2:
            counter += 1
            anchor = '{}-{}'.format(stem, counter)
            heading_ids[text] = anchor
            sections.append((anchor, re.sub(r'[*`]', '', text)))

    return title, sections, heading_ids


STYLE = """
:root{
  --ground:#F5F6F9; --surface:#FFFFFF; --surface-2:#EDEFF5;
  --ink:#191E29; --ink-2:#4A5468; --ink-3:#79839A;
  --rule:#DCE0E9; --rule-2:#C4CAD8;
  --accent:#2F5488; --accent-soft:#E9EEF7;
  --warn:#93670F; --warn-bg:#F8F1E1;
  --code-bg:#EDEFF5; --code-ink:#2B3346;
  --sans:"IBM Plex Sans KR",-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.75;-webkit-font-smoothing:antialiased}
.layout{display:flex;align-items:flex-start;max-width:1360px;margin:0 auto;gap:32px;padding:0 24px}
nav.toc{position:sticky;top:0;flex:0 0 268px;max-height:100vh;overflow-y:auto;
  padding:32px 0 48px;font-size:13px}
nav.toc h2{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);
  margin:0 0 12px;font-weight:600}
nav.toc ol{list-style:none;margin:0 0 18px;padding:0}
nav.toc .doc>a{display:block;padding:5px 10px;border-radius:5px;color:var(--ink);
  font-weight:600;text-decoration:none;line-height:1.45}
nav.toc .doc>a:hover{background:var(--accent-soft);color:var(--accent)}
nav.toc .doc.is-active>a{background:var(--accent-soft);color:var(--accent)}
nav.pager{display:none;justify-content:space-between;gap:12px;margin-top:8px}
nav.pager a{flex:0 1 auto;max-width:48%;padding:11px 16px;background:var(--surface);
  border:1px solid var(--rule);border-radius:8px;text-decoration:none;font-size:13.5px;
  font-weight:500;color:var(--ink-2)}
nav.pager a:hover{border-color:var(--accent);color:var(--accent)}
nav.pager a.next{margin-left:auto;text-align:right}
body.paged nav.pager.is-current{display:flex}
nav.toc .sections{margin:2px 0 14px;padding:0 0 0 10px;border-left:1px solid var(--rule)}
body.paged nav.toc .sections{display:none}
body.paged nav.toc .doc.is-active .sections{display:block}
body.paged article.page{display:none}
body.paged article.page.is-current{display:block}
nav.toc .sections a{display:block;padding:3px 8px;color:var(--ink-3);text-decoration:none;
  border-radius:4px;line-height:1.45}
nav.toc .sections a:hover{background:var(--surface-2);color:var(--accent)}
main{flex:1 1 auto;min-width:0;max-width:860px;padding:32px 0 96px}
header.masthead{background:var(--surface);border:1px solid var(--rule);border-radius:10px;
  padding:28px 32px;margin-bottom:28px}
header.masthead h1{margin:0 0 6px;font-size:24px;letter-spacing:-.01em}
header.masthead p{margin:0;color:var(--ink-3);font-size:13.5px}
article{background:var(--surface);border:1px solid var(--rule);border-radius:10px;
  padding:8px 40px 40px;margin-bottom:24px}
article h2{font-size:22px;margin:36px 0 4px;padding-top:24px;border-top:1px solid var(--rule);
  letter-spacing:-.01em;scroll-margin-top:16px}
article>h2:first-child{border-top:0;margin-top:20px;padding-top:0}
article h2.doc-title{font-size:26px;margin:24px 0 2px;border-top:0;padding-top:0}
article h2.doc-title+blockquote{background:none;border-left:3px solid var(--rule-2);color:var(--ink-2);border-radius:0;padding:2px 0 2px 16px;margin:10px 0 18px}
article h3{font-size:16.5px;margin:30px 0 8px;color:var(--ink);scroll-margin-top:16px}
article h4{font-size:14.5px;margin:22px 0 6px;color:var(--ink-2)}
article p{margin:12px 0;line-height:1.8}
article ul,article ol{margin:10px 0;padding-left:22px}
article li{margin:4px 0}
article li>ul,article li>ol{margin:4px 0}
a{color:var(--accent)}
hr{border:0;border-top:1px solid var(--rule);margin:26px 0}
code{font-family:var(--mono);font-size:.88em;background:var(--code-bg);color:var(--code-ink);
  padding:1px 5px;border-radius:4px}
pre{background:var(--code-bg);border:1px solid var(--rule);border-radius:8px;
  padding:14px 16px;overflow-x:auto;margin:14px 0}
pre code{background:none;padding:0;font-size:12.5px;line-height:1.6;color:var(--code-ink)}
blockquote{margin:16px 0;padding:12px 18px;background:var(--accent-soft);
  border-left:3px solid var(--accent);border-radius:0 6px 6px 0}
blockquote p{margin:6px 0}
blockquote p:first-child{margin-top:0}
blockquote p:last-child{margin-bottom:0}
blockquote ul,blockquote ol{margin:6px 0}
blockquote pre{background:var(--surface);margin:10px 0}
.table-wrap{overflow-x:auto;margin:16px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{border:1px solid var(--rule);padding:7px 11px;text-align:left;vertical-align:top}
th{background:var(--surface-2);font-weight:600;white-space:nowrap}
tbody tr:nth-child(even){background:#FAFBFD}
details.chap{margin:0}
details.chap>summary{list-style:none;cursor:pointer}
details.chap>summary::-webkit-details-marker{display:none}
details.chap>summary h3{position:relative;padding-right:28px}
details.chap>summary h3::after{content:"\u2212";position:absolute;right:4px;top:50%;
  transform:translateY(-50%);color:var(--ink-3);font-size:18px;font-weight:400}
details.chap:not([open])>summary h3::after{content:"+"}
details.chap>summary:hover h3{color:var(--accent)}
details.sub{margin:16px 0;border:1px solid var(--rule);border-radius:8px;
  background:#FCFCFE;overflow:hidden}
details.sub>summary{list-style:none;cursor:pointer;padding:10px 14px;background:var(--surface-2)}
details.sub>summary::-webkit-details-marker{display:none}
details.sub>summary h4{margin:0;font-size:14.5px;position:relative;padding-right:24px}
details.sub>summary h4::after{content:"\u2212";position:absolute;right:2px;top:50%;
  transform:translateY(-50%);color:var(--ink-3);font-weight:400}
details.sub:not([open])>summary h4::after{content:"+"}
details.sub>summary:hover h4{color:var(--accent)}
details.sub>*:not(summary){padding-left:14px;padding-right:14px}
details.sub>ol,details.sub>ul{padding-left:38px}
details.sub>.table-wrap{padding-left:14px;padding-right:14px}
details.sub>*:last-child{padding-bottom:4px}
blockquote.warn{background:var(--warn-bg);border-left-color:var(--warn)}
figure{margin:18px 0;padding:0}
figure img{display:block;max-width:100%;max-height:340px;width:auto;height:auto;margin:0 auto;
  border:1px solid var(--rule);border-radius:8px;background:var(--surface-2)}
figure.wide img{max-height:none;width:100%}
figcaption{margin-top:7px;font-size:12.5px;color:var(--ink-3);text-align:center}
figcaption:empty{display:none}
figure.missing .ph{display:flex;align-items:center;justify-content:center;min-height:120px;
  border:1px dashed var(--rule-2);border-radius:8px;background:var(--surface-2);
  color:var(--ink-3);font-size:13px}
.term{border-bottom:1px dashed var(--rule-2);cursor:help;position:relative;outline:none}
.term:hover,.term:focus{border-bottom-color:var(--accent);color:var(--accent)}
.term .tip{display:none;position:absolute;left:0;top:calc(100% + 7px);z-index:20;width:max-content;
  max-width:320px;background:var(--ink);color:#fff;font-size:12.5px;font-weight:400;line-height:1.6;
  padding:9px 12px;border-radius:7px;box-shadow:0 4px 14px rgba(25,30,41,.22);white-space:normal}
.term:hover .tip,.term:focus .tip{display:block}
footer.colophon{color:var(--ink-3);font-size:12.5px;text-align:center;padding:8px 0 40px}
@media (max-width:1040px){
  .layout{flex-direction:column;gap:0;padding:0 16px}
  nav.toc{position:static;flex:none;width:100%;max-height:none;padding:24px 0 0}
  article{padding:8px 20px 28px}
  main{padding-top:20px}
}
"""


SCRIPT = """
(function () {
    var pages = [].slice.call(document.querySelectorAll('article.page'));
    var items = [].slice.call(document.querySelectorAll('nav.toc li.doc'));
    var pagers = [].slice.call(document.querySelectorAll('nav.pager'));
    if (!pages.length) { return; }
    document.body.classList.add('paged');

    function keyOf(el) { return el.getAttribute('data-page'); }

    function pageIdFor(hash) {
        var fallback = keyOf(pages[0]);
        if (!hash) { return fallback; }
        var el = document.getElementById(hash);
        if (!el) { return fallback; }
        var owner = el.closest('article.page');
        return owner ? keyOf(owner) : fallback;
    }

    function route(animate) {
        var hash = (location.hash || '').replace('#', '');
        var pageId = pageIdFor(hash);
        pages.forEach(function (page) {
            page.classList.toggle('is-current', keyOf(page) === pageId);
        });
        items.forEach(function (item) {
            item.classList.toggle('is-active', item.getAttribute('data-page') === pageId);
        });
        pagers.forEach(function (pager) {
            pager.classList.toggle('is-current', pager.getAttribute('data-page') === pageId);
        });
        var target = hash ? document.getElementById(hash) : null;
        var isPageTop = target && target.classList.contains('doc-title');
        if (target) {
            var parent = target.parentElement;
            while (parent) {
                if (parent.tagName === 'DETAILS') { parent.open = true; }
                parent = parent.parentElement;
            }
        }
        if (target && !isPageTop) {
            target.scrollIntoView({ block: 'start' });
        } else if (animate || isPageTop) {
            window.scrollTo(0, 0);
        }
    }

    window.addEventListener('hashchange', function () { route(true); });
    route(false);
})();
"""


# 처음 나오는 자리에만 설명을 붙인다. 코드 조각과 제목 안에서는 붙이지 않는다.
GLOSSARY = {
    'RSS': '언론사가 새 기사 목록을 정해진 형식으로 공개하는 주소. 프로그램이 읽어 최신 기사를 모을 수 있습니다.',
    '위키미디어 공용': '위키백과의 사진·미디어 저장소. 대부분 자유 라이선스로 공개되어 조건을 지키면 누구나 쓸 수 있습니다.',
    'CC BY-SA': '작가를 밝히고, 이 사진으로 만든 결과물도 같은 라이선스로 공개하면 자유롭게 쓸 수 있는 라이선스.',
    '스킬': 'Claude가 특정 작업을 할 때 읽고 따르는 작업 설명서와 도구 묶음.',
    '캐러셀': '인스타그램 게시물 하나에 여러 장의 이미지를 넣어 옆으로 넘겨 보게 하는 형식.',
}

_TAG_SPLIT_RE = re.compile(r'(<[^>]+>)')
_SKIP_INSIDE = ('code', 'summary', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6')


def apply_glossary(html: str, used: set) -> str:
    """본문 글자에만 용어 설명을 단다. 태그 속성과 코드, 제목은 건드리지 않는다."""
    parts = _TAG_SPLIT_RE.split(html)
    depth = {name: 0 for name in _SKIP_INSIDE}
    out = []
    for part in parts:
        if part.startswith('<'):
            name = re.match(r'</?([a-zA-Z0-9]+)', part)
            if name:
                tag = name.group(1).lower()
                if tag in depth:
                    depth[tag] += -1 if part.startswith('</') else 1
                    if depth[tag] < 0:
                        depth[tag] = 0
            out.append(part)
            continue
        if any(depth[name] for name in _SKIP_INSIDE):
            out.append(part)
            continue
        for term, desc in GLOSSARY.items():
            if term in used or term not in part:
                continue
            used.add(term)
            part = part.replace(
                term,
                '<span class="term" tabindex="0">{}<span class="tip">{}</span></span>'.format(
                    term, html_mod.escape(desc, quote=False)),
                1)
        out.append(part)
    return ''.join(out)


# 접기는 문서에서 제목 끝에 {접기} 를 붙인 절에만 적용한다.
_COLLAPSE_MARK = '{접기}'
_MARKED_RE = re.compile(r'<h([34])([^>]*?)\s*class="collapsible"([^>]*)>(.*?)</h\1>', re.S)


def wrap_marked_details(body: str) -> str:
    """표시한 절만 접은 상태로 감싼다. 같은 단계 이상의 다음 제목까지가 범위다."""
    while True:
        match = _MARKED_RE.search(body)
        if not match:
            return body
        level = int(match.group(1))
        heading = '<h{level}{a}{b}>{text}</h{level}>'.format(
            level=level, a=match.group(2), b=match.group(3), text=match.group(4))
        rest = body[match.end():]
        stop = len(rest)
        for other in re.finditer(r'<h([1-4])[^>]*>', rest):
            if int(other.group(1)) <= level:
                stop = other.start()
                break
        wrapped = '<details class="sub"><summary>{}</summary>{}</details>'.format(
            heading, rest[:stop])
        body = body[:match.start()] + wrapped + rest[stop:]


def build() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    titles: list[str] = []
    toc_parts: list[str] = []
    body_parts: list[str] = []

    for filename in DOCUMENTS:
        path = os.path.join(base_dir, filename)
        with open(path, encoding='utf-8') as handle:
            lines = handle.read().split('\n')

        title, sections, heading_ids = collect_headings(filename, lines)
        titles.append(title)
        rendered = render_blocks(lines, heading_ids)
        rendered = rendered.replace('<h2 id="{}">'.format(doc_anchor(filename)),
                                    '<h2 id="{}" class="doc-title">'.format(doc_anchor(filename)))
        rendered = apply_glossary(rendered, set())
        rendered = wrap_marked_details(rendered)
        body_parts.append(rendered)

        links = ''.join('<a href="#{}">{}</a>'.format(anchor, html.escape(text, quote=False))
                        for anchor, text in sections)
        toc_parts.append(
            '<li class="doc" data-page="{anchor}"><a href="#{anchor}">{title}</a>'
            '<div class="sections">{links}</div></li>'.format(
                anchor=doc_anchor(filename),
                title=html.escape(title, quote=False),
                links=links))

    # 페이지 아래에 이전·다음 문서로 가는 버튼을 붙인다.
    articles: list[str] = []
    for index, filename in enumerate(DOCUMENTS):
        anchor = doc_anchor(filename)
        pager: list[str] = []
        if index > 0:
            pager.append('<a class="prev" href="#{}">← {}</a>'.format(
                doc_anchor(DOCUMENTS[index - 1]), html.escape(titles[index - 1], quote=False)))
        if index < len(DOCUMENTS) - 1:
            pager.append('<a class="next" href="#{}">{} →</a>'.format(
                doc_anchor(DOCUMENTS[index + 1]), html.escape(titles[index + 1], quote=False)))
        pager_html = ('<nav class="pager" data-page="{}">{}</nav>'.format(anchor, ''.join(pager))
                      if pager else '')
        articles.append(
            '<article class="page" id="page-{anchor}" data-page="{anchor}">{body}</article>'
            '{pager}'.format(anchor=anchor, body=body_parts[index], pager=pager_html))
    body_parts = articles

    return (
        '<!DOCTYPE html>\n<html lang="ko">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>{title}</title>\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+KR:wght@300;400;500;600;700'
        '&display=swap">\n'
        '<style>{style}</style>\n</head>\n<body>\n'
        '<div class="layout">\n'
        '<nav class="toc"><h2>문서</h2><ol>{toc}</ol></nav>\n'
        '<main>\n'
        '<header class="masthead"><h1>{title}</h1><p>기준 시점 2026-10-04</p></header>\n'
        '{body}\n'
        '<footer class="colophon">docs/card-news-spec.md 에서 생성</footer>\n'
        '</main>\n</div>\n<script>{script}</script>\n</body>\n</html>\n'
    ).format(title=html.escape(PAGE_TITLE, quote=False), style=STYLE,
             toc=''.join(toc_parts), body='\n'.join(body_parts), script=SCRIPT)


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, OUTPUT_FILENAME)
    with open(output_path, 'w', encoding='utf-8') as handle:
        handle.write(build())
    print('생성 완료: {} ({:,} bytes)'.format(output_path, os.path.getsize(output_path)))
    if MISSING_IMAGES:
        print('이미지 파일 없음 {}건:'.format(len(MISSING_IMAGES)))
        for src in MISSING_IMAGES:
            print('  -', src)


if __name__ == '__main__':
    main()
