from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("public")
SITE_AFFILIATE_ID = "okazumidori-001"

API_LINK_RE = re.compile(
    r"((?:\?|&|&amp;)af_id=)okazumidori-99[0-9]((?:&|&amp;)ch=)api(?=((?:&|&amp;)|\"|'|<|$))"
)


def rewrite_text(text: str) -> tuple[str, int]:
    def repl(match: re.Match[str]) -> str:
        html_escaped = "&amp;" in match.group(2)
        sep = "&amp;" if html_escaped else "&"
        return f"{match.group(1)}{SITE_AFFILIATE_ID}{match.group(2)}link_tool{sep}ch_id=link"

    return API_LINK_RE.subn(repl, text)


def main() -> None:
    total = 0
    touched = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".json", ".js"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new_text, count = rewrite_text(text)
        if not count:
            continue
        path.write_text(new_text, encoding="utf-8")
        touched += 1
        total += count
    print(f"Rewrote {total} FANZA API affiliate URLs across {touched} files to site affiliate ID {SITE_AFFILIATE_ID}")


if __name__ == "__main__":
    main()
