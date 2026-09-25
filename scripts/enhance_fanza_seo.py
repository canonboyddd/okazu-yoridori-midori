from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://okazu-yoridori-midori.pages.dev"
ENTITY_DATA = Path("public/data/fanza-entity-rankings.json")
SITEMAP = Path("public/sitemap.xml")

CONFIG = {
    "actress": {"label": "女優", "field": "actressEntities"},
    "genre": {"label": "ジャンル", "field": "genreEntities"},
    "maker": {"label": "メーカー", "field": "makerEntities"},
}


def _jsonld(data: dict) -> str:
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"


def _breadcrumb(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": name,
                "item": BASE_URL + path,
            }
            for i, (name, path) in enumerate(items, 1)
        ],
    }


def _entity_itemlist(entity_type: str, rows: list[dict]) -> dict:
    label = CONFIG[entity_type]["label"]
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"FANZA {label}別人気作品ランキング一覧",
        "numberOfItems": len(rows),
        "itemListOrder": "https://schema.org/ItemListOrderDescending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": str(row.get("name") or ""),
                "url": f"{BASE_URL}/ranking/{entity_type}/{row.get('id')}/",
            }
            for i, row in enumerate(rows, 1)
        ],
    }


def _product_itemlist(entity_type: str, row: dict) -> dict:
    name = str(row.get("name") or "")
    label = CONFIG[entity_type]["label"]
    elements = []
    for i, item in enumerate(row.get("items") or [], 1):
        thing: dict = {
            "@type": "Thing",
            "name": str(item.get("title") or "FANZA商品"),
            "url": str(item.get("affiliateURL") or ""),
        }
        if item.get("imageURL"):
            thing["image"] = str(item["imageURL"])
        elements.append({"@type": "ListItem", "position": i, "item": thing})
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"{name}のFANZA人気作品ランキング",
        "description": f"{label}「{name}」に該当するFANZA作品を人気順に掲載しています。",
        "numberOfItems": len(elements),
        "itemListOrder": "https://schema.org/ItemListOrderDescending",
        "itemListElement": elements,
    }


def _inject_jsonld(path: Path, schemas: list[dict]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!-- FANZA_SEO_SCHEMA_START -->.*?<!-- FANZA_SEO_SCHEMA_END -->", "", text, flags=re.S)
    block = "<!-- FANZA_SEO_SCHEMA_START -->" + "".join(_jsonld(x) for x in schemas) + "<!-- FANZA_SEO_SCHEMA_END -->"
    text = text.replace("</head>", block + "</head>")
    path.write_text(text, encoding="utf-8")


def _related_links(entity_type: str, row: dict, allowed: dict[str, dict[str, str]]) -> str:
    counts: dict[str, Counter[str]] = {k: Counter() for k in CONFIG if k != entity_type}
    for item in row.get("items") or []:
        for other_type, cfg in CONFIG.items():
            if other_type == entity_type:
                continue
            for entity in item.get(cfg["field"]) or []:
                entity_id = str(entity.get("id") or "")
                if entity_id in allowed.get(other_type, {}):
                    counts[other_type][entity_id] += 1

    cards: list[str] = []
    for other_type, counter in counts.items():
        label = CONFIG[other_type]["label"]
        for entity_id, _ in counter.most_common(2):
            name = allowed[other_type][entity_id]
            cards.append(
                f'<a href="/ranking/{other_type}/{html.escape(entity_id, quote=True)}/">'
                f'<b>{html.escape(name)}の人気作品</b>'
                f'<span>{html.escape(label)}別ランキングで関連作品を見る</span></a>'
            )
    if not cards:
        return ""
    return '<section class="entity-related"><h2>関連ランキング</h2><div class="entity-nav">' + "".join(cards[:6]) + "</div></section>"


def _same_type_links(entity_type: str, rows: list[dict], current_index: int) -> str:
    label = CONFIG[entity_type]["label"]
    candidates = []
    for idx in (current_index - 1, current_index + 1, current_index + 2):
        if 0 <= idx < len(rows):
            candidates.append(rows[idx])
    if not candidates:
        return ""
    links = "".join(
        f'<a href="/ranking/{entity_type}/{html.escape(str(x.get("id") or ""), quote=True)}/">'
        f'<b>{html.escape(str(x.get("name") or ""))}</b><span>ほかの{html.escape(label)}の人気作品を見る</span></a>'
        for x in candidates
    )
    return '<section class="entity-related"><h2>ほかの' + html.escape(label) + 'ランキング</h2><div class="entity-nav">' + links + "</div></section>"


def _inject_internal_links(path: Path, block: str) -> None:
    if not path.exists() or not block:
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!-- FANZA_INTERNAL_START -->.*?<!-- FANZA_INTERNAL_END -->", "", text, flags=re.S)
    marker = '<div class="entity-nav"><a href="/ranking/'
    payload = "<!-- FANZA_INTERNAL_START -->" + block + "<!-- FANZA_INTERNAL_END -->"
    if marker in text:
        text = text.replace(marker, payload + marker, 1)
    else:
        text = text.replace('<div class="entity-api-note">', payload + '<div class="entity-api-note">', 1)
    path.write_text(text, encoding="utf-8")


def _inject_hub_crosslinks(path: Path, current_type: str) -> None:
    if not path.exists():
        return
    cards = []
    for entity_type, cfg in CONFIG.items():
        if entity_type == current_type:
            continue
        label = cfg["label"]
        cards.append(
            f'<a href="/ranking/{entity_type}/"><b>{html.escape(label)}別ランキング</b>'
            f'<span>{html.escape(label)}から人気作品を探す</span></a>'
        )
    cards.append('<a href="/ranking/"><b>総合ランキング</b><span>人気・新着・高評価・セールから探す</span></a>')
    block = '<section class="entity-related"><h2>ほかの条件から探す</h2><div class="entity-nav">' + "".join(cards) + "</div></section>"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!-- FANZA_INTERNAL_START -->.*?<!-- FANZA_INTERNAL_END -->", "", text, flags=re.S)
    payload = "<!-- FANZA_INTERNAL_START -->" + block + "<!-- FANZA_INTERNAL_END -->"
    text = text.replace('<div class="entity-api-note">', payload + '<div class="entity-api-note">', 1)
    path.write_text(text, encoding="utf-8")


def _update_sitemap_lastmod(dynamic_paths: list[str]) -> None:
    if not SITEMAP.exists():
        return
    text = SITEMAP.read_text(encoding="utf-8")
    today = datetime.now(timezone.utc).date().isoformat()
    paths = ["/", "/ranking/"] + dynamic_paths
    for p in paths:
        url = re.escape(BASE_URL + p)
        text = re.sub(
            rf"(<url><loc>{url}</loc><lastmod>)[^<]+(</lastmod></url>)",
            rf"\g<1>{today}\g<2>",
            text,
        )
    SITEMAP.write_text(text, encoding="utf-8")


def main() -> None:
    if not ENTITY_DATA.exists():
        print("FANZA entity data missing; SEO enhancement skipped.")
        return

    payload = json.loads(ENTITY_DATA.read_text(encoding="utf-8"))
    groups: dict[str, list[dict]] = payload.get("groups") or {}
    allowed: dict[str, dict[str, str]] = {
        entity_type: {str(row.get("id") or ""): str(row.get("name") or "") for row in rows}
        for entity_type, rows in groups.items()
    }

    dynamic_paths: list[str] = []
    for entity_type, cfg in CONFIG.items():
        rows = groups.get(entity_type) or []
        hub_path = Path("public") / "ranking" / entity_type / "index.html"
        hub_url_path = f"/ranking/{entity_type}/"
        dynamic_paths.append(hub_url_path)
        _inject_jsonld(
            hub_path,
            [
                _breadcrumb([("ホーム", "/"), ("ランキング", "/ranking/"), (f"{cfg['label']}別", hub_url_path)]),
                _entity_itemlist(entity_type, rows),
            ],
        )
        _inject_hub_crosslinks(hub_path, entity_type)

        for i, row in enumerate(rows):
            entity_id = str(row.get("id") or "")
            detail_path = Path("public") / "ranking" / entity_type / entity_id / "index.html"
            url_path = f"/ranking/{entity_type}/{entity_id}/"
            dynamic_paths.append(url_path)
            _inject_jsonld(
                detail_path,
                [
                    _breadcrumb([
                        ("ホーム", "/"),
                        ("ランキング", "/ranking/"),
                        (f"{cfg['label']}別", hub_url_path),
                        (str(row.get("name") or ""), url_path),
                    ]),
                    _product_itemlist(entity_type, row),
                ],
            )
            internal = _related_links(entity_type, row, allowed) + _same_type_links(entity_type, rows, i)
            _inject_internal_links(detail_path, internal)

    _update_sitemap_lastmod(dynamic_paths)
    print(f"SEO enhanced {len(dynamic_paths)} generated ranking URLs with JSON-LD, breadcrumbs and internal links")


if __name__ == "__main__":
    main()
