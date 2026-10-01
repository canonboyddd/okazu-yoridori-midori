from __future__ import annotations

import json

import qa_production as qa


def find_dynamic_product() -> tuple[str, str, str]:
    rows = qa.catalog_rows(limit_shards=4)
    for row in rows:
        cid = qa.safe_id(row.get("contentId"))
        title = str(row.get("title") or cid)
        affiliate = str(row.get("affiliateURL") or "")
        if not cid or not affiliate:
            continue
        qa.assert_true("okazumidori-001" not in affiliate and "ch=link_tool" not in affiliate, "Broken legacy FANZA URL remains in full catalog")
        qa.assert_true("okazumidori-990" in affiliate and "ch=api" in affiliate, "API-based FANZA affiliate URL missing from full catalog")
        status, shell = qa.fetch(qa.BASE + f"/products/view/?id={cid}")
        if status == 200 and "dynamicProduct" in shell and "dynamic-product.js" in shell:
            return cid, title, shell
    raise RuntimeError("No full-catalog product could be opened through the dynamic product shell")


def test_dynamic_product_page(cid: str, title: str, shell: str) -> None:
    qa.assert_true("dynamicProduct" in shell, "Dynamic product mount missing")
    qa.assert_true("dynamic-product.js" in shell, "Dynamic product loader script missing")

    status, loader = qa.fetch(qa.BASE + "/assets/dynamic-product.js")
    qa.assert_true(status == 200, "Dynamic product loader missing")
    for marker in [
        "/data/catalog-lookup.json",
        "/data/catalog/catalog-",
        "affiliateURL",
        "FANZAでこの作品を見る",
        "FANZA公式で確認",
        "actressEntities",
        "genreEntities",
        "commentBlock",
        "fc-description",
        'data-affiliate-target="product"',
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

    sample_rows = qa.catalog_rows(limit_shards=4)
    comment_count = sum(1 for x in sample_rows if str(x.get("comment") or "").strip())
    print(
        f"QA dynamic product: {cid} / {title[:40]} / shard={shard_no}; "
        f"comment_sample_coverage={comment_count}/{len(sample_rows)}; comment rendering supported by loader"
    )


qa.find_live_product = find_dynamic_product
qa.test_product_page = test_dynamic_product_page
qa.main()
