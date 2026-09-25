from __future__ import annotations

from pathlib import Path

ROOT = Path("public/ranking")
OLD = '<div class="notice"><strong>PRについて：</strong>このページにはアフィリエイト広告を含みます。順位・価格・販売状況は変動するため、リンク先の公式情報をご確認ください。</div>'
NEW = '<div class="entity-pr-footer"><strong>PR：</strong>当ページにはアフィリエイト広告を含みます。</div>'


def main() -> None:
    touched = 0
    for path in ROOT.glob("*/*/index.html"):
        text = path.read_text(encoding="utf-8")
        if OLD not in text:
            continue
        text = text.replace(OLD, "", 1)
        marker = '<p class="entity-credit">'
        if marker in text:
            text = text.replace(marker, NEW + marker, 1)
        else:
            text = text.replace("</main>", NEW + "</main>", 1)
        path.write_text(text, encoding="utf-8")
        touched += 1
    print(f"Moved compact PR disclosure below ranking content on {touched} pages")


if __name__ == "__main__":
    main()
