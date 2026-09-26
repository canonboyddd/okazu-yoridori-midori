from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("public")
ASSET = "/assets/colorful-readable-v1.css?v=20260926-1632"
LINK = f'<link rel="stylesheet" href="{ASSET}">'


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    before = text

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
