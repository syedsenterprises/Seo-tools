"""
Lighthouse Runner - Google Lighthouse CLI integration.

Runs Lighthouse via subprocess and parses the JSON output.
If Lighthouse is not installed, returns a helpful message.
"""

import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional


class LighthouseRunner:
    """
    Runs Google Lighthouse against a URL and returns structured scores.

    Parameters
    ----------
    url : str
        The URL to audit.
    timeout : int
        Subprocess timeout in seconds (default 120).
    """

    def __init__(self, url: str, timeout: int = 120) -> None:
        self.url = url
        self.timeout = timeout

    def run(self) -> Dict[str, Any]:
        """Run a Lighthouse audit.

        Returns
        -------
        dict
            Keys: available, scores, metrics, opportunities, diagnostics.
            If Lighthouse is not installed, available=False and an
            install_hint is included.
        """
        if not self._is_available():
            return {
                "available": False,
                "install_hint": (
                    "Google Lighthouse is not installed. "
                    "Install it with: npm install -g lighthouse"
                ),
                "scores": {},
                "metrics": {},
                "opportunities": [],
                "diagnostics": [],
            }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        try:
            cmd = [
                "lighthouse",
                self.url,
                "--output=json",
                "--quiet",
                f"--output-path={tmp_path}",
                '--chrome-flags=--headless --no-sandbox --disable-gpu',
            ]
            subprocess.run(
                cmd,
                timeout=self.timeout,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return self._parse_report(tmp_path)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as exc:
            return self._error_result(str(exc))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_available() -> bool:
        """Return True if the 'lighthouse' CLI is on PATH."""
        try:
            subprocess.run(
                ["lighthouse", "--version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _parse_report(self, json_path: str) -> Dict[str, Any]:
        """Parse Lighthouse JSON output file."""
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            return self._error_result(f"Could not read Lighthouse report: {exc}")

        categories = data.get("categories", {})
        scores = {
            "performance": self._score(categories, "performance"),
            "accessibility": self._score(categories, "accessibility"),
            "best_practices": self._score(categories, "best-practices"),
            "seo": self._score(categories, "seo"),
        }

        audits = data.get("audits", {})
        metrics = self._extract_metrics(audits)
        opportunities = self._extract_opportunities(audits)
        diagnostics = self._extract_diagnostics(audits)

        return {
            "available": True,
            "scores": scores,
            "metrics": metrics,
            "opportunities": opportunities,
            "diagnostics": diagnostics,
        }

    @staticmethod
    def _score(categories: Dict[str, Any], key: str) -> Optional[int]:
        cat = categories.get(key, {})
        score = cat.get("score")
        if score is None:
            return None
        return round(score * 100)

    @staticmethod
    def _extract_metrics(audits: Dict[str, Any]) -> Dict[str, str]:
        keys_map = {
            "fcp": "first-contentful-paint",
            "lcp": "largest-contentful-paint",
            "tbt": "total-blocking-time",
            "cls": "cumulative-layout-shift",
            "speed_index": "speed-index",
        }
        metrics: Dict[str, str] = {}
        for metric_key, audit_key in keys_map.items():
            audit = audits.get(audit_key, {})
            display = audit.get("displayValue", "N/A")
            metrics[metric_key] = display
        return metrics

    @staticmethod
    def _extract_opportunities(audits: Dict[str, Any]) -> List[Dict[str, str]]:
        opps: List[Dict[str, str]] = []
        for audit in audits.values():
            if audit.get("details", {}).get("type") == "opportunity":
                if audit.get("score", 1) is not None and audit.get("score", 1) < 1:
                    opps.append({
                        "id": audit.get("id", ""),
                        "title": audit.get("title", ""),
                        "description": audit.get("description", ""),
                        "display_value": audit.get("displayValue", ""),
                    })
        return opps

    @staticmethod
    def _extract_diagnostics(audits: Dict[str, Any]) -> List[Dict[str, str]]:
        diags: List[Dict[str, str]] = []
        for audit in audits.values():
            if audit.get("details", {}).get("type") == "table":
                if audit.get("score", 1) is not None and audit.get("score", 1) < 1:
                    diags.append({
                        "id": audit.get("id", ""),
                        "title": audit.get("title", ""),
                        "display_value": audit.get("displayValue", ""),
                    })
        return diags

    @staticmethod
    def _error_result(message: str) -> Dict[str, Any]:
        return {
            "available": True,
            "error": message,
            "scores": {},
            "metrics": {},
            "opportunities": [],
            "diagnostics": [],
        }
