from __future__ import annotations

import html as html_lib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("public")

# Public pages must read as visitor-facing pages. These replacements remove or
# rewrite implementation, SEO and monetization notes that were useful during
# development but should never be shown to normal visitors.
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
    "当サイト運営サークル「桃色ラボ」のFANZA同人作品をまとめる専用ページを追加しました。公開後は商品APIから自動更新します。": "「桃色ラボ」のFANZA同人作品をまとめています。作品情報は公開状況に合わせて更新します。",
    "公開作品はFANZA Webサービスの商品APIから自動更新します。": "公開状況に合わせて作品情報を更新します。",
    "商品情報はFANZA Webサービスの商品APIから取得し、自動更新します。": "公開状況に合わせて作品情報を更新します。",
    "公開作品のAPI反映待ちです": "公開作品の反映待ちです",
    "桃色ラボの作品がFANZAで公開され、FANZA Webサービスの商品APIに反映されると、このページへ自動掲載します。": "桃色ラボの作品がFANZAで公開されると、このページにも順次掲載します。",
    "FANZA API / 人気作品データ": "FANZA人気作品データ",
    "FANZA Webサービスの商品APIで <b>人気順（rank）</b> の作品を上位から取得し、その作品に出演する女優を順番に集計した当サイト独自ランキングです。": "FANZAで公開されている人気作品の順位をもとに、出演女優を順番に集計した当サイト独自ランキングです。",
    "プロフィール画像・女優情報はFANZA Webサービスから取得しています。API更新:": "プロフィール画像・女優情報は公開情報をもとに掲載しています。最終更新:",
    "商品APIから自動更新します。": "作品情報は公開状況に合わせて更新します。",
    "APIから自動更新します。": "最新情報に合わせて更新します。",
    "APIで自動更新します。": "最新情報に合わせて更新します。",
    "API更新:": "最終更新:",
    "HIGH INTENT": "おすすめ",
    "COMPARE": "比較",
    "TRUST": "レビュー",
    "DISCOVERY": "探す",
    "BEGINNER": "はじめての方へ",
}

# Exact owner-facing blocks found in public output. Remove the whole block when
# simply rewriting it would still expose implementation instructions.
OWNER_BLOCKS = [
    re.compile(
        r'<h2>初心者向けの導線</h2>\s*<p>情報系の記事から、比較・ランキング・セールなど購入意図の高いページへ自然につなげます。単発記事だけで終わらず、読者が次に確認するページを必ず用意する構造です。</p>',
        re.S,
    ),
    re.compile(
        r'<div class="affiliate-slot">\s*<strong>広告リンク表示枠</strong>\s*<p>DMM審査通過後にアフィリエイトID/APIを設定すると、この位置に公式商品・キャンペーン導線を表示する設計です。</p>\s*</div>',
        re.S,
    ),
    re.compile(
        r'<(?:section|div)[^>]*>\s*<(?:h2|h3)[^>]*>(?:運営者向け|管理者向け|サイト運営者向け)[^<]*</(?:h2|h3)>.*?</(?:section|div)>',
        re.S | re.I,
    ),
]

TEXT_REPLACEMENTS = {
    "購入意図の高いページ": "比較・ランキング・セールページ",
    "収益ページ": "関連ページ",
    "収益導線": "案内",
    "広告導線": "公式ページへの案内",
    "商品導線": "作品案内",
    "内部リンクして": "関連ページで",
    "内部リンクを": "関連ページへのリンクを",
    "単発記事だけで終わらず": "関連情報も確認できるようにし",
    "DMM審査通過後": "",
    "アフィリエイトID/API": "必要な設定",
    "広告リンク表示枠": "",
    "検索流入": "検索からの訪問",
    "コンバージョン導線": "案内",
}

# Check only phrases that are strongly indicative of owner/developer copy. Avoid
# short generic acronyms such as TODO/CTR/KPI because they can legitimately occur
# inside product titles and therefore create false positives on catalog pages.
VISIBLE_AUDIT_TERMS = [
    "月100万円",
    "購入意図",
    "収益ページ",
    "収益導線",
    "収益化",
    "DMM審査通過後",
    "アフィリエイトID/API",
    "広告リンク表示枠",
    "広告導線",
    "商品導線",
    "コンバージョン導線",
    "サイト運営者向け",
    "運営者向け",
    "管理者向け",
    "管理画面",
    "管理者のみ",
    "管理用",
    "運用メモ",
    "開発メモ",
    "商品API",
    "APIから自動更新",
    "APIで自動更新",
    "API更新:",
    "公開作品のAPI反映待ち",
    "SEO対策",
    "Cloudflare",
    "GitHub",
    "デプロイ",
    "ステージング",
    "本番環境",
    "仮置き",
    "実装予定",
    "テスト用",
]


def looks_like_html(text: str) -> bool:
    head = text[:800].lower()
    return "<html" in head or "<!doctype html" in head


def visible_text(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<(script|style|noscript)\b[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


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

    # Remove empty elements left by cleanup.
    text = re.sub(r'<h[1-6][^>]*>\s*</h[1-6]>', '', text, flags=re.I)
    text = re.sub(r'<p[^>]*>\s*</p>', '', text, flags=re.I)
    text = re.sub(r'<div[^>]*>\s*</div>', '', text, flags=re.I)

    if text != before:
        path.write_text(text, encoding="utf-8")

    visible = visible_text(text)
    remaining = [term for term in VISIBLE_AUDIT_TERMS if term in visible]
    return text != before, remaining


def main() -> None:
    # Keep generated genre/category pages present before auditing every HTML file.
    helper = Path(".github/workflows/helpers/ensure_genre_category_pages.py")
    if helper.exists():
        subprocess.run([sys.executable, str(helper)], check=True)

    checked = 0
    changed = 0
    remaining_pages: list[tuple[str, list[str]]] = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        # The repository contains both .html files and extensionless HTML routes.
        if path.suffix.lower() not in {"", ".html"}:
            continue
        try:
            sample = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not looks_like_html(sample):
            continue

        checked += 1
        did_change, remaining = patch(path)
        if did_change:
            changed += 1
        if remaining:
            remaining_pages.append((path.relative_to(ROOT).as_posix(), remaining))

    print(f"Public-copy audit: checked={checked} changed={changed}")
    if remaining_pages:
        print("ERROR: owner/developer-facing visible text still exists:")
        for rel, terms in remaining_pages[:200]:
            print(f"  {rel}: {', '.join(terms)}")
        if len(remaining_pages) > 200:
            print(f"  ... plus {len(remaining_pages) - 200} more pages")
        raise SystemExit(1)
    print("Public-copy audit passed: every public HTML page is visitor-facing.")


if __name__ == "__main__":
    main()
