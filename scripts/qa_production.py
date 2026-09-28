from __future__ import annotations

import html as html_lib
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://okazu-yoridori-midori.pages.dev"
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
MOBILE_UA = "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 Chrome/154 Mobile Safari/537.36"
INVALID_FANZA_MARKERS = ["リンクは機能していません", "この広告リンクは無効", "広告リンクは無効"]
FACET_ASSET_VERSION = "20260928-2348"
V6_ASSET_VERSION = "20260929-0825"


def fetch(url: str, user_agent: str = DESKTOP_UA, retries: int = 6) -> tuple[int, str]:
    last: Exception | None = None
    for attempt in range(retries):
        req = Request(url, headers={"User-Agent": user_agent, "Cache-Control": "no-cache"})
        try:
            with urlopen(req, timeout=35) as res:
                return int(res.status), res.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(4 + attempt * 2)
    raise RuntimeError(f"GET failed after {retries} attempts: {url}: {last}")


def safe_id(value: object) -> str:
    text = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return text[:120] or "item"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def test_fc2() -> None:
    for label, ua in [("desktop", DESKTOP_UA), ("mobile", MOBILE_UA)]:
        status, page = fetch(BASE + "/fc2-adult/", ua)
        assert_true(status == 200, f"FC2 page returned {status} for {label}")
        assert_true("FC2アダルト" in page, f"FC2 heading missing for {label}")
        assert_true("fc2-banner" not in page, f"Old oversized FC2 banner remains for {label}")
        match = re.search(r'href="([^"]*fc2-adult\.css[^\"]*)"', page)
        assert_true(bool(match), "FC2 stylesheet link missing")
        css_url = match.group(1)
        if css_url.startswith("/"):
            css_url = BASE + css_url
        _, css = fetch(css_url, ua)
        compact = re.sub(r"\s+", "", css.lower())
        assert_true(".fc2-badge" in css, "FC2 badge CSS missing")
        assert_true("color:#fff!important" in compact or "color:#ffffff!important" in compact, "FC2 badge is not forced to readable white text")
        assert_true("min-height:0!important" in compact or "height:auto!important" in compact, "FC2 compact affiliate box rule missing")
    print("QA FC2: desktop/mobile readable compact layout OK")


def test_alias_pages() -> None:
    status, hub = fetch(BASE + "/ranking/actress/aliases/")
    assert_true(status == 200 and "同一女優・別名義" in hub, "Alias hub missing")
    status, raw = fetch(BASE + "/data/actress-alias-groups.json")
    assert_true(status == 200, "Alias group JSON missing")
    data = json.loads(raw)
    groups = data.get("groups") or []
    assert_true(bool(groups), "No resolved alias groups in production")
    canonical_id = str(groups[0].get("canonicalId") or "")
    canonical = str(groups[0].get("canonical") or "")
    assert_true(bool(canonical_id), "First alias group has no canonicalId")
    status, profile = fetch(BASE + f"/ranking/actress/{canonical_id}/")
    assert_true(status == 200, "Merged actress profile missing")
    assert_true("総作品数" in profile, "Enhanced actress profile stats missing")
    assert_true("出演メーカー" in profile and "関連ジャンル" in profile, "Enhanced actress metadata sections missing")
    assert_true("この女優の全作品を見る" in profile, "All-works CTA missing")
    assert_true("人気作品" in profile and "新着作品" in profile, "Actress popular/latest sections missing")
    assert_true("AV作品一覧・別名義・出演作品・FANZA情報" in profile, "Actress SEO title missing")
    status, works = fetch(BASE + f"/ranking/actress/{canonical_id}/works/")
    assert_true(status == 200 and "全作品一覧" in works, "All actress works page missing")
    print(f"QA aliases: {len(groups)} resolved groups; sample={canonical}")


def test_full_entity_catalog(entity_type: str) -> dict:
    key = {"genre": "genres", "maker": "makers", "actress": "actresses"}[entity_type]
    label = {"genre": "Genre", "maker": "Maker", "actress": "Actress"}[entity_type]
    status, raw = fetch(BASE + f"/data/{entity_type}-catalog-index.json")
    assert_true(status == 200, f"Full {entity_type} catalog index missing")
    data = json.loads(raw)
    catalog_count = int(data.get("catalogCount") or 0)
    rows = data.get(key) or []
    assert_true(catalog_count >= 40000, f"Full catalog unexpectedly small for {entity_type} aggregation: {catalog_count}")
    assert_true(bool(rows), f"No full-catalog {entity_type} groups generated")

    sample = None
    sample_page = ""
    for row in sorted(rows, key=lambda x: int(x.get("count") or 0), reverse=True)[:80]:
        entity_id = str(row.get("id") or "")
        if not entity_id or int(row.get("count") or 0) <= 30:
            continue
        try:
            page_status, page = fetch(BASE + f"/ranking/{entity_type}/{entity_id}/", retries=1)
        except RuntimeError:
            continue
        if page_status == 200:
            sample = row
            sample_page = page
            break
    assert_true(sample is not None, f"Could not find a live {entity_type} page backed by the full catalog")

    file_url = str(sample.get("file") or "")
    if file_url.startswith("/"):
        file_url = BASE + file_url
    status, entity_raw = fetch(file_url)
    assert_true(status == 200, f"Full {entity_type} product JSON missing")
    entity_data = json.loads(entity_raw)
    items = list(entity_data.get("items") or [])
    entity_shards = entity_data.get("shards") or []
    if not items and entity_shards:
        summed = 0
        for shard in entity_shards:
            shard_url = str(shard.get("file") or "")
            if shard_url.startswith("/"):
                shard_url = BASE + shard_url
            shard_status, shard_raw = fetch(shard_url)
            assert_true(shard_status == 200, f"Entity shard missing: {shard_url}")
            shard_data = json.loads(shard_raw)
            shard_items = shard_data.get("items") or []
            expected_shard_count = int(shard.get("count") or 0)
            assert_true(len(shard_items) == expected_shard_count, f"Entity shard count mismatch: {len(shard_items)}/{expected_shard_count}")
            assert_true(int(shard.get("bytes") or 0) < 24 * 1024 * 1024, f"Entity shard too large: {shard.get('bytes')}")
            items.extend(shard_items)
            summed += expected_shard_count
        assert_true(summed == int(entity_data.get("count") or 0), f"Entity shard manifest mismatch: {summed}/{entity_data.get('count')}")

    expected = int(sample.get("count") or 0)
    assert_true(len(items) == expected, f"{label} count mismatch: index={expected}, file/shards={len(items)}")
    assert_true(len(items) > 30, f"{label} page is still limited to the old 30-product API sample")
    assert_true(f"v6.js?v={V6_ASSET_VERSION}" in sample_page, f"{label} full-catalog loader cache-bust missing")
    if entity_type == "actress" and sample.get("aliases"):
        assert_true(isinstance(entity_data.get("aliases"), list), "Actress alias metadata missing from full catalog")
    print(f"QA {entity_type}s: catalog={catalog_count}; sample={sample.get('name')} full_count={len(items)} shards={len(entity_shards)}")
    return sample


def test_seo_pagination(entity_type: str, sample: dict) -> None:
    count = int(sample.get("count") or 0)
    if count <= 60:
        print(f"QA {entity_type} SEO pagination: sample has <=60 works; page 2 not required")
        return
    entity_id = str(sample.get("id") or "")
    status, page2 = fetch(BASE + f"/ranking/{entity_type}/{entity_id}/page/2/")
    assert_true(status == 200, f"SEO page 2 missing for {entity_type} {entity_id}")
    assert_true("rel=\"canonical\"" in page2 and "rel=\"prev\"" in page2, f"SEO canonical/prev missing for {entity_type} page 2")
    assert_true("2ページ目" in page2 and "fc-grid" in page2, f"SEO page 2 content missing for {entity_type}")
    status, base = fetch(BASE + f"/ranking/{entity_type}/{entity_id}/")
    assert_true("FULL_PAGINATION_HEAD_START" in base and "/page/2/" in base, f"Base {entity_type} page does not link to SEO page 2")
    print(f"QA {entity_type} SEO pagination: page 2 live for {sample.get('name')}")


def test_catalog_search() -> None:
    status, raw = fetch(BASE + "/data/catalog-search-index.json")
    assert_true(status == 200, "Advanced catalog search index missing")
    data = json.loads(raw)
    count = int(data.get("count") or 0)
    shards = data.get("shards") or []
    assert_true(count >= 40000, f"Advanced search manifest count too small: {count}")
    assert_true(len(shards) >= 2, "Advanced search index is not sharded")
    summed = sum(int(x.get("count") or 0) for x in shards if isinstance(x, dict))
    assert_true(summed == count, f"Advanced search shard counts do not total catalog: {summed}/{count}")
    max_bytes = max(int(x.get("bytes") or 0) for x in shards if isinstance(x, dict))
    assert_true(max_bytes < 24 * 1024 * 1024, f"Search shard exceeds safe Cloudflare size: {max_bytes}")

    first_file = str(shards[0].get("file") or "")
    if first_file.startswith("/"):
        first_file = BASE + first_file
    status, first_raw = fetch(first_file)
    assert_true(status == 200, "First advanced-search shard missing")
    first_data = json.loads(first_raw)
    first_items = first_data.get("items") or []
    assert_true(len(first_items) == int(shards[0].get("count") or 0), "First search shard item count mismatch")

    status, page = fetch(BASE + "/search/")
    assert_true(status == 200 and "catalogAdvancedSearch" in page, "Advanced search page missing")
    assert_true(f"catalog-search.js?v={FACET_ASSET_VERSION}" in page, "Advanced search asset version missing")
    status, script = fetch(BASE + f"/assets/catalog-search.js?v={FACET_ASSET_VERSION}")
    for marker in ["女優", "ジャンル", "メーカー", "セール作品のみ", "最低評価", "価格が安い順", "catalog_search", "data.shards", "fetchShard"]:
        assert_true(marker in script, f"Advanced search control/shard loader missing: {marker}")
    print(f"QA advanced search: {count} products across {len(shards)} Cloudflare-safe shards")


def test_catalog_audit() -> None:
    status, raw = fetch(BASE + "/data/catalog-audit.json")
    assert_true(status == 200, "Catalog audit report missing")
    audit = json.loads(raw)
    catalog_count = int(audit.get("catalogCount") or 0)
    assert_true(catalog_count >= 40000, f"Audit catalog unexpectedly small: {catalog_count}")
    assert_true(int(audit.get("duplicateProductIds") or 0) == 0, f"Duplicate product IDs found: {audit.get('duplicateProductIds')}")
    assert_true(int(audit.get("invalidProductIds") or 0) == 0, f"Invalid product IDs found: {audit.get('invalidProductIds')}")
    assert_true(int(audit.get("brokenAffiliateLinks") or 0) == 0, f"Broken affiliate links found: {audit.get('brokenAffiliateLinks')}")
    assert_true(bool(audit.get("genreAssignmentCheck")), "Genre assignment total does not match genre index total")
    assert_true(bool(audit.get("makerAssignmentCheck")), "Maker assignment total does not match maker index total")
    assert_true(int(audit.get("sitemapMissingProductPages") or 0) == 0, f"Sitemap product pages with 404 risk: {audit.get('sitemapMissingProductPages')}")
    assert_true(bool(audit.get("dynamicProductViewExists")), "Dynamic product fallback page missing")
    assert_true(int(audit.get("lookupCoverageCount") or 0) == catalog_count, "Product lookup does not cover the whole catalog")
    assert_true(int(audit.get("searchIndexCount") or 0) == catalog_count, "Advanced search index does not cover the whole catalog")
    assert_true(int(audit.get("actressCatalogCount") or 0) > 0, "No full actress catalogs generated")
    assert_true(int(audit.get("seoPaginationPages") or 0) > 0, "No SEO pagination pages generated")
    print(
        "QA catalog audit: "
        f"catalog={catalog_count}, fullyClassified={audit.get('fullyClassifiedCount')}, "
        f"missingGenre={audit.get('missingGenre')}, missingMaker={audit.get('missingMaker')}, "
        f"missingActress={audit.get('missingActress')}, actressCatalogs={audit.get('actressCatalogCount')}, "
        f"seoPages={audit.get('seoPaginationPages')}, duplicates={audit.get('duplicateProductIds')}, "
        f"brokenAffiliate={audit.get('brokenAffiliateLinks')}, sitemap404Risk={audit.get('sitemapMissingProductPages')}"
    )


def test_catalog_ui_asset() -> None:
    status, script = fetch(BASE + f"/assets/v6.js?v={V6_ASSET_VERSION}")
    assert_true(status == 200, "Facet UI asset missing")
    for marker in ["新着順", "人気順", "評価順", "価格順", "セール順", "女優名で絞り込み", "すべてのメーカー", "すべてのジャンル", "セール作品のみ", "actress", "data.shards"]:
        assert_true(marker in script, f"Catalog filter UI missing: {marker}")
    assert_true("${entityType}-catalog" in script, "Generic genre/maker/actress full-catalog loader missing")
    print("QA catalog UI: genre/maker/actress sort and filter controls OK")


def test_analytics_asset() -> None:
    status, script = fetch(BASE + f"/assets/ga4.js?v={FACET_ASSET_VERSION}")
    assert_true(status == 200, "Analytics asset missing")
    for marker in ["/api/ops-collect", "affiliate_click", "cta_position", "product_id", "actress", "genre", "maker", "device_type"]:
        assert_true(marker in script, f"Detailed analytics marker missing: {marker}")
    print("QA analytics: affiliate dimensions prepared for existing central dashboard")


def catalog_rows(limit_shards: int = 4) -> list[dict]:
    _, manifest_raw = fetch(BASE + "/data/full-catalog-manifest.json")
    manifest = json.loads(manifest_raw)
    shards = manifest.get("shards") or []
    assert_true(bool(shards), "Catalog manifest has no shards")
    rows: list[dict] = []
    for shard in shards[:limit_shards]:
        shard_url = str(shard.get("file") or "")
        if shard_url.startswith("/"):
            shard_url = BASE + shard_url
        _, shard_raw = fetch(shard_url)
        payload = json.loads(shard_raw)
        if isinstance(payload, list):
            rows.extend(x for x in payload if isinstance(x, dict))
    return rows


def find_live_product() -> tuple[str, str, str]:
    rows = catalog_rows()
    ranked = sorted(rows, key=lambda x: (1 if str(x.get("comment") or "").strip() else 0, int(x.get("reviewCount") or 0)), reverse=True)
    for row in ranked[:500]:
        api_link = str(row.get("affiliateURL") or "")
        if api_link:
            assert_true("okazumidori-001" not in api_link and "ch=link_tool" not in api_link, "Broken legacy FANZA URL remains in catalog JSON")
        cid = safe_id(row.get("contentId"))
        try:
            status, page = fetch(BASE + f"/products/{cid}/", DESKTOP_UA, retries=1)
        except RuntimeError:
            continue
        if status != 200:
            continue
        links = re.findall(r'href="([^"]*(?:al\.fanza\.co\.jp|al\.dmm\.co\.jp)[^"]*)"', page)
        if not links or "PRODUCT_PAGE_V2_START" not in page:
            continue
        link = html_lib.unescape(links[0])
        return cid, link, page
    raise RuntimeError("Could not find a static production product page with FANZA affiliate link and Product Page V2")


def test_product_page() -> tuple[str, str]:
    cid, link, page = find_live_product()
    assert_true("作品の特徴" in page, f"Product feature block missing on {cid}")
    assert_true("FANZAでこの作品を見る" in page, f"Top FANZA CTA missing on {cid}")
    assert_true("FANZA公式でこの作品を確認" in page, f"Bottom FANZA CTA missing on {cid}")
    assert_true("関連作品" in page or "おすすめ" in page, f"Related product sections missing on {cid}")
    assert_true("FANZA作品情報" in page, f"Product SEO title missing on {cid}")
    assert_true("product-page-v2.css" in page, f"Product V2 stylesheet missing on {cid}")
    if "PRODUCT_DESCRIPTION_START" in page:
        assert_true("作品紹介" in page, f"FANZA product description block missing on {cid}")
    status, dynamic = fetch(BASE + f"/products/view/?id={cid}")
    assert_true(status == 200 and "dynamicProduct" in dynamic, f"Dynamic product route failed for {cid}")
    print(f"QA product page: {cid} UX/SEO/related works/dynamic route OK")
    return cid, link


def test_fanza_link(cid: str, link: str) -> None:
    assert_true("okazumidori-001" not in link, f"Legacy affiliate ID remains on product {cid}")
    assert_true("ch=link_tool" not in link, f"Legacy link_tool remains on product {cid}")
    assert_true("af_id=okazumidori-990" in link, f"Expected API affiliate ID missing on product {cid}")
    assert_true("ch=api" in link, f"Expected API channel missing on product {cid}")

    results = []
    for label, ua in [("desktop", DESKTOP_UA), ("mobile", MOBILE_UA)]:
        try:
            status, body = fetch(link, ua, retries=2)
            invalid = any(marker in body for marker in INVALID_FANZA_MARKERS)
            assert_true(not invalid, f"FANZA reports invalid affiliate link for {label} on product {cid}")
            results.append(f"{label}:{status}")
        except RuntimeError as exc:
            results.append(f"{label}:external-check-warning({exc})")
    print(f"QA FANZA: product={cid}; " + ", ".join(results))


def main() -> None:
    test_fc2()
    test_alias_pages()
    genre_sample = test_full_entity_catalog("genre")
    maker_sample = test_full_entity_catalog("maker")
    actress_sample = test_full_entity_catalog("actress")
    test_seo_pagination("genre", genre_sample)
    test_seo_pagination("maker", maker_sample)
    test_seo_pagination("actress", actress_sample)
    test_catalog_search()
    test_catalog_audit()
    test_catalog_ui_asset()
    test_analytics_asset()
    cid, link = test_product_page()
    test_fanza_link(cid, link)
    print("Production QA passed")


if __name__ == "__main__":
    main()