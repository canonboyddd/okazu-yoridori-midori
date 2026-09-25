from __future__ import annotations

import html
import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"
OUTPUT = Path("public/data/fanza-products.json")
ENTITY_OUTPUT = Path("public/data/fanza-entity-rankings.json")
SITEMAP = Path("public/sitemap.xml")
BASE_URL = "https://okazu-yoridori-midori.pages.dev"
ENTITY_LIMIT = 10
ENTITY_HITS = 20

ENTITY_CONFIG = {
    "actress": {"label": "女優", "article": "actress", "field": "actressEntities"},
    "genre": {"label": "ジャンル", "article": "genre", "field": "genreEntities"},
    "maker": {"label": "メーカー", "article": "maker", "field": "makerEntities"},
}


def _entities(iteminfo: dict, key: str, limit: int = 8) -> list[dict]:
    values = iteminfo.get(key) or []
    out: list[dict] = []
    for value in values:
        if isinstance(value, dict):
            entity_id = str(value.get("id") or "").strip()
            name = str(value.get("name") or "").strip()
            if entity_id and name:
                out.append({"id": entity_id, "name": name})
        if len(out) >= limit:
            break
    return out


def _names(entities: list[dict]) -> list[str]:
    return [str(x.get("name") or "") for x in entities if x.get("name")]


def _price_value(value: object) -> int | None:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def fetch_items(
    api_id: str,
    affiliate_id: str,
    sort: str,
    hits: int = 50,
    article: str | None = None,
    article_id: str | None = None,
) -> list[dict]:
    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": str(hits),
        "offset": "1",
        "sort": sort,
        "output": "json",
    }
    if article and article_id:
        params["article"] = article
        params["article_id"] = article_id

    req = Request(
        API_URL + "?" + urlencode(params),
        headers={"User-Agent": "okazu-yoridori-midori/4.0"},
    )
    with urlopen(req, timeout=30) as res:
        payload = json.loads(res.read().decode("utf-8"))

    result = payload.get("result") or {}
    status = result.get("status")
    if status not in (200, "200"):
        raise RuntimeError(f"DMM API error: status={status!r}, article={article!r}, article_id={article_id!r}")

    normalized: list[dict] = []
    for item in result.get("items") or []:
        image = item.get("imageURL") or {}
        prices = item.get("prices") or {}
        review = item.get("review") or {}
        iteminfo = item.get("iteminfo") or {}
        affiliate_url = item.get("affiliateURL") or ""
        if not affiliate_url:
            continue

        price = prices.get("price") or ""
        list_price = prices.get("list_price") or ""
        price_value = _price_value(price)
        list_price_value = _price_value(list_price)
        discount_rate = None
        if price_value and list_price_value and list_price_value > price_value:
            discount_rate = round((1 - price_value / list_price_value) * 100)

        actresses = _entities(iteminfo, "actress", 6)
        genres = _entities(iteminfo, "genre", 8)
        makers = _entities(iteminfo, "maker", 3)
        series = _entities(iteminfo, "series", 3)

        normalized.append(
            {
                "contentId": item.get("content_id") or "",
                "title": item.get("title") or "",
                "affiliateURL": affiliate_url,
                "imageURL": image.get("large") or image.get("small") or image.get("list") or "",
                "price": price,
                "priceValue": price_value,
                "listPrice": list_price,
                "listPriceValue": list_price_value,
                "discountRate": discount_rate,
                "reviewAverage": review.get("average") or "",
                "reviewCount": review.get("count") or 0,
                "date": item.get("date") or "",
                "maker": _names(makers)[0] if makers else "",
                "makerEntities": makers,
                "series": _names(series)[0] if series else "",
                "seriesEntities": series,
                "actresses": _names(actresses),
                "actressEntities": actresses,
                "genres": _names(genres),
                "genreEntities": genres,
            }
        )
    return normalized


def _dedupe(*groups: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for group in groups:
        for item in group:
            key = str(item.get("contentId") or item.get("affiliateURL") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _entity_candidates(ranking: list[dict], latest: list[dict], field: str, limit: int) -> list[dict]:
    stats: dict[str, dict] = defaultdict(lambda: {"name": "", "score": 0, "appearances": 0})
    for pos, item in enumerate(ranking, 1):
        weight = max(1, 70 - pos)
        for entity in item.get(field) or []:
            entity_id = str(entity.get("id") or "")
            name = str(entity.get("name") or "")
            if not entity_id or not name:
                continue
            row = stats[entity_id]
            row["name"] = name
            row["score"] += weight
            row["appearances"] += 1
    for item in latest:
        for entity in item.get(field) or []:
            entity_id = str(entity.get("id") or "")
            name = str(entity.get("name") or "")
            if not entity_id or not name:
                continue
            row = stats[entity_id]
            row["name"] = name
            row["score"] += 3
            row["appearances"] += 1

    rows = [
        {"id": entity_id, **data}
        for entity_id, data in stats.items()
        if data.get("name")
    ]
    rows.sort(key=lambda x: (int(x.get("score") or 0), int(x.get("appearances") or 0)), reverse=True)
    return rows[:limit]


def _build_entity_groups(api_id: str, affiliate_id: str, ranking: list[dict], latest: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for entity_type, cfg in ENTITY_CONFIG.items():
        candidates = _entity_candidates(ranking, latest, cfg["field"], ENTITY_LIMIT)
        results: list[dict] = []
        for candidate in candidates:
            try:
                items = fetch_items(
                    api_id,
                    affiliate_id,
                    "rank",
                    ENTITY_HITS,
                    cfg["article"],
                    str(candidate["id"]),
                )
            except Exception as exc:
                print(f"WARN: {entity_type} {candidate['name']} ({candidate['id']}): {exc}")
                continue
            if not items:
                continue
            results.append({**candidate, "items": items, "itemCount": len(items)})
            time.sleep(0.15)
        groups[entity_type] = results
        print(f"Built {len(results)} {entity_type} ranking pages")
    return groups


def _yen(value: object) -> str:
    n = _price_value(value)
    return f"¥{n:,}" if n is not None else "公式で価格確認"


def _product_card(item: dict, index: int, target_prefix: str) -> str:
    title = html.escape(str(item.get("title") or "FANZA商品"))
    url = html.escape(str(item.get("affiliateURL") or ""), quote=True)
    image_url = html.escape(str(item.get("imageURL") or ""), quote=True)
    rank_class = f" r{index}" if index <= 3 else ""
    discount = int(item.get("discountRate") or 0)
    discount_html = f'<span class="entity-discount">{discount}%OFF</span>' if discount > 0 else ""
    image_html = f'<img src="{image_url}" alt="{title}" loading="lazy" decoding="async">' if image_url else ""

    old_price = ""
    if discount > 0 and item.get("listPrice"):
        old_price = f'<span class="entity-old-price">{html.escape(_yen(item.get("listPrice")))}</span>'
    price_html = old_price + html.escape(_yen(item.get("price")))

    review_html = ""
    if item.get("reviewAverage"):
        review_html = f'★ <strong>{html.escape(str(item.get("reviewAverage")))}</strong>'
        if item.get("reviewCount"):
            review_html += f' ({int(item.get("reviewCount") or 0)})'

    sub_parts = [str(item.get("maker") or "")] + [str(x) for x in (item.get("actresses") or [])[:2]]
    sub = html.escape(" / ".join(x for x in sub_parts if x) or str(item.get("series") or ""))

    return f'''<a class="entity-product-card" href="{url}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate-target="{html.escape(target_prefix)}-{index}">
<div class="entity-product-image"><span class="entity-rank{rank_class}">{index}位</span>{discount_html}{image_html}</div>
<div class="entity-product-body"><div class="entity-pr">PR / 広告</div><div class="entity-title">{title}</div>{f'<div class="entity-sub">{sub}</div>' if sub else ''}<div class="entity-meta"><span class="entity-price">{price_html}</span>{f'<span>{review_html}</span>' if review_html else ''}</div></div></a>'''


def _header() -> str:
    return '''<header><div class="wrap header-inner"><a class="logo" href="/"><span>オカズはよりどりみどり</span></a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/subscription/">見放題比較</a><a href="/reviews/">レビュー</a><a href="/discover/">探す</a><a href="/guide/">初心者ガイド</a></nav></div></header>'''


def _footer() -> str:
    return '''<footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり. All rights reserved.</div></div></footer><div id="ageModal" class="age-modal" aria-modal="true" role="dialog"><div class="age-box"><h2>18歳以上ですか？</h2><p>このサイトは成人向けサービスに関する情報を扱います。18歳未満の方は閲覧できません。</p><div class="age-actions"><button id="ageYes">18歳以上です</button><a class="btn-secondary" href="https://www.google.com/">退出する</a></div><p class="small">年齢確認はこのブラウザ内に保存されます。</p></div></div><script src="/assets/affiliate-config.js"></script><script src="/assets/v6.js"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js"></script><script src="/assets/affiliate-compliance.js"></script>'''


def _page_head(title: str, description: str, canonical: str) -> str:
    title_e = html.escape(title)
    desc_e = html.escape(description, quote=True)
    canonical_e = html.escape(canonical, quote=True)
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": "オカズはよりどりみどり", "url": BASE_URL + "/"},
    }, ensure_ascii=False)
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title_e}</title><meta name="description" content="{desc_e}"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical_e}"><link rel="icon" type="image/png" href="/assets/favicon.png"><meta property="og:site_name" content="オカズはよりどりみどり"><meta property="og:type" content="website"><meta property="og:title" content="{title_e}"><meta property="og:description" content="{desc_e}"><meta property="og:url" content="{canonical_e}"><meta property="og:image" content="{BASE_URL}/assets/og-default.png"><meta name="twitter:card" content="summary_large_image"><link rel="stylesheet" href="/assets/style-white-v2.css?v=20260922-1322"><link rel="stylesheet" href="/assets/entity-rankings.css?v=20260925-2200"><script type="application/ld+json">{schema}</script></head><body>'''


def _write_hub(entity_type: str, rows: list[dict], generated_at: str) -> list[str]:
    cfg = ENTITY_CONFIG[entity_type]
    label = cfg["label"]
    base_path = f"/ranking/{entity_type}/"
    title = f"FANZA {label}別ランキング | オカズはよりどりみどり"
    description = f"FANZA Webサービスの人気作品データをもとに、{label}別の人気作品ランキングを自動生成しています。"
    cards = []
    urls = [base_path]
    for i, row in enumerate(rows, 1):
        entity_id = html.escape(str(row["id"]), quote=True)
        name = html.escape(str(row["name"]))
        cards.append(f'<a class="entity-hub-card" href="{base_path}{entity_id}/"><div><strong>{name}</strong><span>人気順 {int(row.get("itemCount") or 0)}作品を掲載</span></div><div class="entity-hub-rank">{i}</div></a>')
        urls.append(f"{base_path}{row['id']}/")
    cards_html = "".join(cards) if cards else '<div class="entity-empty">現在表示できるランキングがありません。</div>'
    page = _page_head(title, description, BASE_URL + base_path) + _header() + f'''<main><section class="hub-hero"><div class="wrap"><span class="update-badge">FANZA API / {label}別</span><h1>{label}別 人気作品ランキング</h1><p>現在のFANZA人気作品から{label}を自動抽出し、それぞれの人気作品をAPIで再取得してランキング化しています。</p><div class="notice"><strong>集計方法：</strong>{label}自体の公式順位ではなく、当サイトがFANZAの商品APIデータから候補を抽出し、各{label}の作品を人気順で取得して掲載しています。</div></div></section><section class="section"><div class="wrap"><div class="entity-breadcrumb"><a href="/ranking/">ランキング</a> › {label}別</div><div class="entity-hub-grid">{cards_html}</div><div class="entity-api-note">商品画像・商品名・価格・レビュー等はFANZA Webサービスから取得しています。販売状況や価格は変動するため、最終確認は公式ページで行ってください。</div><p class="entity-credit">Powered by <a href="https://affiliate.dmm.com/api/" target="_blank" rel="noopener">FANZA Webサービス</a> / API更新: {html.escape(generated_at)}</p></div></section></main>''' + _footer() + "</body></html>"
    out = Path("public") / "ranking" / entity_type / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return urls


def _write_detail(entity_type: str, row: dict, generated_at: str) -> None:
    cfg = ENTITY_CONFIG[entity_type]
    label = cfg["label"]
    entity_id = str(row["id"])
    name = str(row["name"])
    path = f"/ranking/{entity_type}/{entity_id}/"
    title = f"{name}のFANZA人気作品ランキング | オカズはよりどりみどり"
    description = f"{name}のFANZA人気作品を商品画像・価格・レビュー付きでランキング表示。FANZA Webサービスから人気順に自動取得しています。"
    cards = "".join(_product_card(item, i, f"entity-{entity_type}-{entity_id}") for i, item in enumerate(row.get("items") or [], 1))
    if not cards:
        cards = '<div class="entity-empty">現在表示できる商品がありません。</div>'
    page = _page_head(title, description, BASE_URL + path) + _header() + f'''<main><section class="hub-hero"><div class="wrap"><span class="update-badge">FANZA API / {html.escape(label)}別</span><h1>{html.escape(name)} 人気作品ランキング</h1><p>{html.escape(name)}に該当するFANZA作品を人気順に自動取得し、商品画像・価格・レビュー情報と一緒に比較できます。</p><div class="notice"><strong>PRについて：</strong>このページにはアフィリエイト広告を含みます。順位・価格・販売状況は変動するため、リンク先の公式情報をご確認ください。</div></div></section><section class="section"><div class="wrap"><div class="entity-breadcrumb"><a href="/ranking/">ランキング</a> › <a href="/ranking/{entity_type}/">{html.escape(label)}別</a> › {html.escape(name)}</div><div class="entity-summary"><span class="entity-chip">掲載 {int(row.get("itemCount") or 0)}作品</span><span class="entity-chip">API人気順</span><span class="entity-chip">自動更新</span></div><div class="entity-product-grid">{cards}</div><div class="entity-api-note">このランキングはFANZA Webサービスの商品検索で「{html.escape(name)}」に該当する作品を人気順に取得して構成しています。{html.escape(label)}自体を評価・格付けするランキングではありません。</div><p class="entity-credit">Powered by <a href="https://affiliate.dmm.com/api/" target="_blank" rel="noopener">FANZA Webサービス</a> / API更新: {html.escape(generated_at)}</p><div class="entity-nav"><a href="/ranking/{entity_type}/"><b>{html.escape(label)}別ランキング一覧</b><span>ほかの{html.escape(label)}から探す</span></a><a href="/ranking/"><b>総合ランキング</b><span>人気・新着・高評価・セールから探す</span></a><a href="/discover/"><b>作品を探す</b><span>検索・ガイドから候補を絞る</span></a></div></div></section></main>''' + _footer() + "</body></html>"
    out = Path("public") / "ranking" / entity_type / entity_id / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")


def _write_entity_pages(groups: dict[str, list[dict]], generated_at: str) -> list[str]:
    urls: list[str] = []
    for entity_type, rows in groups.items():
        urls.extend(_write_hub(entity_type, rows, generated_at))
        for row in rows:
            _write_detail(entity_type, row, generated_at)
    return urls


def _update_sitemap(dynamic_urls: list[str]) -> None:
    if not SITEMAP.exists():
        return
    text = SITEMAP.read_text(encoding="utf-8")
    text = re.sub(r"\n?\s*<!-- FANZA_ENTITY_START -->.*?<!-- FANZA_ENTITY_END -->\s*", "\n", text, flags=re.S)
    today = datetime.now(timezone.utc).date().isoformat()
    entries = "\n".join(f"  <url><loc>{BASE_URL}{html.escape(url)}</loc><lastmod>{today}</lastmod></url>" for url in dynamic_urls)
    block = f"  <!-- FANZA_ENTITY_START -->\n{entries}\n  <!-- FANZA_ENTITY_END -->\n"
    text = text.replace("</urlset>", block + "</urlset>")
    SITEMAP.write_text(text, encoding="utf-8")


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"

    if not api_id:
        print("DMM_API_ID is not configured; FANZA API cache generation skipped.")
        return

    ranking = fetch_items(api_id, affiliate_id, "rank", 50)
    latest = fetch_items(api_id, affiliate_id, "date", 50)
    catalog = _dedupe(ranking, latest)

    high_rated = sorted(
        [x for x in catalog if float(x.get("reviewAverage") or 0) > 0],
        key=lambda x: (float(x.get("reviewAverage") or 0), int(x.get("reviewCount") or 0)),
        reverse=True,
    )
    deals = sorted(
        [x for x in catalog if int(x.get("discountRate") or 0) > 0],
        key=lambda x: (int(x.get("discountRate") or 0), int(x.get("reviewCount") or 0)),
        reverse=True,
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": generated_at,
        "affiliateId": affiliate_id,
        "ranking": ranking,
        "latest": latest,
        "highRated": high_rated[:50],
        "deals": deals[:50],
        "stats": {
            "rankingCount": len(ranking),
            "latestCount": len(latest),
            "highRatedCount": len(high_rated),
            "dealCount": len(deals),
        },
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    groups = _build_entity_groups(api_id, affiliate_id, ranking, latest)
    entity_payload = {
        "generatedAt": generated_at,
        "affiliateId": affiliate_id,
        "groups": groups,
    }
    ENTITY_OUTPUT.write_text(json.dumps(entity_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    dynamic_urls = _write_entity_pages(groups, generated_at)
    _update_sitemap(dynamic_urls)

    print(
        f"Wrote {OUTPUT} ({len(ranking)} ranking, {len(latest)} latest, "
        f"{len(high_rated)} highRated, {len(deals)} deals); "
        f"entity pages: {sum(len(v) for v in groups.values())} + {len(groups)} hubs"
    )


if __name__ == "__main__":
    main()
