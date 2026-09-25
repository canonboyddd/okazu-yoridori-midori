from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("public/ranking/actress")
ASSET_VERSION = "20260925-2358"


def clean_directory_page(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    before = text

    # Directory cards without FANZA profile images are omitted rather than showing
    # a made-up or unrelated photo. The full 10,000-person dataset remains in JSON
    # so name/kana filtering still works from the official API data.
    patterns = [
        r'<div class="actress-card"><div class="actress-photo"><span class="actress-fallback">.*?</span></div><div class="actress-card-body">.*?</div></div>',
        r'<a class="actress-card"[^>]*><div class="actress-photo"><span class="actress-fallback">.*?</span></div><div class="actress-card-body">.*?</div></a>',
    ]
    removed = 0
    for pattern in patterns:
        text, n = re.subn(pattern, "", text, flags=re.S)
        removed += n

    text = re.sub(
        r'taxonomy-directory\.css\?v=[0-9-]+',
        f'taxonomy-directory.css?v={ASSET_VERSION}',
        text,
    )
    text = re.sub(
        r'actress-directory\.js\?v=[0-9-]+',
        f'actress-directory.js?v={ASSET_VERSION}',
        text,
    )
    text = text.replace(
        'プロフィール画像・名前はFANZA Webサービスから取得しています。画像が提供されていない人物は文字アイコンで表示します。',
        'プロフィール画像・名前はFANZA Webサービスから取得しています。顔写真が提供されているプロフィールのみ一覧表示します。',
    )

    if text != before:
        path.write_text(text, encoding="utf-8")
    return removed


def main() -> None:
    pages = []
    root_index = ROOT / "index.html"
    if root_index.exists():
        pages.append(root_index)
    page_root = ROOT / "page"
    if page_root.exists():
        pages.extend(sorted(page_root.glob("*/index.html")))

    total_removed = 0
    changed = 0
    for path in pages:
        before = path.read_text(encoding="utf-8")
        removed = clean_directory_page(path)
        after = path.read_text(encoding="utf-8")
        total_removed += removed
        if after != before:
            changed += 1

    print(f"Polished actress directory pages: {changed}; hidden no-photo cards: {total_removed}")


if __name__ == "__main__":
    main()
