"""
Unit tests for broken_link_checker.py
"""

import unittest
from unittest.mock import MagicMock, patch

from broken_link_checker import BrokenLinkChecker


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <link href="https://example.com/style.css" rel="stylesheet">
</head>
<body>
  <a href="https://example.com/ok">OK Link</a>
  <a href="https://example.com/broken">Broken Link</a>
  <a href="https://example.com/redirect">Redirect Link</a>
  <img src="https://example.com/image.jpg" alt="test">
  <script src="https://example.com/script.js"></script>
</body>
</html>"""


def _make_mock_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_redirect = status_code in (301, 302, 303, 307, 308)
    return resp


class TestLinkClassification(unittest.TestCase):
    def test_ok_status(self):
        self.assertEqual(BrokenLinkChecker._classify(200), "ok")
        self.assertEqual(BrokenLinkChecker._classify(201), "ok")
        self.assertEqual(BrokenLinkChecker._classify(204), "ok")

    def test_redirect_status(self):
        self.assertEqual(BrokenLinkChecker._classify(301), "redirect")
        self.assertEqual(BrokenLinkChecker._classify(302), "redirect")
        self.assertEqual(BrokenLinkChecker._classify(307), "redirect")

    def test_client_error_status(self):
        self.assertEqual(BrokenLinkChecker._classify(404), "client_error")
        self.assertEqual(BrokenLinkChecker._classify(403), "client_error")
        self.assertEqual(BrokenLinkChecker._classify(401), "client_error")

    def test_server_error_status(self):
        self.assertEqual(BrokenLinkChecker._classify(500), "server_error")
        self.assertEqual(BrokenLinkChecker._classify(503), "server_error")


class TestSummarize(unittest.TestCase):
    def test_empty_results(self):
        summary = BrokenLinkChecker._summarize([])
        self.assertEqual(summary["total_links"], 0)
        self.assertEqual(summary["ok"], 0)
        self.assertEqual(summary["broken_links"], [])

    def test_mixed_results(self):
        results = [
            {"url": "u1", "status_code": 200, "status": "ok", "error": None, "source_tag": "a"},
            {"url": "u2", "status_code": 404, "status": "client_error", "error": None, "source_tag": "a"},
            {"url": "u3", "status_code": 301, "status": "redirect", "error": None, "source_tag": "a"},
            {"url": "u4", "status_code": 500, "status": "server_error", "error": None, "source_tag": "img"},
            {"url": "u5", "status_code": None, "status": "timeout", "error": "timed out", "source_tag": "a"},
            {"url": "u6", "status_code": None, "status": "error", "error": "conn refused", "source_tag": "a"},
        ]
        summary = BrokenLinkChecker._summarize(results)
        self.assertEqual(summary["total_links"], 6)
        self.assertEqual(summary["ok"], 1)
        self.assertEqual(summary["redirects"], 1)
        self.assertEqual(summary["client_errors"], 1)
        self.assertEqual(summary["server_errors"], 1)
        self.assertEqual(summary["timeouts"], 1)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(len(summary["broken_links"]), 4)


class TestLinkExtraction(unittest.TestCase):
    def _get_extracted(self, html: str, base_url: str = "https://example.com"):
        from bs4 import BeautifulSoup
        checker = BrokenLinkChecker(base_url)
        soup = BeautifulSoup(html, "lxml")
        return checker._extract_links(soup)

    def test_extracts_anchor_links(self):
        html = '<html><body><a href="https://example.com/page">Link</a></body></html>'
        links = self._get_extracted(html)
        urls = [l["url"] for l in links]
        self.assertIn("https://example.com/page", urls)

    def test_extracts_img_links(self):
        html = '<html><body><img src="https://example.com/img.jpg" alt=""></body></html>'
        links = self._get_extracted(html)
        urls = [l["url"] for l in links]
        self.assertIn("https://example.com/img.jpg", urls)

    def test_skips_hash_links(self):
        html = '<html><body><a href="#">Hash link</a></body></html>'
        links = self._get_extracted(html)
        self.assertEqual(links, [])

    def test_skips_javascript_links(self):
        html = '<html><body><a href="javascript:void(0)">JS link</a></body></html>'
        links = self._get_extracted(html)
        self.assertEqual(links, [])

    def test_skips_mailto_links(self):
        html = '<html><body><a href="mailto:test@example.com">Email</a></body></html>'
        links = self._get_extracted(html)
        self.assertEqual(links, [])

    def test_resolves_relative_links(self):
        html = '<html><body><a href="/about">About</a></body></html>'
        links = self._get_extracted(html, "https://example.com")
        urls = [l["url"] for l in links]
        self.assertIn("https://example.com/about", urls)

    def test_no_duplicates(self):
        html = """<html><body>
            <a href="https://example.com/page">Link 1</a>
            <a href="https://example.com/page">Link 2</a>
        </body></html>"""
        links = self._get_extracted(html)
        urls = [l["url"] for l in links]
        self.assertEqual(len(urls), len(set(urls)))


class TestCheckWithMockedHTTP(unittest.TestCase):
    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_check_returns_structure(self, mock_head, mock_get):
        # Mock page fetch
        page_response = MagicMock()
        page_response.text = SAMPLE_HTML
        mock_get.return_value = page_response

        # Mock link check (HEAD returns 200)
        mock_head.return_value = _make_mock_response(200)

        checker = BrokenLinkChecker("https://example.com")
        result = checker.check()

        self.assertIn("total_links", result)
        self.assertIn("ok", result)
        self.assertIn("broken_links", result)
        self.assertIn("all_links", result)

    @patch("requests.Session.get")
    def test_fetch_failure_returns_error_structure(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("refused")
        checker = BrokenLinkChecker("https://example.com")
        result = checker.check()
        self.assertIn("error", result)
        self.assertEqual(result["total_links"], 0)


class TestCheckSingleLink(unittest.TestCase):
    @patch("requests.Session.head")
    def test_ok_link(self, mock_head):
        mock_head.return_value = _make_mock_response(200)
        checker = BrokenLinkChecker("https://example.com")
        result = checker._check_single_link({"url": "https://example.com/ok", "source_tag": "a"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["status_code"], 200)

    @patch("requests.Session.head")
    def test_404_link(self, mock_head):
        mock_head.return_value = _make_mock_response(404)
        checker = BrokenLinkChecker("https://example.com")
        result = checker._check_single_link({"url": "https://example.com/gone", "source_tag": "a"})
        self.assertEqual(result["status"], "client_error")
        self.assertEqual(result["status_code"], 404)

    @patch("requests.Session.head")
    def test_timeout(self, mock_head):
        import requests as req
        mock_head.side_effect = req.exceptions.Timeout()
        checker = BrokenLinkChecker("https://example.com")
        result = checker._check_single_link({"url": "https://example.com/slow", "source_tag": "a"})
        self.assertEqual(result["status"], "timeout")

    @patch("requests.Session.head")
    @patch("requests.Session.get")
    def test_405_falls_back_to_get(self, mock_get, mock_head):
        mock_head.return_value = _make_mock_response(405)
        mock_get.return_value = _make_mock_response(200)
        checker = BrokenLinkChecker("https://example.com")
        result = checker._check_single_link({"url": "https://example.com/head-not-allowed", "source_tag": "a"})
        self.assertEqual(result["status"], "ok")


if __name__ == "__main__":
    unittest.main()
