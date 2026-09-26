from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("public")

# Phrases that are clearly implementation / monetization notes for the site owner,
# not useful copy for normal visitors. The script checks each public HTML document
# one by one on every deploy so generated pages are cleaned too.
REPLACEMENTS = {
    "月100万円を狙うためのサイト導線": "迷わず選ぶための流れ",
    "検索流入を「情報を知りたい人」だけで終わらせず、比較・ランキング・セール・レビューへ内部リンクして、購入判断まで迷わない構造にしています。": "気になる作品やサービスを探し、条件を比べ、最後に公式ページで最新情報を確認しやすい順番に整理しています。",
    "<div class=\"revenue-step\"><b>集客</b>初心者・使い方</div>": "<div class=\"revenue-step\"><b>1. 探す</b>人気・女優・ジャンル</div>",
    "<div class=\"revenue-step\"><b>比較</b>月額・ランキング</div>": "<div class=\"revenue-step\"><b>2. 比べる</b>価格・レビュー・見放題</div>",
    "<div class=\"revenue-step\"><b>購入意図</b>セール・レビュー</div>": "<div class=\"revenue-step\"><b>3. 確認</b>セール・販売条件</div>",
    "<div class=\"revenue-step\"><b>成約</b>広告・商品導線</div>": "<div class=\"revenue-step\"><b>公式へ</b>最新条件を最終確認</div>",
    "いま買う理由がある人を集める更新型ページ。": "現在のセール・クーポン情報を確認できます。",
    "人気・新着・高評価から比較へつなげる入口。": "人気・新着・高評価から作品を探せます。",
    "購入前の疑問から収益ページへ自然につなぐ。": "購入前の疑問を順番に確認できます。",
    "HIGH INTENT": "おすすめ",
    "COMPARE": "比較",
    "TRUST": "レビュー",
    "DISCOVERY": "探す",
    "BEGINNER": "はじめての方へ",
}

# Exact owner-facing blocks already found on the live site.
OWNER_BLOCKS = [
    re.compile(
        r'<h2>初心者向けの導線</h2>\s*<p>情報系の記事から、比較・ランキング・セールなど購入意図の高いページへ自然につなげます。単発記事だけで終わらず、読者が次に確認するページを必ず用意する構造です。</p>',
        re.S,
    ),
    re.compile(
        r'<div class="affiliate-slot">\s*<strong>広告リンク表示枠</strong>\s*<p>DMM審査通過後にアフィリエイトID/APIを設定すると、この位置に公式商品・キャンペーン導線を表示する設計です。</p>\s*</div>',
        re.S,
    ),
]

# Conservative public-copy cleanup for strong internal terms that should never be
# shown as instructions about monetization/SEO on this consumer-facing site.
TEXT_REPLACEMENTS = {
    "購入意図の高いページ": "比較・ランキング・セールページ",
    "収益ページ": "関連ページ",
    "収益導線": "案内",
    "内部リンクして": "関連ページで",
    "単発記事だけで終わらず": "関連情報も確認できるようにし",
    "DMM審査通過後": "",
    "アフィリエイトID/API": "必要な設定",
    "広告リンク表示枠": "",
}

# Terms that indicate owner-only copy may still remain after cleanup.
# These are reported page-by-page in the Action log for QA.
AUDIT_TERMS = [
    "月100万円",
    "購入意図",
    "収益ページ",
    "収益導線",
    "内部リンクして",
    "単発記事だけで終わらず",
    "DMM審査通過後",
    "アフィリエイトID/API",
    "広告リンク表示枠",
    "<b>集客</b>",
    "<b>成約</b>",
]


def looks_like_html(text: str) -> bool:
    head = text[:600].lower()
    return "<html" in head or "<!doctype html" in head


def patch(path: Path) -> tuple[bool, list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False, []
    if not looks_like_html(text):
        return False, []

    before = text

    for pattern in OWNER_BLOCKS:
        text = pattern.sub("", text)

    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)

    for old, new in TEXT_REPLACEMENTS.items():
        text = text.replace(old, new)

    # Remove empty headings/paragraphs left by any placeholder cleanup.
    text = re.sub(r'<h[1-6][^>]*>\s*</h[1-6]>', '', text, flags=re.I)
    text = re.sub(r'<p[^>]*>\s*</p>', '', text, flags=re.I)

    if text != before:
        path.write_text(text, encoding="utf-8")

    remaining = [term for term in AUDIT_TERMS if term in text]
    return text != before, remaining


def main() -> None:
    checked = 0
    changed = 0
    remaining_pages: list[tuple[str, list[str]]] = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        # The repo contains both .html pages and extensionless HTML routes.
        if path.suffix.lower() not in {"", ".html"}:
            continue
        did_change, remaining = patch(path)
        # patch() returns false for non-HTML files, so count only files we can
        # cheaply identify as HTML here.
        try:
            sample = path.read_text(encoding="utf-8")[:600]
        except (UnicodeDecodeError, OSError):
            continue
        if not looks_like_html(sample):
            continue
        checked += 1
        if did_change:
            changed += 1
        if remaining:
            remaining_pages.append((path.relative_to(ROOT).as_posix(), remaining))

    print(f"Public-copy audit: checked={checked} changed={changed}")
    if remaining_pages:
        print("WARNING: owner-facing terms still found:")
        for rel, terms in remaining_pages[:100]:
            print(f"  {rel}: {', '.join(terms)}")
        raise SystemExit(1)
    print("Public-copy audit passed: no owner-only terms remain.")


if __name__ == "__main__":
    main()
