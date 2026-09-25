from __future__ import annotations

import html
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.dmm.com/affiliate/v3"
BASE_URL = "https://okazu-yoridori-midori.pages.dev"
ROOT = Path("public")
DATA = ROOT / "data"
DIRECTORY_JSON = DATA / "fanza-actress-directory.json"
POPULARITY_JSON = DATA / "fanza-actress-popularity.json"
ACTRESS_ROOT = ROOT / "ranking" / "actress"
RANKING_INDEX = ROOT / "ranking" / "index.html"

HITS = 100
TARGET = int(os.environ.get("DMM_POPULAR_ACTRESS_TARGET", "10000"))
MAX_PAGES = int(os.environ.get("DMM_POPULAR_ACTRESS_MAX_PAGES", "500"))
ENRICH_TOP_MISSING = int(os.environ.get("DMM_POPULAR_ACTRESS_ENRICH_MISSING", "300"))
REQUEST_DELAY = float(os.environ.get("DMM_REQUEST_DELAY", "0.10"))


def api_json(endpoint: str, params: dict[str, str], retries: int = 4) -> dict:
    url = f"{API_BASE}/{endpoint}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "okazu-dmm-popular-actress/1.0"})
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=60) as res:
                payload = json.loads(res.read().decode("utf-8"))
            result = payload.get("result") or {}
            if result.get("status") not in (200, "200"):
                raise RuntimeError(f"status={result.get('status')!r}")
            return result
        except Exception as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(last)


def normalize_profile(raw: dict) -> dict | None:
    actress_id = str(raw.get("id") or raw.get("actress_id") or "").strip()
    name = str(raw.get("name") or "").strip()
    if not actress_id or not name:
        return None
    image = raw.get("imageURL") or raw.get("image_url") or {}
    if isinstance(image, dict):
        image_url = str(image.get("large") or image.get("small") or image.get("list") or "")
    else:
        image_url = str(image or "")
    return {
        "id": actress_id,
        "name": name,
        "ruby": str(raw.get("ruby") or "").strip(),
        "imageURL": image_url,
        "birthday": str(raw.get("birthday") or "").strip(),
        "height": raw.get("height") or "",
    }


def fetch_profile(api_id: str, affiliate_id: str, actress_id: str) -> dict | None:
    result = api_json("ActressSearch", {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "actress_id": actress_id,
        "hits": "1",
        "offset": "1",
        "output": "json",
    })
    rows = result.get("actress") or result.get("actresses") or result.get("items") or []
    if not rows or not isinstance(rows[0], dict):
        return None
    return normalize_profile(rows[0])


def collect_popularity(api_id: str, affiliate_id: str) -> list[dict]:
    stats: dict[str, dict] = {}
    offset = 1
    page = 0
    while page < MAX_PAGES and len(stats) < TARGET:
        result = api_json("ItemList", {
            "api_id": api_id,
            "affiliate_id": affiliate_id,
            "site": "FANZA",
            "service": "digital",
            "floor": "videoa",
            "hits": str(HITS),
            "offset": str(offset),
            "sort": "rank",
            "output": "json",
        })
        items = result.get("items") or []
        if not items:
            break
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            product_rank = offset + i
            info = item.get("iteminfo") or {}
            for actress in info.get("actress") or []:
                if not isinstance(actress, dict):
                    continue
                actress_id = str(actress.get("id") or "").strip()
                name = str(actress.get("name") or "").strip()
                if not actress_id or not name:
                    continue
                if actress_id not in stats:
                    stats[actress_id] = {
                        "id": actress_id,
                        "name": name,
                        "firstProductRank": product_rank,
                        "rankedAppearances": 0,
                    }
                stats[actress_id]["rankedAppearances"] += 1
        page += 1
        print(f"DMM rank scan page={page} offset={offset} unique_actresses={len(stats)}")
        if len(items) < HITS:
            break
        offset += HITS
        time.sleep(REQUEST_DELAY)

    rows = list(stats.values())
    rows.sort(key=lambda r: (int(r["firstProductRank"]), -int(r["rankedAppearances"]), str(r["name"])))
    for idx, row in enumerate(rows, 1):
        row["popularityRank"] = idx
    return rows[:TARGET]


def load_directory() -> tuple[dict, dict[str, dict]]:
    if not DIRECTORY_JSON.exists():
        return {}, {}
    payload = json.loads(DIRECTORY_JSON.read_text(encoding="utf-8"))
    rows = payload.get("actresses") or []
    return payload, {str(r.get("id")): dict(r) for r in rows if r.get("id")}


def enrich_and_reorder(api_id: str, affiliate_id: str, ranked: list[dict]) -> tuple[list[dict], list[dict]]:
    old_payload, profiles = load_directory()
    detail_ids = {p.parent.name for p in ACTRESS_ROOT.glob("*/index.html") if p.parent.name.isdigit()}

    missing_enriched = 0
    popular_rows: list[dict] = []
    directory_rows: list[dict] = []
    seen_dir: set[str] = set()

    for stat in ranked:
        aid = str(stat["id"])
        profile = profiles.get(aid)
        if not profile and missing_enriched < ENRICH_TOP_MISSING:
            try:
                profile = fetch_profile(api_id, affiliate_id, aid)
            except Exception as exc:
                print(f"WARN profile {aid}: {exc}")
                profile = None
            if profile:
                profiles[aid] = profile
            missing_enriched += 1
            time.sleep(0.05)

        row = dict(profile or {"id": aid, "name": stat["name"], "ruby": "", "imageURL": "", "birthday": "", "height": ""})
        row.update({
            "popularityRank": int(stat["popularityRank"]),
            "dmmFirstProductRank": int(stat["firstProductRank"]),
            "dmmRankedAppearances": int(stat["rankedAppearances"]),
            "hasDetail": aid in detail_ids,
        })
        popular_rows.append(row)

        # 50音検索は読み仮名が取れた人物だけを採用。並び順はDMM人気作品順を維持。
        if row.get("ruby") and aid not in seen_dir:
            directory_rows.append(row)
            seen_dir.add(aid)

    generated_at = datetime.now(timezone.utc).isoformat()
    DIRECTORY_JSON.parent.mkdir(parents=True, exist_ok=True)
    DIRECTORY_JSON.write_text(json.dumps({
        "generatedAt": generated_at,
        "count": len(directory_rows),
        "strategy": "DMM/FANZA人気作品rank順から出演女優を初出順に採用",
        "actresses": directory_rows,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    POPULARITY_JSON.write_text(json.dumps({
        "generatedAt": generated_at,
        "count": len(popular_rows),
        "method": "FANZA ItemList sort=rank の作品順位を上位から走査し、出演女優の初出作品順位で並べた当サイト集計",
        "officialActressRanking": False,
        "actresses": popular_rows,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return directory_rows, popular_rows


def popular_card(row: dict) -> str:
    rank = int(row.get("popularityRank") or 0)
    name = html.escape(str(row.get("name") or ""))
    ruby = html.escape(str(row.get("ruby") or ""))
    image = html.escape(str(row.get("imageURL") or ""), quote=True)
    aid = html.escape(str(row.get("id") or ""), quote=True)
    if image:
        media = f'<img src="{image}" alt="{name}" loading="lazy" decoding="async">'
    else:
        media = '<div class="popular-no-photo">公式画像なし</div>'
    body = f'<div class="actress-photo">{media}<span class="popular-rank">{rank}位</span></div><div class="actress-card-body"><strong>{name}</strong>{f"<span>{ruby}</span>" if ruby else ""}<small>人気作品 初出 {int(row.get("dmmFirstProductRank") or 0)}位</small></div>'
    if row.get("hasDetail"):
        return f'<a class="actress-card popular-actress-card" href="/ranking/actress/{aid}/">{body}</a>'
    return f'<div class="actress-card popular-actress-card">{body}</div>'


def write_popular_page(rows: list[dict], generated_at: str) -> None:
    display_rows = rows[:100]
    cards = "".join(popular_card(r) for r in display_rows)
    out = ACTRESS_ROOT / "popular" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    title = "DMM/FANZA 人気女優ランキング｜人気作品順から集計"
    desc = "FANZA Webサービスの人気作品ランキングを上位から走査し、出演女優の初出順位をもとに人気女優を並べた当サイト集計です。"
    canonical = BASE_URL + "/ranking/actress/popular/"
    page = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><meta name="description" content="{desc}"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}"><link rel="stylesheet" href="/assets/style-white-v2.css?v=20260922-1322"><link rel="stylesheet" href="/assets/taxonomy-directory.css?v=20260926-0200"><link rel="stylesheet" href="/assets/popular-actress.css?v=20260926-0200"></head><body><header><div class="wrap header-inner"><a class="logo" href="/"><span>オカズはよりどりみどり</span></a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/subscription/">見放題比較</a><a href="/reviews/">レビュー</a><a href="/products/">作品一覧</a><a href="/guide/">初心者ガイド</a></nav></div></header><main><section class="hub-hero"><div class="wrap"><span class="update-badge">FANZA API / 人気作品データ</span><h1>人気女優ランキング</h1><p>DMM/FANZAの人気作品順位を上位から走査し、出演女優を人気作品の初出順で並べています。</p><div class="notice"><strong>集計方法：</strong>DMM/FANZA公式の「女優ランキング」そのものではありません。FANZA Webサービスの商品APIで <b>人気順（rank）</b> の作品を上位から取得し、その作品に出演する女優を順番に集計した当サイト独自ランキングです。</div></div></section><section class="section"><div class="wrap"><div class="entity-breadcrumb"><a href="/ranking/">ランキング</a> › 人気女優ランキング</div><div class="popular-links"><a href="/ranking/actress/">女優50音検索へ</a></div><div class="actress-grid popular-grid">{cards}</div><p class="directory-note">上位100人を表示。プロフィール画像・女優情報はFANZA Webサービスから取得しています。API更新: {html.escape(generated_at)}</p></div></section></main><footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり.</div></div></footer><script src="/assets/affiliate-config.js"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js"></script><script src="/assets/affiliate-compliance.js"></script></body></html>'''
    out.write_text(page, encoding="utf-8")


def patch_ranking_index() -> None:
    if not RANKING_INDEX.exists():
        return
    text = RANKING_INDEX.read_text(encoding="utf-8")
    text = text.replace("FANZA人気ランキング・女優別・ジャンル別・メーカー別比較", "FANZA人気ランキング・人気女優・女優50音検索・ジャンル別・メーカー別比較")
    text = text.replace("女優別・ジャンル別・メーカー別", "人気女優・女優50音検索・ジャンル別・メーカー別")
    text = re.sub(
        r'<a href="/ranking/actress/"><b>女優別ランキング</b><span>.*?</span></a>',
        '<a href="/ranking/actress/popular/"><b>人気女優ランキング</b><span>DMM/FANZAの人気作品順データから出演女優を上位順に集計。</span></a><a href="/ranking/actress/"><b>女優50音検索</b><span>人気順に採用した女優を、名前・読み・50音から検索。</span></a>',
        text,
        flags=re.S,
    )
    text = text.replace('<tr><td>女優別</td><td>現在の人気作品から候補女優を抽出し、各女優の作品を人気順で再取得します。</td></tr>', '<tr><td>人気女優</td><td>DMM/FANZAの人気作品順位を上位から走査し、出演女優の初出順で集計します。</td></tr><tr><td>女優50音検索</td><td>人気作品データから採用した女優を50音・名前・読みで検索できます。</td></tr>')
    RANKING_INDEX.write_text(text, encoding="utf-8")


def patch_actress_index() -> None:
    path = ACTRESS_ROOT / "index.html"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'<title>.*?</title>', '<title>女優50音検索｜DMM/FANZA人気順で収録</title>', text, count=1, flags=re.S)
    text = re.sub(r'<h1>.*?女優.*?</h1>', '<h1>女優50音検索</h1>', text, count=1, flags=re.S)
    text = text.replace('名前だけでなくプロフィール画像を見ながら検索できます。', 'DMM/FANZAの人気作品順を基準に女優を収録し、名前・読み・50音から検索できます。')
    popular_cta = '<div class="popular-directory-cta"><a href="/ranking/actress/popular/"><strong>人気女優ランキングを見る</strong><span>DMM/FANZA人気作品データから集計した上位女優</span></a></div>'
    if "popular-directory-cta" not in text:
        text = text.replace('<div class="actress-search">', popular_cta + '<div class="actress-search">', 1)
    text = re.sub(r'actress-directory\.js\?v=[0-9-]+', 'actress-directory.js?v=20260926-0200', text)
    text = re.sub(r'taxonomy-directory\.css\?v=[0-9-]+', 'taxonomy-directory.css?v=20260926-0200', text)
    path.write_text(text, encoding="utf-8")


def update_sitemap() -> None:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return
    text = sitemap.read_text(encoding="utf-8")
    url = BASE_URL + "/ranking/actress/popular/"
    if url not in text:
        today = datetime.now(timezone.utc).date().isoformat()
        text = text.replace("</urlset>", f"  <url><loc>{url}</loc><lastmod>{today}</lastmod></url>\n</urlset>")
        sitemap.write_text(text, encoding="utf-8")


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"
    if not api_id:
        print("DMM_API_ID missing; popular actress build skipped")
        return
    ranked = collect_popularity(api_id, affiliate_id)
    directory_rows, popular_rows = enrich_and_reorder(api_id, affiliate_id, ranked)
    generated_at = datetime.now(timezone.utc).isoformat()
    write_popular_page(popular_rows, generated_at)
    patch_ranking_index()
    patch_actress_index()
    update_sitemap()
    print(f"Popular actress build complete: ranked={len(popular_rows)} directory={len(directory_rows)}")


if __name__ == "__main__":
    main()
