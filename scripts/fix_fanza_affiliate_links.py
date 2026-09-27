from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("public")
API_AFFILIATE_ID = "okazumidori-990"
CACHE_VERSION = "20260928-0115"

# A previous deployment step incorrectly converted official DMM/FANZA API links
# from:
#   af_id=okazumidori-990&ch=api
# to:
#   af_id=okazumidori-001&ch=link_tool&ch_id=link
#
# That conversion makes the ad link invalid. Restore the original API channel
# while leaving the encoded landing URL (lurl=...) untouched.
BROKEN_LINK_RE = re.compile(
    r"((?:\?|&|&amp;)af_id=)okazumidori-001"
    r"((?:&|&amp;)ch=)link_tool"
    r"(?:&|&amp;)ch_id=link"
)

SCRIPT_PATTERNS = (
    "affiliate-config.js",
    "affiliate-compliance.js",
    "fanza-products.js",
    "dynamic-product.js",
)


def rewrite_text(text: str, suffix: str) -> tuple[str, int]:
    total = 0

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{API_AFFILIATE_ID}{match.group(2)}api"

    text, count = BROKEN_LINK_RE.subn(repl, text)
    total += count

    if suffix == ".html":
        for name in SCRIPT_PATTERNS:
            pattern = re.compile(rf"(/assets/{re.escape(name)})(?:\?v=[^\"']*)?")
            text, count = pattern.subn(rf"\1?v={CACHE_VERSION}", text)
            total += count

    return text, total


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

        new_text, count = rewrite_text(text, path.suffix.lower())
        if not count or new_text == text:
            continue

        path.write_text(new_text, encoding="utf-8")
        touched += 1
        total += count

    print(
        f"Repaired/busted {total} FANZA link or script references across {touched} files; "
        f"API affiliate ID={API_AFFILIATE_ID}, cache={CACHE_VERSION}"
    )


if __name__ == "__main__":
    main()
