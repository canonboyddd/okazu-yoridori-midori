from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path("public")
DATA = ROOT / "data"
PRODUCT_ROOT = ROOT / "products"
CSS = ROOT / "assets" / "product-page-v2.css"
START = "<!-- PRODUCT_PAGE_V2_START -->"
END = "<!-- PRODUCT_PAGE_V2_END -->"
CSS_LINK = '<link rel="stylesheet" href="/assets/product-page-v2.css?v=20260928-1107">'


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def safe_id(value: object) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return s[:120] or "item"


def load_catalog() -> list[dict]:
    manifest = load_json(DATA / "full-catalog-manifest.json", {})
    rows: list[dict] = []
    for shard in manifest.get("shards") or []:
        rel = str(shard.get("file") or "").lstrip("/")
        payload = load_json(ROOT / rel, [])
        if isinstance(payload, list):
            rows.extend(x for x in payload if isinstance(x, dict))
    return rows


def rating(item: dict) -> float:
    try:
        return float(item.get("reviewAverage") or 0)
    except Exception:
        return 0.0


def rank_key(item: dict) -> tuple:
    return (
        int(item.get("reviewCount") or 0),
        rating(item),
        int(item.get("discountRate") or 0),
        str(item.get("date") or ""),
    )


def price_text(item: dict) -> str:
    raw = str(item.get("price") or "")
    digits = "".join(ch for ch in raw if ch.isdigit())
    return f"¥{int(digits):,}" if digits else "公式で確認"


def internal_href(item: dict) -> str:
    cid = safe_id(item.get("contentId"))
    if (PRODUCT_ROOT / cid / "index.html").exists():
        return f"/products/{cid}/"
    return f"/products/view/?id={html.escape(cid, quote=True)}"


def card(item: dict) -> str:
    title = str(item.get("title") or "FANZA作品")
    image = str(item.get("imageURL") or "")
    maker = str(item.get("maker") or "FANZA")
    discount = int(item.get("discountRate") or 0)
    sale = f'<span class="ppv2-sale">{discount}%OFF</span>' if discount > 0 else ""
    return (
        f'<a class="fc-card ppv2-card" href="{internal_href(item)}">'
        f'<div class="fc-img">{sale}<img src="{html.escape(image, quote=True)}" alt="{html.escape(title, quote=True)}" loading="lazy"></div>'
        f'<div class="fc-body"><strong>{html.escape(title)}</strong><span>{html.escape(maker)}</span>'
        f'<b>{html.escape(price_text(item))}</b></div></a>'
    )


def related(pool: list[dict], current_id: str, limit: int = 4) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in sorted(pool, key=rank_key, reverse=True):
        cid = safe_id(item.get("contentId"))
        if not cid or cid == current_id or cid in seen:
            continue
        seen.add(cid)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def feature_chips(item: dict) -> str:
    chips: list[str] = []
    for actress in (item.get("actressEntities") or [])[:3]:
        name = str(actress.get("name") or "").strip()
        if name:
            chips.append(name)
    maker = str(item.get("maker") or "").strip()
    if maker:
        chips.append(maker)
    for genre in (item.get("genreEntities") or [])[:5]:
        name = str(genre.get("name") or "").strip()
        if name:
            chips.append(name)
    discount = int(item.get("discountRate") or 0)
    if discount:
        chips.append(f"{discount}%OFF")
    count = int(item.get("reviewCount") or 0)
    avg = str(item.get("reviewAverage") or "").strip()
    if count and avg:
        chips.append(f"★{avg} / {count}件")
    date = str(item.get("date") or "").strip()
    if date:
        chips.append(f"配信 {date[:10]}")

    uniq: list[str] = []
    for chip in chips:
        if chip not in uniq:
            uniq.append(chip)
    return "".join(f'<span class="ppv2-chip">{html.escape(x)}</span>' for x in uniq[:10])


def write_css() -> None:
    CSS.parent.mkdir(parents=True, exist_ok=True)
    CSS.write_text(
        ".ppv2-top-cta{display:flex!important;margin:14px 0 18px!important;min-height:48px}.ppv2-features{margin:20px 0;padding:18px;border:1px solid #e5e7eb;border-radius:16px;background:#fff}.ppv2-features h2{font-size:1.05rem;margin:0 0 10px}.ppv2-chip-row{display:flex;flex-wrap:wrap;gap:8px}.ppv2-chip{display:inline-flex;padding:7px 10px;border-radius:999px;background:#f3f4f6;color:#374151;font-size:.82rem;font-weight:700}.ppv2-related{margin:34px 0}.ppv2-related-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:14px}.ppv2-related-head h2{margin:0;font-size:1.25rem}.ppv2-related-head a{font-weight:800}.ppv2-card .fc-body strong{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.ppv2-sale{position:absolute;top:8px;left:8px;z-index:2;background:#dc2626;color:#fff;padding:4px 7px;border-radius:999px;font-size:.72rem;font-weight:850}.fc-img{position:relative}.ppv2-bottom-cta{display:flex;justify-content:center;margin:30px 0 8px}.ppv2-bottom-cta a{display:inline-flex;align-items:center;justify-content:center;min-width:min(520px,100%);padding:14px 20px;border-radius:14px;background:linear-gradient(90deg,#ec1769,#7c3aed);color:#fff!important;text-decoration:none!important;font-weight:850}.ppv2-more-actress{display:inline-flex;margin-top:10px;padding:10px 14px;border-radius:12px;border:1px solid #dbe4ee;text-decoration:none!important;font-weight:800}@media(max-width:720px){.ppv2-related-head{align-items:start;flex-direction:column}.ppv2-features{padding:14px}}",
        encoding="utf-8",
    )


def build_block(item: dict, by_actress, by_maker, by_genre) -> str:
    cid = safe_id(item.get("contentId"))
    actresses = item.get("actressEntities") or []
    makers = item.get("makerEntities") or []
    genres = item.get("genreEntities") or []

    primary_actress = actresses[0] if actresses else {}
    actress_id = str(primary_actress.get("id") or "").strip()
    actress_name = str(primary_actress.get("name") or "").strip()
    maker_id = str((makers[0] if makers else {}).get("id") or "").strip()
    maker_name = str((makers[0] if makers else {}).get("name") or item.get("maker") or "").strip()
    genre_id = str((genres[0] if genres else {}).get("id") or "").strip()
    genre_name = str((genres[0] if genres else {}).get("name") or "").strip()

    sections: list[str] = []
    same_actress = related(by_actress.get(actress_id, []), cid) if actress_id else []
    if same_actress:
        more = f'/ranking/actress/{html.escape(actress_id, quote=True)}/' if actress_id else '#'
        sections.append(
            '<section class="ppv2-related"><div class="ppv2-related-head">'
            f'<h2>{html.escape(actress_name or "同じ女優")}の関連作品</h2>'
            f'<a href="{more}">この女優の作品をもっと見る</a></div>'
            f'<div class="fc-grid">{"".join(card(x) for x in same_actress)}</div></section>'
        )

    same_maker = related(by_maker.get(maker_id, []), cid) if maker_id else []
    if same_maker:
        more = f'/ranking/maker/{html.escape(maker_id, quote=True)}/'
        sections.append(
            '<section class="ppv2-related"><div class="ppv2-related-head">'
            f'<h2>{html.escape(maker_name or "同じメーカー")}の関連作品</h2>'
            f'<a href="{more}">メーカー作品一覧</a></div>'
            f'<div class="fc-grid">{"".join(card(x) for x in same_maker)}</div></section>'
        )

    same_genre = related(by_genre.get(genre_id, []), cid) if genre_id else []
    if same_genre:
        more = f'/ranking/genre/{html.escape(genre_id, quote=True)}/'
        sections.append(
            '<section class="ppv2-related"><div class="ppv2-related-head">'
            f'<h2>「{html.escape(genre_name or "同ジャンル")}」のおすすめ</h2>'
            f'<a href="{more}">同ジャンルをもっと見る</a></div>'
            f'<div class="fc-grid">{"".join(card(x) for x in same_genre)}</div></section>'
        )

    affiliate = html.escape(str(item.get("affiliateURL") or ""), quote=True)
    bottom = (
        f'<div class="ppv2-bottom-cta"><a href="{affiliate}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate-target="product-bottom">FANZA公式でこの作品を確認</a></div>'
        if affiliate else ""
    )
    features = (
        '<section class="ppv2-features"><h2>作品の特徴</h2>'
        f'<div class="ppv2-chip-row">{feature_chips(item)}</div>'
        + (f'<a class="ppv2-more-actress" href="/ranking/actress/{html.escape(actress_id, quote=True)}/">{html.escape(actress_name)}の作品一覧を見る</a>' if actress_id and actress_name else "")
        + '</section>'
    )
    return START + features + "".join(sections) + bottom + END


def patch_page(path: Path, item: dict, by_actress, by_maker, by_genre) -> bool:
    text = path.read_text(encoding="utf-8")
    before = text
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), "", text, flags=re.S)
    if CSS_LINK not in text:
        text = text.replace("</head>", CSS_LINK + "</head>", 1)

    affiliate = html.escape(str(item.get("affiliateURL") or ""), quote=True)
    if affiliate and "ppv2-top-cta" not in text:
        top = f'<a class="fc-cta ppv2-top-cta" href="{affiliate}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate-target="product-top">FANZAでこの作品を見る</a>'
        text = re.sub(r'(<div class="fc-price">.*?</div>)', r'\1' + top, text, count=1, flags=re.S)

    block = build_block(item, by_actress, by_maker, by_genre)
    marker = '<p class="fc-pr">'
    if marker in text:
        text = text.replace(marker, block + marker, 1)
    else:
        text = text.replace("</main>", block + "</main>", 1)

    if text != before:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    items = load_catalog()
    if not items:
        print("Product page V2 skipped: full catalog missing")
        return

    by_id = {safe_id(x.get("contentId")): x for x in items if x.get("contentId")}
    by_actress: dict[str, list[dict]] = defaultdict(list)
    by_maker: dict[str, list[dict]] = defaultdict(list)
    by_genre: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        for row in item.get("actressEntities") or []:
            rid = str(row.get("id") or "").strip()
            if rid:
                by_actress[rid].append(item)
        for row in item.get("makerEntities") or []:
            rid = str(row.get("id") or "").strip()
            if rid:
                by_maker[rid].append(item)
        for row in item.get("genreEntities") or []:
            rid = str(row.get("id") or "").strip()
            if rid:
                by_genre[rid].append(item)

    write_css()
    patched = 0
    for cid, item in by_id.items():
        path = PRODUCT_ROOT / cid / "index.html"
        if path.exists() and patch_page(path, item, by_actress, by_maker, by_genre):
            patched += 1
    print(f"Product page V2: catalog={len(items)} static_pages_patched={patched}")


if __name__ == "__main__":
    main()
