from __future__ import annotations

import os
import re
from pathlib import Path

SALE_PAGE = Path("public/sale/index.html")
LIMIT = int(os.environ.get("SALE_STATIC_LIMIT", "120"))
CARD_RE = re.compile(r'<a class="fc-card"\b.*?</a>', re.S)
SUMMARY_RE = re.compile(r'<div class="fc-sale-summary">.*?</div>', re.S)


def main() -> None:
    if not SALE_PAGE.exists():
        raise SystemExit("public/sale/index.html is missing")

    text = SALE_PAGE.read_text(encoding="utf-8")
    cards = list(CARD_RE.finditer(text))
    total = len(cards)
    if total <= LIMIT:
        print(f"Sale page already compact: {total} cards")
        return

    kept = 0

    def keep_card(match: re.Match[str]) -> str:
        nonlocal kept
        kept += 1
        return match.group(0) if kept <= LIMIT else ""

    text = CARD_RE.sub(keep_card, text)
    summary = (
        f'<div class="fc-sale-summary"><strong>{total:,}作品</strong> / '
        f'割引率上位{LIMIT}件を表示中。価格・販売状況は変更される場合があります。 '
        f'<a href="/search/">全作品検索でさらに絞り込む</a></div>'
    )
    text = SUMMARY_RE.sub(summary, text, count=1)
    text = text.replace(
        "現在APIで確認できる割引作品を、割引率の高い順に表示しています。",
        f"現在APIで確認できる割引作品から、割引率の高い上位{LIMIT}件を表示しています。",
        1,
    )

    SALE_PAGE.write_text(text, encoding="utf-8")
    final_cards = len(CARD_RE.findall(text))
    if final_cards != LIMIT:
        raise SystemExit(f"Sale page compaction failed: expected {LIMIT}, got {final_cards}")
    print(f"Sale page optimized: total={total}, visible={final_cards}")


if __name__ == "__main__":
    main()
