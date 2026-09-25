from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"
OUTPUT = Path("public/data/fanza-products.json")


def fetch_items(api_id: str, affiliate_id: str, sort: str, hits: int = 12) -> list[dict]:
    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": str(hits),
        "offset": "1",
        "sort": sort,
        "output": "json",
    }
    req = Request(
        API_URL + "?" + urlencode(params),
        headers={"User-Agent": "okazu-yoridori-midori/1.0"},
    )
    with urlopen(req, timeout=30) as res:
        payload = json.loads(res.read().decode("utf-8"))

    result = payload.get("result") or {}
    status = result.get("status")
    if status not in (200, "200"):
        raise RuntimeError(f"DMM API error: status={status!r}")

    normalized: list[dict] = []
    for item in result.get("items") or []:
        image = item.get("imageURL") or {}
        prices = item.get("prices") or {}
        review = item.get("review") or {}
        affiliate_url = item.get("affiliateURL") or ""
        if not affiliate_url:
            continue

        normalized.append(
            {
                "contentId": item.get("content_id") or "",
                "title": item.get("title") or "",
                "affiliateURL": affiliate_url,
                "imageURL": image.get("large") or image.get("small") or image.get("list") or "",
                "price": prices.get("price") or "",
                "reviewAverage": review.get("average") or "",
                "reviewCount": review.get("count") or 0,
                "date": item.get("date") or "",
            }
        )
    return normalized


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"

    if not api_id:
        print("DMM_API_ID is not configured; FANZA API cache generation skipped.")
        return

    ranking = fetch_items(api_id, affiliate_id, "rank")
    latest = fetch_items(api_id, affiliate_id, "date")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "affiliateId": affiliate_id,
                "ranking": ranking,
                "latest": latest,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT} ({len(ranking)} ranking, {len(latest)} latest)")


if __name__ == "__main__":
    main()
