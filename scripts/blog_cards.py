# -*- coding: utf-8 -*-
# Copyright 2026 Baek Ga-hui (neisii) - https://github.com/neisii/neisii
# SPDX-License-Identifier: Apache-2.0
"""blog_cards.py — 블로그의 projects.json을 읽어 GitHub 프로필 README에 넣을 프로젝트 카드 SVG를 만든다.

GitHub README는 iframe·script를 지우므로 블로그 화면을 그대로 넣을 수 없다. 대신 카드 이미지를 만들어
프로필 저장소에 커밋하고, README가 <a><img></a>로 건다. 카드 안의 화면 이미지는 외부 주소로 걸면 막힐 수
있어 파일 안에 직접 넣는다(data URI).

사용법:
  python3 scripts/blog_cards.py --slugs harness-naroo,marknaroo --out profile/blog --readme README.md
  --json      블로그 JSON 경로 또는 URL(기본 https://neisii.github.io/projects.json)
  --readme    README의 <!-- BLOG-CARDS:START --> 와 <!-- BLOG-CARDS:END --> 사이를 카드와 최근 글로 다시 쓴다
  --posts     최근 글 몇 편을 넣을지(기본 3)
  --local-root 이미지 URL의 사이트 주소 부분을 이 폴더로 바꿔 읽는다(로컬 빌드 시험용)

카드 SVG와 README는 내용이 같으면 다시 쓰지 않으므로, 바뀐 것이 없으면 워크플로가 커밋하지 않는다.
"""
import argparse
import base64
import html
import json
import os
import urllib.request

W = 420
PAD = 20
FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Apple SD Gothic Neo', "
        "'Noto Sans KR', 'Malgun Gothic', sans-serif")


def read_bytes(src, site=None, local_root=None):
    if local_root and site and src.startswith(site):
        with open(os.path.join(local_root, src[len(site):]), 'rb') as f:
            return f.read()
    if src.startswith('http'):
        with urllib.request.urlopen(src, timeout=30) as r:
            return r.read()
    with open(src, 'rb') as f:
        return f.read()


def text_width(s, size):
    """글자 폭 어림값: 한글·한자 등 넓은 글자는 글자 크기만큼, 나머지는 0.56배."""
    return sum(size if ord(ch) >= 0x1100 else size * 0.56 for ch in s)


def wrap(s, size, max_w, max_lines):
    lines, cur = [], ''
    for word in s.split(' '):
        cand = (cur + ' ' + word).strip()
        if text_width(cand, size) <= max_w:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = word
        while text_width(cur, size) > max_w:          # 한 낱말이 너무 길면 글자 단위로 자른다
            i = len(cur)
            while i > 1 and text_width(cur[:i], size) > max_w:
                i -= 1
            lines.append(cur[:i])
            cur = cur[i:]
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        last = lines[max_lines - 1]
        while last and text_width(last + '…', size) > max_w:
            last = last[:-1]
        lines = lines[:max_lines - 1] + [last + '…']
    return lines


TOP_H = round(W * 560 / 1400)   # 위쪽 그림 칸 높이: 1400×560 배너 비율. 이미지가 없어도 같은 높이로 맞춘다


def card_svg(p, image_bytes=None, height=None):
    """height를 주면 카드 높이를 그 값으로 맞춘다(나란히 놓을 카드끼리 높이를 같게)."""
    esc = lambda s: html.escape(s or '', quote=True)
    parts = []
    top_h = TOP_H
    if image_bytes:
        data = base64.b64encode(image_bytes).decode('ascii')
        top = (f'<image href="data:image/png;base64,{data}" x="0" y="0" width="{W}" height="{top_h}" '
               f'preserveAspectRatio="xMidYMid slice"/>')
    else:
        mid = top_h // 2
        top = (f'<rect x="0" y="0" width="{W}" height="{top_h}" fill="{esc(p.get("color") or "#eceae4")}"/>'
               f'<text x="{PAD + 6}" y="{mid + 18}" font-size="52" fill="#2b2b2b">{esc(p.get("mark") or "")}</text>'
               f'<text x="{W - PAD}" y="{mid + 6}" text-anchor="end" font-size="15" letter-spacing="2.5" '
               f'font-weight="600" fill="#2b2b2b">{esc(p["name"])}</text>')
    y = top_h + 26
    meta = ' · '.join(x for x in [p.get('period'), p.get('type')] if x)
    parts.append(f'<text x="{PAD}" y="{y}" font-size="11" fill="#6b7280">{esc(meta)}</text>')
    y += 24
    for line in wrap(p['title'], 16, W - 2 * PAD, 2):
        parts.append(f'<text x="{PAD}" y="{y}" font-size="16" font-weight="700" fill="#111827">{esc(line)}</text>')
        y += 22
    y += 2
    for line in wrap(p.get('summary', ''), 13, W - 2 * PAD, 3):
        parts.append(f'<text x="{PAD}" y="{y}" font-size="13" fill="#4b5563">{esc(line)}</text>')
        y += 19
    h = max(y + 10, height or 0)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
            f'role="img" aria-label="{esc(p["name"] + " — " + p["title"])}">'
            f'<title>{esc(p["name"] + " — " + p["title"])}</title>'
            f'<defs><clipPath id="r"><rect width="{W}" height="{h}" rx="12"/></clipPath></defs>'
            f'<g clip-path="url(#r)" font-family="{FONT}"><rect width="{W}" height="{h}" fill="#ffffff"/>'
            f'{top}{"".join(parts)}</g>'
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="12" fill="none" stroke="#d9dce1"/></svg>')


START, END = '<!-- BLOG-CARDS:START -->', '<!-- BLOG-CARDS:END -->'


def write_if_changed(path, text):
    old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
    if old != text:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    return False


def readme_block(cards, posts, out_dir, readme_path):
    esc = lambda s: html.escape(s or '', quote=True)
    rel = os.path.relpath(out_dir, os.path.dirname(os.path.abspath(readme_path)) or '.')
    lines = [START, '<p>']
    for slug, p, _ in cards:
        lines.append(f'<a href="{esc(p["url"])}"><img src="./{rel}/{slug}.svg" width="48%" '
                     f'alt="{esc(p["name"] + " — " + p["title"])}"></a>')
    lines.append('</p>')
    if posts:
        lines.append('')
        lines.append('최근 글')
        lines.append('')
        for post in posts:
            lines.append(f'- [{post["title"]}]({post["url"]}) <sub>{post["date"]}</sub>')
    lines.append(END)
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default='https://neisii.github.io/projects.json')
    ap.add_argument('--out', required=True)
    ap.add_argument('--slugs', required=True, help='쉼표로 나눈 프로젝트 slug, 이 순서로 만든다')
    ap.add_argument('--readme')
    ap.add_argument('--posts', type=int, default=3)
    ap.add_argument('--local-root')
    a = ap.parse_args()
    raw = read_bytes(a.json)
    data = json.loads(raw.decode('utf-8'))
    site = data['site']
    by_slug = {p['slug']: p for p in data['projects']}
    os.makedirs(a.out, exist_ok=True)
    cards = []
    for slug in a.slugs.split(','):
        p = by_slug[slug]
        img = read_bytes(p['image'], site, a.local_root) if p.get('image') else None
        cards.append((slug, p, img))
    # 한 번 그려 보고 가장 높은 카드에 높이를 맞춘다
    import re
    tallest = max(int(re.search(r'height="(\d+)"', card_svg(p, img)).group(1)) for _, p, img in cards)
    for slug, p, img in cards:
        path = os.path.join(a.out, f'{slug}.svg')
        changed = write_if_changed(path, card_svg(p, img, tallest))
        print(path, '바뀜' if changed else '그대로')
    if a.readme:
        text = open(a.readme, encoding='utf-8').read()
        if START not in text or END not in text:
            raise SystemExit(f'{a.readme}에 {START} / {END} 표시가 없다')
        head, rest = text.split(START, 1)
        _, tail = rest.split(END, 1)
        block = readme_block(cards, data.get('posts', [])[:a.posts], a.out, a.readme)
        changed = write_if_changed(a.readme, head + block + tail)
        print(a.readme, '바뀜' if changed else '그대로')


if __name__ == '__main__':
    main()
