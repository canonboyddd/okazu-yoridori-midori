from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path("public")
DATA = ROOT / "data"
MANIFEST = DATA / "full-catalog-manifest.json"
OUTPUT = DATA / "catalog-lookup.json"
GENRE_DIR = DATA / "genre-catalog"
GENRE_INDEX = DATA / "genre-catalog-index.json"
MAKER_DIR = DATA / "maker-catalog"
MAKER_INDEX = DATA / "maker-catalog-index.json"
AUDIT_OUTPUT = DATA / "catalog-audit.json"
LOADER_VERSION = "20260928-1905"
V6_VERSION = "20260928-1905"


def safe_id(value: object) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return s[:120]


def price_value(value: object) -> int | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else None


def compact_product(row: dict) -> dict:
    maker_entities = [x for x in (row.get("makerEntities") or []) if isinstance(x, dict)]
    maker = maker_entities[0] if maker_entities else {}
    return {
        "id": safe_id(row.get("contentId")),
        "title": str(row.get("title") or ""),
        "image": str(row.get("imageURL") or ""),
        "price": str(row.get("price") or ""),
        "priceValue": price_value(row.get("price")),
        "maker": str(row.get("maker") or maker.get("name") or ""),
        "makerId": safe_id(maker.get("id")),
        "actresses": [str(x) for x in (row.get("actresses") or []) if str(x).strip()][:20],
        "genres": [str(x) for x in (row.get("genres") or []) if str(x).strip()][:30],
        "reviewAverage": row.get("reviewAverage") or "",
        "reviewCount": int(row.get("reviewCount") or 0),
        "date": str(row.get("date") or ""),
        "discountRate": int(row.get("discountRate") or 0),
    }


def valid_affiliate(url: str) -> bool:
    if not url or "okazumidori-001" in url or "ch=link_tool" in url:
        return False
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    return host.lower() in {"al.dmm.co.jp", "al.dmm.com", "al.fanza.co.jp", "al.fanza.com"}


def write_entity_catalog(
    directory: Path,
    index_path: Path,
    groups: dict[str, dict],
    manifest: dict,
    entity_key: str,
    catalog_count: int,
) -> tuple[int, int, int]:
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)

    index_rows = []
    total_bytes = 0
    total_assignments = 0
    for entity_id, data in sorted(groups.items(), key=lambda kv: len(kv[1]["items"]), reverse=True):
        items = data["items"]
        items.sort(key=lambda x: (x.get("date") or "", int(x.get("reviewCount") or 0)), reverse=True)
        payload = {
            "version": 2,
            "generatedAt": manifest.get("generatedAt"),
            "id": entity_id,
            "name": data["name"],
            "count": len(items),
            "items": items,
        }
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        (directory / f"{entity_id}.json").write_text(text, encoding="utf-8")
        size = len(text.encode("utf-8"))
        total_bytes += size
        total_assignments += len(items)
        index_rows.append({
            "id": entity_id,
            "name": data["name"],
            "count": len(items),
            "file": f"/data/{directory.name}/{entity_id}.json",
        })

    index_payload = {
        "version": 2,
        "generatedAt": manifest.get("generatedAt"),
        "catalogCount": catalog_count,
        f"{entity_key}Count": len(index_rows),
        "assignmentCount": total_assignments,
        f"{entity_key}s": index_rows,
    }
    index_path.write_text(json.dumps(index_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(index_rows), total_assignments, total_bytes


def sitemap_product_404_risk() -> tuple[int, int]:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return 0, 0
    text = sitemap.read_text(encoding="utf-8")
    ids = re.findall(r"/products/([^/?<]+)/</loc>", text)
    missing = 0
    for cid in ids:
        if cid == "view":
            continue
        if not (ROOT / "products" / cid / "index.html").exists():
            missing += 1
    return len(ids), missing


def build_index() -> dict:
    if not MANIFEST.exists():
        raise SystemExit(f"Missing {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lookup: dict[str, int] = {}
    genres: dict[str, dict] = {}
    makers: dict[str, dict] = {}
    shards = manifest.get("shards") or []

    seen: set[str] = set()
    duplicate_ids = 0
    missing_genre = 0
    missing_maker = 0
    missing_actress = 0
    broken_affiliate = 0
    invalid_product_id = 0
    raw_rows = 0
    genre_assignments = 0
    maker_assignments = 0

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
            raw_rows += 1
            cid = safe_id(row.get("contentId"))
            if not cid:
                invalid_product_id += 1
                continue
            if cid in seen:
                duplicate_ids += 1
                continue
            seen.add(cid)
            lookup[cid] = shard_no

            genre_entities = [x for x in (row.get("genreEntities") or []) if isinstance(x, dict) and x.get("id") and x.get("name")]
            maker_entities = [x for x in (row.get("makerEntities") or []) if isinstance(x, dict) and x.get("id") and x.get("name")]
            actress_entities = [x for x in (row.get("actressEntities") or []) if isinstance(x, dict) and x.get("id") and x.get("name")]
            if not genre_entities:
                missing_genre += 1
            if not maker_entities:
                missing_maker += 1
            if not actress_entities:
                missing_actress += 1
            if not valid_affiliate(str(row.get("affiliateURL") or "")):
                broken_affiliate += 1

            product = compact_product(row)
            for genre in genre_entities:
                gid = safe_id(genre.get("id"))
                name = str(genre.get("name") or "").strip()
                if not gid or not name:
                    continue
                bucket = genres.setdefault(gid, {"name": name, "items": []})
                bucket["name"] = name
                bucket["items"].append(product)
                genre_assignments += 1
            for maker in maker_entities:
                mid = safe_id(maker.get("id"))
                name = str(maker.get("name") or "").strip()
                if not mid or not name:
                    continue
                bucket = makers.setdefault(mid, {"name": name, "items": []})
                bucket["name"] = name
                bucket["items"].append(product)
                maker_assignments += 1

    payload = {
        "version": 2,
        "generatedAt": manifest.get("generatedAt"),
        "count": len(lookup),
        "items": lookup,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    lookup_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text(lookup_text, encoding="utf-8")

    genre_count, genre_index_assignments, genre_bytes = write_entity_catalog(
        GENRE_DIR, GENRE_INDEX, genres, manifest, "genre", len(lookup)
    )
    maker_count, maker_index_assignments, maker_bytes = write_entity_catalog(
        MAKER_DIR, MAKER_INDEX, makers, manifest, "maker", len(lookup)
    )

    sitemap_product_urls, sitemap_missing_pages = sitemap_product_404_risk()
    dynamic_view_exists = (ROOT / "products" / "view" / "index.html").exists()
    classification = {
        "catalogCount": len(lookup),
        "rawRows": raw_rows,
        "duplicateProductIds": duplicate_ids,
        "invalidProductIds": invalid_product_id,
        "missingGenre": missing_genre,
        "missingMaker": missing_maker,
        "missingActress": missing_actress,
        "brokenAffiliateLinks": broken_affiliate,
        "genreCount": genre_count,
        "genreAssignmentCount": genre_assignments,
        "genreIndexAssignmentCount": genre_index_assignments,
        "genreAssignmentCheck": genre_assignments == genre_index_assignments,
        "makerCount": maker_count,
        "makerAssignmentCount": maker_assignments,
        "makerIndexAssignmentCount": maker_index_assignments,
        "makerAssignmentCheck": maker_assignments == maker_index_assignments,
        "sitemapProductUrls": sitemap_product_urls,
        "sitemapMissingProductPages": sitemap_missing_pages,
        "dynamicProductViewExists": dynamic_view_exists,
        "lookupCoverageCount": len(lookup),
    }
    AUDIT_OUTPUT.write_text(json.dumps({
        "version": 1,
        "generatedAt": manifest.get("generatedAt"),
        **classification,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    return {
        **classification,
        "lookupBytes": len(lookup_text.encode("utf-8")),
        "genreBytes": genre_bytes,
        "makerBytes": maker_bytes,
    }


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

    entity_pages = 0
    for entity_type in ("genre", "maker"):
        root = ROOT / "ranking" / entity_type
        if not root.exists():
            continue
        for html_path in root.rglob("*.html"):
            text = html_path.read_text(encoding="utf-8")
            updated = re.sub(
                r"/assets/v6\.js(?:\?v=[^\"'<> ]+)?",
                f"/assets/v6.js?v={V6_VERSION}",
                text,
            )
            if updated != text:
                html_path.write_text(updated, encoding="utf-8")
                entity_pages += 1
    return bumped, entity_pages


def main() -> None:
    stats = build_index()
    bumped, entity_pages = bump_loader_version()
    print(
        "Catalog facets/audit: "
        f"catalog={stats['catalogCount']}, genres={stats['genreCount']}, makers={stats['makerCount']}, "
        f"missing_genre={stats['missingGenre']}, missing_maker={stats['missingMaker']}, "
        f"missing_actress={stats['missingActress']}, duplicates={stats['duplicateProductIds']}, "
        f"broken_affiliate={stats['brokenAffiliateLinks']}, sitemap_404_risk={stats['sitemapMissingProductPages']}; "
        f"product_loader_bumped={bumped}; entity_pages_cache_busted={entity_pages}"
    )


if __name__ == "__main__":
    main()
