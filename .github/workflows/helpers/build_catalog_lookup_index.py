from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("public")
MANIFEST = ROOT / "data" / "full-catalog-manifest.json"
OUTPUT = ROOT / "data" / "catalog-lookup.json"
LOADER_VERSION = "20260927-1450"


def safe_id(value: object) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return s[:120]


def build_index() -> tuple[int, int]:
    if not MANIFEST.exists():
        raise SystemExit(f"Missing {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lookup: dict[str, int] = {}
    shards = manifest.get("shards") or []
    for shard_no, shard in enumerate(shards, 1):
        rel = str(shard.get("file") or "").lstrip("/")
        if not rel:
            continue
        path = ROOT / rel
        if not path.exists():
            print(f"WARN missing shard: {path}")
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        for row in rows if isinstance(rows, list) else []:
            cid = safe_id(row.get("contentId") if isinstance(row, dict) else "")
            if cid:
                lookup[cid] = shard_no
    payload = {
        "version": 1,
        "generatedAt": manifest.get("generatedAt"),
        "count": len(lookup),
        "items": lookup,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text(text, encoding="utf-8")
    return len(lookup), len(text.encode("utf-8"))


def bump_loader_version() -> bool:
    page = ROOT / "products" / "view" / "index.html"
    if not page.exists():
        return False
    text = page.read_text(encoding="utf-8")
    updated = re.sub(
        r"dynamic-product\.js(?:\?v=[^\"'<> ]+)?",
        f"dynamic-product.js?v={LOADER_VERSION}",
        text,
    )
    if updated != text:
        page.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    count, size = build_index()
    bumped = bump_loader_version()
    print(f"Catalog lookup index: {count} products, {size} bytes; loader cache bumped={bumped}")


if __name__ == "__main__":
    main()
