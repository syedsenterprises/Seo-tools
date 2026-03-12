"""
SEO Analyzer - Core analysis engine for SEO checks.

Performs 23+ checks on a given URL and returns a structured results dict
with a score and letter grade.
"""

import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "not", "no", "nor",
    "so", "yet", "both", "either", "neither", "that", "this", "these",
    "those", "it", "its", "as", "if", "than", "then", "when", "where",
    "who", "which", "what", "how", "all", "each", "every", "more", "most",
    "other", "some", "such", "only", "own", "same", "too", "very", "just",
    "about", "above", "after", "before", "between", "into", "through",
    "during", "up", "out", "off", "over", "under", "again",
}

DEPRECATED_TAGS = ["font", "center", "marquee", "bgsound", "blink",
                   "strike", "tt", "u", "big", "small", "basefont",
                   "applet", "acronym", "dir", "frame", "frameset",
                   "noframes", "isindex", "listing", "plaintext",
                   "xmp", "rb", "rtc"]


class SEOAnalyzer:
    """
    Analyzes a URL for SEO issues and returns structured results.

    Parameters
    ----------
    url : str
        The URL to analyze.
    timeout : int
        HTTP request timeout in seconds (default 10).
    """

    def __init__(self, url: str, timeout: int = 10) -> None:
        self.url = url
        self.timeout = timeout
        self.parsed_url = urlparse(url)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; SEOAnalyzer/1.0; "
                "+https://github.com/syedsenterprises/portfolio)"
            )
        })
        self._soup: Optional[BeautifulSoup] = None
        self._response: Optional[requests.Response] = None
        self._response_time: float = 0.0
        self._checks: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> Dict[str, Any]:
        """Fetch the URL and run all SEO checks.

        Returns
        -------
        dict
            keys: url, checks, score, grade, summary
        """
        fetch_ok = self._fetch()
        self._run_all_checks(fetch_ok)

        total_points = sum(c["points"] for c in self._checks)
        max_points = sum(c["max_points"] for c in self._checks)
        score = round((total_points / max_points * 100) if max_points else 0, 1)
        grade = self._letter_grade(score)

        pass_count = sum(1 for c in self._checks if c["status"] == "pass")
        warn_count = sum(1 for c in self._checks if c["status"] == "warning")
        fail_count = sum(1 for c in self._checks if c["status"] == "fail")
        info_count = sum(1 for c in self._checks if c["status"] == "info")

        return {
            "url": self.url,
            "checks": self._checks,
            "score": score,
            "grade": grade,
            "summary": {
                "pass": pass_count,
                "warning": warn_count,
                "fail": fail_count,
                "info": info_count,
                "total_points": total_points,
                "max_points": max_points,
            },
        }

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def _fetch(self) -> bool:
        """Fetch the URL and parse HTML. Returns True on success."""
        try:
            start = time.monotonic()
            self._response = self.session.get(
                self.url, timeout=self.timeout, allow_redirects=True
            )
            self._response_time = time.monotonic() - start
            self._soup = BeautifulSoup(self._response.text, "lxml")
            return True
        except requests.exceptions.Timeout:
            self._add_check(
                "Technical", "Page Fetch", "fail",
                f"Request timed out after {self.timeout}s.", 0, 5,
            )
            return False
        except requests.exceptions.RequestException as exc:
            self._add_check(
                "Technical", "Page Fetch", "fail",
                f"Could not fetch page: {exc}", 0, 5,
            )
            return False

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    def _run_all_checks(self, fetch_ok: bool) -> None:
        if not fetch_ok:
            return
        self._check_title()
        self._check_meta_description()
        self._check_headings()
        self._check_images()
        self._check_links()
        self._check_canonical()
        self._check_robots_meta()
        self._check_viewport()
        self._check_language()
        self._check_charset()
        self._check_open_graph()
        self._check_twitter_cards()
        self._check_structured_data()
        self._check_page_speed()
        self._check_https()
        self._check_url_structure()
        self._check_content_length()
        self._check_keyword_density()
        self._check_favicon()
        self._check_sitemap()
        self._check_robots_txt()
        self._check_hreflang()
        self._check_deprecated_tags()

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_title(self) -> None:
        tag = self._soup.find("title")
        if not tag or not tag.get_text(strip=True):
            self._add_check("Content", "Title Tag", "fail",
                            "Title tag is missing.", 0, 10)
            return
        text = tag.get_text(strip=True)
        length = len(text)
        if 50 <= length <= 60:
            self._add_check("Content", "Title Tag", "pass",
                            f"Title length is {length} chars (ideal 50–60): '{text}'", 10, 10)
        elif 30 <= length < 50 or 60 < length <= 70:
            self._add_check("Content", "Title Tag", "warning",
                            f"Title length is {length} chars (ideal 50–60): '{text}'", 6, 10)
        else:
            self._add_check("Content", "Title Tag", "fail",
                            f"Title length is {length} chars (ideal 50–60): '{text}'", 3, 10)

    def _check_meta_description(self) -> None:
        tag = self._soup.find("meta", attrs={"name": "description"})
        if not tag or not tag.get("content", "").strip():
            self._add_check("Content", "Meta Description", "fail",
                            "Meta description is missing.", 0, 10)
            return
        content = tag["content"].strip()
        length = len(content)
        if 150 <= length <= 160:
            self._add_check("Content", "Meta Description", "pass",
                            f"Meta description length is {length} chars (ideal 150–160).", 10, 10)
        elif 120 <= length < 150 or 160 < length <= 180:
            self._add_check("Content", "Meta Description", "warning",
                            f"Meta description length is {length} chars (ideal 150–160).", 6, 10)
        else:
            self._add_check("Content", "Meta Description", "fail",
                            f"Meta description length is {length} chars (ideal 150–160).", 3, 10)

    def _check_headings(self) -> None:
        h1_tags = self._soup.find_all("h1")
        if len(h1_tags) == 0:
            self._add_check("Content", "H1 Heading", "fail",
                            "No H1 heading found on the page.", 0, 8)
        elif len(h1_tags) == 1:
            self._add_check("Content", "H1 Heading", "pass",
                            f"Exactly one H1: '{h1_tags[0].get_text(strip=True)}'", 8, 8)
        else:
            self._add_check("Content", "H1 Heading", "warning",
                            f"Multiple H1 headings found ({len(h1_tags)}). Use only one.", 3, 8)

        # Check heading hierarchy (h2 before h3, etc.)
        levels = [int(tag.name[1]) for tag in self._soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6"])]
        hierarchy_ok = True
        for i in range(1, len(levels)):
            if levels[i] > levels[i - 1] + 1:
                hierarchy_ok = False
                break
        if levels and not hierarchy_ok:
            self._add_check("Content", "Heading Hierarchy", "warning",
                            "Heading levels are skipped (e.g., H1 → H3).", 3, 5)
        elif levels:
            self._add_check("Content", "Heading Hierarchy", "pass",
                            "Heading hierarchy is correct.", 5, 5)

    def _check_images(self) -> None:
        imgs = self._soup.find_all("img")
        if not imgs:
            self._add_check("Content", "Image Alt Text", "info",
                            "No images found on the page.", 5, 5)
            return
        missing_alt = [img for img in imgs if not img.get("alt")]
        missing_dims = [img for img in imgs
                        if not (img.get("width") and img.get("height"))]
        if not missing_alt:
            self._add_check("Content", "Image Alt Text", "pass",
                            f"All {len(imgs)} images have alt text.", 5, 5)
        else:
            self._add_check(
                "Content", "Image Alt Text", "fail",
                f"{len(missing_alt)} of {len(imgs)} images are missing alt text.", 0, 5,
            )
        if not missing_dims:
            self._add_check("Content", "Image Dimensions", "pass",
                            f"All {len(imgs)} images have explicit width/height.", 3, 3)
        else:
            self._add_check(
                "Content", "Image Dimensions", "warning",
                f"{len(missing_dims)} of {len(imgs)} images are missing width/height.", 1, 3,
            )

    def _check_links(self) -> None:
        links = self._soup.find_all("a", href=True)
        base = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"
        internal, external, empty = 0, 0, []
        for link in links:
            href = link["href"].strip()
            if not href or href == "#":
                empty.append(href)
            elif href.startswith(("http://", "https://")):
                if self.parsed_url.netloc in href:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1
        msg = (f"Found {len(links)} links: {internal} internal, "
               f"{external} external, {len(empty)} empty/hash.")
        status = "warning" if empty else "pass"
        points = 4 if not empty else 2
        self._add_check("Links", "Link Analysis", status, msg, points, 4)

    def _check_canonical(self) -> None:
        tag = self._soup.find("link", rel=lambda r: r and "canonical" in r)
        if tag and tag.get("href"):
            self._add_check("Technical", "Canonical URL", "pass",
                            f"Canonical URL present: {tag['href']}", 5, 5)
        else:
            self._add_check("Technical", "Canonical URL", "warning",
                            "No canonical URL tag found.", 0, 5)

    def _check_robots_meta(self) -> None:
        tag = self._soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if not tag:
            self._add_check("Technical", "Robots Meta", "info",
                            "No robots meta tag found (defaults to index, follow).", 4, 4)
            return
        content = tag.get("content", "").lower()
        issues = []
        if "noindex" in content:
            issues.append("noindex")
        if "nofollow" in content:
            issues.append("nofollow")
        if issues:
            self._add_check("Technical", "Robots Meta", "warning",
                            f"Robots meta contains: {', '.join(issues)}.", 1, 4)
        else:
            self._add_check("Technical", "Robots Meta", "pass",
                            f"Robots meta is set to: {content}.", 4, 4)

    def _check_viewport(self) -> None:
        tag = self._soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
        if tag and tag.get("content"):
            self._add_check("Mobile", "Viewport Meta", "pass",
                            f"Viewport meta tag present: {tag['content']}", 6, 6)
        else:
            self._add_check("Mobile", "Viewport Meta", "fail",
                            "Viewport meta tag is missing (not mobile-friendly).", 0, 6)

    def _check_language(self) -> None:
        html_tag = self._soup.find("html")
        lang = html_tag.get("lang", "") if html_tag else ""
        if lang:
            self._add_check("Internationalization", "Language Attribute", "pass",
                            f"HTML lang attribute is set to '{lang}'.", 4, 4)
        else:
            self._add_check("Internationalization", "Language Attribute", "warning",
                            "HTML lang attribute is missing.", 0, 4)

    def _check_charset(self) -> None:
        tag = self._soup.find("meta", charset=True)
        if not tag:
            # Also accept http-equiv content-type
            tag = self._soup.find("meta", attrs={"http-equiv": re.compile(r"content-type", re.I)})
        if tag:
            charset = tag.get("charset", "")
            if charset.lower() == "utf-8":
                self._add_check("Technical", "Charset", "pass",
                                "UTF-8 charset declared.", 3, 3)
            else:
                self._add_check("Technical", "Charset", "warning",
                                f"Charset declared as '{charset}' (UTF-8 recommended).", 1, 3)
        else:
            self._add_check("Technical", "Charset", "warning",
                            "No charset meta tag found.", 0, 3)

    def _check_open_graph(self) -> None:
        required = ["og:title", "og:description", "og:image", "og:url", "og:type"]
        found = []
        missing = []
        for prop in required:
            tag = self._soup.find("meta", property=prop)
            if tag and tag.get("content", "").strip():
                found.append(prop)
            else:
                missing.append(prop)
        if not missing:
            self._add_check("Social", "Open Graph Tags", "pass",
                            "All required Open Graph tags present.", 6, 6)
        elif len(missing) <= 2:
            self._add_check("Social", "Open Graph Tags", "warning",
                            f"Missing OG tags: {', '.join(missing)}.", 3, 6)
        else:
            self._add_check("Social", "Open Graph Tags", "fail",
                            f"Missing OG tags: {', '.join(missing)}.", 0, 6)

    def _check_twitter_cards(self) -> None:
        tag = self._soup.find("meta", attrs={"name": "twitter:card"})
        if tag and tag.get("content", "").strip():
            self._add_check("Social", "Twitter Card", "pass",
                            f"Twitter card meta present: {tag['content']}.", 3, 3)
        else:
            self._add_check("Social", "Twitter Card", "warning",
                            "twitter:card meta tag is missing.", 0, 3)

    def _check_structured_data(self) -> None:
        json_ld = self._soup.find("script", type="application/ld+json")
        microdata = self._soup.find(attrs={"itemscope": True})
        if json_ld:
            self._add_check("Content", "Structured Data", "pass",
                            "JSON-LD structured data found.", 5, 5)
        elif microdata:
            self._add_check("Content", "Structured Data", "pass",
                            "Microdata structured data found.", 5, 5)
        else:
            self._add_check("Content", "Structured Data", "warning",
                            "No structured data (JSON-LD / Microdata) found.", 0, 5)

    def _check_page_speed(self) -> None:
        response_ms = round(self._response_time * 1000)
        size_kb = round(len(self._response.content) / 1024, 1)
        if self._response_time < 1.0:
            self._add_check("Performance", "Response Time", "pass",
                            f"Page loaded in {response_ms}ms.", 5, 5)
        elif self._response_time < 3.0:
            self._add_check("Performance", "Response Time", "warning",
                            f"Page loaded in {response_ms}ms (aim < 1000ms).", 2, 5)
        else:
            self._add_check("Performance", "Response Time", "fail",
                            f"Page loaded in {response_ms}ms (very slow).", 0, 5)

        if size_kb < 500:
            self._add_check("Performance", "Page Size", "pass",
                            f"Page size is {size_kb} KB.", 3, 3)
        elif size_kb < 1000:
            self._add_check("Performance", "Page Size", "warning",
                            f"Page size is {size_kb} KB (aim < 500 KB).", 1, 3)
        else:
            self._add_check("Performance", "Page Size", "fail",
                            f"Page size is {size_kb} KB (very large).", 0, 3)

    def _check_https(self) -> None:
        if self.parsed_url.scheme == "https":
            self._add_check("Security", "HTTPS", "pass",
                            "Site uses HTTPS.", 8, 8)
        else:
            self._add_check("Security", "HTTPS", "fail",
                            "Site does not use HTTPS.", 0, 8)

    def _check_url_structure(self) -> None:
        path = self.parsed_url.path
        issues = []
        if any(c.isupper() for c in path):
            issues.append("uppercase letters")
        if "_" in path:
            issues.append("underscores (use hyphens)")
        if len(path) > 100:
            issues.append("very long URL path")
        if not issues:
            self._add_check("Technical", "URL Structure", "pass",
                            "URL structure looks clean.", 4, 4)
        else:
            self._add_check("Technical", "URL Structure", "warning",
                            f"URL issues: {', '.join(issues)}.", 1, 4)

    def _check_content_length(self) -> None:
        text = self._soup.get_text(separator=" ", strip=True)
        words = [w for w in text.split() if w.isalpha()]
        count = len(words)
        if count >= 300:
            self._add_check("Content", "Content Length", "pass",
                            f"Page has {count} words (aim 300+).", 6, 6)
        elif count >= 100:
            self._add_check("Content", "Content Length", "warning",
                            f"Page has {count} words (aim 300+).", 3, 6)
        else:
            self._add_check("Content", "Content Length", "fail",
                            f"Page has only {count} words (too thin content).", 0, 6)

    def _check_keyword_density(self) -> None:
        text = self._soup.get_text(separator=" ", strip=True).lower()
        words = [w for w in re.findall(r"[a-z]+", text) if w not in STOP_WORDS and len(w) > 2]
        if not words:
            self._add_check("Content", "Keyword Density", "info",
                            "Could not determine keywords (no content).", 2, 2)
            return
        freq: Dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        top10 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
        top_str = ", ".join(f"{w}({c})" for w, c in top10)
        self._add_check("Content", "Keyword Density", "info",
                        f"Top keywords: {top_str}", 2, 2)

    def _check_favicon(self) -> None:
        tag = self._soup.find("link", rel=lambda r: r and any(
            v in ("icon", "shortcut icon") for v in (r if isinstance(r, list) else [r])
        ))
        if tag:
            self._add_check("Branding", "Favicon", "pass",
                            "Favicon link tag found.", 3, 3)
        else:
            self._add_check("Branding", "Favicon", "warning",
                            "No favicon link tag found.", 0, 3)

    def _check_sitemap(self) -> None:
        sitemap_url = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}/sitemap.xml"
        try:
            resp = self.session.head(sitemap_url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 200:
                self._add_check("Technical", "Sitemap.xml", "pass",
                                f"sitemap.xml accessible at {sitemap_url}", 4, 4)
            else:
                self._add_check("Technical", "Sitemap.xml", "warning",
                                f"sitemap.xml returned HTTP {resp.status_code}.", 0, 4)
        except requests.exceptions.RequestException:
            self._add_check("Technical", "Sitemap.xml", "warning",
                            "sitemap.xml not accessible.", 0, 4)

    def _check_robots_txt(self) -> None:
        robots_url = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}/robots.txt"
        try:
            resp = self.session.get(robots_url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 200:
                self._add_check("Technical", "robots.txt", "pass",
                                f"robots.txt accessible at {robots_url}", 4, 4)
            else:
                self._add_check("Technical", "robots.txt", "warning",
                                f"robots.txt returned HTTP {resp.status_code}.", 0, 4)
        except requests.exceptions.RequestException:
            self._add_check("Technical", "robots.txt", "warning",
                            "robots.txt not accessible.", 0, 4)

    def _check_hreflang(self) -> None:
        tags = self._soup.find_all("link", rel=lambda r: r and "alternate" in r)
        hreflang_tags = [t for t in tags if t.get("hreflang")]
        if hreflang_tags:
            langs = [t["hreflang"] for t in hreflang_tags]
            self._add_check(
                "Internationalization", "Hreflang Tags", "pass",
                f"Hreflang tags found for: {', '.join(langs)}.", 3, 3,
            )
        else:
            self._add_check("Internationalization", "Hreflang Tags", "info",
                            "No hreflang tags found (only needed for multi-language sites).", 3, 3)

    def _check_deprecated_tags(self) -> None:
        found = []
        for tag_name in DEPRECATED_TAGS:
            if self._soup.find(tag_name):
                found.append(f"<{tag_name}>")
        if not found:
            self._add_check("Technical", "Deprecated Tags", "pass",
                            "No deprecated HTML tags found.", 4, 4)
        else:
            self._add_check("Technical", "Deprecated Tags", "warning",
                            f"Deprecated tags found: {', '.join(found)}.", 0, 4)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_check(
        self,
        category: str,
        title: str,
        status: str,
        message: str,
        points: int,
        max_points: int,
    ) -> None:
        self._checks.append({
            "category": category,
            "title": title,
            "status": status,
            "message": message,
            "points": points,
            "max_points": max_points,
        })

    @staticmethod
    def _letter_grade(score: float) -> str:
        if score >= 97:
            return "A+"
        if score >= 93:
            return "A"
        if score >= 90:
            return "A-"
        if score >= 87:
            return "B+"
        if score >= 83:
            return "B"
        if score >= 80:
            return "B-"
        if score >= 77:
            return "C+"
        if score >= 73:
            return "C"
        if score >= 70:
            return "C-"
        if score >= 67:
            return "D+"
        if score >= 63:
            return "D"
        if score >= 60:
            return "D-"
        return "F"
