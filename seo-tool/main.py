"""
SEO Analyzer CLI - Entry point for the seo-tool.

Usage
-----
    python main.py <url> [options]
"""

import argparse
import json
import sys
from typing import Any, Dict


def _print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


def _print_check(check: Dict[str, Any]) -> None:
    icons = {"pass": "✅", "warning": "⚠️ ", "fail": "❌", "info": "ℹ️ "}
    icon = icons.get(check["status"], "  ")
    print(f"  {icon} [{check['category']}] {check['title']}")
    print(f"       {check['message']}")


def run_analysis(args: argparse.Namespace) -> Dict[str, Any]:
    """Run the selected analyses and return a combined results dict."""
    from seo_analyzer import SEOAnalyzer

    print(f"\n🔍 Analyzing: {args.url}")
    print("   Running core SEO checks…", end=" ", flush=True)
    analyzer = SEOAnalyzer(args.url, timeout=args.timeout)
    seo_results = analyzer.analyze()
    print("done")

    broken_results = None
    sitemap_results = None
    lighthouse_results = None
    redirect_results = None

    if args.check_links or args.full:
        from broken_link_checker import BrokenLinkChecker
        print("   Checking links…", end=" ", flush=True)
        checker = BrokenLinkChecker(args.url, timeout=args.timeout, max_workers=args.max_workers)
        broken_results = checker.check()
        print("done")

    if args.parse_sitemap or args.validate_sitemap or args.full:
        from sitemap_parser import SitemapParser
        print("   Parsing sitemap…", end=" ", flush=True)
        parser = SitemapParser(args.url, timeout=args.timeout)
        sitemap_results = parser.parse(validate=args.validate_sitemap)
        print("done")

    if args.lighthouse or args.full:
        from lighthouse_runner import LighthouseRunner
        print("   Running Lighthouse…", end=" ", flush=True)
        runner = LighthouseRunner(args.url)
        lighthouse_results = runner.run()
        print("done")

    if args.check_redirects or args.full:
        from redirect_checker import RedirectChecker
        print("   Checking redirects…", end=" ", flush=True)
        rc = RedirectChecker(args.url, timeout=args.timeout)
        redirect_results = rc.check()
        print("done")

    return {
        "seo": seo_results,
        "broken_links": broken_results,
        "sitemap": sitemap_results,
        "lighthouse": lighthouse_results,
        "redirects": redirect_results,
    }


def print_results(results: Dict[str, Any]) -> None:
    """Pretty-print analysis results to the terminal."""
    seo = results["seo"]

    _print_section(f"SEO Score: {seo['grade']} ({seo['score']}/100)")
    summary = seo.get("summary", {})
    print(f"  ✅ Pass: {summary.get('pass',0)}   "
          f"⚠️  Warning: {summary.get('warning',0)}   "
          f"❌ Fail: {summary.get('fail',0)}   "
          f"ℹ️  Info: {summary.get('info',0)}")

    _print_section("Core SEO Checks")
    current_category = None
    for check in seo.get("checks", []):
        if check["category"] != current_category:
            current_category = check["category"]
            print(f"\n  📂 {current_category}")
        _print_check(check)

    bl = results.get("broken_links")
    if bl:
        _print_section("Broken Links")
        if bl.get("error"):
            print(f"  ❌ Error: {bl['error']}")
        else:
            print(f"  Total: {bl['total_links']}  OK: {bl['ok']}  "
                  f"Redirects: {bl['redirects']}  Broken: {bl['client_errors'] + bl['server_errors']}  "
                  f"Timeouts: {bl['timeouts']}  Errors: {bl['errors']}")
            for link in bl.get("broken_links", []):
                print(f"  ❌ [{link.get('status_code','?')}] {link['url']}")

    sm = results.get("sitemap")
    if sm:
        _print_section("Sitemap Analysis")
        print(f"  Found: {'Yes' if sm.get('found') else 'No'}  "
              f"URLs: {sm.get('total_urls',0)}  "
              f"Issues: {len(sm.get('issues',[]))}")
        for issue in sm.get("issues", [])[:10]:
            print(f"  ⚠️  {issue['message']}")

    lh = results.get("lighthouse")
    if lh:
        _print_section("Lighthouse Scores")
        if not lh.get("available"):
            print(f"  ℹ️  {lh.get('install_hint','Lighthouse not available.')}")
        elif lh.get("error"):
            print(f"  ❌ {lh['error']}")
        else:
            for cat, score in lh.get("scores", {}).items():
                label = cat.replace("_", " ").title()
                bar = "█" * (score // 10) + "░" * (10 - score // 10) if score else "N/A"
                print(f"  {label:20s}: {bar} {score}")

    rd = results.get("redirects")
    if rd:
        _print_section("Redirect Analysis")
        print(f"  Chain length: {rd.get('chain_length',0)}  "
              f"Loop: {'Yes ⚠️' if rd.get('has_loop') else 'No'}")
        for issue in rd.get("issues", []):
            print(f"  ↪️  {issue}")

    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seo-analyzer",
        description="Comprehensive SEO website analyzer",
    )
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--output", metavar="FILE", help="Save HTML report to FILE")
    parser.add_argument("--json", metavar="FILE", dest="json_file", help="Save JSON results to FILE")
    parser.add_argument("--check-links", action="store_true", help="Enable broken link checking")
    parser.add_argument("--parse-sitemap", action="store_true", help="Enable sitemap parsing")
    parser.add_argument("--validate-sitemap", action="store_true", help="Parse and validate sitemap URLs")
    parser.add_argument("--lighthouse", action="store_true", help="Run Lighthouse audit")
    parser.add_argument("--check-redirects", action="store_true", help="Check redirect chains")
    parser.add_argument("--full", action="store_true", help="Run all checks")
    parser.add_argument("--timeout", type=int, default=10, metavar="SECS", help="Request timeout (default 10)")
    parser.add_argument("--max-workers", type=int, default=10, metavar="N", help="Max parallel workers (default 10)")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    results = run_analysis(args)
    print_results(results)

    if args.output:
        from report_generator import ReportGenerator
        gen = ReportGenerator(
            seo_results=results["seo"],
            broken_links_results=results.get("broken_links"),
            sitemap_results=results.get("sitemap"),
            lighthouse_results=results.get("lighthouse"),
            redirect_results=results.get("redirects"),
        )
        html = gen.generate()
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"📄 HTML report saved to: {args.output}")

    if args.json_file:
        with open(args.json_file, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, default=str)
        print(f"📦 JSON results saved to: {args.json_file}")


if __name__ == "__main__":
    main()
