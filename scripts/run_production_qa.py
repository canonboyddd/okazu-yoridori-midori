from __future__ import annotations

import json

import qa_production as qa


def find_dynamic_product() -> tuple[str, str, str]:
    rows = qa.catalog_rows(limit_shards=4)
    preferred = []
    fallback = []
    for row in rows:
        cid = qa.safe_id(row.get("contentId"))
        title = str(row.get("title") or cid)
        affiliate = str(row.get("affiliateURL") or "")
        if not cid or not affiliate:
            continue
        qa.assert_true("okazumidori-001" not in affiliate and "ch=link_tool" not in affiliate, "Broken legacy FANZA URL remains in full catalog")
        qa.assert_true("okazumidori-990" in affiliate and "ch=api" in affiliate, "API-based FANZA affiliate URL missing from full catalog")
        entry = (cid, title, row)
        if row.get("actressEntities") and row.get("makerEntities") and row.get("genreEntities"):
            preferred.append(entry)
        else:
            fallback.append(entry)

    for cid, title, _row in preferred + fallback:
        status, shell = qa.fetch(qa.BASE + f"/products/view/?id={cid}")
        if status == 200 and "dynamicProduct" in shell and "dynamic-product.js" in shell:
            return cid, title, shell
    raise RuntimeError("No full-catalog product could be opened through the dynamic product shell")


def assert_related_catalog(product: dict, entity_type: str, entity_key: str) -> None:
    entities = product.get(entity_key) or []
    if not isinstance(entities, list) or not entities:
        print(f"QA dynamic product related {entity_type}: sample product has no entity; skipped")
        return
    entity = entities[0] if isinstance(entities[0], dict) else {}
    entity_id = qa.safe_id(entity.get("id"))
    if not entity_id:
        print(f"QA dynamic product related {entity_type}: sample entity has no id; skipped")
        return
    status, raw = qa.fetch(qa.BASE + f"/data/{entity_type}-catalog/{entity_id}.json")
    qa.assert_true(status == 200, f"Related {entity_type} catalog missing: {entity_id}")
    payload = json.loads(raw)
    direct = payload.get("items") or []
    shards = payload.get("shards") or []
    qa.assert_true(bool(direct) or bool(shards), f"Related {entity_type} catalog is empty: {entity_id}")
    print(f"QA dynamic product related {entity_type}: {entity_id} OK")


def test_dynamic_product_page(cid: str, title: str, shell: str) -> None:
    qa.assert_true("dynamicProduct" in shell, "Dynamic product mount missing")
    qa.assert_true("dynamic-product.js" in shell, "Dynamic product loader script missing")

    status, loader = qa.fetch(qa.BASE + "/assets/dynamic-product.js")
    qa.assert_true(status == 200, "Dynamic product loader missing")
    for marker in [
        "/data/catalog-lookup.json",
        "/data/catalog/catalog-",
        "/data/${type}-catalog/",
        "loadEntityItems('actress'",
        "loadEntityItems('maker'",
        "loadEntityItems('genre'",
        "affiliateURL",
        "FANZAでこの作品を見る",
        "FANZA公式で確認",
        "actressEntities",
        "makerEntities",
        "genreEntities",
        "commentBlock",
        "fc-description",
        "作品データの要点",
        "renderRelated",
        'data-affiliate-target="product-top"',
        'data-affiliate-target="product-bottom"',
    ]:
        qa.assert_true(marker in loader, f"Dynamic product loader capability missing: {marker}")

    status, lookup_raw = qa.fetch(qa.BASE + "/data/catalog-lookup.json")
    qa.assert_true(status == 200, "Catalog lookup missing")
    lookup = json.loads(lookup_raw)
    shard_no = int((lookup.get("items") or {}).get(cid) or 0)
    qa.assert_true(shard_no > 0, f"Dynamic product lookup does not contain {cid}")

    shard_url = qa.BASE + f"/data/catalog/catalog-{shard_no:04d}.json"
    status, shard_raw = qa.fetch(shard_url)
    qa.assert_true(status == 200, f"Dynamic product shard missing: {shard_no}")
    rows = json.loads(shard_raw)
    product = next((x for x in rows if isinstance(x, dict) and qa.safe_id(x.get("contentId")) == cid), None)
    qa.assert_true(product is not None, f"Product {cid} missing from mapped catalog shard")
    qa.assert_true(str(product.get("title") or "").strip(), "Dynamic product has no title")
    qa.assert_true(str(product.get("imageURL") or "").strip(), "Dynamic product has no image")
    affiliate = str(product.get("affiliateURL") or "")
    qa.assert_true("okazumidori-990" in affiliate and "ch=api" in affiliate, "Dynamic product affiliate URL is not the API affiliate URL")
    qa.assert_true("okazumidori-001" not in affiliate and "ch=link_tool" not in affiliate, "Legacy link-tool URL remains in dynamic product record")

    assert_related_catalog(product, "actress", "actressEntities")
    assert_related_catalog(product, "maker", "makerEntities")
    assert_related_catalog(product, "genre", "genreEntities")

    sample_rows = qa.catalog_rows(limit_shards=4)
    comment_count = sum(1 for x in sample_rows if str(x.get("comment") or "").strip())
    print(
        f"QA dynamic product: {cid} / {title[:40]} / shard={shard_no}; "
        f"comment_sample_coverage={comment_count}/{len(sample_rows)}; "
        "factual summary + related actress/maker/genre sections verified"
    )


qa.find_live_product = find_dynamic_product
qa.test_product_page = test_dynamic_product_page
qa.main()
