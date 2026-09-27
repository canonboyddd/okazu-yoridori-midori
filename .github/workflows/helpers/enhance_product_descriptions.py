from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path("public")
MANIFEST = ROOT / "data" / "full-catalog-manifest.json"
START = "<!-- PRODUCT_DESCRIPTION_START -->"
END = "<!-- PRODUCT_DESCRIPTION_END -->"
MAX_EXCERPT = 360


def safe_id(value: object) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return s[:120] or "item"


def clean_comment(value: object) -> str:
    text = str(value or "")
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def excerpt(value: object) -> str:
    text = clean_comment(value)
    if len(text) <= MAX_EXCERPT:
        return text
    cut = text[:MAX_EXCERPT]
    best = max(cut.rfind("。"), cut.rfind("！"), cut.rfind("？"), cut.rfind("!"), cut.rfind("?"))
    if best >= 120:
        cut = cut[: best + 1]
    else:
        cut = cut.rstrip(" 、，。！？!?") + "…"
    return cut


def product_block(row: dict) -> str:
    comment = excerpt(row.get("comment"))
    if not comment:
        return ""
    return (
        f"{START}"
        '<section class="fc-description" aria-label="作品紹介">'
        '<div class="fc-description-title">作品紹介</div>'
        f'<p class="fc-description-text">{html.escape(comment)}</p>'
        '<p class="fc-description-note">FANZA Webサービスの商品説明から、作品選びに必要な範囲を抜粋しています。</p>'
        f"</section>{END}"
    )


def iter_catalog_rows():
    if not MANIFEST.exists():
        return
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for shard in manifest.get("shards") or []:
        rel = str(shard.get("file") or "").lstrip("/")
        if not rel:
            continue
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(rows, list):
            yield from rows


def patch_page(path: Path, row: dict) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    before = text
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), "", text, flags=re.S)
    block = product_block(row)
    if block:
        if "</dl>" in text:
            text = text.replace("</dl>", "</dl>" + block, 1)
        elif '<a class="fc-cta"' in text:
            text = text.replace('<a class="fc-cta"', block + '<a class="fc-cta"', 1)

        comment = excerpt(row.get("comment"))
        if comment:
            meta = html.escape(comment[:150], quote=True)
            text = re.sub(
                r'<meta name="description" content="[^"]*">',
                f'<meta name="description" content="{meta}">',
                text,
                count=1,
            )

    if text != before:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    if not MANIFEST.exists():
        print("Product description enhancement skipped: full catalog manifest missing")
        return

    rows_with_comments = 0
    patched = 0
    for row in iter_catalog_rows() or []:
        if not isinstance(row, dict) or not clean_comment(row.get("comment")):
            continue
        rows_with_comments += 1
        cid = safe_id(row.get("contentId"))
        if patch_page(ROOT / "products" / cid / "index.html", row):
            patched += 1

    print(f"Product descriptions: catalog_comments={rows_with_comments} static_pages_patched={patched}")


if __name__ == "__main__":
    main()
