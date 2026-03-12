"""
Report Generator - Produces a styled HTML report from analysis results.

Uses a dark GitHub-inspired theme.
"""

from datetime import datetime
from typing import Any, Dict, Optional


_STATUS_ICON = {
    "pass": "✅",
    "warning": "⚠️",
    "fail": "❌",
    "info": "ℹ️",
}

_STATUS_COLOR = {
    "pass": "#3fb950",
    "warning": "#d29922",
    "fail": "#f85149",
    "info": "#58a6ff",
}


class ReportGenerator:
    """
    Generates a self-contained HTML report from SEO analysis results.

    Parameters
    ----------
    seo_results : dict
        Output from SEOAnalyzer.analyze().
    broken_links_results : dict, optional
    sitemap_results : dict, optional
    lighthouse_results : dict, optional
    redirect_results : dict, optional
    """

    def __init__(
        self,
        seo_results: Dict[str, Any],
        broken_links_results: Optional[Dict[str, Any]] = None,
        sitemap_results: Optional[Dict[str, Any]] = None,
        lighthouse_results: Optional[Dict[str, Any]] = None,
        redirect_results: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.seo = seo_results
        self.broken = broken_links_results
        self.sitemap = sitemap_results
        self.lighthouse = lighthouse_results
        self.redirect = redirect_results
        self.generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    def generate(self) -> str:
        """Return the complete HTML report as a string."""
        sections = [
            self._header(),
            self._score_card(),
            self._seo_checks_table(),
        ]
        if self.broken:
            sections.append(self._broken_links_section())
        if self.sitemap:
            sections.append(self._sitemap_section())
        if self.lighthouse:
            sections.append(self._lighthouse_section())
        if self.redirect:
            sections.append(self._redirect_section())
        sections.append(self._footer())

        body = "\n".join(sections)
        return self._wrap_html(body)

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _header(self) -> str:
        url = self.seo.get("url", "")
        return f"""
<div class="header">
  <h1>🔍 SEO Analysis Report</h1>
  <p class="subtitle">URL: <a href="{url}" target="_blank">{url}</a></p>
  <p class="subtitle">Generated: {self.generated_at}</p>
</div>
"""

    def _score_card(self) -> str:
        score = self.seo.get("score", 0)
        grade = self.seo.get("grade", "F")
        summary = self.seo.get("summary", {})
        color = self._grade_color(score)
        return f"""
<div class="section">
  <h2>📊 Score Summary</h2>
  <div class="score-card">
    <div class="grade" style="color:{color}">{grade}</div>
    <div class="score-num" style="color:{color}">{score}/100</div>
    <div class="score-pills">
      <span class="pill pass">✅ Pass: {summary.get('pass', 0)}</span>
      <span class="pill warning">⚠️ Warning: {summary.get('warning', 0)}</span>
      <span class="pill fail">❌ Fail: {summary.get('fail', 0)}</span>
      <span class="pill info">ℹ️ Info: {summary.get('info', 0)}</span>
    </div>
  </div>
</div>
"""

    def _seo_checks_table(self) -> str:
        checks = self.seo.get("checks", [])
        # Group by category
        categories: Dict[str, list] = {}
        for check in checks:
            cat = check.get("category", "Other")
            categories.setdefault(cat, []).append(check)

        rows = []
        for cat, items in categories.items():
            rows.append(f'<tr class="cat-row"><td colspan="4"><strong>{cat}</strong></td></tr>')
            for item in items:
                icon = _STATUS_ICON.get(item["status"], "")
                color = _STATUS_COLOR.get(item["status"], "#c9d1d9")
                rows.append(
                    f'<tr>'
                    f'<td style="color:{color}">{icon}</td>'
                    f'<td>{item["title"]}</td>'
                    f'<td style="color:{color}">{item["status"].upper()}</td>'
                    f'<td>{item["message"]}</td>'
                    f'</tr>'
                )

        return f"""
<div class="section">
  <h2>🔎 Core SEO Checks</h2>
  <table>
    <thead><tr><th>Status</th><th>Check</th><th>Result</th><th>Details</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
</div>
"""

    def _broken_links_section(self) -> str:
        bl = self.broken
        if bl.get("error"):
            return f'<div class="section"><h2>🔗 Broken Links</h2><p class="error">{bl["error"]}</p></div>'

        rows = []
        for link in bl.get("broken_links", []):
            color = _STATUS_COLOR.get("fail", "#f85149")
            rows.append(
                f'<tr>'
                f'<td><a href="{link["url"]}" target="_blank">{link["url"][:80]}</a></td>'
                f'<td style="color:{color}">{link.get("status_code","N/A")}</td>'
                f'<td>{link.get("status","")}</td>'
                f'<td>{link.get("source_tag","")}</td>'
                f'</tr>'
            )

        table = ""
        if rows:
            table = f"""
<table>
  <thead><tr><th>URL</th><th>Status Code</th><th>Status</th><th>Source Tag</th></tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>"""

        return f"""
<div class="section">
  <h2>🔗 Broken Links</h2>
  <div class="stats-row">
    <span class="stat">Total: {bl.get('total_links',0)}</span>
    <span class="stat ok">OK: {bl.get('ok',0)}</span>
    <span class="stat warn">Redirects: {bl.get('redirects',0)}</span>
    <span class="stat fail">Broken: {bl.get('client_errors',0) + bl.get('server_errors',0)}</span>
    <span class="stat fail">Timeouts: {bl.get('timeouts',0)}</span>
    <span class="stat fail">Errors: {bl.get('errors',0)}</span>
  </div>
  {table if rows else "<p>No broken links found. 🎉</p>"}
</div>
"""

    def _sitemap_section(self) -> str:
        sm = self.sitemap
        found = sm.get("found", False)
        issues = sm.get("issues", [])
        issue_items = "".join(f'<li>⚠️ {i["message"]}</li>' for i in issues) if issues else "<li>No issues found.</li>"
        return f"""
<div class="section">
  <h2>🗺️ Sitemap Analysis</h2>
  <p><strong>Sitemap URL:</strong> {sm.get('sitemap_url') or 'Not found'}</p>
  <p><strong>Found:</strong> {'Yes' if found else 'No'}</p>
  <p><strong>Is Index:</strong> {'Yes' if sm.get('is_index') else 'No'}</p>
  <p><strong>Total URLs:</strong> {sm.get('total_urls', 0)}</p>
  <h3>Issues</h3>
  <ul>{issue_items}</ul>
</div>
"""

    def _lighthouse_section(self) -> str:
        lh = self.lighthouse
        if not lh.get("available"):
            return f"""
<div class="section">
  <h2>🏎️ Lighthouse</h2>
  <p>{lh.get('install_hint', 'Lighthouse not available.')}</p>
</div>
"""
        if lh.get("error"):
            return f'<div class="section"><h2>🏎️ Lighthouse</h2><p class="error">{lh["error"]}</p></div>'

        scores = lh.get("scores", {})
        metrics = lh.get("metrics", {})
        opps = lh.get("opportunities", [])

        score_html = "".join(
            f'<div class="gauge"><div class="gauge-label">{k.replace("_"," ").title()}</div>'
            f'<div class="gauge-value" style="color:{self._grade_color(v or 0)}">{v if v is not None else "N/A"}</div></div>'
            for k, v in scores.items()
        )

        metrics_html = "".join(
            f'<p><strong>{k.upper()}:</strong> {v}</p>'
            for k, v in metrics.items()
        )

        opp_html = "".join(f'<li>{o["title"]}: {o.get("display_value","")}</li>' for o in opps)

        return f"""
<div class="section">
  <h2>🏎️ Lighthouse Scores</h2>
  <div class="gauges">{score_html}</div>
  <h3>Key Metrics</h3>
  {metrics_html}
  {'<h3>Opportunities</h3><ul>' + opp_html + '</ul>' if opp_html else ''}
</div>
"""

    def _redirect_section(self) -> str:
        rd = self.redirect
        if not rd:
            return ""
        chain = rd.get("chain", [])
        issues = rd.get("issues", [])
        chain_rows = "".join(
            f'<tr><td>{hop["url"][:80]}</td><td>{hop["status_code"]}</td>'
            f'<td>{hop.get("redirect_to","") or "-"}</td></tr>'
            for hop in chain
        )
        issue_items = "".join(f'<li>{i}</li>' for i in issues) if issues else "<li>No issues found.</li>"
        return f"""
<div class="section">
  <h2>↪️ Redirect Analysis</h2>
  <p><strong>Chain length:</strong> {rd.get('chain_length', 0)}</p>
  <p><strong>Has loop:</strong> {'Yes ⚠️' if rd.get('has_loop') else 'No'}</p>
  <p><strong>Final URL:</strong> {rd.get('final_url','')}</p>
  {'<table><thead><tr><th>URL</th><th>Status</th><th>Redirect To</th></tr></thead><tbody>' + chain_rows + '</tbody></table>' if chain_rows else ''}
  <h3>Issues</h3>
  <ul>{issue_items}</ul>
</div>
"""

    def _footer(self) -> str:
        return f'<div class="footer"><p>Generated by SEO Analyzer • {self.generated_at}</p></div>'

    # ------------------------------------------------------------------
    # HTML wrapper & CSS
    # ------------------------------------------------------------------

    def _wrap_html(self, body: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SEO Analysis Report</title>
  <style>
    :root {{
      --bg: #0d1117;
      --bg2: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --accent: #58a6ff;
      --pass: #3fb950;
      --warn: #d29922;
      --fail: #f85149;
      --info: #58a6ff;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; padding: 2rem; }}
    a {{ color: var(--accent); }}
    h1 {{ font-size: 2rem; color: var(--accent); margin-bottom: 0.5rem; }}
    h2 {{ font-size: 1.4rem; color: var(--accent); margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
    h3 {{ font-size: 1.1rem; color: var(--text); margin: 1rem 0 0.5rem; }}
    .header {{ margin-bottom: 2rem; }}
    .subtitle {{ color: #8b949e; }}
    .section {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }}
    .score-card {{ display: flex; align-items: center; gap: 2rem; flex-wrap: wrap; margin-top: 1rem; }}
    .grade {{ font-size: 4rem; font-weight: bold; }}
    .score-num {{ font-size: 2rem; font-weight: bold; }}
    .score-pills {{ display: flex; gap: 0.75rem; flex-wrap: wrap; }}
    .pill {{ padding: 0.3rem 0.75rem; border-radius: 999px; font-size: 0.9rem; }}
    .pill.pass {{ background: rgba(63,185,80,0.15); color: var(--pass); }}
    .pill.warning {{ background: rgba(210,153,34,0.15); color: var(--warn); }}
    .pill.fail {{ background: rgba(248,81,73,0.15); color: var(--fail); }}
    .pill.info {{ background: rgba(88,166,255,0.15); color: var(--info); }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 0.9rem; }}
    th {{ background: var(--bg); color: #8b949e; text-align: left; padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); }}
    td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: top; word-break: break-word; max-width: 500px; }}
    tr:last-child td {{ border-bottom: none; }}
    .cat-row td {{ background: rgba(88,166,255,0.05); color: var(--accent); font-size: 0.85rem; padding: 0.4rem 0.75rem; }}
    .stats-row {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }}
    .stat {{ padding: 0.25rem 0.75rem; border-radius: 6px; background: var(--bg); border: 1px solid var(--border); font-size: 0.85rem; }}
    .stat.ok {{ border-color: var(--pass); color: var(--pass); }}
    .stat.warn {{ border-color: var(--warn); color: var(--warn); }}
    .stat.fail {{ border-color: var(--fail); color: var(--fail); }}
    .gauges {{ display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1rem; }}
    .gauge {{ background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.5rem; text-align: center; }}
    .gauge-label {{ font-size: 0.8rem; color: #8b949e; margin-bottom: 0.5rem; }}
    .gauge-value {{ font-size: 2rem; font-weight: bold; }}
    ul {{ padding-left: 1.5rem; }}
    li {{ margin-bottom: 0.25rem; }}
    .footer {{ text-align: center; color: #8b949e; font-size: 0.85rem; margin-top: 2rem; }}
    .error {{ color: var(--fail); }}
  </style>
</head>
<body>
{body}
</body>
</html>"""

    @staticmethod
    def _grade_color(score: float) -> str:
        if score >= 90:
            return "#3fb950"
        if score >= 70:
            return "#d29922"
        return "#f85149"
