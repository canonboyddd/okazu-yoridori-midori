from __future__ import annotations

import html
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("public")
DATA = ROOT / "data"
CATALOG_DIR = DATA / "catalog"
ACTRESS_ROOT = ROOT / "ranking" / "actress"
CONFIG = Path("config/actress_aliases.json")
DIRECTORY_JSON = DATA / "fanza-actress-directory.json"
SEARCH_JSON = DATA / "site-search-index.json"
OUTPUT_JSON = DATA / "actress-alias-groups.json"
BASE_URL = "https://okazu-yoridori-midori.pages.dev"


def norm(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().casefold()


def safe_id(value: object) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return s[:120] or "item"


def price_text(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return f"¥{int(digits):,}" if digits else "公式で確認"


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
        path = ROOT / rel
        payload = load_json(path, [])
        if isinstance(payload, list):
            items.extend(x for x in payload if isinstance(x, dict))
    if not items and CATALOG_DIR.exists():
        for path in sorted(CATALOG_DIR.glob("catalog-*.json")):
            payload = load_json(path, [])
            if isinstance(payload, list):
                items.extend(x for x in payload if isinstance(x, dict))
    return items


def dedupe_items(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for item in items:
        key = str(item.get("contentId") or item.get("affiliateURL") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def card(item: dict, matched_names: set[str]) -> str:
    title = html.escape(str(item.get("title") or "FANZA作品"))
    image = html.escape(str(item.get("imageURL") or ""), quote=True)
    cid = safe_id(item.get("contentId"))
    static = ROOT / "products" / cid / "index.html"
    href = f"/products/{cid}/" if static.exists() else f"/products/view/?id={html.escape(cid, quote=True)}"
    credited = []
    for actress in item.get("actressEntities") or []:
        name = str(actress.get("name") or "").strip()
        if norm(name) in matched_names and name not in credited:
            credited.append(name)
    credit = " / ".join(credited)
    maker = str(item.get("maker") or "FANZA")
    price = price_text(item.get("price"))
    sub = maker + (f" / 掲載名: {credit}" if credit else "")
    return (
        f'<a class="fc-card" href="{href}">'
        f'<div class="fc-img"><img src="{image}" alt="{title}" loading="lazy"></div>'
        f'<div class="fc-body"><strong>{title}</strong><span>{html.escape(sub)}</span><b>{html.escape(price)}</b></div>'
        f'</a>'
    )


def page_head(title: str, desc: str, canonical: str, image: str = "") -> str:
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc, quote=True)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{html.escape(canonical, quote=True)}"><meta property="og:type" content="website"><meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:description" content="{html.escape(desc, quote=True)}"><meta property="og:url" content="{html.escape(canonical, quote=True)}"><meta property="og:image" content="{html.escape(image or BASE_URL + '/assets/og-default.png', quote=True)}"><link rel="stylesheet" href="/assets/style-white-v2.css?v=20260922-1322"><link rel="stylesheet" href="/assets/full-catalog.css?v=20260926-001"></head><body>'''


def header() -> str:
    return '''<header><div class="wrap header-inner"><a class="logo" href="/">オカズはよりどりみどり</a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/products/">作品一覧</a><a href="/search/">サイト内検索</a><a href="/guide/">初心者ガイド</a></nav></div></header>'''


def footer() -> str:
    return '''<footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり.</div></div></footer><script src="/assets/affiliate-config.js?v=20260928-0115"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js"></script><script src="/assets/affiliate-compliance.js?v=20260928-0115"></script>'''


def redirect_page(canonical_id: str, canonical_name: str, alias_name: str) -> str:
    target = f"/ranking/actress/{canonical_id}/"
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,follow"><link rel="canonical" href="{BASE_URL}{target}"><meta http-equiv="refresh" content="0;url={target}"><title>{html.escape(alias_name)}｜{html.escape(canonical_name)}の別名義</title></head><body><p>{html.escape(alias_name)}は{html.escape(canonical_name)}の別名義としてまとめています。<a href="{target}">統合ページへ移動</a></p><script>location.replace({json.dumps(target, ensure_ascii=False)});</script></body></html>'''


def main() -> None:
    cfg = load_json(CONFIG, {})
    groups = cfg.get("groups") or []
    if not groups:
        print("No actress alias groups configured")
        return

    items = load_catalog()
    if not items:
        raise SystemExit("Full catalog is missing; cannot build alias groups")

    directory_payload = load_json(DIRECTORY_JSON, {})
    directory = directory_payload.get("actresses") or []
    profile_by_id = {str(x.get("id")): x for x in directory if isinstance(x, dict) and x.get("id")}
    profiles_by_name: dict[str, list[dict]] = defaultdict(list)
    id_counts: dict[str, int] = defaultdict(int)
    name_to_ids: dict[str, set[str]] = defaultdict(set)

    for row in directory:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("id") or "").strip()
        name = str(row.get("name") or "").strip()
        if aid and name:
            profiles_by_name[norm(name)].append(row)
            name_to_ids[norm(name)].add(aid)

    for item in items:
        for actress in item.get("actressEntities") or []:
            aid = str(actress.get("id") or "").strip()
            name = str(actress.get("name") or "").strip()
            if aid and name:
                id_counts[aid] += 1
                name_to_ids[norm(name)].add(aid)

    resolved_groups: list[dict] = []
    alias_id_to_canonical: dict[str, tuple[str, str, str]] = {}
    search_alias_rows: list[dict] = []

    for group in groups:
        canonical = str(group.get("canonical") or "").strip()
        aliases = [str(x).strip() for x in (group.get("aliases") or []) if str(x).strip()]
        all_names = [canonical] + [x for x in aliases if x != canonical]
        matched_names = {norm(x) for x in all_names if x}
        if not canonical:
            continue

        candidate_ids: list[str] = []
        for aid in name_to_ids.get(norm(canonical), set()):
            candidate_ids.append(aid)
        if not candidate_ids:
            for alias in aliases:
                candidate_ids.extend(name_to_ids.get(norm(alias), set()))
        candidate_ids = sorted(set(candidate_ids), key=lambda aid: (-id_counts.get(aid, 0), aid))
        if not candidate_ids:
            print(f"WARN no actress id resolved for {canonical}")
            continue
        canonical_id = candidate_ids[0]

        alias_ids: set[str] = set()
        for name in all_names:
            alias_ids.update(name_to_ids.get(norm(name), set()))

        extra_ids = {norm(x) for x in (group.get("extraContentIds") or []) if str(x).strip()}
        title_aliases = [norm(x) for x in (group.get("titleAliases") or []) if len(str(x).strip()) >= 3]
        works: list[dict] = []
        for item in items:
            content_key = norm(item.get("contentId"))
            credited = {
                norm(a.get("name"))
                for a in (item.get("actressEntities") or [])
                if isinstance(a, dict) and a.get("name")
            }
            by_name = bool(credited & matched_names)
            by_id = content_key in extra_ids
            title_norm = norm(item.get("title"))
            by_title = any(alias in title_norm for alias in title_aliases)
            if by_name or by_id or by_title:
                works.append(item)
        works = dedupe_items(works)
        if not works:
            print(f"WARN no works found for {canonical}")
            continue

        profile = profile_by_id.get(canonical_id) or (profiles_by_name.get(norm(canonical)) or [{}])[0]
        image = str(profile.get("imageURL") or "")
        ruby = str(profile.get("ruby") or "")

        latest = sorted(works, key=lambda x: str(x.get("date") or ""), reverse=True)
        popular = sorted(
            works,
            key=lambda x: (
                int(x.get("reviewCount") or 0),
                float(x.get("reviewAverage") or 0) if str(x.get("reviewAverage") or "").replace(".", "", 1).isdigit() else 0,
                str(x.get("date") or ""),
            ),
            reverse=True,
        )

        alias_chips = "".join(f'<span class="fc-chip">{html.escape(name)}</span>' for name in aliases)
        extra_note = (
            f'<p class="fc-pr">別名義として確認できた名前：{alias_chips}</p>'
            if aliases else
            '<p class="fc-pr">別名義・別クレジット作品を同一人物として名寄せしています。</p>'
        )
        path = f"/ranking/actress/{canonical_id}/"
        out = ACTRESS_ROOT / canonical_id / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        profile_html = f'<img class="fc-actress-photo" src="{html.escape(image, quote=True)}" alt="{html.escape(canonical)}">' if image else ""
        desc = f"{canonical}の出演作品を、公開情報で確認できた別名義も含めて1ページにまとめています。現在{len(works)}作品。"
        schema = json.dumps({
            "@context": "https://schema.org",
            "@type": "ProfilePage",
            "name": canonical,
            "alternateName": aliases,
            "url": BASE_URL + path,
        }, ensure_ascii=False)
        page = page_head(f"{canonical}｜別名義を含む出演作品まとめ", desc, BASE_URL + path, image) + header() + f'''<main><section class="section"><div class="wrap"><div class="fc-breadcrumb"><a href="/">トップ</a> › <a href="/ranking/actress/">女優</a> › {html.escape(canonical)}</div><div class="fc-actress-head">{profile_html}<div><h1>{html.escape(canonical)}</h1>{f'<p>{html.escape(ruby)}</p>' if ruby else ''}<p>名寄せ後の出演作品：<strong>{len(works)}</strong>件</p></div></div>{extra_note}<h2>人気順</h2><div class="fc-grid">{''.join(card(x, matched_names) for x in popular)}</div><h2>新着順</h2><div class="fc-grid">{''.join(card(x, matched_names) for x in latest)}</div><p class="fc-pr">PR：当ページにはアフィリエイト広告を含みます。別名義情報は公開情報を参考に当サイトで整理しています。</p></div></section></main><script type="application/ld+json">{schema}</script>''' + footer() + "</body></html>"
        out.write_text(page, encoding="utf-8")

        for name in aliases:
            search_alias_rows.append({
                "type": "actress",
                "id": canonical_id,
                "title": name,
                "ruby": "",
                "image": image,
                "aliasOf": canonical,
            })
        search_alias_rows.append({
            "type": "actress",
            "id": canonical_id,
            "title": canonical,
            "ruby": ruby,
            "image": image,
            "aliases": aliases,
        })

        for alias_id in alias_ids:
            if alias_id == canonical_id:
                continue
            alias_name = next(
                (
                    str(row.get("name") or "")
                    for row in directory
                    if isinstance(row, dict) and str(row.get("id") or "") == alias_id
                ),
                "別名義",
            )
            alias_out = ACTRESS_ROOT / alias_id / "index.html"
            alias_out.parent.mkdir(parents=True, exist_ok=True)
            alias_out.write_text(redirect_page(canonical_id, canonical, alias_name), encoding="utf-8")
            alias_id_to_canonical[alias_id] = (canonical_id, canonical, alias_name)

        resolved_groups.append({
            "canonical": canonical,
            "canonicalId": canonical_id,
            "aliases": aliases,
            "aliasIds": sorted(alias_ids - {canonical_id}),
            "workCount": len(works),
            "extraContentIds": list(group.get("extraContentIds") or []),
            "sourceUrls": list(group.get("sourceUrls") or []),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        })

    # Make 50-on directory aliases land on the canonical merged page.
    changed_directory = False
    canonical_by_name = {norm(g["canonical"]): g for g in resolved_groups}
    for g in resolved_groups:
        for alias in g.get("aliases") or []:
            canonical_by_name[norm(alias)] = g
    for row in directory:
        if not isinstance(row, dict):
            continue
        g = canonical_by_name.get(norm(row.get("name")))
        if not g:
            continue
        if str(row.get("id") or "") != str(g["canonicalId"]):
            row["originalAliasId"] = row.get("id")
            row["id"] = str(g["canonicalId"])
            row["aliasOf"] = g["canonical"]
            row["hasDetail"] = True
            changed_directory = True
    if changed_directory:
        directory_payload["actresses"] = directory
        directory_payload["aliasMergedAt"] = datetime.now(timezone.utc).isoformat()
        DIRECTORY_JSON.write_text(json.dumps(directory_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Add canonical/alias names to site search, pointing every alias to the canonical page.
    search_rows = load_json(SEARCH_JSON, [])
    if isinstance(search_rows, list):
        alias_names = {norm(row.get("title")) for row in search_alias_rows}
        search_rows = [
            row for row in search_rows
            if not (isinstance(row, dict) and row.get("type") == "actress" and norm(row.get("title")) in alias_names)
        ]
        search_rows.extend(search_alias_rows)
        SEARCH_JSON.write_text(json.dumps(search_rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    OUTPUT_JSON.write_text(json.dumps({
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(resolved_groups),
        "groups": resolved_groups,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Build a discoverable alias hub.
    hub = ACTRESS_ROOT / "aliases" / "index.html"
    hub.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for g in resolved_groups:
        aliases = "、".join(g.get("aliases") or []) or "別名義作品あり"
        rows.append(
            f'<a class="entity-hub-card" href="/ranking/actress/{html.escape(str(g["canonicalId"]), quote=True)}/">'
            f'<div><strong>{html.escape(g["canonical"])}</strong><span>{html.escape(aliases)} / {int(g["workCount"])}作品</span></div></a>'
        )
    hub_page = page_head("同一女優・別名義まとめ", "名前が違っても同一人物と確認できた女優の作品を1ページに名寄せしています。", BASE_URL + "/ranking/actress/aliases/") + header() + f'''<main><section class="hub-hero"><div class="wrap"><h1>同一女優・別名義まとめ</h1><p>公開情報で同一人物と確認できた別名義を、作品単位で1ページにまとめています。</p></div></section><section class="section"><div class="wrap"><div class="entity-hub-grid">{''.join(rows) if rows else '<p>現在準備中です。</p>'}</div></div></section></main>''' + footer() + "</body></html>"
    hub.write_text(hub_page, encoding="utf-8")

    actress_index = ACTRESS_ROOT / "index.html"
    if actress_index.exists():
        text = actress_index.read_text(encoding="utf-8")
        marker = 'data-alias-hub-link="1"'
        if marker not in text:
            insert = '<div class="wrap" data-alias-hub-link="1" style="margin:18px auto"><a class="fc-search-link" href="/ranking/actress/aliases/">同一女優・別名義まとめを見る</a></div>'
            text = text.replace("</main>", insert + "</main>", 1)
            actress_index.write_text(text, encoding="utf-8")

    print(f"Alias merge complete: groups={len(resolved_groups)}, redirects={len(alias_id_to_canonical)}, catalog={len(items)}")


if __name__ == "__main__":
    main()
