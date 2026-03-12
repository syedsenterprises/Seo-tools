"""
Sitemap Parser - Fetches and parses sitemap.xml files.

Handles sitemap index files recursively (max depth 3) and optionally
validates each URL with a HEAD request.
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from xml.etree import ElementTree

import requests


# XML namespaces used in sitemaps
_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}

_MAX_URLS = 50_000
_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class SitemapParser:
    """
    Fetches and parses sitemap.xml for a given domain.

    Parameters
    ----------
    url : str
        Any URL on the target domain (sitemap is fetched from the root).
    timeout : int
        HTTP request timeout in seconds (default 10).
    """

    def __init__(self, url: str, timeout: int = 10) -> None:
        parsed = urlparse(url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.domain = parsed.netloc
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; SitemapParser/1.0)"})

    def parse(self, validate: bool = False) -> Dict[str, Any]:
        """Fetch and parse the sitemap. Optionally validate each URL.

        Parameters
        ----------
        validate : bool
            If True, HEAD-check each URL in the sitemap.

        Returns
        -------
        dict
            Structured sitemap results.
        """
        sitemap_url = self._find_sitemap_url()
        if not sitemap_url:
            return {
                "sitemap_url": None,
                "found": False,
                "is_index": False,
                "total_urls": 0,
                "issues": [{"type": "missing", "message": "sitemap.xml not found"}],
                "urls": [],
                "validated_urls": [],
            }

        issues: List[Dict[str, str]] = []
        urls: List[Dict[str, Any]] = []

        content, size_bytes = self._fetch_content(sitemap_url)
        if content is None:
            return {
                "sitemap_url": sitemap_url,
                "found": False,
                "is_index": False,
                "total_urls": 0,
                "issues": [{"type": "fetch_error", "message": "Could not fetch sitemap"}],
                "urls": [],
                "validated_urls": [],
            }

        if size_bytes > _MAX_SIZE_BYTES:
            issues.append({
                "type": "too_large",
                "message": f"Sitemap is {size_bytes // (1024*1024)}MB (limit 50MB)",
            })

        is_index, urls = self._parse_xml(content, sitemap_url, depth=0, issues=issues)

        # Detect duplicates
        seen_locs: Dict[str, int] = {}
        for entry in urls:
            loc = entry.get("loc", "")
            seen_locs[loc] = seen_locs.get(loc, 0) + 1
        for loc, count in seen_locs.items():
            if count > 1:
                issues.append({"type": "duplicate", "message": f"Duplicate URL: {loc}"})

        # Check for URLs outside the domain
        for entry in urls:
            loc = entry.get("loc", "")
            if loc and urlparse(loc).netloc != self.domain:
                issues.append({
                    "type": "external_url",
                    "message": f"URL not matching domain: {loc}",
                })

        if len(urls) > _MAX_URLS:
            issues.append({
                "type": "too_many_urls",
                "message": f"Sitemap has {len(urls)} URLs (limit 50,000)",
            })

        validated: List[Dict[str, Any]] = []
        if validate:
            validated = self._validate_urls(urls)

        return {
            "sitemap_url": sitemap_url,
            "found": True,
            "is_index": is_index,
            "total_urls": len(urls),
            "issues": issues,
            "urls": urls,
            "validated_urls": validated,
        }

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _find_sitemap_url(self) -> Optional[str]:
        """Try sitemap.xml directly; also check robots.txt."""
        candidate = f"{self.base_url}/sitemap.xml"
        try:
            resp = self.session.head(candidate, timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 200:
                return candidate
        except requests.exceptions.RequestException:
            pass

        # Check robots.txt for Sitemap: directive
        try:
            robots_url = f"{self.base_url}/robots.txt"
            resp = self.session.get(robots_url, timeout=self.timeout)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    match = re.match(r"Sitemap:\s*(.+)", line, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
        except requests.exceptions.RequestException:
            pass

        return None

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def _fetch_content(self, url: str) -> tuple:
        """Return (content_bytes, size_bytes) or (None, 0) on failure."""
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 200:
                return resp.content, len(resp.content)
        except requests.exceptions.RequestException:
            pass
        return None, 0

    # ------------------------------------------------------------------
    # XML Parsing
    # ------------------------------------------------------------------

    def _parse_xml(
        self,
        content: bytes,
        source_url: str,
        depth: int,
        issues: List[Dict[str, str]],
    ) -> tuple:
        """Parse sitemap XML. Returns (is_index, list_of_url_dicts)."""
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            issues.append({"type": "parse_error", "message": f"XML parse error: {exc}"})
            return False, []

        # Strip namespace for easy tag matching
        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        if tag == "sitemapindex":
            return True, self._parse_sitemap_index(root, depth, issues)

        return False, self._parse_urlset(root, source_url, issues)

    def _parse_sitemap_index(
        self,
        root: ElementTree.Element,
        depth: int,
        issues: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """Recursively parse a sitemap index (max depth 3)."""
        all_urls: List[Dict[str, Any]] = []
        if depth >= 3:
            issues.append({"type": "depth_limit", "message": "Sitemap index depth limit reached"})
            return all_urls

        for sitemap_elem in root.iter():
            local = sitemap_elem.tag.split("}")[-1] if "}" in sitemap_elem.tag else sitemap_elem.tag
            if local != "sitemap":
                continue
            loc_elem = None
            for child in sitemap_elem:
                child_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child_local == "loc":
                    loc_elem = child
                    break
            if loc_elem is not None and loc_elem.text:
                child_url = loc_elem.text.strip()
                content, _ = self._fetch_content(child_url)
                if content:
                    _, child_urls = self._parse_xml(content, child_url, depth + 1, issues)
                    all_urls.extend(child_urls)
        return all_urls

    def _parse_urlset(
        self,
        root: ElementTree.Element,
        source_url: str,
        issues: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """Parse a standard urlset sitemap."""
        urls: List[Dict[str, Any]] = []
        for url_elem in root.iter():
            local = url_elem.tag.split("}")[-1] if "}" in url_elem.tag else url_elem.tag
            if local != "url":
                continue
            entry: Dict[str, Any] = {"loc": None, "lastmod": None, "changefreq": None, "priority": None}
            for child in url_elem:
                child_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child_local in entry:
                    entry[child_local] = child.text.strip() if child.text else None
            if entry["loc"]:
                if not entry["lastmod"]:
                    issues.append({
                        "type": "missing_lastmod",
                        "message": f"Missing <lastmod> for {entry['loc']}",
                    })
                urls.append(entry)
        return urls

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_urls(self, urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """HEAD-check each URL and return validation results."""
        validated: List[Dict[str, Any]] = []
        for entry in urls[:200]:  # limit to 200 to avoid long waits
            loc = entry.get("loc", "")
            result: Dict[str, Any] = {"loc": loc, "status_code": None, "accessible": False}
            try:
                resp = self.session.head(loc, timeout=self.timeout, allow_redirects=True)
                result["status_code"] = resp.status_code
                result["accessible"] = resp.status_code == 200
            except requests.exceptions.RequestException as exc:
                result["error"] = str(exc)
            validated.append(result)
        return validated
