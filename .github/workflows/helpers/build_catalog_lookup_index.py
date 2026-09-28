from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path("public")
MANIFEST = ROOT / "data" / "full-catalog-manifest.json"
OUTPUT = ROOT / "data" / "catalog-lookup.json"
GENRE_DIR = ROOT / "data" / "genre-catalog"
GENRE_INDEX = ROOT / "data" / "genre-catalog-index.json"
LOADER_VERSION = "20260928-1317"
V6_VERSION = "20260928-1317"


def safe_id(value: object) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return s[:120]


def compact_product(row: dict) -> dict:
    return {
        "id": safe_id(row.get("contentId")),
        "title": str(row.get("title") or ""),
        "image": str(row.get("imageURL") or ""),
        "price": str(row.get("price") or ""),
        "maker": str(row.get("maker") or ""),
        "actresses": [str(x) for x in (row.get("actresses") or [])[:2]],
        "reviewAverage": row.get("reviewAverage") or "",
        "reviewCount": int(row.get("reviewCount") or 0),
        "date": str(row.get("date") or ""),
        "discountRate": int(row.get("discountRate") or 0),
    }


def build_index() -> tuple[int, int, int, int]:
    if not MANIFEST.exists():
        raise SystemExit(f"Missing {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lookup: dict[str, int] = {}
    genres: dict[str, dict] = {}
    shards = manifest.get("shards") or []

    if GENRE_DIR.exists():
        shutil.rmtree(GENRE_DIR)
    GENRE_DIR.mkdir(parents=True, exist_ok=True)

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
            if not isinstance(row, dict):
                continue
            cid = safe_id(row.get("contentId"))
            if not cid:
                continue
            lookup[cid] = shard_no
            product = compact_product(row)
            for genre in row.get("genreEntities") or []:
                if not isinstance(genre, dict):
                    continue
                gid = safe_id(genre.get("id"))
                name = str(genre.get("name") or "").strip()
                if not gid or not name:
                    continue
                bucket = genres.setdefault(gid, {"name": name, "items": []})
                bucket["name"] = name
                bucket["items"].append(product)

    payload = {
        "version": 1,
        "generatedAt": manifest.get("generatedAt"),
        "count": len(lookup),
        "items": lookup,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text(text, encoding="utf-8")

    genre_index = []
    genre_bytes = 0
    for gid, data in sorted(genres.items(), key=lambda kv: len(kv[1]["items"]), reverse=True):
        items = data["items"]
        items.sort(key=lambda x: (x.get("date") or "", int(x.get("reviewCount") or 0)), reverse=True)
        genre_payload = {
            "version": 1,
            "generatedAt": manifest.get("generatedAt"),
            "id": gid,
            "name": data["name"],
            "count": len(items),
            "items": items,
        }
        genre_text = json.dumps(genre_payload, ensure_ascii=False, separators=(",", ":"))
        (GENRE_DIR / f"{gid}.json").write_text(genre_text, encoding="utf-8")
        genre_bytes += len(genre_text.encode("utf-8"))
        genre_index.append({
            "id": gid,
            "name": data["name"],
            "count": len(items),
            "file": f"/data/genre-catalog/{gid}.json",
        })

    index_payload = {
        "version": 1,
        "generatedAt": manifest.get("generatedAt"),
        "catalogCount": len(lookup),
        "genreCount": len(genre_index),
        "genres": genre_index,
    }
    GENRE_INDEX.write_text(json.dumps(index_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(lookup), len(text.encode("utf-8")), len(genre_index), genre_bytes


def bump_loader_version() -> tuple[bool, int]:
    page = ROOT / "products" / "view" / "index.html"
    bumped = False
    if page.exists():
        text = page.read_text(encoding="utf-8")
        updated = re.sub(
            r"dynamic-product\.js(?:\?v=[^\"'<> ]+)?",
            f"dynamic-product.js?v={LOADER_VERSION}",
            text,
        )
        if updated != text:
            page.write_text(updated, encoding="utf-8")
            bumped = True

    genre_pages = 0
    genre_root = ROOT / "ranking" / "genre"
    if genre_root.exists():
        for html_path in genre_root.rglob("*.html"):
            text = html_path.read_text(encoding="utf-8")
            updated = re.sub(
                r"/assets/v6\.js(?:\?v=[^\"'<> ]+)?",
                f"/assets/v6.js?v={V6_VERSION}",
                text,
            )
            if updated != text:
                html_path.write_text(updated, encoding="utf-8")
                genre_pages += 1
    return bumped, genre_pages


def main() -> None:
    count, size, genre_count, genre_bytes = build_index()
    bumped, genre_pages = bump_loader_version()
    print(
        f"Catalog lookup index: {count} products, {size} bytes; "
        f"full genre catalogs={genre_count}, genre_bytes={genre_bytes}; "
        f"product loader bumped={bumped}; genre pages cache-busted={genre_pages}"
    )


if __name__ == "__main__":
    main()
