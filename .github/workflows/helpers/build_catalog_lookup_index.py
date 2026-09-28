from __future__ import annotations

import html
import json
import math
import re
import shutil
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
ACTRESS_DIR = DATA / "actress-catalog"
ACTRESS_INDEX = DATA / "actress-catalog-index.json"
ALIAS_GROUPS = DATA / "actress-alias-groups.json"
SEARCH_INDEX = DATA / "catalog-search-index.json"
AUDIT_OUTPUT = DATA / "catalog-audit.json"
SITEMAP = ROOT / "sitemap.xml"
LOADER_VERSION = "20260928-2348"
V6_VERSION = "20260928-2348"
SEARCH_VERSION = "20260928-2348"
PAGE_SIZE = 60
BASE_URL = "https://okazu-yoridori-midori.pages.dev"
ENTITY_LABELS = {"genre": "ジャンル", "maker": "メーカー", "actress": "女優"}


def safe_id(value: object) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return s[:120]


def price_value(value: object) -> int | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else None


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def unique_text(values: list[object]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def load_alias_resolution() -> tuple[dict[str, str], dict[str, dict]]:
    payload = load_json(ALIAS_GROUPS, {})
    id_to_canonical: dict[str, str] = {}
    canonical_meta: dict[str, dict] = {}
    for group in payload.get("groups") or []:
        if not isinstance(group, dict):
            continue
        canonical_id = safe_id(group.get("canonicalId"))
        canonical = str(group.get("canonical") or "").strip()
        if not canonical_id or not canonical:
            continue
        aliases = unique_text(list(group.get("aliases") or []))
        ids = [canonical_id] + [safe_id(x) for x in (group.get("aliasIds") or [])]
        for aid in ids:
            if aid:
                id_to_canonical[aid] = canonical_id
        canonical_meta[canonical_id] = {
            "name": canonical,
            "aliases": aliases,
            "rawIds": [x for x in ids if x],
        }
    return id_to_canonical, canonical_meta


def compact_product(row: dict, alias_map: dict[str, str], alias_meta: dict[str, dict]) -> dict:
    maker_entities = [x for x in (row.get("makerEntities") or []) if isinstance(x, dict)]
    maker = maker_entities[0] if maker_entities else {}
    actress_entities = [x for x in (row.get("actressEntities") or []) if isinstance(x, dict)]
    actress_names = [str(x.get("name") or "") for x in actress_entities]
    actress_ids: list[str] = []
    for actress in actress_entities:
        raw_id = safe_id(actress.get("id"))
        canonical_id = alias_map.get(raw_id, raw_id)
        if canonical_id:
            actress_ids.append(canonical_id)
        meta = alias_meta.get(canonical_id)
        if meta:
            actress_names.extend([meta.get("name") or ""] + list(meta.get("aliases") or []))
    genre_entities = [x for x in (row.get("genreEntities") or []) if isinstance(x, dict)]
    return {
        "id": safe_id(row.get("contentId")),
        "title": str(row.get("title") or ""),
        "image": str(row.get("imageURL") or ""),
        "price": str(row.get("price") or ""),
        "priceValue": price_value(row.get("price")),
        "maker": str(row.get("maker") or maker.get("name") or ""),
        "makerId": safe_id(maker.get("id")),
        "actresses": unique_text(actress_names)[:30],
        "actressIds": unique_text(actress_ids)[:20],
        "genres": unique_text([x.get("name") for x in genre_entities] + list(row.get("genres") or []))[:40],
        "genreIds": unique_text([safe_id(x.get("id")) for x in genre_entities])[:40],
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


def normalized_items(data: dict) -> list[dict]:
    items = data.get("items") or []
    if isinstance(items, dict):
        items = list(items.values())
    by_id: dict[str, dict] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        cid = safe_id(item.get("id"))
        if cid:
            by_id[cid] = item
    out = list(by_id.values())
    out.sort(key=lambda x: (str(x.get("date") or ""), int(x.get("reviewCount") or 0)), reverse=True)
    return out


def write_entity_catalog(
    directory: Path,
    index_path: Path,
    groups: dict[str, dict],
    manifest: dict,
    entity_key: str,
    catalog_count: int,
) -> tuple[int, int, int, list[dict]]:
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)

    index_rows = []
    total_bytes = 0
    total_assignments = 0
    for entity_id, data in sorted(groups.items(), key=lambda kv: len(normalized_items(kv[1])), reverse=True):
        items = normalized_items(data)
        if not items:
            continue
        payload = {
            "version": 3,
            "generatedAt": manifest.get("generatedAt"),
            "id": entity_id,
            "name": data["name"],
            "count": len(items),
            "aliases": unique_text(list(data.get("aliases") or [])),
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
            "aliases": payload["aliases"],
            "count": len(items),
            "file": f"/data/{directory.name}/{entity_id}.json",
        })

    index_payload = {
        "version": 3,
        "generatedAt": manifest.get("generatedAt"),
        "catalogCount": catalog_count,
        f"{entity_key}Count": len(index_rows),
        "assignmentCount": total_assignments,
        f"{entity_key}s": index_rows,
    }
    index_path.write_text(json.dumps(index_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(index_rows), total_assignments, total_bytes, index_rows


def sitemap_product_404_risk() -> tuple[int, int]:
    if not SITEMAP.exists():
        return 0, 0
    text = SITEMAP.read_text(encoding="utf-8")
    ids = re.findall(r"/products/([^/?<]+)/</loc>", text)
    missing = 0
    for cid in ids:
        if cid == "view":
            continue
        if not (ROOT / "products" / cid / "index.html").exists():
            missing += 1
    return len(ids), missing


def product_card(item: dict) -> str:
    cid = html.escape(str(item.get("id") or ""), quote=True)
    title = html.escape(str(item.get("title") or "FANZA作品"))
    image = html.escape(str(item.get("image") or ""), quote=True)
    maker = html.escape(str(item.get("maker") or "FANZA"))
    actresses = html.escape(" / ".join((item.get("actresses") or [])[:2]))
    price = html.escape(str(item.get("price") or "公式で価格確認"))
    review = ""
    if item.get("reviewAverage"):
        review = f'★ {html.escape(str(item.get("reviewAverage")))}'
        if item.get("reviewCount"):
            review += f' ({int(item.get("reviewCount") or 0)})'
    discount = int(item.get("discountRate") or 0)
    badge = f'<span class="fc-discount">{discount}%OFF</span>' if discount > 0 else ""
    sub = " / ".join(x for x in [maker, actresses] if x)
    return f'''<a class="fc-card" href="/products/view/?id={cid}"><div class="fc-img">{badge}<img src="{image}" alt="{title}" loading="lazy" decoding="async"></div><div class="fc-body"><strong>{title}</strong><span>{sub}</span><b>{price}</b>{f'<small>{review}</small>' if review else ''}</div></a>'''


def page_head(title: str, description: str, canonical: str, prev_url: str = "", next_url: str = "") -> str:
    rels = ""
    if prev_url:
        rels += f'<link rel="prev" href="{html.escape(prev_url, quote=True)}">'
    if next_url:
        rels += f'<link rel="next" href="{html.escape(next_url, quote=True)}">'
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="{html.escape(description, quote=True)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{html.escape(canonical, quote=True)}">{rels}<link rel="icon" type="image/png" href="/assets/favicon.png"><link rel="stylesheet" href="/assets/style-white-v2.css?v=20260922-1322"><link rel="stylesheet" href="/assets/full-catalog.css?v=20260926-001"><link rel="stylesheet" href="/assets/entity-rankings.css?v=20260925-2315"></head><body>'''


def header() -> str:
    return '''<header><div class="wrap header-inner"><a class="logo" href="/">オカズはよりどりみどり</a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/products/">作品一覧</a><a href="/search/">5万作品検索</a><a href="/guide/">初心者ガイド</a></nav></div></header>'''


def footer() -> str:
    return '''<footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり.</div></div></footer><script src="/assets/affiliate-config.js"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js?v=20260928-2348"></script><script src="/assets/affiliate-compliance.js"></script>'''


def clean_old_pagination(entity_type: str) -> None:
    root = ROOT / "ranking" / entity_type
    if not root.exists():
        return
    for path in root.glob("*/page"):
        if path.is_dir():
            shutil.rmtree(path)


def patch_base_page(entity_type: str, entity_id: str, page_count: int, total_count: int) -> bool:
    base_file = ROOT / "ranking" / entity_type / entity_id / "index.html"
    if not base_file.exists() or page_count <= 1:
        return False
    text = base_file.read_text(encoding="utf-8")
    text = re.sub(r"<!-- FULL_PAGINATION_HEAD_START -->.*?<!-- FULL_PAGINATION_HEAD_END -->", "", text, flags=re.S)
    text = re.sub(r"<!-- FULL_PAGINATION_NAV_START -->.*?<!-- FULL_PAGINATION_NAV_END -->", "", text, flags=re.S)
    next_url = f"{BASE_URL}/ranking/{entity_type}/{entity_id}/page/2/"
    head_block = f'<!-- FULL_PAGINATION_HEAD_START --><link rel="next" href="{next_url}"><!-- FULL_PAGINATION_HEAD_END -->'
    text = text.replace("</head>", head_block + "</head>", 1)
    nav = f'''<!-- FULL_PAGINATION_NAV_START --><div class="wrap" style="margin:24px auto"><nav class="fc-pagination"><span>全{total_count:,}作品</span><a href="/ranking/{entity_type}/{entity_id}/page/2/">2ページ目を見る →</a></nav></div><!-- FULL_PAGINATION_NAV_END -->'''
    text = text.replace("</main>", nav + "</main>", 1)
    base_file.write_text(text, encoding="utf-8")
    return True


def write_seo_pagination(entity_type: str, groups: dict[str, dict]) -> tuple[list[str], int]:
    clean_old_pagination(entity_type)
    urls: list[str] = []
    patched = 0
    label = ENTITY_LABELS[entity_type]
    for entity_id, data in groups.items():
        items = normalized_items(data)
        if len(items) <= PAGE_SIZE:
            continue
        base_file = ROOT / "ranking" / entity_type / entity_id / "index.html"
        if not base_file.exists():
            continue
        page_count = math.ceil(len(items) / PAGE_SIZE)
        if patch_base_page(entity_type, entity_id, page_count, len(items)):
            patched += 1
        name = str(data.get("name") or label)
        for page_no in range(2, page_count + 1):
            chunk = items[(page_no - 1) * PAGE_SIZE: page_no * PAGE_SIZE]
            path = f"/ranking/{entity_type}/{entity_id}/page/{page_no}/"
            canonical = BASE_URL + path
            prev_path = f"/ranking/{entity_type}/{entity_id}/" if page_no == 2 else f"/ranking/{entity_type}/{entity_id}/page/{page_no - 1}/"
            next_path = f"/ranking/{entity_type}/{entity_id}/page/{page_no + 1}/" if page_no < page_count else ""
            title = f"{name}のFANZA作品一覧 {page_no}ページ目｜{len(items):,}作品"
            desc = f"{name}に該当するFANZA作品を全{len(items):,}作品から表示。{page_no}ページ目。新着・人気・評価・価格・セール条件でも探せます。"
            nav = f'<nav class="fc-pagination"><a href="{prev_path}">← 前へ</a><span>{page_no} / {page_count}</span>' + (f'<a href="{next_path}">次へ →</a>' if next_path else '<span></span>') + '</nav>'
            cards = "".join(product_card(x) for x in chunk)
            page = page_head(title, desc, canonical, BASE_URL + prev_path, BASE_URL + next_path if next_path else "") + header() + f'''<main><section class="section"><div class="wrap"><div class="fc-breadcrumb"><a href="/ranking/">ランキング</a> › <a href="/ranking/{entity_type}/">{label}別</a> › <a href="/ranking/{entity_type}/{entity_id}/">{html.escape(name)}</a> › {page_no}ページ目</div><h1>{html.escape(name)} 全{len(items):,}作品</h1><p>{label}「{html.escape(name)}」の全作品一覧です。現在{page_no}/{page_count}ページ。</p>{nav}<div class="fc-grid">{cards}</div>{nav}<p class="fc-pr">PR：当ページにはアフィリエイト広告を含みます。</p></div></section></main>''' + footer() + "</body></html>"
            out = ROOT / path.lstrip("/") / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(page, encoding="utf-8")
            urls.append(path)
    return urls, patched


def update_sitemap_pagination(urls: list[str]) -> None:
    if not SITEMAP.exists():
        return
    text = SITEMAP.read_text(encoding="utf-8")
    text = re.sub(r"\s*<!-- FULL_FACET_PAGINATION_START -->.*?<!-- FULL_FACET_PAGINATION_END -->\s*", "\n", text, flags=re.S)
    entries = "\n".join(f"  <url><loc>{BASE_URL}{html.escape(url)}</loc></url>" for url in urls)
    block = f"  <!-- FULL_FACET_PAGINATION_START -->\n{entries}\n  <!-- FULL_FACET_PAGINATION_END -->\n"
    text = text.replace("</urlset>", block + "</urlset>")
    SITEMAP.write_text(text, encoding="utf-8")


def write_search_index(products: list[dict], generated_at: object) -> int:
    payload = {
        "version": 2,
        "generatedAt": generated_at,
        "count": len(products),
        "items": products,
    }
    SEARCH_INDEX.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(products)


def write_search_page(catalog_count: int) -> None:
    path = ROOT / "search" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    title = f"FANZA {catalog_count:,}作品を条件検索｜オカズはよりどりみどり"
    desc = "女優・ジャンル・メーカー・作品名・セール・価格・評価を組み合わせてFANZA作品を検索できます。"
    page = page_head(title, desc, BASE_URL + "/search/") + header() + f'''<main><section class="section"><div class="wrap"><div class="fc-breadcrumb"><a href="/">トップ</a> › 5万作品検索</div><h1>FANZA {catalog_count:,}作品をまとめて検索</h1><p>作品名・女優・ジャンル・メーカー・セール・価格・評価を組み合わせて絞り込めます。</p><div id="catalogAdvancedSearch" class="catalog-search-app"><div class="catalog-search-loading">検索データを読み込み中です…</div></div><p class="fc-pr">PR：当ページにはアフィリエイト広告を含みます。価格・販売状況はFANZA公式で最終確認してください。</p></div></section></main>''' + footer() + f'<script src="/assets/catalog-search.js?v={SEARCH_VERSION}"></script></body></html>'
    path.write_text(page, encoding="utf-8")


def build_index() -> dict:
    if not MANIFEST.exists():
        raise SystemExit(f"Missing {MANIFEST}")
    manifest = load_json(MANIFEST, {})
    alias_map, alias_meta = load_alias_resolution()
    lookup: dict[str, int] = {}
    genres: dict[str, dict] = {}
    makers: dict[str, dict] = {}
    actresses: dict[str, dict] = {}
    search_products: list[dict] = []
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
    actress_assignments = 0

    for shard_no, shard in enumerate(shards, 1):
        rel = str(shard.get("file") or "").lstrip("/")
        if not rel:
            continue
        path = ROOT / rel
        if not path.exists():
            print(f"WARN missing shard: {path}")
            continue
        rows = load_json(path, [])
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

            product = compact_product(row, alias_map, alias_meta)
            search_products.append(product)
            for genre in genre_entities:
                gid = safe_id(genre.get("id"))
                name = str(genre.get("name") or "").strip()
                if not gid or not name:
                    continue
                bucket = genres.setdefault(gid, {"name": name, "items": {}})
                bucket["name"] = name
                bucket["items"][cid] = product
                genre_assignments += 1
            for maker in maker_entities:
                mid = safe_id(maker.get("id"))
                name = str(maker.get("name") or "").strip()
                if not mid or not name:
                    continue
                bucket = makers.setdefault(mid, {"name": name, "items": {}})
                bucket["name"] = name
                bucket["items"][cid] = product
                maker_assignments += 1

            per_product_actresses: set[str] = set()
            for actress in actress_entities:
                raw_id = safe_id(actress.get("id"))
                aid = alias_map.get(raw_id, raw_id)
                if not aid or aid in per_product_actresses:
                    continue
                per_product_actresses.add(aid)
                meta = alias_meta.get(aid) or {}
                name = str(meta.get("name") or actress.get("name") or "").strip()
                bucket = actresses.setdefault(aid, {"name": name, "aliases": list(meta.get("aliases") or []), "items": {}})
                if name:
                    bucket["name"] = name
                if meta.get("aliases"):
                    bucket["aliases"] = list(meta.get("aliases") or [])
                bucket["items"][cid] = product
                actress_assignments += 1

    payload = {
        "version": 3,
        "generatedAt": manifest.get("generatedAt"),
        "count": len(lookup),
        "items": lookup,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    lookup_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text(lookup_text, encoding="utf-8")

    genre_count, genre_index_assignments, genre_bytes, genre_rows = write_entity_catalog(
        GENRE_DIR, GENRE_INDEX, genres, manifest, "genre", len(lookup)
    )
    maker_count, maker_index_assignments, maker_bytes, maker_rows = write_entity_catalog(
        MAKER_DIR, MAKER_INDEX, makers, manifest, "maker", len(lookup)
    )

    # Only publish per-actress catalogs when a real actress profile page exists. Alias IDs are already mapped to canonical IDs.
    actresses = {
        aid: data for aid, data in actresses.items()
        if (ROOT / "ranking" / "actress" / aid / "index.html").exists()
    }
    actress_count, actress_index_assignments, actress_bytes, actress_rows = write_entity_catalog(
        ACTRESS_DIR, ACTRESS_INDEX, actresses, manifest, "actress", len(lookup)
    )

    search_count = write_search_index(search_products, manifest.get("generatedAt"))
    write_search_page(len(lookup))

    pagination_urls: list[str] = []
    genre_urls, genre_bases = write_seo_pagination("genre", genres)
    maker_urls, maker_bases = write_seo_pagination("maker", makers)
    actress_urls, actress_bases = write_seo_pagination("actress", actresses)
    pagination_urls.extend(genre_urls)
    pagination_urls.extend(maker_urls)
    pagination_urls.extend(actress_urls)
    update_sitemap_pagination(pagination_urls)

    sitemap_product_urls, sitemap_missing_pages = sitemap_product_404_risk()
    dynamic_view_exists = (ROOT / "products" / "view" / "index.html").exists()
    fully_classified = len(lookup) - len({
        p["id"] for p in search_products
        if not p.get("genres") or not p.get("maker") or not p.get("actresses")
    })
    classification = {
        "catalogCount": len(lookup),
        "rawRows": raw_rows,
        "duplicateProductIds": duplicate_ids,
        "invalidProductIds": invalid_product_id,
        "missingGenre": missing_genre,
        "missingMaker": missing_maker,
        "missingActress": missing_actress,
        "fullyClassifiedCount": fully_classified,
        "brokenAffiliateLinks": broken_affiliate,
        "genreCount": genre_count,
        "genreAssignmentCount": genre_assignments,
        "genreIndexAssignmentCount": genre_index_assignments,
        "genreAssignmentCheck": genre_assignments == genre_index_assignments,
        "makerCount": maker_count,
        "makerAssignmentCount": maker_assignments,
        "makerIndexAssignmentCount": maker_index_assignments,
        "makerAssignmentCheck": maker_assignments == maker_index_assignments,
        "actressCatalogCount": actress_count,
        "actressAssignmentCount": actress_assignments,
        "actressPublishedAssignmentCount": actress_index_assignments,
        "searchIndexCount": search_count,
        "seoPaginationPages": len(pagination_urls),
        "seoGenreBasePages": genre_bases,
        "seoMakerBasePages": maker_bases,
        "seoActressBasePages": actress_bases,
        "sitemapProductUrls": sitemap_product_urls,
        "sitemapMissingProductPages": sitemap_missing_pages,
        "dynamicProductViewExists": dynamic_view_exists,
        "lookupCoverageCount": len(lookup),
    }
    AUDIT_OUTPUT.write_text(json.dumps({
        "version": 2,
        "generatedAt": manifest.get("generatedAt"),
        **classification,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    return {
        **classification,
        "lookupBytes": len(lookup_text.encode("utf-8")),
        "genreBytes": genre_bytes,
        "makerBytes": maker_bytes,
        "actressBytes": actress_bytes,
        "genreIndexRows": len(genre_rows),
        "makerIndexRows": len(maker_rows),
        "actressIndexRows": len(actress_rows),
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
    for entity_type in ("genre", "maker", "actress"):
        root = ROOT / "ranking" / entity_type
        if not root.exists():
            continue
        for html_path in root.glob("*/index.html"):
            text = html_path.read_text(encoding="utf-8")
            updated = re.sub(
                r"/assets/v6\.js(?:\?v=[^\"'<> ]+)?",
                f"/assets/v6.js?v={V6_VERSION}",
                text,
            )
            if "/assets/v6.js" not in updated and "http-equiv=\"refresh\"" not in updated:
                updated = updated.replace("</body>", f'<script src="/assets/v6.js?v={V6_VERSION}"></script></body>')
            if updated != text:
                html_path.write_text(updated, encoding="utf-8")
                entity_pages += 1
    return bumped, entity_pages


def main() -> None:
    stats = build_index()
    bumped, entity_pages = bump_loader_version()
    print(
        "Catalog facets/search/audit: "
        f"catalog={stats['catalogCount']}, genres={stats['genreCount']}, makers={stats['makerCount']}, "
        f"actress_catalogs={stats['actressCatalogCount']}, search={stats['searchIndexCount']}, "
        f"missing_genre={stats['missingGenre']}, missing_maker={stats['missingMaker']}, "
        f"missing_actress={stats['missingActress']}, duplicates={stats['duplicateProductIds']}, "
        f"broken_affiliate={stats['brokenAffiliateLinks']}, sitemap_404_risk={stats['sitemapMissingProductPages']}, "
        f"seo_pages={stats['seoPaginationPages']}; product_loader_bumped={bumped}; entity_pages_cache_busted={entity_pages}"
    )


if __name__ == "__main__":
    main()
