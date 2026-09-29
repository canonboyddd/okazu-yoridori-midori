from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path("public")
PRODUCT_ROOT = ROOT / "products"
DATA = ROOT / "data"
TARGET_FILES = int(os.environ.get("CLOUDFLARE_PAGES_TARGET_FILES", "19000"))
HARD_LIMIT = 20000
BASE_URL = "https://okazu-yoridori-midori.pages.dev"
DEFAULT_PROTECTED = {"1sods00082"}


def count_files() -> int:
    return sum(1 for p in ROOT.rglob("*") if p.is_file())


def safe_id(value: object) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")
    return s[:120]


def numeric(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def catalog_scores() -> dict[str, tuple]:
    scores: dict[str, tuple] = {}
    manifest_path = DATA / "full-catalog-manifest.json"
    if not manifest_path.exists():
        return scores
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return scores
    for shard in manifest.get("shards") or []:
        file_name = str((shard or {}).get("file") or "").lstrip("/")
        path = ROOT / file_name
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            cid = safe_id(row.get("contentId"))
            if not cid:
                continue
            scores[cid] = (
                1 if row.get("imageURL") else 0,
                1 if (row.get("actressEntities") or row.get("actresses")) else 0,
                int(row.get("reviewCount") or 0),
                numeric(row.get("reviewAverage")),
                int(row.get("discountRate") or 0),
                str(row.get("date") or ""),
            )
    return scores


def static_product_dirs() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    if not PRODUCT_ROOT.exists():
        return out
    for child in PRODUCT_ROOT.iterdir():
        if not child.is_dir() or child.name in {"view", "page"}:
            continue
        if (child / "index.html").exists():
            out.append((child.name, child))
    return out


def patch_html_links(removed: set[str]) -> int:
    if not removed:
        return 0
    pattern = re.compile(
        r"(?P<absolute>https://okazu-yoridori-midori\.pages\.dev)?/products/(?P<cid>[0-9A-Za-z_-]+)/"
    )
    changed = 0
    for path in ROOT.rglob("*.html"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue

        def repl(match: re.Match[str]) -> str:
            cid = match.group("cid")
            if cid not in removed:
                return match.group(0)
            prefix = match.group("absolute") or ""
            return f"{prefix}/products/view/?id={cid}"

        new_text = pattern.sub(repl, text)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
    return changed


def prune_sitemaps(removed: set[str]) -> int:
    if not removed:
        return 0
    changed = 0
    url_block = re.compile(r"\s*<url>.*?</url>", re.S)
    product = re.compile(r"/products/([0-9A-Za-z_-]+)/")
    for path in ROOT.glob("sitemap*.xml"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue

        def keep_or_drop(match: re.Match[str]) -> str:
            block = match.group(0)
            m = product.search(block)
            if m and m.group(1) in removed:
                return ""
            return block

        new_text = url_block.sub(keep_or_drop, text)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
    return changed


def main() -> None:
    before = count_files()
    print(f"Cloudflare file guard: current={before}, target={TARGET_FILES}, hard_limit={HARD_LIMIT}")
    if before <= TARGET_FILES:
        if before > HARD_LIMIT:
            raise SystemExit(f"File count {before} still exceeds Cloudflare Pages hard limit {HARD_LIMIT}")
        print("Cloudflare file guard: no pruning required")
        return

    protected = set(DEFAULT_PROTECTED)
    protected.update(
        safe_id(x)
        for x in os.environ.get("CLOUDFLARE_PROTECTED_PRODUCT_IDS", "").split(",")
        if safe_id(x)
    )
    scores = catalog_scores()
    candidates = [
        (scores.get(cid, (0, 0, 0, 0.0, 0, "")), cid, path)
        for cid, path in static_product_dirs()
        if cid not in protected
    ]
    candidates.sort(key=lambda x: (x[0], x[1]))

    removed: set[str] = set()
    current = before
    for _score, cid, path in candidates:
        if current <= TARGET_FILES:
            break
        removed_files = sum(1 for p in path.rglob("*") if p.is_file())
        shutil.rmtree(path)
        removed.add(cid)
        current -= max(1, removed_files)

    if current > TARGET_FILES:
        raise SystemExit(
            f"Unable to reach Cloudflare Pages target: current={current}, target={TARGET_FILES}, "
            f"removable_static_products={len(candidates)}"
        )

    sitemap_files = prune_sitemaps(removed)
    html_files = patch_html_links(removed)
    after = count_files()
    print(
        f"Cloudflare file guard complete: before={before}, after={after}, "
        f"static_products_pruned={len(removed)}, html_files_rewritten={html_files}, "
        f"sitemaps_updated={sitemap_files}"
    )
    if after > HARD_LIMIT:
        raise SystemExit(f"File count {after} exceeds Cloudflare Pages hard limit {HARD_LIMIT}")


if __name__ == "__main__":
    main()
