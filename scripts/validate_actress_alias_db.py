from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

CONFIG = Path("config/actress_aliases.json")
OUTPUT = Path("public/data/actress-identity-db.json")


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if not CONFIG.exists():
        fail(f"Missing alias database: {CONFIG}")

    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    groups = payload.get("groups") or []
    if not isinstance(groups, list) or not groups:
        fail("Alias database has no groups")

    person_ids: set[str] = set()
    names: dict[str, str] = {}
    normalized: list[dict] = []

    for index, group in enumerate(groups, 1):
        if not isinstance(group, dict):
            fail(f"Group #{index} is not an object")

        person_id = str(group.get("personId") or "").strip()
        canonical = str(group.get("canonical") or "").strip()
        aliases = [str(x).strip() for x in (group.get("aliases") or []) if str(x).strip()]
        sources = [str(x).strip() for x in (group.get("sourceUrls") or []) if str(x).strip()]

        if not person_id:
            fail(f"Group #{index} is missing personId")
        if person_id in person_ids:
            fail(f"Duplicate personId: {person_id}")
        person_ids.add(person_id)

        if not canonical:
            fail(f"{person_id} is missing canonical name")
        if canonical in aliases:
            fail(f"{person_id} repeats canonical name inside aliases: {canonical}")
        if len(set(aliases)) != len(aliases):
            fail(f"{person_id} has duplicate aliases")
        if not sources:
            fail(f"{person_id} has no sourceUrls")

        for source in sources:
            parsed = urlparse(source)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                fail(f"{person_id} has invalid source URL: {source}")

        for name in [canonical, *aliases]:
            key = name.casefold()
            previous = names.get(key)
            if previous and previous != person_id:
                fail(f"Actress name is assigned to multiple identities: {name} ({previous}, {person_id})")
            names[key] = person_id

        normalized.append({
            "personId": person_id,
            "canonical": canonical,
            "aliases": aliases,
            "extraContentIds": list(group.get("extraContentIds") or []),
            "titleAliases": list(group.get("titleAliases") or []),
            "sourceUrls": sources,
            "note": str(group.get("note") or ""),
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "identityCount": len(normalized),
                "nameCount": sum(1 + len(row["aliases"]) for row in normalized),
                "identities": normalized,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"Alias DB valid: identities={len(normalized)}, names={sum(1 + len(row['aliases']) for row in normalized)}")


if __name__ == "__main__":
    main()
