from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"
ROOT = Path("public")
MANIFEST = ROOT / "data" / "full-catalog-manifest.json"
HITS = 100
REQUEST_DELAY = float(os.environ.get("DMM_COMMENT_REQUEST_DELAY", "0.12"))
MAX_PAGES = int(os.environ.get("DMM_COMMENT_MAX_PAGES", "0"))


def api_page(api_id: str, affiliate_id: str, offset: int) -> tuple[list[dict], int]:
    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": str(HITS),
        "offset": str(offset),
        "sort": "date",
        "output": "json",
    }
    req = Request(API_URL + "?" + urlencode(params), headers={"User-Agent": "okazu-comment-enricher/1.0"})
    last = None
    for attempt in range(4):
        try:
            with urlopen(req, timeout=60) as res:
                payload = json.loads(res.read().decode("utf-8"))
            result = payload.get("result") or {}
            if result.get("status") not in (200, "200"):
                raise RuntimeError(f"API status={result.get('status')} offset={offset}")
            total = int(result.get("total_count") or result.get("totalCount") or 0)
            rows = [x for x in (result.get("items") or []) if isinstance(x, dict)]
            return rows, total
        except Exception as exc:
            last = exc
            if attempt < 3:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"ItemList comment enrichment failed offset={offset}: {last}")


def collect_comments(api_id: str, affiliate_id: str, wanted: set[str]) -> dict[str, str]:
    comments: dict[str, str] = {}
    offset = 1
    page_no = 0
    reported_total = 0

    while wanted - comments.keys():
        rows, total = api_page(api_id, affiliate_id, offset)
        reported_total = max(reported_total, total)
        if not rows:
            break

        for item in rows:
            cid = str(item.get("content_id") or "").strip()
            if cid not in wanted:
                continue
            comment = str(item.get("comment") or item.get("description") or "").strip()
            if comment:
                comments[cid] = comment

        page_no += 1
        print(
            f"Comment API page={page_no} offset={offset} "
            f"matched={len(comments)}/{len(wanted)} reported_total={reported_total}"
        )
        if len(rows) < HITS or (reported_total and offset + HITS > reported_total):
            break
        if MAX_PAGES and page_no >= MAX_PAGES:
            print(f"Stopped by DMM_COMMENT_MAX_PAGES={MAX_PAGES}")
            break
        offset += HITS
        time.sleep(REQUEST_DELAY)

    return comments


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip()
    if not api_id or not affiliate_id:
        raise SystemExit("DMM_API_ID / DMM_API_AFFILIATE_ID are required")
    if not MANIFEST.exists():
        raise SystemExit("full-catalog-manifest.json is missing")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    shard_paths: list[Path] = []
    wanted: set[str] = set()

    for shard in manifest.get("shards") or []:
        rel = str(shard.get("file") or "").lstrip("/")
        if not rel:
            continue
        path = ROOT / rel
        if not path.exists():
            continue
        shard_paths.append(path)
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("contentId") or "").strip()
            if cid:
                wanted.add(cid)

    if not wanted:
        raise SystemExit("No catalog content IDs found")

    comments = collect_comments(api_id, affiliate_id, wanted)
    patched_rows = 0
    patched_shards = 0

    for path in shard_paths:
        rows = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("contentId") or "").strip()
            comment = comments.get(cid, "")
            if comment and row.get("comment") != comment:
                row["comment"] = comment
                patched_rows += 1
                changed = True
        if changed:
            path.write_text(
                json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            patched_shards += 1

    print(
        f"FANZA comments enriched: catalog_items={len(wanted)} "
        f"comments_found={len(comments)} rows_patched={patched_rows} shards_patched={patched_shards}"
    )


if __name__ == "__main__":
    main()
