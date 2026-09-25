from __future__ import annotations

import json
import os
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.dmm.com/affiliate/v3"
OUT = Path("public/data/fanza-actress-directory.json")
TARGET = 10_000
HITS = 100
PAGES_PER_INITIAL = 3

BASE_KANA = list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん")
VARIANTS = {
    "か": "が", "き": "ぎ", "く": "ぐ", "け": "げ", "こ": "ご",
    "さ": "ざ", "し": "じ", "す": "ず", "せ": "ぜ", "そ": "ぞ",
    "た": "だ", "ち": "ぢ", "つ": "づ", "て": "で", "と": "ど",
    "は": "ばぱ", "ひ": "びぴ", "ふ": "ぶぷ", "へ": "べぺ", "ほ": "ぼぽ",
}


def api_json(endpoint: str, params: dict[str, str], retries: int = 3) -> dict:
    url = f"{API_BASE}/{endpoint}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "okazu-yoridori-midori-balanced-actress/1.0"})
    last = None
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=45) as res:
                payload = json.loads(res.read().decode("utf-8"))
            result = payload.get("result") or {}
            status = result.get("status")
            if status not in (200, "200"):
                raise RuntimeError(f"status={status!r}")
            return result
        except Exception as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(last)


def image_url(row: dict) -> str:
    value = row.get("imageURL") or row.get("image_url") or {}
    if isinstance(value, dict):
        return str(value.get("large") or value.get("small") or value.get("list") or "")
    return str(value or "")


def normalize_hira(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    chars = []
    for ch in value:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            ch = chr(code - 0x60)
        chars.append(ch)
    value = "".join(chars)
    value = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn")


def base_initial(row: dict) -> str:
    source = normalize_hira(str(row.get("ruby") or row.get("name") or "")).strip()
    if not source:
        return ""
    c = source[0]
    voiced_to_base = {
        "が":"か","ぎ":"き","ぐ":"く","げ":"け","ご":"こ",
        "ざ":"さ","じ":"し","ず":"す","ぜ":"せ","ぞ":"そ",
        "だ":"た","ぢ":"ち","づ":"つ","で":"て","ど":"と",
        "ば":"は","び":"ひ","ぶ":"ふ","べ":"へ","ぼ":"ほ",
        "ぱ":"は","ぴ":"ひ","ぷ":"ふ","ぺ":"へ","ぽ":"ほ",
    }
    return voiced_to_base.get(c, c)


def normalize_row(row: dict) -> dict | None:
    actress_id = str(row.get("id") or row.get("actress_id") or "").strip()
    name = str(row.get("name") or "").strip()
    if not actress_id or not name:
        return None
    return {
        "id": actress_id,
        "name": name,
        "ruby": str(row.get("ruby") or "").strip(),
        "imageURL": image_url(row),
        "birthday": str(row.get("birthday") or "").strip(),
        "height": row.get("height") or "",
    }


def fetch_initial(api_id: str, affiliate_id: str, initial: str) -> list[dict]:
    rows_out: list[dict] = []
    for page in range(PAGES_PER_INITIAL):
        offset = page * HITS + 1
        result = api_json("ActressSearch", {
            "api_id": api_id,
            "affiliate_id": affiliate_id,
            "initial": initial,
            "hits": str(HITS),
            "offset": str(offset),
            "output": "json",
        })
        rows = result.get("actress") or result.get("actresses") or result.get("items") or []
        if not rows:
            break
        for raw in rows:
            if isinstance(raw, dict):
                row = normalize_row(raw)
                if row:
                    rows_out.append(row)
        if len(rows) < HITS:
            break
        time.sleep(0.08)
    return rows_out


def sequential_fallback(api_id: str, affiliate_id: str, seen: set[str], need: int) -> list[dict]:
    out: list[dict] = []
    offset = 1
    while len(out) < need and offset <= 30000:
        result = api_json("ActressSearch", {
            "api_id": api_id,
            "affiliate_id": affiliate_id,
            "hits": str(HITS),
            "offset": str(offset),
            "output": "json",
        })
        rows = result.get("actress") or result.get("actresses") or result.get("items") or []
        if not rows:
            break
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            row = normalize_row(raw)
            if not row or row["id"] in seen:
                continue
            seen.add(row["id"])
            out.append(row)
            if len(out) >= need:
                break
        if len(rows) < HITS:
            break
        offset += HITS
        time.sleep(0.08)
    return out


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"
    if not api_id:
        print("DMM_API_ID missing; balanced actress directory skipped")
        return

    buckets: dict[str, list[dict]] = defaultdict(list)
    seen: set[str] = set()

    for base in BASE_KANA:
        query_chars = base + VARIANTS.get(base, "")
        for initial in query_chars:
            try:
                rows = fetch_initial(api_id, affiliate_id, initial)
            except Exception as exc:
                print(f"WARN initial={initial}: {exc}")
                continue
            for row in rows:
                if row["id"] in seen:
                    continue
                bucket = base_initial(row)
                if bucket not in BASE_KANA:
                    continue
                seen.add(row["id"])
                buckets[bucket].append(row)
        print(f"kana {base}: {len(buckets[base])}")

    # Prefer profiles with official photos, while keeping broad 50-on coverage.
    for kana in BASE_KANA:
        buckets[kana].sort(key=lambda r: (not bool(r.get("imageURL")), str(r.get("ruby") or r.get("name") or "")))

    selected: list[dict] = []
    quota = max(1, TARGET // len(BASE_KANA))
    for kana in BASE_KANA:
        selected.extend(buckets[kana][:quota])

    # Round-robin remaining records so no early kana monopolizes the 10,000 slots.
    idx = quota
    while len(selected) < TARGET:
        added = 0
        for kana in BASE_KANA:
            bucket = buckets[kana]
            if idx < len(bucket):
                selected.append(bucket[idx])
                added += 1
                if len(selected) >= TARGET:
                    break
        if added == 0:
            break
        idx += 1

    if len(selected) < TARGET:
        selected_ids = {row["id"] for row in selected}
        selected.extend(sequential_fallback(api_id, affiliate_id, selected_ids, TARGET - len(selected)))

    selected = selected[:TARGET]
    detail_root = Path("public/ranking/actress")
    detail_ids = {p.parent.name for p in detail_root.glob("*/index.html") if p.parent.name.isdigit()}
    for row in selected:
        row["hasDetail"] = row["id"] in detail_ids

    OUT.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps({
        "generatedAt": generated_at,
        "count": len(selected),
        "actresses": selected,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    counts = defaultdict(int)
    photo_counts = defaultdict(int)
    for row in selected:
        k = base_initial(row)
        counts[k] += 1
        if row.get("imageURL"):
            photo_counts[k] += 1
    print("Balanced actress directory complete:", len(selected))
    print("kana counts:", " ".join(f"{k}:{counts[k]}(photo {photo_counts[k]})" for k in BASE_KANA))


if __name__ == "__main__":
    main()
