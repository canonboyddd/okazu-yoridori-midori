"""Keep every HTML page in public/ on a .html file name.

Cloudflare Pages chooses the Content-Type from the file extension. A page saved
without an extension (public/articles/sale-guide, public/about, ...) is served as
application/octet-stream, so browsers download it instead of rendering it. With a
.html name Pages serves the same clean URL (/articles/sale-guide) as text/html and
redirects the .html form to it.

Fast deploys restore an older production snapshot before overlaying repository
changes, so stale extensionless copies can come back from the snapshot. Run this
after every restore and before every deploy.

    python scripts/normalize_public_routes.py           # repair in place
    python scripts/normalize_public_routes.py --check   # fail if any remain
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path("public")

# Cloudflare Pages control files: plain text, extensionless on purpose.
CONTROL_FILES = {"_headers", "_redirects", "_routes.json", "_worker.js"}


def looks_like_html(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            head = handle.read(1024).decode("utf-8", errors="ignore").lower()
    except OSError:
        return False
    return "<!doctype html" in head or "<html" in head


def extensionless_html(root: Path = ROOT) -> list[Path]:
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix or path.name in CONTROL_FILES:
            continue
        if looks_like_html(path):
            found.append(path)
    return found


def normalize(root: Path = ROOT) -> tuple[int, int]:
    """Rename extensionless HTML pages to .html; drop them when the .html page exists."""
    renamed = removed = 0
    for path in extensionless_html(root):
        target = path.with_name(path.name + ".html")
        if target.exists():
            # The .html page is the maintained one; the extensionless copy would shadow it.
            path.unlink()
            removed += 1
        else:
            path.rename(target)
            renamed += 1
    return renamed, removed


def main(argv: list[str]) -> int:
    if "--check" in argv:
        remaining = extensionless_html()
        if remaining:
            print("ERROR: HTML pages without a .html extension would be served as downloads:")
            for path in remaining[:50]:
                print(f"  {path.as_posix()}")
            return 1
        print("Public route check passed: every HTML page has a .html file name.")
        return 0
    renamed, removed = normalize()
    print(f"Public routes normalized: renamed={renamed} removed_duplicates={removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
