from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path("public")
HOME = ROOT / "index.html"
PRODUCTS = ROOT / "data" / "fanza-products.json"
POPULAR_ACTRESSES = ROOT / "data" / "fanza-actress-popularity.json"
ENTITY_RANKINGS = ROOT / "data" / "fanza-entity-rankings.json"
CSS = "/assets/instant-discovery-v1.css?v=20260927-0105"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def safe_id(value: str) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip()).strip("-")
    return s[:120] or "item"


def yen(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return f"¥{int(digits):,}" if digits else "価格を確認"


def product_href(item: dict) -> str:
    cid = safe_id(str(item.get("contentId") or ""))
    static = ROOT / "products" / cid / "index.html"
    return f"/products/{cid}/" if static.exists() else f"/products/view/?id={html.escape(cid, quote=True)}"


def product_card(item: dict, rank: int | None = None) -> str:
    title = html.escape(str(item.get("title") or "FANZA作品"))
    image = html.escape(str(item.get("imageURL") or ""), quote=True)
    href = product_href(item)
    discount = int(item.get("discountRate") or 0)
    actresses = [str(x) for x in (item.get("actresses") or [])[:2] if x]
    maker = str(item.get("maker") or "")
    sub = " / ".join(actresses) or maker
    review = str(item.get("reviewAverage") or "").strip()
    badges = []
    if rank:
        badges.append(f'<span class="instant-rank">{rank}位</span>')
    if discount > 0:
        badges.append(f'<span class="instant-discount">{discount}%OFF</span>')
    badge_html = "".join(badges)
    img_html = f'<img src="{image}" alt="{title}" loading="lazy" decoding="async">' if image else '<div class="instant-noimage">画像なし</div>'
    review_html = f'<span class="instant-review">★ {html.escape(review)}</span>' if review else ""
    return f'''<a class="instant-product-card" href="{href}">
<div class="instant-product-image">{badge_html}{img_html}</div>
<div class="instant-product-body"><strong>{title}</strong>{f'<span class="instant-sub">{html.escape(sub)}</span>' if sub else ''}<div class="instant-product-meta"><b>{html.escape(yen(item.get("price")))}</b>{review_html}</div></div>
</a>'''


def actress_card(row: dict) -> str:
    aid = html.escape(str(row.get("id") or ""), quote=True)
    name = html.escape(str(row.get("name") or ""))
    image = html.escape(str(row.get("imageURL") or ""), quote=True)
    rank = int(row.get("popularityRank") or 0)
    img_html = f'<img src="{image}" alt="{name}" loading="lazy" decoding="async">' if image else '<div class="instant-noimage">画像なし</div>'
    return f'''<a class="instant-actress-card" href="/ranking/actress/{aid}/"><div class="instant-actress-photo">{img_html}<span>{rank}位</span></div><strong>{name}</strong></a>'''


def genre_card(row: dict) -> str:
    gid = html.escape(str(row.get("id") or ""), quote=True)
    name = html.escape(str(row.get("name") or ""))
    count = int(row.get("itemCount") or 0)
    return f'<a class="instant-genre" href="/ranking/genre/{gid}/"><strong>{name}</strong><span>人気 {count}作品</span></a>'


def choose_rows(data: list[dict], limit: int, image_required: bool = True) -> list[dict]:
    out = []
    seen = set()
    for row in data:
        key = str(row.get("contentId") or row.get("id") or row.get("name") or "")
        if not key or key in seen:
            continue
        if image_required and not row.get("imageURL"):
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def build_main() -> str:
    product_data = load_json(PRODUCTS)
    actress_data = load_json(POPULAR_ACTRESSES)
    entity_data = load_json(ENTITY_RANKINGS)

    ranking = choose_rows(product_data.get("ranking") or [], 8)
    deals = choose_rows(product_data.get("deals") or [], 6)
    high_rated = choose_rows(product_data.get("highRated") or [], 4)

    actresses_all = actress_data.get("actresses") or []
    actresses = choose_rows(actresses_all, 8)

    groups = entity_data.get("groups") or {}
    genres = (groups.get("genre") or [])[:12]

    ranking_html = "".join(product_card(row, i) for i, row in enumerate(ranking, 1)) or '<p>ランキングを更新中です。</p>'
    deals_html = "".join(product_card(row) for row in deals) or '<p>セール情報を更新中です。</p>'
    actress_html = "".join(actress_card(row) for row in actresses) or '<p>人気女優データを更新中です。</p>'
    genre_html = "".join(genre_card(row) for row in genres) or '<a class="instant-genre" href="/ranking/genre/"><strong>ジャンル一覧</strong></a>'
    high_html = "".join(product_card(row) for row in high_rated)

    return f'''<main class="instant-home">
<section class="instant-hero"><div class="instant-wrap">
<div class="instant-eyebrow">18+ / すぐ探せる作品ナビ</div>
<h1>今すぐ、好みの作品を探す。</h1>
<p>説明を読む前に、人気作品・女優・ジャンル・セールからすぐ選べます。</p>
<div class="instant-actions"><a class="primary" href="#popular-now">人気作品を見る</a><a href="/ranking/actress/popular/">人気女優から探す</a><a href="/search/">作品名・女優名で検索</a></div>
<div class="instant-shortcuts"><a href="/ranking/">ランキング</a><a href="/sale/">セール</a><a href="/ranking/actress/">女優50音</a><a href="/ranking/genre/">ジャンル</a><a href="/fc2-adult/">FC2</a></div>
</div></section>

<section class="instant-section" id="popular-now"><div class="instant-wrap">
<div class="instant-section-head"><div><span>いま見るならここ</span><h2>人気作品</h2></div><a href="/ranking/">ランキングを全部見る →</a></div>
<div class="instant-product-grid">{ranking_html}</div>
</div></section>

<section class="instant-section instant-soft"><div class="instant-wrap">
<div class="instant-section-head"><div><span>顔から選びたい人向け</span><h2>人気女優から探す</h2></div><a href="/ranking/actress/popular/">人気女優を全部見る →</a></div>
<div class="instant-actress-grid">{actress_html}</div>
<div class="instant-under-links"><a href="/ranking/actress/">50音から女優を探す</a><a href="/search/">女優名を検索する</a></div>
</div></section>

<section class="instant-section"><div class="instant-wrap">
<div class="instant-section-head"><div><span>好みから絞る</span><h2>ジャンルから探す</h2></div><a href="/ranking/genre/">ジャンル一覧 →</a></div>
<div class="instant-genre-grid">{genre_html}</div>
</div></section>

<section class="instant-section instant-sale"><div class="instant-wrap">
<div class="instant-section-head"><div><span>安く見つけたい人向け</span><h2>セール作品</h2></div><a href="/sale/">セールを全部見る →</a></div>
<div class="instant-product-grid">{deals_html}</div>
</div></section>

{f'''<section class="instant-section"><div class="instant-wrap"><div class="instant-section-head"><div><span>評価から選ぶ</span><h2>高評価作品</h2></div><a href="/ranking/">ほかのランキング →</a></div><div class="instant-product-grid instant-small-grid">{high_html}</div></div></section>''' if high_html else ''}

<section class="instant-section instant-more"><div class="instant-wrap">
<h2>ほかの探し方</h2>
<div class="instant-more-grid"><a href="/products/"><strong>作品一覧</strong><span>新着から幅広く見る</span></a><a href="/search/"><strong>サイト内検索</strong><span>作品名・女優名から探す</span></a><a href="/subscription/"><strong>見放題比較</strong><span>月額でまとめて見たい</span></a><a href="/reviews/"><strong>レビュー</strong><span>評価を見てから決める</span></a><a href="/fc2-adult/"><strong>FC2アダルト</strong><span>FC2系から探す</span></a><a href="/guide/"><strong>初心者ガイド</strong><span>使い方を確認したい人向け</span></a></div>
<details class="instant-info"><summary>このサイトについて・PR表記</summary><p>商品情報・価格・販売状況は変動するため、購入前にリンク先の公式情報をご確認ください。当サイトにはアフィリエイト広告が含まれます。</p></details>
</div></section>
</main>'''


def main() -> None:
    if not HOME.exists():
        print("Homepage not found; skipped")
        return
    text = HOME.read_text(encoding="utf-8")
    before = text

    text = re.sub(r'<link\s+rel="stylesheet"\s+href="/assets/instant-discovery-v1\.css(?:\?v=[^"]*)?"\s*/?>', '', text, flags=re.I)
    if "</head>" in text:
        text = text.replace("</head>", f'<link rel="stylesheet" href="{CSS}"></head>', 1)

    text = re.sub(r'<main\b.*?</main>', build_main(), text, count=1, flags=re.S)

    text = re.sub(r'<title>.*?</title>', '<title>人気作品・女優・ジャンルからすぐ探す | オカズはよりどりみどり</title>', text, count=1, flags=re.S)
    text = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="FANZAの人気作品、人気女優、ジャンル、セールからすぐに作品を探せる成人向け作品ナビ。">', text, count=1)

    if text != before:
        HOME.write_text(text, encoding="utf-8")
        print("Homepage optimized for immediate discovery")
    else:
        print("Homepage already optimized")


if __name__ == "__main__":
    main()
