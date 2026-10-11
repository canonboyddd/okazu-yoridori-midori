"""Offline regression tests for bounded parallel FANZA API pagination.

Do not make network calls or touch production files.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def module_from(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CatalogParallelFetchTests(unittest.TestCase):
    def test_catalog_offset_order_and_terminal_short_page(self):
        m = module_from("scripts/build_full_catalog_upgrade.py", "full_catalog_parallel_check")
        m.FETCH_WORKERS = 3
        m.MAX_PAGES = 0
        def fake_page(_api, _affiliate, offset, _sort):
            end = min(offset + m.HITS, 331)
            rows = [{"contentId": f"p{i}", "title": f"Title {i}"} for i in range(offset, end)]
            return rows, 330
        m.api_page = fake_page
        rows, total = m.collect_sort("fake", "fake", "date")
        self.assertEqual(total, 330)
        self.assertEqual([x["contentId"] for x in rows], [f"p{i}" for i in range(1, 331)])

    def test_catalog_page_limit(self):
        m = module_from("scripts/build_full_catalog_upgrade.py", "full_catalog_page_limit")
        m.FETCH_WORKERS = 3
        m.MAX_PAGES = 2
        m.api_page = lambda _a, _b, offset, _s: (
            [{"contentId": f"p{i}", "title": "T"} for i in range(offset, offset + 100)], 1000
        )
        rows, total = m.collect_sort("fake", "fake", "rank")
        self.assertEqual((len(rows), total), (200, 1000))


class PopularityParallelFetchTests(unittest.TestCase):
    def test_rank_order_and_short_last_page(self):
        m = module_from("scripts/build_dmm_popular_actresses.py", "popularity_parallel_check")
        m.FETCH_WORKERS = 3
        m.MAX_PAGES = 20
        m.TARGET = 10000
        def fake_api(_endpoint, params):
            offset = int(params["offset"])
            count = max(0, min(100, 230 - offset + 1))
            items = []
            for i in range(count):
                number = offset + i
                actress_id = str(100 + number % 10)
                items.append({"iteminfo": {"actress": [{"id": actress_id, "name": actress_id}]}})
            return {"items": items}
        m.api_json = fake_api
        rows = m.collect_popularity("fake", "fake")
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["id"], "101")
        self.assertEqual(rows[0]["firstProductRank"], 1)
        self.assertEqual(rows[0]["rankedAppearances"], 23)
        self.assertEqual(rows[-1]["id"], "100")
        self.assertEqual(rows[-1]["firstProductRank"], 10)


if __name__ == "__main__":
    unittest.main()
