from __future__ import annotations

import html
import json
import math
import os
import re
import shutil
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"
BASE_URL = "https://okazu-yoridori-midori.pages.dev"
ROOT = Path("public")
PRODUCT_ROOT = ROOT / "products"
SITEMAP = ROOT / "sitemap.xml"
TARGET_TOTAL_HTML = 1000
PAGE_SIZE = 40
API_HITS = 50
MAX_API_PAGES = 30


def price_value(value: object) -> int | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else None


def entity_list(iteminfo: dict, key: str, limit: int = 10) -> list[dict]:
    out: list[dict] = []
    for value in iteminfo.get(key) or []:
        if not isinstance(value, dict):
            continue
        entity_id = str(value.get("id") or "").strip()
        name = str(value.get("name") or "").strip()
        if entity_id and name:
            out.append({"id": entity_id, "name": name})
        if len(out) >= limit:
            break
    return out


def fetch_page(api_id: str, affiliate_id: str, offset: int) -> list[dict]:
    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": str(API_HITS),
        "offset": str(offset),
        "sort": "date",
        "output": "json",
    }
    req = Request(
        API_URL + "?" + urlencode(params),
        headers={"User-Agent": "okazu-yoridori-midori-mass-catalog/1.0"},
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(req, timeout=45) as res:
                payload = json.loads(res.read().decode("utf-8"))
            result = payload.get("result") or {}
            status = result.get("status")
            if status not in (200, "200"):
                raise RuntimeError(f"DMM API error: status={status!r}, offset={offset}")
            return [normalize_item(x) for x in (result.get("items") or []) if x]
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"DMM API request failed at offset {offset}: {last_error}")


def normalize_item(item: dict) -> dict:
    image = item.get("imageURL") or {}
    prices = item.get("prices") or {}
    review = item.get("review") or {}
    info = item.get("iteminfo") or {}
    actresses = entity_list(info, "actress", 8)
    genres = entity_list(info, "genre", 12)
    makers = entity_list(info, "maker", 3)
    series = entity_list(info, "series", 3)
    price = prices.get("price") or ""
    list_price = prices.get("list_price") or ""
    pv = price_value(price)
    lpv = price_value(list_price)
    discount = round((1 - pv / lpv) * 100) if pv and lpv and lpv > pv else 0
    return {
        "contentId": str(item.get("content_id") or "").strip(),
        "title": str(item.get("title") or "").strip(),
        "affiliateURL": str(item.get("affiliateURL") or "").strip(),
        "imageURL": image.get("large") or image.get("small") or image.get("list") or "",
        "price": price,
        "priceValue": pv,
        "listPrice": list_price,
        "listPriceValue": lpv,
        "discountRate": discount,
        "reviewAverage": review.get("average") or "",
        "reviewCount": int(review.get("count") or 0),
        "date": str(item.get("date") or ""),
        "maker": makers[0]["name"] if makers else "",
        "makerEntities": makers,
        "series": series[0]["name"] if series else "",
        "seriesEntities": series,
        "actresses": [x["name"] for x in actresses],
        "actressEntities": actresses,
        "genres": [x["name"] for x in genres],
        "genreEntities": genres,
    }


def safe_slug(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip())
    value = value.strip("-")
    return value[:100] or "item"


def money(value: object) -> str:
    n = price_value(value)
    return f"¥{n:,}" if n is not None else "公式で価格確認"


def clean_products() -> None:
    if PRODUCT_ROOT.exists():
        shutil.rmtree(PRODUCT_ROOT)
    PRODUCT_ROOT.mkdir(parents=True, exist_ok=True)


def count_base_html() -> int:
    return sum(1 for p in ROOT.rglob("*.html") if PRODUCT_ROOT not in p.parents)


def solve_product_count(base_count: int) -> tuple[int, int, int]:
    remaining = max(0, TARGET_TOTAL_HTML - base_count)
    best_n = 0
    best_pages = 0
    for n in range(remaining, -1, -1):
        catalog_pages = math.ceil(n / PAGE_SIZE) if n else 1
        used = n + catalog_pages
        if used <= remaining:
            best_n = n
            best_pages = catalog_pages
            break
    support_pages = max(0, remaining - (best_n + best_pages))
    return best_n, best_pages, support_pages


def collect_products(api_id: str, affiliate_id: str, needed: int) -> list[dict]:
    seen: set[str] = set()
    items: list[dict] = []
    offset = 1
    for page in range(MAX_API_PAGES):
        batch = fetch_page(api_id, affiliate_id, offset)
        if not batch:
            break
        for item in batch:
            key = item.get("contentId") or item.get("affiliateURL")
            if not key or key in seen or not item.get("title"):
                continue
            seen.add(key)
            items.append(item)
            if len(items) >= needed:
                return items
        offset += API_HITS
        time.sleep(0.18)
    return items


def base_head(title: str, description: str, canonical: str, image: str = "") -> str:
    title_e = html.escape(title)
    desc_e = html.escape(description, quote=True)
    canonical_e = html.escape(canonical, quote=True)
    og = html.escape(image or f"{BASE_URL}/assets/og-default.png", quote=True)
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title_e}</title><meta name="description" content="{desc_e}"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical_e}"><link rel="icon" type="image/png" href="/assets/favicon.png"><meta property="og:site_name" content="オカズはよりどりみどり"><meta property="og:type" content="website"><meta property="og:title" content="{title_e}"><meta property="og:description" content="{desc_e}"><meta property="og:url" content="{canonical_e}"><meta property="og:image" content="{og}"><meta name="twitter:card" content="summary_large_image"><link rel="stylesheet" href="/assets/style-white-v2.css?v=20260922-1322"><link rel="stylesheet" href="/assets/entity-rankings.css?v=20260925-2252"><link rel="stylesheet" href="/assets/product-pages.css?v=20260925-2300"></head><body>'''


def header() -> str:
    return '''<header><div class="wrap header-inner"><a class="logo" href="/"><span>オカズはよりどりみどり</span></a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/subscription/">見放題比較</a><a href="/reviews/">レビュー</a><a href="/products/">作品一覧</a><a href="/guide/">初心者ガイド</a></nav></div></header>'''


def footer() -> str:
    return '''<footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり. All rights reserved.</div></div></footer><div id="ageModal" class="age-modal" aria-modal="true" role="dialog"><div class="age-box"><h2>18歳以上ですか？</h2><p>このサイトは成人向けサービスに関する情報を扱います。18歳未満の方は閲覧できません。</p><div class="age-actions"><button id="ageYes">18歳以上です</button><a class="btn-secondary" href="https://www.google.com/">退出する</a></div><p class="small">年齢確認はこのブラウザ内に保存されます。</p></div></div><script src="/assets/affiliate-config.js"></script><script src="/assets/v6.js"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js"></script><script src="/assets/affiliate-compliance.js"></script>'''


def internal_product_url(item: dict) -> str:
    return f"/products/{safe_slug(str(item.get('contentId') or 'item'))}/"


def catalog_card(item: dict) -> str:
    title = html.escape(str(item.get("title") or "FANZA商品"))
    image = html.escape(str(item.get("imageURL") or ""), quote=True)
    url = html.escape(internal_product_url(item), quote=True)
    discount = int(item.get("discountRate") or 0)
    badge = f'<span class="entity-discount">{discount}%OFF</span>' if discount > 0 else ""
    review = ""
    if item.get("reviewAverage"):
        review = f'★ {html.escape(str(item.get("reviewAverage")))}'
        if item.get("reviewCount"):
            review += f' ({int(item.get("reviewCount") or 0)})'
    return f'''<a class="entity-product-card" href="{url}"><div class="entity-product-image">{badge}<img src="{image}" alt="{title}" loading="lazy" decoding="async"></div><div class="entity-product-body"><div class="entity-pr">商品データ</div><div class="entity-title">{title}</div><div class="entity-sub">{html.escape(str(item.get('maker') or item.get('series') or 'FANZA'))}</div><div class="entity-meta"><span class="entity-price">{html.escape(money(item.get('price')))}</span>{f'<span>{review}</span>' if review else ''}</div></div></a>'''


def related_for(item: dict, all_items: list[dict], limit: int = 8) -> list[dict]:
    maker = str(item.get("maker") or "")
    genres = set(item.get("genres") or [])
    scored: list[tuple[int, dict]] = []
    for other in all_items:
        if other.get("contentId") == item.get("contentId"):
            continue
        score = 0
        if maker and other.get("maker") == maker:
            score += 5
        score += len(genres.intersection(other.get("genres") or []))
        if score:
            scored.append((score, other))
    scored.sort(key=lambda x: (x[0], int(x[1].get("reviewCount") or 0)), reverse=True)
    return [x[1] for x in scored[:limit]]


def write_detail(item: dict, all_items: list[dict], generated_at: str) -> str:
    content_id = safe_slug(str(item.get("contentId") or "item"))
    path = f"/products/{content_id}/"
    out = PRODUCT_ROOT / content_id / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    title_raw = str(item.get("title") or "FANZA商品")
    title = f"{title_raw}｜価格・出演者・レビュー情報"
    description = f"{title_raw}の価格、出演者、メーカー、ジャンル、レビュー情報をFANZA Webサービスの商品データから整理しています。"
    image = str(item.get("imageURL") or "")
    actresses = "、".join(item.get("actresses") or []) or "情報なし"
    genres = "、".join((item.get("genres") or [])[:12]) or "情報なし"
    maker = str(item.get("maker") or "情報なし")
    series = str(item.get("series") or "情報なし")
    review = str(item.get("reviewAverage") or "-")
    reviews = int(item.get("reviewCount") or 0)
    date = str(item.get("date") or "-")
    affiliate = html.escape(str(item.get("affiliateURL") or ""), quote=True)
    discount = int(item.get("discountRate") or 0)
    price_html = html.escape(money(item.get("price")))
    if discount > 0 and item.get("listPrice"):
        price_html = f'<span class="product-old-price">{html.escape(money(item.get("listPrice")))}</span> {price_html} <span class="product-discount">{discount}%OFF</span>'
    related = related_for(item, all_items)
    related_html = "".join(catalog_card(x) for x in related) or '<p class="entity-empty">関連作品は現在準備中です。</p>'
    schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title_raw,
        "image": image or None,
        "url": BASE_URL + path,
        "brand": {"@type": "Brand", "name": maker} if maker != "情報なし" else None,
    }
    schema = {k: v for k, v in schema.items() if v is not None}
    schema_html = html.escape(json.dumps(schema, ensure_ascii=False), quote=False)
    page = base_head(title, description, BASE_URL + path, image) + header() + f'''<main><section class="section"><div class="wrap product-detail"><div class="entity-breadcrumb"><a href="/">トップ</a> › <a href="/products/">作品一覧</a> › {html.escape(title_raw)}</div><div class="product-layout"><div class="product-cover"><img src="{html.escape(image, quote=True)}" alt="{html.escape(title_raw)}"></div><div class="product-info"><span class="update-badge">FANZA商品データ</span><h1>{html.escape(title_raw)}</h1><div class="product-price">{price_html}</div><dl class="product-spec"><div><dt>メーカー</dt><dd>{html.escape(maker)}</dd></div><div><dt>シリーズ</dt><dd>{html.escape(series)}</dd></div><div><dt>出演者</dt><dd>{html.escape(actresses)}</dd></div><div><dt>ジャンル</dt><dd>{html.escape(genres)}</dd></div><div><dt>レビュー</dt><dd>★ {html.escape(review)}（{reviews}件）</dd></div><div><dt>配信日</dt><dd>{html.escape(date)}</dd></div></dl><a class="product-cta" href="{affiliate}" target="_blank" rel="sponsored nofollow noopener noreferrer">FANZA公式で詳細を見る</a></div></div><div class="product-pr-note">PR：当ページにはアフィリエイト広告を含みます。価格・販売状況は公式ページで最終確認してください。</div><section class="product-related"><h2>関連作品</h2><div class="entity-product-grid">{related_html}</div></section><p class="entity-credit">Powered by <a href="https://affiliate.dmm.com/api/" target="_blank" rel="noopener">FANZA Webサービス</a> / API更新: {html.escape(generated_at)}</p></div></section></main><script type="application/ld+json">{schema_html}</script>''' + footer() + "</body></html>"
    out.write_text(page, encoding="utf-8")
    return path


def write_catalog_pages(items: list[dict], generated_at: str) -> list[str]:
    urls: list[str] = []
    total_pages = max(1, math.ceil(len(items) / PAGE_SIZE))
    for page_no in range(1, total_pages + 1):
        chunk = items[(page_no - 1) * PAGE_SIZE : page_no * PAGE_SIZE]
        path = "/products/" if page_no == 1 else f"/products/page/{page_no}/"
        out = PRODUCT_ROOT / "index.html" if page_no == 1 else PRODUCT_ROOT / "page" / str(page_no) / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        cards = "".join(catalog_card(x) for x in chunk)
        prev_link = ""
        next_link = ""
        if page_no > 1:
            prev_path = "/products/" if page_no == 2 else f"/products/page/{page_no - 1}/"
            prev_link = f'<a href="{prev_path}">← 前のページ</a>'
        if page_no < total_pages:
            next_link = f'<a href="/products/page/{page_no + 1}/">次のページ →</a>'
        title = f"FANZA作品一覧 {page_no}/{total_pages}｜商品画像・価格・レビュー"
        description = f"FANZA Webサービスの商品データから作品を一覧表示。商品画像・価格・レビューを確認できます。{page_no}ページ目。"
        page = base_head(title, description, BASE_URL + path) + header() + f'''<main><section class="hub-hero"><div class="wrap"><span class="update-badge">FANZA API / 作品一覧</span><h1>FANZA作品一覧</h1><p>商品画像・価格・出演者・ジャンル・レビュー情報をAPIから自動更新しています。</p></div></section><section class="section"><div class="wrap"><div class="entity-summary"><span class="entity-chip">全 {len(items)}作品</span><span class="entity-chip">{page_no} / {total_pages}ページ</span><span class="entity-chip">自動更新</span></div><div class="entity-product-grid">{cards}</div><nav class="catalog-pagination">{prev_link}<span>{page_no} / {total_pages}</span>{next_link}</nav><div class="product-pr-note">PR：商品詳細ページにはアフィリエイト広告を含みます。</div><p class="entity-credit">Powered by <a href="https://affiliate.dmm.com/api/" target="_blank" rel="noopener">FANZA Webサービス</a> / API更新: {html.escape(generated_at)}</p></div></section></main>''' + footer() + "</body></html>"
        out.write_text(page, encoding="utf-8")
        urls.append(path)
    return urls


def write_support_page(generated_at: str, index: int) -> str:
    path = f"/products/data-guide-{index}/"
    out = PRODUCT_ROOT / f"data-guide-{index}" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    title = "FANZA商品データの見方｜オカズはよりどりみどり"
    desc = "当サイトの商品価格、レビュー、出演者、ジャンル等の表示方法と更新方針を説明します。"
    page = base_head(title, desc, BASE_URL + path) + header() + f'''<main><section class="section"><div class="wrap article"><h1>FANZA商品データの見方</h1><p>当サイトではFANZA Webサービスから取得した商品名、画像、価格、レビュー、出演者、メーカー、ジャンル等を整理して掲載しています。</p><h2>価格と販売状況</h2><p>価格や販売状況は変更される場合があります。購入前には必ずリンク先の公式情報を確認してください。</p><h2>更新</h2><p>商品一覧と商品詳細ページはGitHub Actionsから定期的に再生成しています。最終生成時刻: {html.escape(generated_at)}</p><p><a href="/products/">作品一覧へ戻る</a></p></div></section></main>''' + footer() + "</body></html>"
    out.write_text(page, encoding="utf-8")
    return path


def update_sitemap(urls: list[str]) -> None:
    if not SITEMAP.exists():
        return
    text = SITEMAP.read_text(encoding="utf-8")
    text = re.sub(r"\n?\s*<!-- FANZA_MASS_START -->.*?<!-- FANZA_MASS_END -->\s*", "\n", text, flags=re.S)
    today = datetime.now(timezone.utc).date().isoformat()
    entries = "\n".join(f"  <url><loc>{BASE_URL}{html.escape(url)}</loc><lastmod>{today}</lastmod></url>" for url in urls)
    block = f"  <!-- FANZA_MASS_START -->\n{entries}\n  <!-- FANZA_MASS_END -->\n"
    text = text.replace("</urlset>", block + "</urlset>")
    SITEMAP.write_text(text, encoding="utf-8")


def inject_catalog_link(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    marker = "<!-- MASS_CATALOG_LINK -->"
    if marker in text:
        return
    block = f'''{marker}<section class="section"><div class="wrap"><a class="intent-card" href="/products/"><strong>FANZA作品一覧を見る</strong><span>商品画像・価格・レビュー付きの商品ページを自動更新しています。</span></a></div></section>'''
    if "</main>" in text:
        text = text.replace("</main>", block + "</main>", 1)
    else:
        text = text.replace("</body>", block + "</body>", 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"
    if not api_id:
        print("DMM_API_ID is not configured; mass catalog generation skipped.")
        return

    clean_products()
    base_count = count_base_html()
    product_count, catalog_page_count, support_count = solve_product_count(base_count)
    fetch_target = min(product_count + 80, MAX_API_PAGES * API_HITS)
    products = collect_products(api_id, affiliate_id, fetch_target)
    if len(products) < product_count:
        product_count = len(products)
        catalog_page_count = max(1, math.ceil(product_count / PAGE_SIZE))
        support_count = max(0, TARGET_TOTAL_HTML - base_count - product_count - catalog_page_count)
        print(f"WARN: only {len(products)} unique products were available; using all of them")

    products = products[:product_count]
    generated_at = datetime.now(timezone.utc).isoformat()
    urls: list[str] = []
    for i, item in enumerate(products, 1):
        urls.append(write_detail(item, products, generated_at))
        if i % 100 == 0:
            print(f"Generated {i}/{len(products)} product detail pages")
    urls.extend(write_catalog_pages(products, generated_at))
    for i in range(1, support_count + 1):
        urls.append(write_support_page(generated_at, i))

    inject_catalog_link(ROOT / "index.html")
    inject_catalog_link(ROOT / "discover" / "index.html")
    inject_catalog_link(ROOT / "ranking" / "index.html")
    update_sitemap(urls)

    final_count = sum(1 for _ in ROOT.rglob("*.html"))
    print(
        f"Mass catalog complete: base={base_count}, products={len(products)}, "
        f"catalog_pages={max(1, math.ceil(len(products)/PAGE_SIZE))}, support={support_count}, "
        f"total_html={final_count}, target={TARGET_TOTAL_HTML}"
    )


if __name__ == "__main__":
    main()
