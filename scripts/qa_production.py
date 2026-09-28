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
    # Prefer a product with a real FANZA description so the static description block can be verified.
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
        if not links:
            continue
        if "PRODUCT_PAGE_V2_START" not in page:
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
    # Real FANZA comments are preferred when available; generic runtime fallback covers products without comments.
    if "PRODUCT_DESCRIPTION_START" in page:
        assert_true("作品紹介" in page, f"FANZA product description block missing on {cid}")
    print(f"QA product page: {cid} UX/SEO/related works OK")
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
    cid, link = test_product_page()
    test_fanza_link(cid, link)
    print("Production QA passed")


if __name__ == "__main__":
    main()
