from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path("public")
DATA = ROOT / "data"
MANIFEST = DATA / "full-catalog-manifest.json"
TAXONOMY = DATA / "fanza-taxonomy-directory.json"
GENRE_ROOT = ROOT / "ranking" / "genre"
BASE_URL = "https://okazu-yoridori-midori.pages.dev"
PAGE_LIMIT = 60
ASSET_VERSION = "20260927-1435"


def load_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def safe_id(value: object) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return s[:120] or "item"


def yen(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return f"¥{int(digits):,}" if digits else "価格を確認"


def product_href(item: dict) -> str:
    cid = safe_id(item.get("contentId"))
    static = ROOT / "products" / cid / "index.html"
    return f"/products/{cid}/" if static.exists() else f"/products/view/?id={html.escape(cid, quote=True)}"


def product_card(item: dict) -> str:
    title = html.escape(str(item.get("title") or "FANZA作品"))
    image = html.escape(str(item.get("imageURL") or ""), quote=True)
    href = product_href(item)
    discount = int(item.get("discountRate") or 0)
    maker = html.escape(str(item.get("maker") or "FANZA"))
    discount_html = f'<span class="fc-discount">{discount}%OFF</span>' if discount else ""
    image_html = f'<img src="{image}" alt="{title}" loading="lazy" decoding="async">' if image else ""
    return (
        f'<a class="fc-card" href="{href}">'
        f'<div class="fc-img">{discount_html}{image_html}</div>'
        f'<div class="fc-body"><strong>{title}</strong><span>{maker}</span><b>{html.escape(yen(item.get("price")))}</b></div>'
        f'</a>'
    )


def site_header() -> str:
    return '''<header><div class="wrap header-inner"><a class="logo" href="/"><span>オカズはよりどりみどり</span></a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/products/">作品一覧</a><a href="/search/">サイト内検索</a><a href="/fc2-adult/">FC2アダルト</a><a href="/guide/">初心者ガイド</a></nav></div></header>'''


def site_footer() -> str:
    return '''<footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり.</div></div></footer><div id="ageModal" class="age-modal" aria-modal="true" role="dialog"><div class="age-box"><h2>18歳以上ですか？</h2><p>このサイトは成人向けサービスに関する情報を扱います。18歳未満の方は閲覧できません。</p><div class="age-actions"><button id="ageYes">18歳以上です</button><a class="btn-secondary" href="https://www.google.com/">退出する</a></div></div></div><script src="/assets/affiliate-config.js"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js"></script><script src="/assets/affiliate-compliance.js"></script>'''


def genre_page(gid: str, name: str, items: list[dict]) -> str:
    name_e = html.escape(name)
    gid_e = html.escape(gid, quote=True)
    cards = "".join(product_card(x) for x in items)
    if not cards:
        cards = '<div class="entity-empty">現在表示できる作品がありません。</div>'
    title = f"{name}の作品一覧｜オカズはよりどりみどり"
    desc = f"FANZAのジャンル「{name}」に該当する作品を画像・価格付きで一覧表示します。"
    canonical = f"{BASE_URL}/ranking/genre/{gid_e}/"
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc, quote=True)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}"><link rel="icon" type="image/png" href="/assets/favicon.png"><link rel="stylesheet" href="/assets/style-white-v2.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/full-catalog.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/entity-rankings.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/colorful-readable-v1.css?v={ASSET_VERSION}"><link rel="stylesheet" href="/assets/benchmark-upgrade-v1.css?v={ASSET_VERSION}"></head><body>{site_header()}<main><section class="hub-hero"><div class="wrap"><span class="update-badge">FANZA / ジャンル</span><h1>{name_e}の作品</h1><p>このジャンルに該当する作品を新しい順から表示しています。</p></div></section><section class="section"><div class="wrap"><div class="entity-breadcrumb"><a href="/ranking/">ランキング</a> › <a href="/ranking/genre/">ジャンル</a> › {name_e}</div><div class="entity-summary"><span class="entity-chip">{len(items)}作品を表示</span><span class="entity-chip">毎日更新</span></div><div class="fc-grid">{cards}</div><p class="fc-pr">PR：当サイトにはアフィリエイト広告を含みます。価格・配信状況はリンク先の公式情報をご確認ください。</p></div></section></main>{site_footer()}</body></html>'''


def collect_genres() -> dict[str, dict]:
    manifest = load_json(MANIFEST)
    groups: dict[str, dict] = {}
    for shard in manifest.get("shards") or []:
        rel = str(shard.get("file") or "").lstrip("/")
        if not rel:
            continue
        path = ROOT / rel
        if not path.exists():
            continue
        rows = load_json(path)
        if not isinstance(rows, list):
            continue
        for item in rows:
            if not isinstance(item, dict):
                continue
            for genre in item.get("genreEntities") or []:
                if not isinstance(genre, dict):
                    continue
                gid = str(genre.get("id") or "").strip()
                name = str(genre.get("name") or "").strip()
                if not gid or not name:
                    continue
                bucket = groups.setdefault(gid, {"name": name, "items": []})
                if len(bucket["items"]) < PAGE_LIMIT:
                    bucket["items"].append(item)
    return groups


def page_has_products(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "entity-product-card" in text or "class=\"fc-card\"" in text


def patch_directory(groups: dict[str, dict]) -> int:
    path = GENRE_ROOT / "index.html"
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    before = text
    taxonomy = load_json(TAXONOMY)
    for row in taxonomy.get("genres") or []:
        gid = str(row.get("id") or "").strip()
        name = str(row.get("name") or "").strip()
        if not gid or not name or gid not in groups:
            continue
        name_e = html.escape(name)
        inner = f'<strong>{name_e}</strong><span>API商品データから自動抽出</span>'
        old = f'<div class="taxonomy-card">{inner}</div>'
        new = f'<a class="taxonomy-card" href="/ranking/genre/{html.escape(gid, quote=True)}/">{inner}</a>'
        text = text.replace(old, new)
    if text != before:
        path.write_text(text, encoding="utf-8")
    return before.count('<div class="taxonomy-card">') - text.count('<div class="taxonomy-card">')


def main() -> None:
    if not MANIFEST.exists():
        print("Genre category repair skipped: full catalog manifest missing")
        return
    groups = collect_genres()
    if not groups:
        raise SystemExit("Genre category repair failed: no genre data found in full catalog")

    created = 0
    kept = 0
    for gid, data in groups.items():
        out = GENRE_ROOT / safe_id(gid) / "index.html"
        if page_has_products(out):
            kept += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(genre_page(gid, str(data["name"]), list(data["items"])), encoding="utf-8")
        created += 1

    fixed_links = patch_directory(groups)
    unresolved = []
    taxonomy = load_json(TAXONOMY)
    for row in taxonomy.get("genres") or []:
        gid = str(row.get("id") or "").strip()
        if gid and gid in groups and not page_has_products(GENRE_ROOT / safe_id(gid) / "index.html"):
            unresolved.append(gid)
    if unresolved:
        raise SystemExit(f"Genre category repair incomplete: {len(unresolved)} unresolved")

    print(f"Genre category repair: catalog_genres={len(groups)} created={created} existing={kept} directory_links_fixed={fixed_links}")


if __name__ == "__main__":
    main()
