from __future__ import annotations

import json
from pathlib import Path

INDEX = Path("public/data/actress-catalog-index.json")


def main() -> None:
    if not INDEX.exists():
        raise SystemExit("public/data/actress-catalog-index.json is missing")

    data = json.loads(INDEX.read_text(encoding="utf-8"))

    # build_catalog_lookup_index.py historically emitted "actresss" from
    # the generic f"{entity_key}s" pluralization. Normalize it for the
    # public API and Production QA.
    if "actresses" not in data and "actresss" in data:
        data["actresses"] = data.pop("actresss")

    rows = data.get("actresses")
    if not isinstance(rows, list) or not rows:
        raise SystemExit("Actress catalog index has no non-empty 'actresses' list")

    expected = int(data.get("actressCount") or len(rows))
    if expected != len(rows):
        raise SystemExit(
            f"Actress catalog index count mismatch: actressCount={expected}, rows={len(rows)}"
        )

    data["actressCount"] = len(rows)
    data.pop("actresss", None)
    INDEX.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Actress catalog index normalized: actresses={len(rows)}")


if __name__ == "__main__":
    main()
