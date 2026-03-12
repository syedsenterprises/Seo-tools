"""
Broken Link Checker - Detects broken links on a web page.

Uses ThreadPoolExecutor for parallel HTTP HEAD/GET requests.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class BrokenLinkChecker:
    """
    Checks all links on a page for broken URLs.

    Parameters
    ----------
    url : str
        The page URL to check.
    timeout : int
        Per-request timeout in seconds (default 10).
    max_workers : int
        Maximum parallel threads (default 10).
    """

    def __init__(self, url: str, timeout: int = 10, max_workers: int = 10) -> None:
        self.url = url
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; BrokenLinkChecker/1.0)"
            )
        })

    def check(self) -> Dict[str, Any]:
        """Fetch the page and check all extracted links.

        Returns
        -------
        dict
            Summary counts and lists of broken/all links.
        """
        try:
            response = self.session.get(self.url, timeout=self.timeout, allow_redirects=True)
            soup = BeautifulSoup(response.text, "lxml")
        except requests.exceptions.RequestException as exc:
            return {
                "error": str(exc),
                "total_links": 0,
                "checked": 0,
                "ok": 0,
                "redirects": 0,
                "client_errors": 0,
                "server_errors": 0,
                "timeouts": 0,
                "errors": 0,
                "broken_links": [],
                "all_links": [],
            }

        links = self._extract_links(soup)
        results = self._check_links_parallel(links)
        return self._summarize(results)

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _extract_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract all links from the page HTML."""
        extracted: List[Dict[str, str]] = []
        selectors = [
            ("a", "href"),
            ("img", "src"),
            ("script", "src"),
            ("link", "href"),
        ]
        seen = set()
        for tag_name, attr in selectors:
            for tag in soup.find_all(tag_name, **{attr: True}):
                raw = tag[attr].strip()
                if not raw or raw.startswith(("data:", "javascript:", "#", "mailto:", "tel:")):
                    continue
                absolute = urljoin(self.url, raw)
                parsed = urlparse(absolute)
                if parsed.scheme not in ("http", "https"):
                    continue
                key = (absolute, tag_name)
                if key not in seen:
                    seen.add(key)
                    extracted.append({"url": absolute, "source_tag": tag_name})
        return extracted

    # ------------------------------------------------------------------
    # Checking
    # ------------------------------------------------------------------

    def _check_single_link(self, link_info: Dict[str, str]) -> Dict[str, Any]:
        """Check a single link. Returns a result dict."""
        url = link_info["url"]
        source_tag = link_info["source_tag"]
        result: Dict[str, Any] = {
            "url": url,
            "status_code": None,
            "status": "error",
            "error": None,
            "source_tag": source_tag,
        }
        try:
            resp = self.session.head(
                url, timeout=self.timeout, allow_redirects=True
            )
            # Some servers return 405 for HEAD; fall back to GET
            if resp.status_code == 405:
                resp = self.session.get(
                    url, timeout=self.timeout, allow_redirects=True, stream=True
                )
                resp.close()
            result["status_code"] = resp.status_code
            result["status"] = self._classify(resp.status_code)
        except requests.exceptions.Timeout:
            result["status"] = "timeout"
            result["error"] = "Request timed out"
        except requests.exceptions.RequestException as exc:
            result["status"] = "error"
            result["error"] = str(exc)
        return result

    def _check_links_parallel(
        self, links: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_link = {
                executor.submit(self._check_single_link, link): link
                for link in links
            }
            for future in as_completed(future_to_link):
                try:
                    results.append(future.result())
                except (RuntimeError, TimeoutError) as exc:
                    link = future_to_link[future]
                    results.append({
                        "url": link["url"],
                        "status_code": None,
                        "status": "error",
                        "error": str(exc),
                        "source_tag": link["source_tag"],
                    })
        return results

    # ------------------------------------------------------------------
    # Classification & summary
    # ------------------------------------------------------------------

    @staticmethod
    def _classify(status_code: int) -> str:
        if 200 <= status_code < 300:
            return "ok"
        if 300 <= status_code < 400:
            return "redirect"
        if 400 <= status_code < 500:
            return "client_error"
        if 500 <= status_code < 600:
            return "server_error"
        return "error"

    @staticmethod
    def _summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        ok = sum(1 for r in results if r["status"] == "ok")
        redirects = sum(1 for r in results if r["status"] == "redirect")
        client_errors = sum(1 for r in results if r["status"] == "client_error")
        server_errors = sum(1 for r in results if r["status"] == "server_error")
        timeouts = sum(1 for r in results if r["status"] == "timeout")
        errors = sum(1 for r in results if r["status"] == "error")

        broken = [
            r for r in results
            if r["status"] in ("client_error", "server_error", "timeout", "error")
        ]

        return {
            "total_links": len(results),
            "checked": len(results),
            "ok": ok,
            "redirects": redirects,
            "client_errors": client_errors,
            "server_errors": server_errors,
            "timeouts": timeouts,
            "errors": errors,
            "broken_links": broken,
            "all_links": results,
        }
