from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path("public")
DATA = ROOT / "data"
ENTITY_TYPES = ("genre", "maker", "actress")
MAX_ROOT_BYTES = 20 * 1024 * 1024
SHARD_ITEMS = 2500
MAX_SHARD_BYTES = 24 * 1024 * 1024
OLD_V6_VERSION = "20260928-2348"
NEW_V6_VERSION = "20260929-0825"


def compact_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def shard_catalog_file(path: Path) -> tuple[bool, int, int]:
    raw = path.read_bytes()
    shard_dir = path.with_suffix("")

    if len(raw) < MAX_ROOT_BYTES:
        if shard_dir.is_dir():
            shutil.rmtree(shard_dir)
        return False, 0, len(raw)

    data = json.loads(raw.decode("utf-8"))
    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        return False, 0, len(raw)

    if shard_dir.exists():
        shutil.rmtree(shard_dir)
    shard_dir.mkdir(parents=True, exist_ok=True)

    shards: list[dict] = []
    total_bytes = 0
    for shard_no, start in enumerate(range(0, len(items), SHARD_ITEMS), 1):
        chunk = items[start:start + SHARD_ITEMS]
        filename = f"part-{shard_no:03d}.json"
        shard_payload = {"version": 4, "items": chunk}
        text = compact_json(shard_payload)
        size = len(text.encode("utf-8"))
        if size >= MAX_SHARD_BYTES:
            raise SystemExit(f"Entity shard too large for Cloudflare Pages: {path} -> {filename}={size} bytes")
        (shard_dir / filename).write_text(text, encoding="utf-8")
        total_bytes += size
        shards.append({
            "file": f"/data/{path.parent.name}/{path.stem}/{filename}",
            "count": len(chunk),
            "bytes": size,
        })

    manifest = {
        "version": 4,
        "generatedAt": data.get("generatedAt"),
        "id": data.get("id"),
        "name": data.get("name"),
        "count": len(items),
        "aliases": data.get("aliases") or [],
        "shardSize": SHARD_ITEMS,
        "shardCount": len(shards),
        "shards": shards,
    }
    manifest_text = compact_json(manifest)
    path.write_text(manifest_text, encoding="utf-8")
    return True, len(shards), total_bytes


def bump_v6_cache_version() -> int:
    changed = 0
    for path in ROOT.rglob("*.html"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        old = f"v6.js?v={OLD_V6_VERSION}"
        new = f"v6.js?v={NEW_V6_VERSION}"
        if old not in text:
            continue
        path.write_text(text.replace(old, new), encoding="utf-8")
        changed += 1
    return changed


def main() -> None:
    sharded = 0
    total_shards = 0
    largest_root = 0

    for entity_type in ENTITY_TYPES:
        directory = DATA / f"{entity_type}-catalog"
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            did_shard, shard_count, _ = shard_catalog_file(path)
            if did_shard:
                sharded += 1
                total_shards += shard_count
            largest_root = max(largest_root, path.stat().st_size)

    bumped = bump_v6_cache_version()
    if largest_root >= 25 * 1024 * 1024:
        raise SystemExit(f"Cloudflare Pages file limit still exceeded: largest root entity file={largest_root} bytes")

    print(
        f"Cloudflare entity sharding: catalogs_sharded={sharded}, shards={total_shards}, "
        f"largest_root={largest_root}, v6_cache_bumped_pages={bumped}"
    )


if __name__ == "__main__":
    main()
