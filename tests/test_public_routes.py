"""Regression tests for the 2026-11-18 audit finding.

The 30 guide articles and the about/privacy pages were stored without a .html
extension, so Cloudflare Pages served them as application/octet-stream and browsers
downloaded them. Internal links pointed at /articles/<slug>.html, which was a 404.
"""
import re
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import enhance_fanza_seo as seo  # noqa: E402
import normalize_public_routes as routes  # noqa: E402

PUBLIC = REPO / "public"
HTML = "<!doctype html><html lang=\"ja\"><head><title>t</title></head><body></body></html>"


class RepositoryRoutes(unittest.TestCase):
    def test_every_html_page_has_a_html_file_name(self):
        self.assertEqual([p.relative_to(PUBLIC).as_posix() for p in routes.extensionless_html(PUBLIC)], [])

    def test_article_links_resolve_to_article_files(self):
        missing = []
        for page in PUBLIC.rglob("*.html"):
            text = page.read_text(encoding="utf-8", errors="ignore")
            for slug in re.findall(r'href="/articles/([a-z0-9-]+)(?:\.html)?(?:[?#][^"]*)?"', text):
                if not (PUBLIC / "articles" / f"{slug}.html").is_file():
                    missing.append(f"{page.relative_to(PUBLIC).as_posix()} -> /articles/{slug}")
        self.assertEqual(missing, [])

    def test_article_canonicals_use_the_clean_url(self):
        articles = sorted((PUBLIC / "articles").glob("*.html"))
        self.assertGreaterEqual(len(articles), 30)
        for page in articles:
            text = page.read_text(encoding="utf-8", errors="ignore")
            self.assertIn(f'<link rel="canonical" href="{seo.BASE_URL}/articles/{page.stem}">', text, page.name)

    def test_about_and_privacy_canonicals_use_the_clean_url(self):
        for name in ("about", "privacy"):
            text = (PUBLIC / f"{name}.html").read_text(encoding="utf-8")
            self.assertIn(f'<link rel="canonical" href="{seo.BASE_URL}/{name}">', text)
            self.assertFalse((PUBLIC / name).exists(), f"extensionless {name} would shadow {name}.html")


class Normalizer(unittest.TestCase):
    def test_snapshot_leftovers_are_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "articles").mkdir()
            (root / "articles" / "only-extensionless").write_text(HTML, encoding="utf-8")
            (root / "about").write_text(HTML + "<!--stale-->", encoding="utf-8")
            (root / "about.html").write_text(HTML + "<!--current-->", encoding="utf-8")
            (root / "_headers").write_text("/*\n  X-Test: 1\n", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "plain").write_text("not html", encoding="utf-8")

            self.assertEqual(routes.normalize(root), (1, 1))

            self.assertTrue((root / "articles" / "only-extensionless.html").is_file())
            self.assertFalse((root / "articles" / "only-extensionless").exists())
            self.assertFalse((root / "about").exists())
            self.assertIn("<!--current-->", (root / "about.html").read_text(encoding="utf-8"))
            self.assertTrue((root / "_headers").is_file())
            self.assertTrue((root / "data" / "plain").is_file())
            self.assertEqual(routes.extensionless_html(root), [])
            self.assertEqual(routes.normalize(root), (0, 0))


class StaticSitemap(unittest.TestCase):
    def test_editorial_pages_are_added_once_and_noindex_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "articles").mkdir()
            (root / "guide").mkdir()
            (root / "articles" / "sale-guide.html").write_text(HTML, encoding="utf-8")
            (root / "articles" / "hidden.html").write_text(
                HTML.replace("<title>", '<meta name="robots" content="noindex,follow"><title>'), encoding="utf-8"
            )
            (root / "guide" / "index.html").write_text(HTML, encoding="utf-8")
            (root / "about.html").write_text(HTML, encoding="utf-8")
            sitemap = root / "sitemap.xml"
            sitemap.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f"  <url><loc>{seo.BASE_URL}/</loc><lastmod>2026-11-01</lastmod></url>\n"
                f"  <url><loc>{seo.BASE_URL}/guide/</loc><lastmod>2026-11-01</lastmod></url>\n"
                "</urlset>\n",
                encoding="utf-8",
            )

            self.assertEqual(seo._ensure_static_pages_in_sitemap(sitemap, root), 2)
            text = sitemap.read_text(encoding="utf-8")
            locs = re.findall(r"<loc>([^<]+)</loc>", text)
            self.assertEqual(
                locs,
                [f"{seo.BASE_URL}/", f"{seo.BASE_URL}/guide/", f"{seo.BASE_URL}/about", f"{seo.BASE_URL}/articles/sale-guide"],
            )
            self.assertNotIn("hidden", text)
            self.assertTrue(text.rstrip().endswith("</urlset>"))
            self.assertEqual(seo._ensure_static_pages_in_sitemap(sitemap, root), 0)
            self.assertEqual(sitemap.read_text(encoding="utf-8"), text)


class ProductionQaWorkflow(unittest.TestCase):
    """The post-deploy page audit is a script embedded in production-qa.yml.

    Nothing else runs it before a deploy, so it once kept expecting the old
    /about.html canonical and failed right after the pages were fixed.
    """

    def _main_page_audit(self):
        text = (REPO / ".github" / "workflows" / "production-qa.yml").read_text(encoding="utf-8").replace("\r\n", "\n")
        step = text.split("- name: Audit every main public page type", 1)[1]
        body = step.split("python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        return textwrap.dedent(body)

    def test_embedded_audit_is_valid_python(self):
        compile(self._main_page_audit(), "production-qa.yml main-page audit", "exec")

    def test_embedded_audit_matches_the_clean_urls(self):
        source = self._main_page_audit()
        self.assertNotRegex(source, r'rel="canonical" href="[^"]*\.html"')
        for path in ("'/about'", "'/privacy'", "'/articles/fanza-beginner'"):
            self.assertIn(path, source)
        self.assertIn("text/html", source)
        for name in ("about", "privacy"):
            self.assertIn(f'<link rel="canonical" href="{seo.BASE_URL}/{name}">', (PUBLIC / f"{name}.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
