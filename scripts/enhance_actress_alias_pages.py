from __future__ import annotations

import html
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("public")
DATA = ROOT / "data"
CATALOG_DIR = DATA / "catalog"
ACTRESS_ROOT = ROOT / "ranking" / "actress"
CONFIG = Path("config/actress_aliases.json")
RESOLVED = DATA / "actress-alias-groups.json"
DIRECTORY_JSON = DATA / "fanza-actress-directory.json"
SUMMARY_JSON = DATA / "actress-profile-summary.json"
CSS = ROOT / "assets" / "actress-profile-v2.css"
BASE_URL = "https://okazu-yoridori-midori.pages.dev"


def norm(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().casefold()


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def load_catalog() -> list[dict]:
    manifest = load_json(DATA / "full-catalog-manifest.json", {})
    items: list[dict] = []
    for shard in manifest.get("shards") or []:
        rel = str(shard.get("file") or "").lstrip("/")
        payload = load_json(ROOT / rel, [])
        if isinstance(payload, list):
            items.extend(row for row in payload if isinstance(row, dict))
    if not items and CATALOG_DIR.exists():
        for path in sorted(CATALOG_DIR.glob("catalog-*.json")):
            payload = load_json(path, [])
            if isinstance(payload, list):
                items.extend(row for row in payload if isinstance(row, dict))
    return items


def safe_id(value: object) -> str:
    text = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return text[:120] or "item"


def price_text(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return f"¥{int(digits):,}" if digits else "公式で確認"


def dedupe(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = str(item.get("contentId") or item.get("affiliateURL") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def matching_works(items: list[dict], names: list[str], extra_ids: list[str], title_aliases: list[str]) -> list[dict]:
    wanted_names = {norm(name) for name in names if name}
    wanted_ids = {norm(cid) for cid in extra_ids if cid}
    wanted_titles = [norm(name) for name in title_aliases if len(str(name).strip()) >= 3]
    out: list[dict] = []
    for item in items:
        credits = {
            norm(row.get("name"))
            for row in (item.get("actressEntities") or [])
            if isinstance(row, dict) and row.get("name")
        }
        by_name = bool(credits & wanted_names)
        by_id = norm(item.get("contentId")) in wanted_ids
        title = norm(item.get("title"))
        by_title = any(alias in title for alias in wanted_titles)
        if by_name or by_id or by_title:
            out.append(item)
    return dedupe(out)


def rating_value(item: dict) -> float:
    value = str(item.get("reviewAverage") or "")
    try:
        return float(value)
    except ValueError:
        return 0.0


def card(item: dict, names: set[str]) -> str:
    title_raw = str(item.get("title") or "FANZA作品")
    title = html.escape(title_raw)
    image = html.escape(str(item.get("imageURL") or ""), quote=True)
    cid = safe_id(item.get("contentId"))
    static = ROOT / "products" / cid / "index.html"
    href = f"/products/{cid}/" if static.exists() else f"/products/view/?id={html.escape(cid, quote=True)}"
    credits: list[str] = []
    for actress in item.get("actressEntities") or []:
        name = str(actress.get("name") or "").strip()
        if norm(name) in names and name not in credits:
            credits.append(name)
    maker = str(item.get("maker") or "FANZA")
    credit_text = f" / 掲載名: {' / '.join(credits)}" if credits else ""
    discount = int(item.get("discountRate") or 0)
    sale = f'<span class="ap-sale">{discount}%OFF</span>' if discount > 0 else ""
    return (
        f'<a class="fc-card" href="{href}">'
        f'<div class="fc-img">{sale}<img src="{image}" alt="{title}" loading="lazy"></div>'
        f'<div class="fc-body"><strong>{title}</strong><span>{html.escape(maker + credit_text)}</span>'
        f'<b>{html.escape(price_text(item.get("price")))}</b></div></a>'
    )


def head(title: str, desc: str, canonical: str, image: str = "") -> str:
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc, quote=True)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{html.escape(canonical, quote=True)}"><meta property="og:type" content="profile"><meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:description" content="{html.escape(desc, quote=True)}"><meta property="og:url" content="{html.escape(canonical, quote=True)}"><meta property="og:image" content="{html.escape(image or BASE_URL + '/assets/og-default.png', quote=True)}"><link rel="stylesheet" href="/assets/style-white-v2.css?v=20260922-1322"><link rel="stylesheet" href="/assets/full-catalog.css?v=20260926-001"><link rel="stylesheet" href="/assets/actress-profile-v2.css?v=20260928-0200"></head><body>'''


def header() -> str:
    return '''<header><div class="wrap header-inner"><a class="logo" href="/">オカズはよりどりみどり</a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/products/">作品一覧</a><a href="/search/">サイト内検索</a><a href="/guide/">初心者ガイド</a></nav></div></header>'''


def footer() -> str:
    return '''<footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり.</div></div></footer><script src="/assets/affiliate-config.js?v=20260928-0115"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js"></script><script src="/assets/affiliate-compliance.js?v=20260928-0115"></script>'''


def entity_chips(works: list[dict], field: str, fallback: str, limit: int = 12) -> tuple[str, list[str]]:
    counter: Counter[tuple[str, str]] = Counter()
    for item in works:
        rows = item.get(field) or []
        if rows:
            for row in rows:
                if not isinstance(row, dict):
                    continue
                rid = str(row.get("id") or "").strip()
                name = str(row.get("name") or "").strip()
                if name:
                    counter[(rid, name)] += 1
        elif fallback:
            name = str(item.get(fallback) or "").strip()
            if name:
                counter[("", name)] += 1

    parts: list[str] = []
    names: list[str] = []
    base = "maker" if field == "makerEntities" else "genre"
    for (rid, name), count in counter.most_common(limit):
        names.append(name)
        label = f"{html.escape(name)} <small>{count}</small>"
        if rid:
            parts.append(f'<a class="ap-chip" href="/ranking/{base}/{html.escape(rid, quote=True)}/">{label}</a>')
        else:
            parts.append(f'<span class="ap-chip">{label}</span>')
    return "".join(parts), names


def write_css() -> None:
    CSS.parent.mkdir(parents=True, exist_ok=True)
    CSS.write_text(
        ".ap-hero{display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:center;margin:18px 0 24px}.ap-photo{width:140px;max-height:180px;object-fit:cover;border-radius:18px;box-shadow:0 10px 30px rgba(15,23,42,.12)}.ap-aliases{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.ap-chip{display:inline-flex;gap:6px;align-items:center;padding:7px 10px;border:1px solid #dbe4ee;border-radius:999px;background:#fff;color:#334155!important;text-decoration:none!important;font-weight:700}.ap-chip small{color:#64748b}.ap-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0}.ap-stat{padding:14px;border:1px solid #e2e8f0;border-radius:14px;background:#f8fafc}.ap-stat strong{display:block;font-size:1.45rem}.ap-stat span{color:#64748b;font-size:.82rem}.ap-meta{margin:24px 0}.ap-meta h2{margin-bottom:10px}.ap-chip-row{display:flex;gap:8px;flex-wrap:wrap}.ap-section-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin:32px 0 14px}.ap-all-cta{display:inline-flex;padding:12px 18px;border-radius:12px;background:#111827;color:#fff!important;text-decoration:none!important;font-weight:850}.ap-sale{position:absolute;top:9px;left:9px;z-index:2;background:#dc2626;color:#fff;padding:4px 7px;border-radius:999px;font-size:.72rem;font-weight:850}.fc-img{position:relative}.ap-source{margin-top:28px;padding:14px 16px;border:1px solid #e2e8f0;border-radius:14px;background:#f8fafc;color:#475569;font-size:.86rem;line-height:1.7}@media(max-width:720px){.ap-hero{grid-template-columns:1fr}.ap-photo{width:110px}.ap-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.ap-section-head{align-items:start;flex-direction:column}}",
        encoding="utf-8",
    )


def main() -> None:
    cfg = load_json(CONFIG, {})
    resolved = load_json(RESOLVED, {})
    items = load_catalog()
    if not items:
        raise SystemExit("Full catalog missing")
    resolved_groups = resolved.get("groups") or []
    if not resolved_groups:
        raise SystemExit("Resolved alias groups missing")

    cfg_by_canonical = {
        str(row.get("canonical") or "").strip(): row
        for row in (cfg.get("groups") or [])
        if isinstance(row, dict) and row.get("canonical")
    }
    directory = (load_json(DIRECTORY_JSON, {}) or {}).get("actresses") or []
    profile_by_id = {
        str(row.get("id")): row
        for row in directory
        if isinstance(row, dict) and row.get("id")
    }

    write_css()
    summaries: list[dict] = []

    for group in resolved_groups:
        canonical = str(group.get("canonical") or "").strip()
        canonical_id = str(group.get("canonicalId") or "").strip()
        if not canonical or not canonical_id:
            continue
        source = cfg_by_canonical.get(canonical, {})
        aliases = [str(x).strip() for x in (source.get("aliases") or group.get("aliases") or []) if str(x).strip()]
        names = [canonical, *aliases]
        name_keys = {norm(x) for x in names}
        works = matching_works(
            items,
            names,
            list(source.get("extraContentIds") or group.get("extraContentIds") or []),
            list(source.get("titleAliases") or []),
        )
        if not works:
            continue

        latest = sorted(works, key=lambda x: str(x.get("date") or ""), reverse=True)
        popular = sorted(
            works,
            key=lambda x: (int(x.get("reviewCount") or 0), rating_value(x), str(x.get("date") or "")),
            reverse=True,
        )
        sale = sorted(
            [x for x in works if int(x.get("discountRate") or 0) > 0],
            key=lambda x: (int(x.get("discountRate") or 0), int(x.get("reviewCount") or 0), str(x.get("date") or "")),
            reverse=True,
        )
        maker_html, makers = entity_chips(works, "makerEntities", "maker")
        genre_html, genres = entity_chips(works, "genreEntities", "")

        profile = profile_by_id.get(canonical_id) or {}
        image = str(profile.get("imageURL") or "")
        if not image:
            image = next((str(x.get("imageURL") or "") for x in latest if x.get("imageURL")), "")
        ruby = str(profile.get("ruby") or "")
        alias_text = "、".join(aliases)
        title = f"{canonical} AV作品一覧・別名義・出演作品 | オカズはよりどりみどり"
        desc = f"{canonical}のAV出演作品を{len(works)}件掲載。"
        if alias_text:
            desc += f"別名義（{alias_text}）も同一人物としてまとめ、新着・人気・セール作品、メーカー、ジャンルを確認できます。"
        else:
            desc += "新着・人気・セール作品、メーカー、ジャンルをまとめて確認できます。"

        alias_chips = "".join(f'<span class="ap-chip">{html.escape(name)}</span>' for name in aliases)
        photo = f'<img class="ap-photo" src="{html.escape(image, quote=True)}" alt="{html.escape(canonical)}">' if image else ""
        stats = (
            f'<div class="ap-stats"><div class="ap-stat"><strong>{len(works)}</strong><span>総作品数</span></div>'
            f'<div class="ap-stat"><strong>{len(aliases)}</strong><span>別名義</span></div>'
            f'<div class="ap-stat"><strong>{len(sale)}</strong><span>セール作品</span></div>'
            f'<div class="ap-stat"><strong>{len(makers)}</strong><span>主なメーカー</span></div></div>'
        )
        schema = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "ProfilePage",
                "name": f"{canonical} AV作品一覧・別名義・出演作品",
                "url": BASE_URL + f"/ranking/actress/{canonical_id}/",
                "mainEntity": {
                    "@type": "Person",
                    "name": canonical,
                    "alternateName": aliases,
                    "image": image or None,
                },
            },
            ensure_ascii=False,
        )
        popular_cards = "".join(card(x, name_keys) for x in popular[:12])
        latest_cards = "".join(card(x, name_keys) for x in latest[:12])
        sale_cards = "".join(card(x, name_keys) for x in sale[:12])
        source_count = len(source.get("sourceUrls") or [])
        main_url = BASE_URL + f"/ranking/actress/{canonical_id}/"
        works_url = f"/ranking/actress/{canonical_id}/works/"

        body = f'''<main><section class="section"><div class="wrap"><div class="fc-breadcrumb"><a href="/">トップ</a> › <a href="/ranking/actress/">女優</a> › {html.escape(canonical)}</div><div class="ap-hero">{photo}<div><h1>{html.escape(canonical)} AV作品一覧</h1>{f'<p>{html.escape(ruby)}</p>' if ruby else ''}{f'<div class="ap-aliases"><strong>別名義：</strong>{alias_chips}</div>' if aliases else '<p>別名義・別クレジット作品も同一人物として名寄せしています。</p>'}</div></div>{stats}<div class="ap-meta"><h2>出演メーカー</h2><div class="ap-chip-row">{maker_html or '<span class="ap-chip">情報なし</span>'}</div></div><div class="ap-meta"><h2>関連ジャンル</h2><div class="ap-chip-row">{genre_html or '<span class="ap-chip">情報なし</span>'}</div></div><div class="ap-section-head"><h2>人気作品</h2><a href="{works_url}">全作品を見る</a></div><div class="fc-grid">{popular_cards}</div><div class="ap-section-head"><h2>新着作品</h2><a href="{works_url}">新着をもっと見る</a></div><div class="fc-grid">{latest_cards}</div>{f'<div class="ap-section-head"><h2>セール作品</h2><a href="/sale/">セール一覧</a></div><div class="fc-grid">{sale_cards}</div>' if sale_cards else ''}<div class="ap-section-head"><h2>全出演作品</h2><a class="ap-all-cta" href="{works_url}">この女優の全作品を見る（{len(works)}件）</a></div><div class="ap-source">別名義情報は公開情報を参考に当サイトで整理しています。確認ソース数：{source_count}。PR：当ページにはアフィリエイト広告を含みます。</div></div></section></main>'''
        page = head(title, desc, main_url, image) + header() + body + f'<script type="application/ld+json">{schema}</script>' + footer() + "</body></html>"
        out = ACTRESS_ROOT / canonical_id / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")

        all_title = f"{canonical} 全AV作品一覧（{len(works)}件） | オカズはよりどりみどり"
        all_desc = f"{canonical}の出演作品{len(works)}件を新着順で一覧表示。" + (f"別名義（{alias_text}）を含みます。" if alias_text else "")
        all_body = f'''<main><section class="section"><div class="wrap"><div class="fc-breadcrumb"><a href="/">トップ</a> › <a href="/ranking/actress/">女優</a> › <a href="/ranking/actress/{html.escape(canonical_id, quote=True)}/">{html.escape(canonical)}</a> › 全作品</div><h1>{html.escape(canonical)} 全作品一覧</h1><p>{html.escape(all_desc)}</p><div class="fc-grid">{''.join(card(x, name_keys) for x in latest)}</div><p class="ap-source">掲載作品はFANZAカタログをもとに自動更新しています。PR：当ページにはアフィリエイト広告を含みます。</p></div></section></main>'''
        works_out = ACTRESS_ROOT / canonical_id / "works" / "index.html"
        works_out.parent.mkdir(parents=True, exist_ok=True)
        works_out.write_text(head(all_title, all_desc, BASE_URL + works_url, image) + header() + all_body + footer() + "</body></html>", encoding="utf-8")

        summaries.append({
            "personId": str(source.get("personId") or ""),
            "canonical": canonical,
            "canonicalId": canonical_id,
            "aliases": aliases,
            "workCount": len(works),
            "saleCount": len(sale),
            "makers": makers,
            "genres": genres,
            "url": f"/ranking/actress/{canonical_id}/",
            "worksUrl": works_url,
        })

    SUMMARY_JSON.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "count": len(summaries),
                "profiles": summaries,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"Enhanced actress alias pages: {len(summaries)}")


if __name__ == "__main__":
    main()
