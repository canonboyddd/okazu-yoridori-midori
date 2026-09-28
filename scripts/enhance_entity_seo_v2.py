from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path("public")
DATA = ROOT / "data"
PRODUCT_ROOT = ROOT / "products"
ACTRESS_ROOT = ROOT / "ranking" / "actress"


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
    out: list[dict] = []
    for shard in manifest.get("shards") or []:
        rel = str(shard.get("file") or "").lstrip("/")
        payload = load_json(ROOT / rel, [])
        if isinstance(payload, list):
            out.extend(x for x in payload if isinstance(x, dict))
    return out


def replace_meta(text: str, name: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    pattern = rf'<meta name="{re.escape(name)}" content="[^"]*">'
    tag = f'<meta name="{name}" content="{escaped}">'
    if re.search(pattern, text):
        return re.sub(pattern, tag, text, count=1)
    return text.replace("</head>", tag + "</head>", 1)


def replace_og(text: str, prop: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    pattern = rf'<meta property="{re.escape(prop)}" content="[^"]*">'
    tag = f'<meta property="{prop}" content="{escaped}">'
    if re.search(pattern, text):
        return re.sub(pattern, tag, text, count=1)
    return text.replace("</head>", tag + "</head>", 1)


def patch_product(path: Path, row: dict) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    before = text
    title_raw = str(row.get("title") or "FANZA作品").strip()
    actress_names = [str(x.get("name") or "").strip() for x in (row.get("actressEntities") or []) if str(x.get("name") or "").strip()]
    maker = str(row.get("maker") or "").strip()
    genres = [str(x.get("name") or "").strip() for x in (row.get("genreEntities") or []) if str(x.get("name") or "").strip()][:3]
    lead = "・".join(actress_names[:2])
    seo_title = f"{lead}出演｜{title_raw}｜FANZA作品情報" if lead else f"{title_raw}｜FANZA作品情報"
    details = []
    if maker:
        details.append(maker)
    if genres:
        details.append("・".join(genres))
    seo_desc = (f"{lead}出演「{title_raw}」のFANZA作品情報。" if lead else f"「{title_raw}」のFANZA作品情報。")
    if details:
        seo_desc += "、".join(details) + "、レビュー、関連作品を掲載。"
    else:
        seo_desc += "出演者、メーカー、ジャンル、レビュー、関連作品を掲載。"
    seo_desc += "価格・配信状況はFANZA公式で確認できます。"
    seo_desc = seo_desc[:155]

    text = re.sub(r"<title>.*?</title>", f"<title>{html.escape(seo_title)}</title>", text, count=1, flags=re.S)
    text = replace_meta(text, "description", seo_desc)
    text = replace_og(text, "og:title", seo_title)
    text = replace_og(text, "og:description", seo_desc)
    if text != before:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def patch_actress(path: Path, canonical: str, aliases: list[str], work_count: int, works_page: bool = False) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    before = text
    alias_text = "・".join(aliases[:5])
    if works_page:
        seo_title = f"{canonical} AV全作品一覧（{work_count}件）・FANZA出演作品"
        seo_desc = f"{canonical}のAV出演作品{work_count}件を一覧掲載。"
    else:
        seo_title = f"{canonical} AV作品一覧・別名義・出演作品・FANZA情報"
        seo_desc = f"{canonical}のAV出演作品を{work_count}件掲載。"
    if alias_text:
        seo_desc += f"別名義（{alias_text}）も同一人物としてまとめています。"
    seo_desc += "新着・人気・セール作品、メーカー、ジャンルから探せます。"
    seo_desc = seo_desc[:155]

    text = re.sub(r"<title>.*?</title>", f"<title>{html.escape(seo_title)} | オカズはよりどりみどり</title>", text, count=1, flags=re.S)
    text = replace_meta(text, "description", seo_desc)
    text = replace_og(text, "og:title", seo_title)
    text = replace_og(text, "og:description", seo_desc)
    if text != before:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    items = load_catalog()
    product_patched = 0
    for row in items:
        cid = safe_id(row.get("contentId"))
        if patch_product(PRODUCT_ROOT / cid / "index.html", row):
            product_patched += 1

    summary = load_json(DATA / "actress-profile-summary.json", {})
    actress_patched = 0
    for profile in summary.get("profiles") or []:
        canonical = str(profile.get("canonical") or "").strip()
        canonical_id = str(profile.get("canonicalId") or "").strip()
        aliases = [str(x).strip() for x in (profile.get("aliases") or []) if str(x).strip()]
        work_count = int(profile.get("workCount") or 0)
        if not canonical or not canonical_id:
            continue
        if patch_actress(ACTRESS_ROOT / canonical_id / "index.html", canonical, aliases, work_count, False):
            actress_patched += 1
        if patch_actress(ACTRESS_ROOT / canonical_id / "works" / "index.html", canonical, aliases, work_count, True):
            actress_patched += 1

    print(f"Entity SEO V2: product_pages={product_patched} actress_pages={actress_patched}")


if __name__ == "__main__":
    main()
