"""
Unit tests for sitemap_parser.py
"""

import unittest
from unittest.mock import MagicMock, patch

from sitemap_parser import SitemapParser


SIMPLE_SITEMAP_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2024-01-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://example.com/about</loc>
    <lastmod>2024-01-02</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>"""

SITEMAP_NO_LASTMOD = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page1</loc>
  </url>
  <url>
    <loc>https://example.com/page2</loc>
  </url>
</urlset>"""

SITEMAP_INDEX_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-pages.xml</loc>
  </sitemap>
</sitemapindex>"""

DUPLICATE_SITEMAP = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/dup</loc>
    <lastmod>2024-01-01</lastmod>
  </url>
  <url>
    <loc>https://example.com/dup</loc>
    <lastmod>2024-01-01</lastmod>
  </url>
</urlset>"""

EXTERNAL_URL_SITEMAP = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://other-domain.com/page</loc>
    <lastmod>2024-01-01</lastmod>
  </url>
</urlset>"""


class TestSitemapXMLParsing(unittest.TestCase):
    def _parser(self) -> SitemapParser:
        return SitemapParser("https://example.com")

    def test_parse_simple_sitemap(self):
        parser = self._parser()
        issues = []
        is_index, urls = parser._parse_xml(SIMPLE_SITEMAP_XML, "https://example.com/sitemap.xml", 0, issues)
        self.assertFalse(is_index)
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls[0]["loc"], "https://example.com/")
        self.assertEqual(urls[0]["lastmod"], "2024-01-01")
        self.assertEqual(issues, [])

    def test_missing_lastmod_triggers_issue(self):
        parser = self._parser()
        issues = []
        parser._parse_xml(SITEMAP_NO_LASTMOD, "https://example.com/sitemap.xml", 0, issues)
        missing = [i for i in issues if i["type"] == "missing_lastmod"]
        self.assertEqual(len(missing), 2)

    def test_parse_index_detected(self):
        parser = self._parser()
        issues = []

        # Mock the child sitemap fetch
        with patch.object(parser, "_fetch_content", return_value=(SIMPLE_SITEMAP_XML, len(SIMPLE_SITEMAP_XML))):
            is_index, urls = parser._parse_xml(
                SITEMAP_INDEX_XML, "https://example.com/sitemap.xml", 0, issues
            )
        self.assertTrue(is_index)
        self.assertEqual(len(urls), 2)  # From the child sitemap

    def test_invalid_xml_adds_issue(self):
        parser = self._parser()
        issues = []
        parser._parse_xml(b"this is not xml", "https://example.com/sitemap.xml", 0, issues)
        parse_errors = [i for i in issues if i["type"] == "parse_error"]
        self.assertEqual(len(parse_errors), 1)

    def test_index_depth_limit(self):
        parser = self._parser()
        issues = []
        # At depth >= 3, should stop and add depth_limit issue
        import xml.etree.ElementTree as ET
        root = ET.fromstring(SITEMAP_INDEX_XML)
        with patch.object(parser, "_fetch_content", return_value=(SIMPLE_SITEMAP_XML, len(SIMPLE_SITEMAP_XML))):
            result = parser._parse_sitemap_index(root, depth=3, issues=issues)
        depth_issues = [i for i in issues if i["type"] == "depth_limit"]
        self.assertEqual(len(depth_issues), 1)
        self.assertEqual(result, [])


class TestDuplicateDetection(unittest.TestCase):
    def test_duplicate_urls_detected(self):
        parser = SitemapParser("https://example.com")
        with patch.object(parser, "_find_sitemap_url", return_value="https://example.com/sitemap.xml"):
            with patch.object(parser, "_fetch_content", return_value=(DUPLICATE_SITEMAP, len(DUPLICATE_SITEMAP))):
                result = parser.parse()
        dup_issues = [i for i in result["issues"] if i["type"] == "duplicate"]
        self.assertGreater(len(dup_issues), 0)


class TestExternalURLDetection(unittest.TestCase):
    def test_external_url_flagged(self):
        parser = SitemapParser("https://example.com")
        with patch.object(parser, "_find_sitemap_url", return_value="https://example.com/sitemap.xml"):
            with patch.object(parser, "_fetch_content", return_value=(EXTERNAL_URL_SITEMAP, len(EXTERNAL_URL_SITEMAP))):
                result = parser.parse()
        ext_issues = [i for i in result["issues"] if i["type"] == "external_url"]
        self.assertGreater(len(ext_issues), 0)


class TestSitemapNotFound(unittest.TestCase):
    def test_returns_not_found(self):
        parser = SitemapParser("https://example.com")
        with patch.object(parser, "_find_sitemap_url", return_value=None):
            result = parser.parse()
        self.assertFalse(result["found"])
        self.assertEqual(result["total_urls"], 0)
        self.assertGreater(len(result["issues"]), 0)


class TestSitemapDiscovery(unittest.TestCase):
    @patch("requests.Session.head")
    def test_finds_sitemap_xml(self, mock_head):
        mock_head.return_value = MagicMock(status_code=200)
        parser = SitemapParser("https://example.com")
        url = parser._find_sitemap_url()
        self.assertEqual(url, "https://example.com/sitemap.xml")

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_falls_back_to_robots_txt(self, mock_head, mock_get):
        # HEAD for sitemap.xml fails
        mock_head.return_value = MagicMock(status_code=404)
        # GET robots.txt succeeds with a Sitemap directive
        robots_resp = MagicMock()
        robots_resp.status_code = 200
        robots_resp.text = "User-agent: *\nDisallow: /private\nSitemap: https://example.com/custom-sitemap.xml"
        mock_get.return_value = robots_resp

        parser = SitemapParser("https://example.com")
        url = parser._find_sitemap_url()
        self.assertEqual(url, "https://example.com/custom-sitemap.xml")


class TestValidation(unittest.TestCase):
    def test_validate_urls(self):
        parser = SitemapParser("https://example.com")
        urls = [
            {"loc": "https://example.com/", "lastmod": None, "changefreq": None, "priority": None},
            {"loc": "https://example.com/about", "lastmod": None, "changefreq": None, "priority": None},
        ]
        with patch("requests.Session.head") as mock_head:
            mock_head.return_value = MagicMock(status_code=200)
            result = parser._validate_urls(urls)
        self.assertEqual(len(result), 2)
        for r in result:
            self.assertTrue(r["accessible"])
            self.assertEqual(r["status_code"], 200)


if __name__ == "__main__":
    unittest.main()
