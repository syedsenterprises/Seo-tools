"""
Redirect Checker - Follows redirect chains and detects issues.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests


class RedirectChecker:
    """
    Follows redirect chains for a URL and reports issues.

    Parameters
    ----------
    url : str
        The URL to check.
    timeout : int
        HTTP request timeout per hop (default 10).
    max_redirects : int
        Maximum redirects to follow (default 10).
    """

    def __init__(self, url: str, timeout: int = 10, max_redirects: int = 10) -> None:
        self.url = url
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.session = requests.Session()
        self.session.max_redirects = max_redirects
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; RedirectChecker/1.0)"})

    def check(self) -> Dict[str, Any]:
        """Follow the redirect chain for the configured URL.

        Returns
        -------
        dict
            url, chain, chain_length, has_loop, issues, final_url
        """
        return self._follow_chain(self.url)

    def check_page_links(self) -> List[Dict[str, Any]]:
        """Fetch the page and check redirect chains for all internal links.

        Returns a list of redirect-check result dicts for each unique link.
        """
        from bs4 import BeautifulSoup

        parsed = urlparse(self.url)
        base_netloc = parsed.netloc
        results: List[Dict[str, Any]] = []
        try:
            resp = self.session.get(self.url, timeout=self.timeout, allow_redirects=False)
            soup = BeautifulSoup(resp.text, "lxml")
        except requests.exceptions.RequestException:
            return results

        seen = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            if href.startswith("/"):
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif not href.startswith("http"):
                continue
            if urlparse(href).netloc != base_netloc:
                continue
            if href in seen:
                continue
            seen.add(href)
            results.append(self._follow_chain(href))
        return results

    # ------------------------------------------------------------------
    # Core chain-following logic
    # ------------------------------------------------------------------

    def _follow_chain(self, start_url: str) -> Dict[str, Any]:
        chain: List[Dict[str, Any]] = []
        issues: List[str] = []
        seen_urls = set()
        has_loop = False
        current_url = start_url
        final_url = start_url

        for _ in range(self.max_redirects + 1):
            if current_url in seen_urls:
                has_loop = True
                issues.append(f"Redirect loop detected at: {current_url}")
                break
            seen_urls.add(current_url)
            try:
                resp = self.session.get(
                    current_url,
                    timeout=self.timeout,
                    allow_redirects=False,
                )
            except requests.exceptions.Timeout:
                issues.append(f"Timeout while following redirect at: {current_url}")
                break
            except requests.exceptions.RequestException as exc:
                issues.append(f"Error at {current_url}: {exc}")
                break

            redirect_to: Optional[str] = None
            if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                redirect_to = resp.headers.get("Location", "")
                if redirect_to and not redirect_to.startswith("http"):
                    parsed = urlparse(current_url)
                    redirect_to = f"{parsed.scheme}://{parsed.netloc}{redirect_to}"

            chain.append({
                "url": current_url,
                "status_code": resp.status_code,
                "redirect_to": redirect_to,
            })
            final_url = current_url

            if redirect_to:
                self._detect_redirect_issues(current_url, redirect_to, issues)
                current_url = redirect_to
            else:
                break

        chain_length = len(chain)

        if chain_length > 3:
            issues.append(f"Long redirect chain ({chain_length} hops). Aim for ≤3.")

        return {
            "url": start_url,
            "chain": chain,
            "chain_length": chain_length,
            "has_loop": has_loop,
            "issues": issues,
            "final_url": final_url,
        }

    # ------------------------------------------------------------------
    # Issue detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_redirect_issues(
        from_url: str, to_url: str, issues: List[str]
    ) -> None:
        from_scheme = urlparse(from_url).scheme
        to_scheme = urlparse(to_url).scheme

        if from_scheme == "http" and to_scheme == "https":
            issues.append(f"HTTP → HTTPS redirect (good): {from_url} → {to_url}")
        elif from_scheme == "https" and to_scheme == "http":
            issues.append(
                f"⚠ HTTPS → HTTP redirect (mixed content / bad): {from_url} → {to_url}"
            )
