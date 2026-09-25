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
DATA = ROOT / "data"
CATALOG_DIR = DATA / "catalog"
PRODUCT_ROOT = ROOT / "products"
ACTRESS_ROOT = ROOT / "ranking" / "actress"
SITEMAP = ROOT / "sitemap.xml"

HITS = 100
SHARD_SIZE = 500
CATALOG_PAGE_SIZE = 60
ACTRESS_MIN_WORKS = 3
MAX_INDEXABLE_FILES = int(os.environ.get("MAX_INDEXABLE_FILES", "18000"))
REQUEST_DELAY = float(os.environ.get("DMM_REQUEST_DELAY", "0.12"))
MAX_PAGES = int(os.environ.get("DMM_FULL_CATALOG_MAX_PAGES", "0"))  # 0 = APIが空になるまで


def yen(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return f"¥{int(digits):,}" if digits else "公式で確認"


def price_num(value: object) -> int | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else None


def entities(info: dict, key: str, limit: int = 20) -> list[dict]:
    out = []
    for row in info.get(key) or []:
        if not isinstance(row, dict):
            continue
        i = str(row.get("id") or "").strip()
        n = str(row.get("name") or "").strip()
        if i and n:
            out.append({"id": i, "name": n})
        if len(out) >= limit:
            break
    return out


def normalize(item: dict) -> dict:
    info = item.get("iteminfo") or {}
    img = item.get("imageURL") or {}
    prices = item.get("prices") or {}
    review = item.get("review") or {}
    price = prices.get("price") or ""
    list_price = prices.get("list_price") or ""
    p = price_num(price)
    lp = price_num(list_price)
    discount = round((1 - p / lp) * 100) if p and lp and lp > p else 0
    actresses = entities(info, "actress", 20)
    genres = entities(info, "genre", 30)
    makers = entities(info, "maker", 5)
    series = entities(info, "series", 5)
    return {
        "contentId": str(item.get("content_id") or "").strip(),
        "title": str(item.get("title") or "").strip(),
        "affiliateURL": str(item.get("affiliateURL") or "").strip(),
        "imageURL": img.get("large") or img.get("small") or img.get("list") or "",
        "price": price,
        "priceValue": p,
        "listPrice": list_price,
        "listPriceValue": lp,
        "discountRate": discount,
        "reviewAverage": review.get("average") or "",
        "reviewCount": int(review.get("count") or 0),
        "date": str(item.get("date") or ""),
        "actressEntities": actresses,
        "genreEntities": genres,
        "makerEntities": makers,
        "seriesEntities": series,
        "actresses": [x["name"] for x in actresses],
        "genres": [x["name"] for x in genres],
        "maker": makers[0]["name"] if makers else "",
        "series": series[0]["name"] if series else "",
    }


def api_page(api_id: str, affiliate_id: str, offset: int) -> tuple[list[dict], int]:
    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": str(HITS),
        "offset": str(offset),
        "sort": "date",
        "output": "json",
    }
    req = Request(API_URL + "?" + urlencode(params), headers={"User-Agent": "okazu-full-catalog/1.0"})
    last = None
    for attempt in range(4):
        try:
            with urlopen(req, timeout=60) as res:
                payload = json.loads(res.read().decode("utf-8"))
            result = payload.get("result") or {}
            if result.get("status") not in (200, "200"):
                raise RuntimeError(f"API status={result.get('status')} offset={offset}")
            total = int(result.get("total_count") or result.get("totalCount") or 0)
            return [normalize(x) for x in (result.get("items") or []) if isinstance(x, dict)], total
        except Exception as exc:
            last = exc
            if attempt < 3:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"ItemList failed offset={offset}: {last}")


def collect_all(api_id: str, affiliate_id: str) -> tuple[list[dict], int]:
    seen = set()
    out = []
    offset = 1
    page_no = 0
    reported_total = 0
    while True:
        rows, total = api_page(api_id, affiliate_id, offset)
        reported_total = max(reported_total, total)
        if not rows:
            break
        new_count = 0
        for row in rows:
            key = row.get("contentId") or row.get("affiliateURL")
            if not key or not row.get("title") or key in seen:
                continue
            seen.add(key)
            out.append(row)
            new_count += 1
        page_no += 1
        print(f"Catalog API page={page_no} offset={offset} collected={len(out)} reported_total={reported_total}")
        if len(rows) < HITS or (reported_total and offset + HITS > reported_total):
            break
        if MAX_PAGES and page_no >= MAX_PAGES:
            print(f"Stopped by DMM_FULL_CATALOG_MAX_PAGES={MAX_PAGES}")
            break
        if new_count == 0:
            break
        offset += HITS
        time.sleep(REQUEST_DELAY)
    return out, reported_total


def safe_id(value: str) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip()).strip("-")
    return s[:120] or "item"


def head(title: str, desc: str, canonical: str, image: str = "", robots: str = "index,follow") -> str:
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc, quote=True)}"><meta name="robots" content="{robots}"><link rel="canonical" href="{html.escape(canonical, quote=True)}"><link rel="icon" type="image/png" href="/assets/favicon.png"><meta property="og:site_name" content="オカズはよりどりみどり"><meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:description" content="{html.escape(desc, quote=True)}"><meta property="og:url" content="{html.escape(canonical, quote=True)}"><meta property="og:image" content="{html.escape(image or BASE_URL + '/assets/og-default.png', quote=True)}"><link rel="stylesheet" href="/assets/style-white-v2.css?v=20260922-1322"><link rel="stylesheet" href="/assets/full-catalog.css?v=20260926-001"></head><body>'''


def header() -> str:
    return '''<header><div class="wrap header-inner"><a class="logo" href="/">オカズはよりどりみどり</a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/products/">作品一覧</a><a href="/search/">サイト内検索</a><a href="/guide/">初心者ガイド</a></nav></div></header>'''


def footer() -> str:
    return '''<footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり.</div></div></footer><div id="ageModal" class="age-modal" aria-modal="true" role="dialog"><div class="age-box"><h2>18歳以上ですか？</h2><p>このサイトは成人向けサービスに関する情報を扱います。18歳未満の方は閲覧できません。</p><div class="age-actions"><button id="ageYes">18歳以上です</button><a class="btn-secondary" href="https://www.google.com/">退出する</a></div></div></div><script src="/assets/affiliate-config.js"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js"></script><script src="/assets/affiliate-compliance.js"></script>'''


def card(item: dict, internal: bool = True) -> str:
    title = html.escape(str(item.get("title") or "FANZA作品"))
    image = html.escape(str(item.get("imageURL") or ""), quote=True)
    cid = safe_id(str(item.get("contentId") or ""))
    href = f"/products/{cid}/" if internal else str(item.get("affiliateURL") or "#")
    if internal and not (PRODUCT_ROOT / cid / "index.html").exists():
        href = f"/products/view/?id={html.escape(cid, quote=True)}"
    discount = int(item.get("discountRate") or 0)
    d = f'<span class="fc-discount">{discount}%OFF</span>' if discount else ""
    return f'''<a class="fc-card" href="{href}"><div class="fc-img">{d}<img src="{image}" alt="{title}" loading="lazy"></div><div class="fc-body"><strong>{title}</strong><span>{html.escape(str(item.get('maker') or 'FANZA'))}</span><b>{html.escape(yen(item.get('price')))}</b></div></a>'''


def write_shards(items: list[dict], generated_at: str, reported_total: int) -> None:
    if CATALOG_DIR.exists():
        shutil.rmtree(CATALOG_DIR)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    shards = []
    for i in range(0, len(items), SHARD_SIZE):
        chunk = items[i:i + SHARD_SIZE]
        name = f"catalog-{i // SHARD_SIZE + 1:04d}.json"
        (CATALOG_DIR / name).write_text(json.dumps(chunk, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        shards.append({"file": f"/data/catalog/{name}", "count": len(chunk)})
    (DATA / "full-catalog-manifest.json").write_text(json.dumps({"generatedAt": generated_at, "count": len(items), "reportedTotal": reported_total, "shards": shards}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def quality_score(item: dict) -> tuple:
    return (
        1 if item.get("imageURL") else 0,
        1 if item.get("actressEntities") else 0,
        int(item.get("reviewCount") or 0),
        float(item.get("reviewAverage") or 0) if str(item.get("reviewAverage") or "").replace(".", "", 1).isdigit() else 0,
        str(item.get("date") or ""),
    )


def write_product_pages(items: list[dict], file_budget: int) -> set[str]:
    if PRODUCT_ROOT.exists():
        for p in PRODUCT_ROOT.iterdir():
            if p.name not in {"view"}:
                if p.is_dir(): shutil.rmtree(p)
                elif p.is_file(): p.unlink()
    PRODUCT_ROOT.mkdir(parents=True, exist_ok=True)
    ranked = sorted(items, key=quality_score, reverse=True)
    selected = ranked[:max(0, file_budget)]
    static_ids = set()
    by_maker = defaultdict(list)
    by_genre = defaultdict(list)
    for item in items:
        for m in item.get("makerEntities") or []: by_maker[m["id"]].append(item)
        for g in item.get("genreEntities") or []: by_genre[g["id"]].append(item)
    for item in selected:
        cid = safe_id(str(item.get("contentId") or ""))
        static_ids.add(cid)
        out = PRODUCT_ROOT / cid / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        title = str(item.get("title") or "FANZA作品")
        actresses = item.get("actressEntities") or []
        actress_html = "、".join(f'<a href="/ranking/actress/{html.escape(str(a["id"]), quote=True)}/">{html.escape(a["name"])}</a>' for a in actresses) or "情報なし"
        genres = item.get("genreEntities") or []
        genre_html = "、".join(f'<a href="/ranking/genre/{html.escape(str(g["id"]), quote=True)}/">{html.escape(g["name"])}</a>' for g in genres[:12]) or "情報なし"
        makers = item.get("makerEntities") or []
        maker_html = "、".join(f'<a href="/ranking/maker/{html.escape(str(m["id"]), quote=True)}/">{html.escape(m["name"])}</a>' for m in makers) or "情報なし"
        affiliate = html.escape(str(item.get("affiliateURL") or ""), quote=True)
        schema = json.dumps({"@context":"https://schema.org","@type":"Product","name":title,"image":item.get("imageURL") or None,"url":BASE_URL+f"/products/{cid}/"}, ensure_ascii=False)
        page = head(title + "｜作品情報", f"{title}の価格・出演者・メーカー・ジャンル・レビュー情報。", BASE_URL + f"/products/{cid}/", str(item.get("imageURL") or "")) + header() + f'''<main><section class="section"><div class="wrap"><div class="fc-breadcrumb"><a href="/">トップ</a> › <a href="/products/">作品一覧</a> › {html.escape(title)}</div><div class="fc-detail"><div><img class="fc-cover" src="{html.escape(str(item.get('imageURL') or ''), quote=True)}" alt="{html.escape(title)}"></div><div><h1>{html.escape(title)}</h1><div class="fc-price">{html.escape(yen(item.get('price')))} {f'<span>{int(item.get("discountRate") or 0)}%OFF</span>' if item.get('discountRate') else ''}</div><dl><dt>出演者</dt><dd>{actress_html}</dd><dt>メーカー</dt><dd>{maker_html}</dd><dt>ジャンル</dt><dd>{genre_html}</dd><dt>レビュー</dt><dd>★ {html.escape(str(item.get('reviewAverage') or '-'))}（{int(item.get('reviewCount') or 0)}件）</dd><dt>配信日</dt><dd>{html.escape(str(item.get('date') or '-'))}</dd></dl><a class="fc-cta" href="{affiliate}" target="_blank" rel="sponsored nofollow noopener noreferrer">FANZA公式で確認</a></div></div><p class="fc-pr">PR：当ページにはアフィリエイト広告を含みます。</p></div></section></main><script type="application/ld+json">{schema}</script>''' + footer() + "</body></html>"
        out.write_text(page, encoding="utf-8")
    return static_ids


def write_catalog_pages(items: list[dict], static_ids: set[str]) -> list[str]:
    pages = max(1, math.ceil(len(items) / CATALOG_PAGE_SIZE))
    urls = []
    for n in range(1, pages + 1):
        chunk = items[(n-1)*CATALOG_PAGE_SIZE:n*CATALOG_PAGE_SIZE]
        rows = []
        for it in chunk:
            cid = safe_id(str(it.get("contentId") or ""))
            href = f"/products/{cid}/" if cid in static_ids else f"/products/view/?id={cid}"
            copy = dict(it); copy["_href"] = href
            title = html.escape(str(it.get("title") or "")); image = html.escape(str(it.get("imageURL") or ""), quote=True)
            rows.append(f'<a class="fc-card" href="{href}"><div class="fc-img"><img src="{image}" alt="{title}" loading="lazy"></div><div class="fc-body"><strong>{title}</strong><span>{html.escape(str(it.get("maker") or "FANZA"))}</span><b>{html.escape(yen(it.get("price")))}</b></div></a>')
        path = "/products/" if n == 1 else f"/products/page/{n}/"
        out = PRODUCT_ROOT / "index.html" if n == 1 else PRODUCT_ROOT / "page" / str(n) / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        prev_link = "" if n == 1 else f'<a href="{ "/products/" if n == 2 else f"/products/page/{n-1}/" }">← 前へ</a>'
        next_link = "" if n == pages else f'<a href="/products/page/{n+1}/">次へ →</a>'
        page = head(f"FANZA作品一覧 {n}/{pages}", f"FANZA APIから取得した作品を一覧表示。現在{len(items):,}作品を収録。", BASE_URL + path) + header() + f'''<main><section class="hub-hero"><div class="wrap"><h1>FANZA作品一覧</h1><p>APIから取得できた {len(items):,} 作品を掲載しています。</p><a class="fc-search-link" href="/search/">作品・女優・メーカー・ジャンルを検索</a></div></section><section class="section"><div class="wrap"><div class="fc-grid">{''.join(rows)}</div><nav class="fc-pager">{prev_link}<span>{n} / {pages}</span>{next_link}</nav></div></section></main>''' + footer() + "</body></html>"
        out.write_text(page, encoding="utf-8")
        urls.append(path)
    return urls


def write_actress_pages(items: list[dict], directory: list[dict], remaining_budget: int) -> list[str]:
    meta = {str(x.get("id")): x for x in directory if x.get("id")}
    grouped = defaultdict(list)
    for item in items:
        for a in item.get("actressEntities") or []:
            grouped[str(a["id"])].append(item)
    candidates = [(aid, works) for aid, works in grouped.items() if len(works) >= ACTRESS_MIN_WORKS]
    candidates.sort(key=lambda x: len(x[1]), reverse=True)
    urls = []
    for aid, works in candidates[:max(0, remaining_budget)]:
        row = meta.get(aid, {})
        name = str(row.get("name") or next((a["name"] for a in works[0].get("actressEntities") or [] if str(a["id"]) == aid), aid))
        ruby = str(row.get("ruby") or "")
        image = str(row.get("imageURL") or "")
        popular = sorted(works, key=lambda x: (int(x.get("reviewCount") or 0), float(x.get("reviewAverage") or 0) if str(x.get("reviewAverage") or "").replace(".","",1).isdigit() else 0), reverse=True)
        latest = sorted(works, key=lambda x: str(x.get("date") or ""), reverse=True)
        rated = sorted(works, key=lambda x: (float(x.get("reviewAverage") or 0) if str(x.get("reviewAverage") or "").replace(".","",1).isdigit() else 0, int(x.get("reviewCount") or 0)), reverse=True)
        genre_counts = defaultdict(int); maker_counts = defaultdict(int)
        for w in works:
            for g in w.get("genreEntities") or []: genre_counts[(g["id"], g["name"])] += 1
            for m in w.get("makerEntities") or []: maker_counts[(m["id"], m["name"])] += 1
        genre_links = " ".join(f'<a class="fc-chip" href="/ranking/genre/{gid}/">{html.escape(gn)} ({c})</a>' for (gid,gn),c in sorted(genre_counts.items(), key=lambda x:x[1], reverse=True)[:12])
        maker_links = " ".join(f'<a class="fc-chip" href="/ranking/maker/{mid}/">{html.escape(mn)} ({c})</a>' for (mid,mn),c in sorted(maker_counts.items(), key=lambda x:x[1], reverse=True)[:10])
        def cards(seq): return "".join(card(x) for x in seq)
        path = f"/ranking/actress/{aid}/"
        out = ACTRESS_ROOT / aid / "index.html"; out.parent.mkdir(parents=True, exist_ok=True)
        profile = f'<img class="fc-actress-photo" src="{html.escape(image, quote=True)}" alt="{html.escape(name)}">' if image else ""
        schema = json.dumps({"@context":"https://schema.org","@type":"ProfilePage","name":name,"url":BASE_URL+path}, ensure_ascii=False)
        page = head(f"{name} 出演作品一覧・人気順・新着順", f"{name}のFANZA出演作品{len(works)}件を人気順・新着順・評価順で掲載。", BASE_URL+path, image) + header() + f'''<main><section class="section"><div class="wrap"><div class="fc-breadcrumb"><a href="/">トップ</a> › <a href="/ranking/actress/">女優</a> › {html.escape(name)}</div><div class="fc-actress-head">{profile}<div><h1>{html.escape(name)}</h1>{f'<p>{html.escape(ruby)}</p>' if ruby else ''}<p>取得済み出演作品：<strong>{len(works)}</strong>件</p></div></div><h2>人気順</h2><div class="fc-grid">{cards(popular)}</div><h2>新着順</h2><div class="fc-grid">{cards(latest)}</div><h2>評価順</h2><div class="fc-grid">{cards(rated)}</div><h2>関連ジャンル</h2><div>{genre_links or 'データなし'}</div><h2>関連メーカー</h2><div>{maker_links or 'データなし'}</div><p class="fc-pr">PR：当ページにはアフィリエイト広告を含みます。</p></div></section></main><script type="application/ld+json">{schema}</script>''' + footer() + "</body></html>"
        out.write_text(page, encoding="utf-8"); urls.append(path)
    return urls


def write_sale(items: list[dict]) -> str:
    sales = [x for x in items if int(x.get("discountRate") or 0) > 0]
    sales.sort(key=lambda x: (int(x.get("discountRate") or 0), -(int(x.get("priceValue") or 10**9))), reverse=True)
    rows = "".join(card(x) for x in sales)
    path = "/sale/"; out = ROOT / "sale" / "index.html"; out.parent.mkdir(parents=True, exist_ok=True)
    page = head("FANZAセール作品｜割引率順", f"FANZA APIで取得したセール対象作品{len(sales)}件を割引率順に掲載。", BASE_URL+path) + header() + f'''<main><section class="hub-hero"><div class="wrap"><h1>FANZAセール作品</h1><p>現在APIで確認できる割引作品を、割引率の高い順に表示しています。</p></div></section><section class="section"><div class="wrap"><div class="fc-sale-summary"><strong>{len(sales)}作品</strong> / 価格・販売状況は変更される場合があります。</div><div class="fc-grid">{rows or '<p>現在、割引価格を取得できる作品がありません。</p>'}</div><p class="fc-pr">PR：当ページにはアフィリエイト広告を含みます。</p></div></section></main>''' + footer() + "</body></html>"
    out.write_text(page, encoding="utf-8")
    return path


def write_search(items: list[dict], directory: list[dict]) -> str:
    search_items = []
    for x in items:
        search_items.append({"type":"product","id":safe_id(str(x.get("contentId") or "")),"title":x.get("title") or "","image":x.get("imageURL") or "","maker":x.get("maker") or "","actresses":x.get("actresses") or [],"genres":x.get("genres") or [],"price":yen(x.get("price"))})
    for a in directory:
        search_items.append({"type":"actress","id":str(a.get("id") or ""),"title":str(a.get("name") or ""),"ruby":str(a.get("ruby") or ""),"image":str(a.get("imageURL") or "")})
    (DATA / "site-search-index.json").write_text(json.dumps(search_items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    out = ROOT / "search" / "index.html"; out.parent.mkdir(parents=True, exist_ok=True)
    page = head("サイト内検索｜作品・女優・メーカー・ジャンル", "FANZA作品、女優、メーカー、ジャンルを1つの検索欄から検索できます。", BASE_URL+"/search/") + header() + '''<main><section class="hub-hero"><div class="wrap"><h1>サイト内検索</h1><p>作品名・女優名・メーカー・ジャンルをまとめて検索できます。</p></div></section><section class="section"><div class="wrap"><div class="fc-search"><input id="siteSearch" type="search" placeholder="作品・女優・メーカー・ジャンルを検索"><span id="siteSearchCount"></span></div><div id="siteSearchResults" class="fc-grid"></div></div></section></main><script src="/assets/site-search.js?v=20260926-001"></script>''' + footer() + "</body></html>"
    out.write_text(page, encoding="utf-8")
    return "/search/"


def write_view_fallback() -> None:
    out = PRODUCT_ROOT / "view" / "index.html"; out.parent.mkdir(parents=True, exist_ok=True)
    page = head("作品情報", "FANZA作品情報を表示します。", BASE_URL+"/products/view/", robots="noindex,follow") + header() + '''<main><section class="section"><div class="wrap"><div id="dynamicProduct">作品情報を読み込み中です…</div></div></section></main><script src="/assets/dynamic-product.js?v=20260926-001"></script>''' + footer() + "</body></html>"
    out.write_text(page, encoding="utf-8")


def update_sitemap(urls: list[str]) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    unique = []
    seen = set()
    for u in urls:
        if u not in seen:
            seen.add(u); unique.append(u)
    xml = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in unique:
        xml.append(f'  <url><loc>{BASE_URL}{html.escape(u)}</loc><lastmod>{today}</lastmod></url>')
    xml.append('</urlset>')
    SITEMAP.write_text("\n".join(xml)+"\n", encoding="utf-8")


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"
    if not api_id:
        raise SystemExit("DMM_API_ID missing")
    DATA.mkdir(parents=True, exist_ok=True)
    directory_path = DATA / "fanza-actress-directory.json"
    directory = []
    if directory_path.exists():
        try: directory = (json.loads(directory_path.read_text(encoding="utf-8")) or {}).get("actresses") or []
        except Exception: directory = []
    generated_at = datetime.now(timezone.utc).isoformat()
    items, reported_total = collect_all(api_id, affiliate_id)
    print(f"Full catalog collected: {len(items)} items; API total={reported_total}")
    write_shards(items, generated_at, reported_total)
    write_view_fallback()
    # Cloudflare Pagesのファイル数余裕を残し、残り作品は動的フォールバックで全件閲覧可能にする。
    base_files = sum(1 for p in ROOT.rglob("*") if p.is_file() and PRODUCT_ROOT not in p.parents and ACTRESS_ROOT not in p.parents)
    product_budget = max(500, min(len(items), MAX_INDEXABLE_FILES - base_files - 2500))
    static_ids = write_product_pages(items, product_budget)
    catalog_urls = write_catalog_pages(items, static_ids)
    remaining = max(0, MAX_INDEXABLE_FILES - base_files - len(static_ids) - len(catalog_urls) - 500)
    actress_urls = write_actress_pages(items, directory, remaining)
    sale_url = write_sale(items)
    search_url = write_search(items, directory)
    product_urls = [f"/products/{cid}/" for cid in static_ids]
    update_sitemap(["/", "/ranking/", "/ranking/actress/", "/ranking/genre/", "/ranking/maker/", sale_url, search_url] + catalog_urls + product_urls + actress_urls)
    print(f"Upgrade complete: catalog={len(items)}, static_products={len(static_ids)}, actress_pages={len(actress_urls)}, catalog_pages={len(catalog_urls)}, sales={sum(1 for x in items if int(x.get('discountRate') or 0)>0)}")


if __name__ == "__main__":
    main()
