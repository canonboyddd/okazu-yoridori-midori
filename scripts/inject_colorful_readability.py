from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("public")
ASSET_VERSION = "20260927-1418"
ASSET = f"/assets/colorful-readable-v1.css?v={ASSET_VERSION}"
LINK = f'<link rel="stylesheet" href="{ASSET}">'


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    before = text

    # Force fresh base/product CSS after design fixes so mobile browsers do not
    # keep an older dark-theme or CTA stylesheet for 24 hours.
    text = re.sub(
        r'/assets/style-white-v2\.css(?:\?v=[^"\']*)?',
        f'/assets/style-white-v2.css?v={ASSET_VERSION}',
        text,
        flags=re.I,
    )
    text = re.sub(
        r'/assets/full-catalog\.css(?:\?v=[^"\']*)?',
        f'/assets/full-catalog.css?v={ASSET_VERSION}',
        text,
        flags=re.I,
    )

    # Remove older copies/versions so the theme is loaded exactly once and last.
    text = re.sub(
        r'<link\s+rel="stylesheet"\s+href="/assets/colorful-readable-v1\.css(?:\?v=[^"]*)?"\s*/?>',
        "",
        text,
        flags=re.I,
    )
    if "</head>" in text:
        text = text.replace("</head>", LINK + "</head>", 1)

    if text != before:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    total = 0
    for path in ROOT.rglob("*.html"):
        total += 1
        if patch(path):
            changed += 1
    print(f"Colorful readability theme injected: {changed}/{total} HTML files")


if __name__ == "__main__":
    main()
