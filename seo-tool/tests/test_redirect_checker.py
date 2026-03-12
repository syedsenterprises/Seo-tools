"""
Unit tests for redirect_checker.py
"""

import unittest
from unittest.mock import MagicMock, call, patch

from redirect_checker import RedirectChecker


def _make_response(status_code: int, location: str = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_redirect = status_code in (301, 302, 303, 307, 308)
    if location:
        resp.headers = {"Location": location}
    else:
        resp.headers = {}
    return resp


class TestRedirectChainFollowing(unittest.TestCase):
    @patch("requests.Session.get")
    def test_no_redirect(self, mock_get):
        mock_get.return_value = _make_response(200)
        checker = RedirectChecker("https://example.com/")
        result = checker.check()
        self.assertEqual(result["chain_length"], 1)
        self.assertEqual(result["chain"][0]["status_code"], 200)
        self.assertFalse(result["has_loop"])

    @patch("requests.Session.get")
    def test_single_redirect(self, mock_get):
        mock_get.side_effect = [
            _make_response(301, "https://example.com/new"),
            _make_response(200),
        ]
        checker = RedirectChecker("https://example.com/old")
        result = checker.check()
        self.assertEqual(result["chain_length"], 2)
        self.assertEqual(result["chain"][0]["status_code"], 301)
        self.assertEqual(result["chain"][1]["status_code"], 200)

    @patch("requests.Session.get")
    def test_http_to_https_redirect_noted(self, mock_get):
        mock_get.side_effect = [
            _make_response(301, "https://example.com/"),
            _make_response(200),
        ]
        checker = RedirectChecker("http://example.com/")
        result = checker.check()
        http_to_https = [i for i in result["issues"] if "HTTP → HTTPS" in i]
        self.assertGreater(len(http_to_https), 0)

    @patch("requests.Session.get")
    def test_https_to_http_flagged(self, mock_get):
        mock_get.side_effect = [
            _make_response(301, "http://example.com/"),
            _make_response(200),
        ]
        checker = RedirectChecker("https://example.com/")
        result = checker.check()
        mixed = [i for i in result["issues"] if "HTTPS → HTTP" in i]
        self.assertGreater(len(mixed), 0)

    @patch("requests.Session.get")
    def test_long_chain_flagged(self, mock_get):
        # 4 hops: triggers long chain warning
        mock_get.side_effect = [
            _make_response(301, "https://example.com/step2"),
            _make_response(301, "https://example.com/step3"),
            _make_response(301, "https://example.com/step4"),
            _make_response(200),
        ]
        checker = RedirectChecker("https://example.com/start")
        result = checker.check()
        long_chain = [i for i in result["issues"] if "Long redirect chain" in i]
        self.assertGreater(len(long_chain), 0)
        self.assertEqual(result["chain_length"], 4)


class TestLoopDetection(unittest.TestCase):
    @patch("requests.Session.get")
    def test_redirect_loop_detected(self, mock_get):
        mock_get.side_effect = [
            _make_response(301, "https://example.com/b"),
            _make_response(301, "https://example.com/a"),  # loops back
            _make_response(200),  # should not reach here
        ]
        checker = RedirectChecker("https://example.com/a", max_redirects=10)
        result = checker.check()
        self.assertTrue(result["has_loop"])
        loop_issues = [i for i in result["issues"] if "loop" in i.lower()]
        self.assertGreater(len(loop_issues), 0)


class TestTimeoutAndError(unittest.TestCase):
    @patch("requests.Session.get")
    def test_timeout_handling(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()
        checker = RedirectChecker("https://example.com/")
        result = checker.check()
        self.assertIn("issues", result)

    @patch("requests.Session.get")
    def test_connection_error_handling(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("refused")
        checker = RedirectChecker("https://example.com/")
        result = checker.check()
        self.assertIn("issues", result)
        self.assertIn("chain", result)


class TestDetectRedirectIssues(unittest.TestCase):
    def test_http_to_https(self):
        issues = []
        RedirectChecker._detect_redirect_issues(
            "http://example.com", "https://example.com", issues
        )
        self.assertEqual(len(issues), 1)
        self.assertIn("HTTP → HTTPS", issues[0])

    def test_https_to_http(self):
        issues = []
        RedirectChecker._detect_redirect_issues(
            "https://example.com", "http://example.com", issues
        )
        self.assertEqual(len(issues), 1)
        self.assertIn("HTTPS → HTTP", issues[0])

    def test_same_scheme_no_issue(self):
        issues = []
        RedirectChecker._detect_redirect_issues(
            "https://example.com/a", "https://example.com/b", issues
        )
        self.assertEqual(issues, [])


class TestResultStructure(unittest.TestCase):
    @patch("requests.Session.get")
    def test_result_has_required_keys(self, mock_get):
        mock_get.return_value = _make_response(200)
        checker = RedirectChecker("https://example.com/")
        result = checker.check()
        for key in ("url", "chain", "chain_length", "has_loop", "issues", "final_url"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
