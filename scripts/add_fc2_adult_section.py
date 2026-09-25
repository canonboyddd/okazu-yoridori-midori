from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("public")
NAV_LINK = '<a href="/fc2-adult/">FC2アダルト</a>'
BASE_URL = "https://okazu-yoridori-midori.pages.dev"


def inject_nav(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if '/fc2-adult/' in text and 'class="topnav"' in text:
        return False
    before = text

    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        if '/fc2-adult/' in inner:
            return match.group(0)
        # Put FC2 Adult just before the beginner guide when possible.
        beginner = re.search(r'<a[^>]+href="/guide/"[^>]*>.*?</a>', inner, flags=re.S)
        if beginner:
            pos = beginner.start()
            inner = inner[:pos] + NAV_LINK + inner[pos:]
        else:
            inner += NAV_LINK
        return f'<nav class="topnav">{inner}</nav>'

    text = re.sub(r'<nav class="topnav">(.*?)</nav>', repl, text, count=1, flags=re.S)
    if text != before:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def update_sitemap() -> bool:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return False
    text = sitemap.read_text(encoding="utf-8")
    url = BASE_URL + "/fc2-adult/"
    if url in text:
        return False
    today = datetime.now(timezone.utc).date().isoformat()
    entry = f'  <url><loc>{url}</loc><lastmod>{today}</lastmod></url>\n'
    text = text.replace("</urlset>", entry + "</urlset>")
    sitemap.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    changed = 0
    total = 0
    for path in ROOT.rglob("*.html"):
        total += 1
        if inject_nav(path):
            changed += 1
    sitemap_changed = update_sitemap()
    print(f"FC2 Adult nav injected: {changed}/{total}; sitemap_updated={sitemap_changed}")


if __name__ == "__main__":
    main()
