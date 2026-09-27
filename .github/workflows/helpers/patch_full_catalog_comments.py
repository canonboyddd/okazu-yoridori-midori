from __future__ import annotations

from pathlib import Path

TARGET = Path("scripts/build_full_catalog_upgrade.py")
COMMENT_LINE = '        "comment": str(item.get("comment") or "").strip()[:800],\n'
NEEDLE = '        "title": str(item.get("title") or "").strip(),\n        "affiliateURL": str(item.get("affiliateURL") or "").strip(),\n'


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Missing generator: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    if COMMENT_LINE.strip() in text:
        print("Full catalog generator already captures product comments")
        return

    if NEEDLE not in text:
        raise SystemExit("Could not locate full-catalog normalize block for comment capture")

    replacement = (
        '        "title": str(item.get("title") or "").strip(),\n'
        + COMMENT_LINE
        + '        "affiliateURL": str(item.get("affiliateURL") or "").strip(),\n'
    )
    TARGET.write_text(text.replace(NEEDLE, replacement, 1), encoding="utf-8")
    print("Enabled FANZA product comment capture in full catalog generator")


if __name__ == "__main__":
    main()
