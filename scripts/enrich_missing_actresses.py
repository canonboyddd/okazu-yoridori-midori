from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"
ROOT = Path("public")
DATA = ROOT / "data"
MANIFEST = DATA / "full-catalog-manifest.json"
DIRECTORY = DATA / "fanza-actress-directory.json"
REPORT = DATA / "missing-actress-enrichment.json"
PRODUCT_ROOT = ROOT / "products"

API_LIMIT = int(os.environ.get("DMM_MISSING_ACTRESS_API_LIMIT", "1500"))
REQUEST_DELAY = float(os.environ.get("DMM_REQUEST_DELAY", "0.12"))
MIN_NAME_LEN = int(os.environ.get("DMM_TITLE_ACTRESS_MIN_LEN", "2"))


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def safe_id(value: object) -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "-", str(value or "").strip()).strip("-")[:120]


def unique_entities(values: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for row in values:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("id") or row.get("actress_id") or "").strip()
        name = str(row.get("name") or "").strip()
        if not aid or not name or aid in seen:
            continue
        seen.add(aid)
        out.append({"id": aid, "name": name})
    return out[:20]


def load_directory() -> list[dict]:
    payload = load_json(DIRECTORY, {})
    rows = payload.get("actresses") or payload.get("actress") or []
    clean = unique_entities([x for x in rows if isinstance(x, dict)])
    # Longest names first prevents a short name contained inside a longer name
    # from becoming a false duplicate match.
    clean.sort(key=lambda x: (len(x["name"]), x["name"]), reverse=True)
    return clean


def title_matches(title: str, directory: list[dict]) -> list[dict]:
    title = str(title or "")
    if not title:
        return []
    matched: list[dict] = []
    matched_names: list[str] = []
    for actress in directory:
        name = actress["name"]
        if len(name) < MIN_NAME_LEN or name not in title:
            continue
        # If this exact text is already covered by a longer matched name, skip it.
        if any(name in longer for longer in matched_names):
            continue
        matched.append(actress)
        matched_names.append(name)
        if len(matched) >= 20:
            break
    return matched


def api_lookup(api_id: str, affiliate_id: str, cid: str) -> list[dict]:
    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "cid": cid,
        "hits": "10",
        "offset": "1",
        "output": "json",
    }
    req = Request(API_URL + "?" + urlencode(params), headers={"User-Agent": "okazu-missing-actress-enricher/1.0"})
    last: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(req, timeout=45) as res:
                payload = json.loads(res.read().decode("utf-8"))
            result = payload.get("result") or {}
            if result.get("status") not in (200, "200"):
                return []
            for item in result.get("items") or []:
                if not isinstance(item, dict):
                    continue
                if str(item.get("content_id") or "").strip() != cid:
                    continue
                info = item.get("iteminfo") or {}
                return unique_entities([x for x in (info.get("actress") or []) if isinstance(x, dict)])
            return []
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(0.8 * (attempt + 1))
    print(f"WARN exact actress lookup failed cid={cid}: {last}")
    return []


def patch_static_product(cid: str, actresses: list[dict]) -> bool:
    path = PRODUCT_ROOT / safe_id(cid) / "index.html"
    if not path.exists() or not actresses:
        return False
    text = path.read_text(encoding="utf-8")
    if "<dt>出演者</dt><dd>情報なし</dd>" not in text:
        return False
    links = "、".join(
        f'<a href="/ranking/actress/{str(a["id"])}/">{str(a["name"])}</a>'
        for a in actresses
    ).replace("\\/", "/")
    text = text.replace("<dt>出演者</dt><dd>情報なし</dd>", f"<dt>出演者</dt><dd>{links}</dd>", 1)
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    manifest = load_json(MANIFEST, {})
    shards = manifest.get("shards") or []
    if not shards:
        raise SystemExit("full-catalog-manifest.json has no shards")

    directory = load_directory()
    if not directory:
        raise SystemExit("fanza-actress-directory.json has no actress rows")

    shard_payloads: list[tuple[Path, list[dict]]] = []
    missing_refs: list[tuple[int, int, dict]] = []
    catalog_count = 0
    before_missing = 0

    for shard_index, shard in enumerate(shards):
        rel = str(shard.get("file") or "").lstrip("/")
        path = ROOT / rel
        payload = load_json(path, [])
        if not isinstance(payload, list):
            raise SystemExit(f"catalog shard is not a list: {path}")
        shard_payloads.append((path, payload))
        for row_index, row in enumerate(payload):
            if not isinstance(row, dict):
                continue
            catalog_count += 1
            if not (row.get("actressEntities") or []):
                before_missing += 1
                missing_refs.append((shard_index, row_index, row))

    title_matched = 0
    static_patched = 0
    unresolved: list[tuple[int, int, dict]] = []

    for shard_index, row_index, row in missing_refs:
        matched = title_matches(str(row.get("title") or ""), directory)
        if not matched:
            unresolved.append((shard_index, row_index, row))
            continue
        row["actressEntities"] = matched
        row["actresses"] = [x["name"] for x in matched]
        row["actressEnrichmentSource"] = "official-directory-title-match"
        title_matched += 1
        if patch_static_product(str(row.get("contentId") or ""), matched):
            static_patched += 1

    # Exact ItemList lookup is deliberately bounded. It is used for the most
    # valuable unresolved products first, rather than re-querying all missing rows.
    unresolved.sort(
        key=lambda ref: (
            int(ref[2].get("reviewCount") or 0),
            str(ref[2].get("date") or ""),
        ),
        reverse=True,
    )
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"
    api_attempted = 0
    api_matched = 0
    if api_id and API_LIMIT > 0:
        for shard_index, row_index, row in unresolved[:API_LIMIT]:
            cid = str(row.get("contentId") or "").strip()
            if not cid:
                continue
            api_attempted += 1
            matched = api_lookup(api_id, affiliate_id, cid)
            if matched:
                row["actressEntities"] = matched
                row["actresses"] = [x["name"] for x in matched]
                row["actressEnrichmentSource"] = "fanza-itemlist-cid"
                api_matched += 1
                if patch_static_product(cid, matched):
                    static_patched += 1
            time.sleep(REQUEST_DELAY)
    elif not api_id:
        print("DMM_API_ID missing; exact API enrichment skipped")

    # Persist all touched catalog shards. JSON size is controlled later by the
    # existing sharding step in the deployment workflow.
    after_missing = 0
    for path, payload in shard_payloads:
        after_missing += sum(
            1 for row in payload
            if isinstance(row, dict) and not (row.get("actressEntities") or [])
        )
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    recovered = before_missing - after_missing
    report = {
        "catalogCount": catalog_count,
        "beforeMissingActress": before_missing,
        "recovered": recovered,
        "afterMissingActress": after_missing,
        "titleMatched": title_matched,
        "apiAttempted": api_attempted,
        "apiMatched": api_matched,
        "staticProductPagesPatched": static_patched,
        "directoryActressCount": len(directory),
        "apiLimit": API_LIMIT,
        "titleMatchMinLength": MIN_NAME_LEN,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("Missing actress enrichment:", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
