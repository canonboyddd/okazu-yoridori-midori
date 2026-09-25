from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"
OUTPUT = Path("public/data/fanza-products.json")


def _names(iteminfo: dict, key: str, limit: int = 5) -> list[str]:
    values = iteminfo.get(key) or []
    out: list[str] = []
    for value in values:
        if isinstance(value, dict):
            name = str(value.get("name") or "").strip()
            if name:
                out.append(name)
        elif isinstance(value, str) and value.strip():
            out.append(value.strip())
        if len(out) >= limit:
            break
    return out


def _first_name(iteminfo: dict, key: str) -> str:
    values = _names(iteminfo, key, 1)
    return values[0] if values else ""


def _price_value(value: object) -> int | None:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def fetch_items(api_id: str, affiliate_id: str, sort: str, hits: int = 50) -> list[dict]:
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
        headers={"User-Agent": "okazu-yoridori-midori/3.0"},
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
        iteminfo = item.get("iteminfo") or {}
        affiliate_url = item.get("affiliateURL") or ""
        if not affiliate_url:
            continue

        price = prices.get("price") or ""
        list_price = prices.get("list_price") or ""
        price_value = _price_value(price)
        list_price_value = _price_value(list_price)
        discount_rate = None
        if price_value and list_price_value and list_price_value > price_value:
            discount_rate = round((1 - price_value / list_price_value) * 100)

        normalized.append(
            {
                "contentId": item.get("content_id") or "",
                "title": item.get("title") or "",
                "affiliateURL": affiliate_url,
                "imageURL": image.get("large") or image.get("small") or image.get("list") or "",
                "price": price,
                "priceValue": price_value,
                "listPrice": list_price,
                "listPriceValue": list_price_value,
                "discountRate": discount_rate,
                "reviewAverage": review.get("average") or "",
                "reviewCount": review.get("count") or 0,
                "date": item.get("date") or "",
                "maker": _first_name(iteminfo, "maker"),
                "series": _first_name(iteminfo, "series"),
                "actresses": _names(iteminfo, "actress", 4),
                "genres": _names(iteminfo, "genre", 5),
            }
        )
    return normalized


def _dedupe(*groups: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for group in groups:
        for item in group:
            key = str(item.get("contentId") or item.get("affiliateURL") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"

    if not api_id:
        print("DMM_API_ID is not configured; FANZA API cache generation skipped.")
        return

    ranking = fetch_items(api_id, affiliate_id, "rank", 50)
    latest = fetch_items(api_id, affiliate_id, "date", 50)
    catalog = _dedupe(ranking, latest)

    high_rated = sorted(
        [x for x in catalog if float(x.get("reviewAverage") or 0) > 0],
        key=lambda x: (float(x.get("reviewAverage") or 0), int(x.get("reviewCount") or 0)),
        reverse=True,
    )
    deals = sorted(
        [x for x in catalog if int(x.get("discountRate") or 0) > 0],
        key=lambda x: (int(x.get("discountRate") or 0), int(x.get("reviewCount") or 0)),
        reverse=True,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "affiliateId": affiliate_id,
        "ranking": ranking,
        "latest": latest,
        "highRated": high_rated[:50],
        "deals": deals[:50],
        "stats": {
            "rankingCount": len(ranking),
            "latestCount": len(latest),
            "highRatedCount": len(high_rated),
            "dealCount": len(deals),
        },
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {OUTPUT} ({len(ranking)} ranking, {len(latest)} latest, "
        f"{len(high_rated)} highRated, {len(deals)} deals)"
    )


if __name__ == "__main__":
    main()
