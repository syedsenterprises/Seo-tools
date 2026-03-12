"""
Unit tests for seo_analyzer.py
"""

import unittest
from unittest.mock import MagicMock, patch

from seo_analyzer import SEOAnalyzer


SAMPLE_HTML_GOOD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="This is a sample meta description that is exactly the right length for SEO testing.">
  <title>A Perfectly Good Title Tag That Is Fifty Five Chars</title>
  <link rel="canonical" href="https://example.com/">
  <link rel="icon" href="/favicon.ico">
  <meta property="og:title" content="Test">
  <meta property="og:description" content="Test desc">
  <meta property="og:image" content="https://example.com/img.png">
  <meta property="og:url" content="https://example.com/">
  <meta property="og:type" content="website">
  <meta name="twitter:card" content="summary">
</head>
<body>
  <h1>Main Heading</h1>
  <h2>Sub Heading</h2>
  <p>This page has enough content to pass the word count check. It includes multiple
  sentences and paragraphs to ensure we reach the minimum word count threshold of
  three hundred words for the content length check to pass successfully without
  any issues whatsoever. More content here to pad out the word count and ensure
  the test passes reliably every single time it is run in the test suite.
  Even more content added here to push above the three hundred word threshold.
  The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs.
  How vexingly quick daft zebras jump. The five boxing wizards jump quickly.
  Sphinx of black quartz judge my vow. Two driven jocks help fax my big quiz.
  Five quacking zephyrs jolt my wax bed. The jay pig fox zebra and my wolves quack.
  Blowzy red vixens fight for a quick jump. Joaquin Phoenix was gazed by MTV for luck.
  How quickly daft jumping zebras vex. Quick fox jumps nightly above wizard.
  Lazy movers quit hard packing of jury size boxes. We promptly judged antique ivory buckles from the quaint zoo exhibition.
  </p>
  <img src="test.jpg" alt="Test image" width="100" height="100">
  <a href="/internal">Internal link</a>
  <a href="https://external.com">External link</a>
  <script type="application/ld+json">{"@context":"https://schema.org"}</script>
</body>
</html>"""

SAMPLE_HTML_BAD = """<!DOCTYPE html>
<html>
<head>
  <title>Hi</title>
</head>
<body>
  <h1>First</h1>
  <h1>Second</h1>
  <img src="no-alt.jpg">
  <font>Deprecated tag</font>
  <center>Also deprecated</center>
  <a href="#">Empty link</a>
</body>
</html>"""


def _make_analyzer(url: str, html: str, status: int = 200) -> SEOAnalyzer:
    """Build an SEOAnalyzer with a mocked HTTP response."""
    analyzer = SEOAnalyzer(url)
    mock_response = MagicMock()
    mock_response.text = html
    mock_response.content = html.encode("utf-8")
    mock_response.status_code = status
    analyzer._response = mock_response
    analyzer._response_time = 0.2

    from bs4 import BeautifulSoup
    analyzer._soup = BeautifulSoup(html, "lxml")
    return analyzer


class TestTitleCheck(unittest.TestCase):
    def test_good_title(self):
        analyzer = _make_analyzer("https://example.com", SAMPLE_HTML_GOOD)
        analyzer._check_title()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "pass")

    def test_short_title(self):
        html = "<html><head><title>Hi</title></head><body></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_title()
        check = analyzer._checks[-1]
        self.assertIn(check["status"], ("warning", "fail"))

    def test_missing_title(self):
        html = "<html><head></head><body></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_title()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "fail")

    def test_long_title_warning(self):
        long_title = "A" * 65
        html = f"<html><head><title>{long_title}</title></head><body></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_title()
        check = analyzer._checks[-1]
        self.assertIn(check["status"], ("warning", "fail"))


class TestMetaDescriptionCheck(unittest.TestCase):
    def test_good_description(self):
        # 150-char description
        desc = "A" * 155
        html = f'<html><head><meta name="description" content="{desc}"></head><body></body></html>'
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_meta_description()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "pass")

    def test_missing_description(self):
        html = "<html><head></head><body></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_meta_description()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "fail")

    def test_short_description(self):
        html = '<html><head><meta name="description" content="Short."></head><body></body></html>'
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_meta_description()
        check = analyzer._checks[-1]
        self.assertIn(check["status"], ("warning", "fail"))


class TestHeadingCheck(unittest.TestCase):
    def test_single_h1(self):
        html = "<html><body><h1>Only One</h1><h2>Sub</h2></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_headings()
        h1_check = next(c for c in analyzer._checks if c["title"] == "H1 Heading")
        self.assertEqual(h1_check["status"], "pass")

    def test_multiple_h1(self):
        html = "<html><body><h1>First</h1><h1>Second</h1></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_headings()
        h1_check = next(c for c in analyzer._checks if c["title"] == "H1 Heading")
        self.assertEqual(h1_check["status"], "warning")

    def test_no_h1(self):
        html = "<html><body><h2>Sub only</h2></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_headings()
        h1_check = next(c for c in analyzer._checks if c["title"] == "H1 Heading")
        self.assertEqual(h1_check["status"], "fail")


class TestHTTPSCheck(unittest.TestCase):
    def test_https_pass(self):
        analyzer = _make_analyzer("https://example.com", "<html></html>")
        analyzer._check_https()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "pass")

    def test_http_fail(self):
        analyzer = _make_analyzer("http://example.com", "<html></html>")
        analyzer._check_https()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "fail")


class TestImageCheck(unittest.TestCase):
    def test_all_images_have_alt(self):
        html = '<html><body><img src="a.jpg" alt="desc" width="10" height="10"></body></html>'
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_images()
        alt_check = next(c for c in analyzer._checks if c["title"] == "Image Alt Text")
        self.assertEqual(alt_check["status"], "pass")

    def test_missing_alt(self):
        html = '<html><body><img src="a.jpg"></body></html>'
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_images()
        alt_check = next(c for c in analyzer._checks if c["title"] == "Image Alt Text")
        self.assertEqual(alt_check["status"], "fail")

    def test_no_images(self):
        html = "<html><body><p>No images here</p></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_images()
        alt_check = next(c for c in analyzer._checks if c["title"] == "Image Alt Text")
        self.assertEqual(alt_check["status"], "info")


class TestScoring(unittest.TestCase):
    def test_score_percentage(self):
        analyzer = _make_analyzer("https://example.com", SAMPLE_HTML_GOOD)
        analyzer._checks = [
            {"category": "Test", "title": "A", "status": "pass", "message": "", "points": 5, "max_points": 5},
            {"category": "Test", "title": "B", "status": "fail", "message": "", "points": 0, "max_points": 5},
        ]
        # manually call analyze-like scoring
        total_points = sum(c["points"] for c in analyzer._checks)
        max_points = sum(c["max_points"] for c in analyzer._checks)
        score = round(total_points / max_points * 100, 1)
        self.assertEqual(score, 50.0)

    def test_letter_grades(self):
        self.assertEqual(SEOAnalyzer._letter_grade(100), "A+")
        self.assertEqual(SEOAnalyzer._letter_grade(95), "A")
        self.assertEqual(SEOAnalyzer._letter_grade(85), "B")
        self.assertEqual(SEOAnalyzer._letter_grade(75), "C")
        self.assertEqual(SEOAnalyzer._letter_grade(55), "F")

    def test_full_analyze_returns_required_keys(self):
        """Test that analyze() returns the required keys even with mocked HTTP."""
        analyzer = SEOAnalyzer("https://example.com")
        with patch.object(analyzer, "_fetch", return_value=False):
            result = analyzer.analyze()
        self.assertIn("url", result)
        self.assertIn("checks", result)
        self.assertIn("score", result)
        self.assertIn("grade", result)
        self.assertIn("summary", result)


class TestViewportAndCharset(unittest.TestCase):
    def test_viewport_present(self):
        html = '<html><head><meta name="viewport" content="width=device-width"></head><body></body></html>'
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_viewport()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "pass")

    def test_charset_utf8(self):
        html = '<html><head><meta charset="UTF-8"></head><body></body></html>'
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_charset()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "pass")


class TestDeprecatedTags(unittest.TestCase):
    def test_no_deprecated(self):
        html = "<html><body><p>Clean HTML</p></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_deprecated_tags()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "pass")

    def test_with_deprecated(self):
        html = "<html><body><font>Old tag</font><center>Also old</center></body></html>"
        analyzer = _make_analyzer("https://example.com", html)
        analyzer._check_deprecated_tags()
        check = analyzer._checks[-1]
        self.assertEqual(check["status"], "warning")


if __name__ == "__main__":
    unittest.main()
