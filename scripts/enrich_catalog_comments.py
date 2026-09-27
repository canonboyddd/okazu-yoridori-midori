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
    last: Exception | None = None
    for attempt in range(4):
        try:
            with urlopen(req, timeout=60) as res:
                payload = json.loads(res.read().decode("utf-8"))
            result = payload.get("result") or {}
            if result.get("status") not in (200, "200"):
                raise RuntimeError(f"API status={result.get('status')} offset={offset}")
            total = int(result.get("total_count") or result.get("totalCount") or 0)
            items = [x for x in (result.get("items") or []) if isinstance(x, dict)]
            return items, total
        except Exception as exc:
            last = exc
            if attempt < 3:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"ItemList failed offset={offset}: {last}")


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip()
    if not api_id or not affiliate_id:
        raise SystemExit("DMM_API_ID and DMM_API_AFFILIATE_ID are required")
    if not MANIFEST.exists():
        raise SystemExit("Full catalog manifest is missing")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    shard_docs: list[tuple[Path, list[dict]]] = []
    by_content_id: dict[str, dict] = {}

    for shard in manifest.get("shards") or []:
        rel = str(shard.get("file") or "").lstrip("/")
        if not rel:
            continue
        path = ROOT / rel
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            continue
        shard_docs.append((path, rows))
        for row in rows:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("contentId") or "").strip()
            if cid:
                by_content_id[cid] = row

    if not by_content_id:
        raise SystemExit("Catalog contains no product IDs")

    target_count = len(by_content_id)
    matched = 0
    comments = 0
    changed = 0
    seen: set[str] = set()
    offset = 1
    reported_total = 0

    while True:
        items, total = api_page(api_id, affiliate_id, offset)
        reported_total = max(reported_total, total)
        if not items:
            break

        for item in items:
            cid = str(item.get("content_id") or "").strip()
            if not cid or cid in seen:
                continue
            seen.add(cid)
            row = by_content_id.get(cid)
            if row is None:
                continue
            matched += 1
            comment = str(item.get("comment") or "").strip()
            if comment:
                comments += 1
                if row.get("comment") != comment:
                    row["comment"] = comment
                    changed += 1

        print(
            f"Comment enrichment offset={offset} matched={matched}/{target_count} "
            f"comments={comments} reported_total={reported_total}"
        )

        if matched >= target_count:
            break
        if len(items) < HITS or (reported_total and offset + HITS > reported_total):
            break
        offset += HITS
        time.sleep(REQUEST_DELAY)

    for path, rows in shard_docs:
        path.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    summary = {
        "catalogProducts": target_count,
        "matchedProducts": matched,
        "productsWithOfficialComment": comments,
        "rowsUpdated": changed,
    }
    out = ROOT / "data" / "product-description-enrichment.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Product comment enrichment:", summary)


if __name__ == "__main__":
    main()
