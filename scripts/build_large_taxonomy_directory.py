from __future__ import annotations

import html
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.dmm.com/affiliate/v3"
BASE_URL = "https://okazu-yoridori-midori.pages.dev"
ROOT = Path("public")
DATA_DIR = ROOT / "data"
SITEMAP = ROOT / "sitemap.xml"
ACTRESS_TARGET = 10_000
ACTRESS_HITS = 100
DIRECTORY_PAGE_SIZE = 100
GENRE_TARGET = 100
MAKER_TARGET = 100
PRODUCT_SCAN_HITS = 100
PRODUCT_SCAN_PAGES = 20


def api_json(endpoint: str, params: dict[str, str], retries: int = 3) -> dict:
    url = f"{API_BASE}/{endpoint}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "okazu-yoridori-midori-taxonomy/1.0"})
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=45) as res:
                payload = json.loads(res.read().decode("utf-8"))
            result = payload.get("result") or {}
            status = result.get("status")
            if status not in (200, "200"):
                raise RuntimeError(f"API {endpoint} status={status!r}")
            return result
        except Exception as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"API {endpoint} failed: {last}")


def image_url(row: dict) -> str:
    value = row.get("imageURL") or row.get("image_url") or {}
    if isinstance(value, dict):
        return str(value.get("large") or value.get("small") or value.get("list") or "")
    return str(value or "")


def collect_actresses(api_id: str, affiliate_id: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    offset = 1
    while len(out) < ACTRESS_TARGET:
        result = api_json(
            "ActressSearch",
            {
                "api_id": api_id,
                "affiliate_id": affiliate_id,
                "hits": str(ACTRESS_HITS),
                "offset": str(offset),
                "output": "json",
            },
        )
        rows = result.get("actress") or result.get("actresses") or result.get("items") or []
        if not rows:
            break
        added = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            actress_id = str(row.get("id") or row.get("actress_id") or "").strip()
            name = str(row.get("name") or "").strip()
            if not actress_id or not name or actress_id in seen:
                continue
            seen.add(actress_id)
            out.append(
                {
                    "id": actress_id,
                    "name": name,
                    "ruby": str(row.get("ruby") or "").strip(),
                    "imageURL": image_url(row),
                    "birthday": str(row.get("birthday") or "").strip(),
                    "height": row.get("height") or "",
                }
            )
            added += 1
            if len(out) >= ACTRESS_TARGET:
                break
        if added == 0 or len(rows) < ACTRESS_HITS:
            break
        offset += ACTRESS_HITS
        if len(out) % 1000 == 0:
            print(f"Actress directory: {len(out)}/{ACTRESS_TARGET}")
        time.sleep(0.12)
    return out


def collect_genres_and_makers(api_id: str, affiliate_id: str) -> tuple[list[dict], list[dict]]:
    genre_names: dict[str, str] = {}
    maker_names: dict[str, str] = {}
    genre_count: Counter[str] = Counter()
    maker_count: Counter[str] = Counter()
    offset = 1

    for _ in range(PRODUCT_SCAN_PAGES):
        result = api_json(
            "ItemList",
            {
                "api_id": api_id,
                "affiliate_id": affiliate_id,
                "site": "FANZA",
                "service": "digital",
                "floor": "videoa",
                "hits": str(PRODUCT_SCAN_HITS),
                "offset": str(offset),
                "sort": "rank",
                "output": "json",
            },
        )
        rows = result.get("items") or []
        if not rows:
            break
        for item in rows:
            info = item.get("iteminfo") or {}
            for g in info.get("genre") or []:
                if not isinstance(g, dict):
                    continue
                gid = str(g.get("id") or "").strip()
                name = str(g.get("name") or "").strip()
                if gid and name:
                    genre_names[gid] = name
                    genre_count[gid] += 1
            for m in info.get("maker") or []:
                if not isinstance(m, dict):
                    continue
                mid = str(m.get("id") or "").strip()
                name = str(m.get("name") or "").strip()
                if mid and name:
                    maker_names[mid] = name
                    maker_count[mid] += 1
        offset += PRODUCT_SCAN_HITS
        if len(rows) < PRODUCT_SCAN_HITS:
            break
        if len(genre_names) >= GENRE_TARGET and len(maker_names) >= MAKER_TARGET and offset > 1000:
            break
        time.sleep(0.12)

    genres = [
        {"id": gid, "name": genre_names[gid], "score": count}
        for gid, count in genre_count.most_common(GENRE_TARGET)
    ]
    makers = [
        {"id": mid, "name": maker_names[mid], "score": count}
        for mid, count in maker_count.most_common(MAKER_TARGET)
    ]
    return genres, makers


def site_header() -> str:
    return '''<header><div class="wrap header-inner"><a class="logo" href="/"><span>オカズはよりどりみどり</span></a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/subscription/">見放題比較</a><a href="/reviews/">レビュー</a><a href="/products/">作品一覧</a><a href="/guide/">初心者ガイド</a></nav></div></header>'''


def site_footer() -> str:
    return '''<footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり. All rights reserved.</div></div></footer><div id="ageModal" class="age-modal" aria-modal="true" role="dialog"><div class="age-box"><h2>18歳以上ですか？</h2><p>このサイトは成人向けサービスに関する情報を扱います。18歳未満の方は閲覧できません。</p><div class="age-actions"><button id="ageYes">18歳以上です</button><a class="btn-secondary" href="https://www.google.com/">退出する</a></div><p class="small">年齢確認はこのブラウザ内に保存されます。</p></div></div><script src="/assets/affiliate-config.js"></script><script src="/assets/v6.js"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js"></script><script src="/assets/affiliate-compliance.js"></script>'''


def head(title: str, description: str, canonical: str) -> str:
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="{html.escape(description, quote=True)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{html.escape(canonical, quote=True)}"><link rel="icon" type="image/png" href="/assets/favicon.png"><link rel="stylesheet" href="/assets/style-white-v2.css?v=20260922-1322"><link rel="stylesheet" href="/assets/taxonomy-directory.css?v=20260925-2335"></head><body>'''


def actress_card(row: dict, has_detail: bool) -> str:
    name = html.escape(str(row.get("name") or ""))
    ruby = html.escape(str(row.get("ruby") or ""))
    image = html.escape(str(row.get("imageURL") or ""), quote=True)
    media = f'<img src="{image}" alt="{name}" loading="lazy" decoding="async">' if image else f'<span class="actress-fallback">{name[:1]}</span>'
    inner = f'''<div class="actress-photo">{media}</div><div class="actress-card-body"><strong>{name}</strong>{f'<span>{ruby}</span>' if ruby else ''}</div>'''
    if has_detail:
        return f'<a class="actress-card" href="/ranking/actress/{html.escape(str(row["id"]), quote=True)}/">{inner}</a>'
    return f'<div class="actress-card">{inner}</div>'


def page_nav(base: str, page_no: int, total_pages: int) -> str:
    prev_html = ""
    next_html = ""
    if page_no > 1:
        prev_path = base if page_no == 2 else f"{base}page/{page_no - 1}/"
        prev_html = f'<a href="{prev_path}">← 前へ</a>'
    if page_no < total_pages:
        next_html = f'<a href="{base}page/{page_no + 1}/">次へ →</a>'
    return f'<nav class="directory-pagination">{prev_html}<span>{page_no} / {total_pages}</span>{next_html}</nav>'


def write_actress_pages(actresses: list[dict], generated_at: str) -> list[str]:
    urls: list[str] = []
    base = "/ranking/actress/"
    total_pages = max(1, (len(actresses) + DIRECTORY_PAGE_SIZE - 1) // DIRECTORY_PAGE_SIZE)
    for page_no in range(1, total_pages + 1):
        chunk = actresses[(page_no - 1) * DIRECTORY_PAGE_SIZE : page_no * DIRECTORY_PAGE_SIZE]
        cards = []
        for row in chunk:
            detail = ROOT / "ranking" / "actress" / str(row["id"]) / "index.html"
            cards.append(actress_card(row, detail.exists()))
        path = base if page_no == 1 else f"{base}page/{page_no}/"
        out = ROOT / "ranking" / "actress" / "index.html" if page_no == 1 else ROOT / "ranking" / "actress" / "page" / str(page_no) / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        title = f"FANZA女優検索・一覧 {page_no}/{total_pages}｜顔写真付き"
        desc = f"FANZA Webサービスの女優データを顔写真付きで検索・一覧表示。最大{len(actresses):,}人を収録しています。"
        search = '''<div class="actress-search"><input id="actressSearch" type="search" placeholder="女優名・読みで検索" autocomplete="off"><span id="actressSearchCount"></span></div><div id="actressSearchResults" class="actress-grid" hidden></div>''' if page_no == 1 else ""
        page = head(title, desc, BASE_URL + path) + site_header() + f'''<main><section class="hub-hero"><div class="wrap"><span class="update-badge">FANZA API / 女優データ</span><h1>女優を顔写真から探す</h1><p>名前だけでなくプロフィール画像を見ながら検索できます。現在 {len(actresses):,} 人をAPIから取得しています。</p></div></section><section class="section"><div class="wrap"><div class="entity-breadcrumb"><a href="/ranking/">ランキング</a> › 女優一覧</div>{search}<div id="actressDirectoryGrid" class="actress-grid">{''.join(cards)}</div>{page_nav(base, page_no, total_pages)}<p class="directory-note">プロフィール画像・名前はFANZA Webサービスから取得しています。画像が提供されていない人物は文字アイコンで表示します。</p><p class="entity-credit">Powered by <a href="https://affiliate.dmm.com/api/" target="_blank" rel="noopener">FANZA Webサービス</a> / API更新: {html.escape(generated_at)}</p></div></section></main>''' + site_footer()
        if page_no == 1:
            page += '<script src="/assets/actress-directory.js?v=20260925-2335"></script>'
        page += "</body></html>"
        out.write_text(page, encoding="utf-8")
        urls.append(path)
    return urls


def simple_card(kind: str, row: dict) -> str:
    name = html.escape(str(row.get("name") or ""))
    entity_id = str(row.get("id") or "")
    detail = ROOT / "ranking" / kind / entity_id / "index.html"
    inner = f'<strong>{name}</strong><span>API商品データから自動抽出</span>'
    if detail.exists():
        return f'<a class="taxonomy-card" href="/ranking/{kind}/{html.escape(entity_id, quote=True)}/">{inner}</a>'
    return f'<div class="taxonomy-card">{inner}</div>'


def write_simple_directory(kind: str, label: str, rows: list[dict], generated_at: str) -> list[str]:
    base = f"/ranking/{kind}/"
    cards = "".join(simple_card(kind, row) for row in rows)
    title = f"FANZA {label}一覧・ランキング｜約{len(rows)}件"
    desc = f"FANZAの商品APIから{label}を抽出し、利用頻度の高い約{len(rows)}件を一覧表示しています。"
    page = head(title, desc, BASE_URL + base) + site_header() + f'''<main><section class="hub-hero"><div class="wrap"><span class="update-badge">FANZA API / {html.escape(label)}</span><h1>{html.escape(label)}から探す</h1><p>取得した商品データをもとに、{html.escape(label)}を約 {len(rows)} 件まで拡張しました。</p></div></section><section class="section"><div class="wrap"><div class="entity-breadcrumb"><a href="/ranking/">ランキング</a> › {html.escape(label)}</div><div class="taxonomy-grid">{cards}</div><p class="entity-credit">Powered by <a href="https://affiliate.dmm.com/api/" target="_blank" rel="noopener">FANZA Webサービス</a> / API更新: {html.escape(generated_at)}</p></div></section></main>''' + site_footer() + "</body></html>"
    out = ROOT / "ranking" / kind / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return [base]


def update_sitemap(urls: list[str]) -> None:
    if not SITEMAP.exists():
        return
    text = SITEMAP.read_text(encoding="utf-8")
    text = re.sub(r"\n?\s*<!-- FANZA_TAXONOMY_START -->.*?<!-- FANZA_TAXONOMY_END -->\s*", "\n", text, flags=re.S)
    today = datetime.now(timezone.utc).date().isoformat()
    entries = "\n".join(f"  <url><loc>{BASE_URL}{html.escape(url)}</loc><lastmod>{today}</lastmod></url>" for url in urls)
    block = f"  <!-- FANZA_TAXONOMY_START -->\n{entries}\n  <!-- FANZA_TAXONOMY_END -->\n"
    text = text.replace("</urlset>", block + "</urlset>")
    SITEMAP.write_text(text, encoding="utf-8")


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"
    if not api_id:
        print("DMM_API_ID is not configured; large taxonomy generation skipped.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()

    try:
        actresses = collect_actresses(api_id, affiliate_id)
    except Exception as exc:
        print(f"WARN: ActressSearch failed: {exc}")
        actresses = []

    genres, makers = collect_genres_and_makers(api_id, affiliate_id)

    detail_ids = {
        p.parent.name
        for p in (ROOT / "ranking" / "actress").glob("*/index.html")
        if p.parent.name.isdigit()
    }
    for row in actresses:
        row["hasDetail"] = str(row.get("id") or "") in detail_ids

    (DATA_DIR / "fanza-actress-directory.json").write_text(
        json.dumps({"generatedAt": generated_at, "count": len(actresses), "actresses": actresses}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (DATA_DIR / "fanza-taxonomy-directory.json").write_text(
        json.dumps({"generatedAt": generated_at, "genres": genres, "makers": makers}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    urls: list[str] = []
    if actresses:
        urls.extend(write_actress_pages(actresses, generated_at))
    urls.extend(write_simple_directory("genre", "ジャンル", genres, generated_at))
    urls.extend(write_simple_directory("maker", "メーカー", makers, generated_at))
    update_sitemap(urls)

    print(f"Large taxonomy complete: actresses={len(actresses)}, genres={len(genres)}, makers={len(makers)}, directory_pages={len(urls)}")


if __name__ == "__main__":
    main()
