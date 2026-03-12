# SEO Analyzer Tool

A comprehensive Python-based SEO website analyzer that checks any URL for SEO issues, generates detailed reports, and includes advanced features like broken link detection, sitemap parsing, Google Lighthouse integration, and redirect chain analysis.

## Features

- ✅ **23+ Core SEO Checks** — title, meta description, headings, images, links, canonical, robots meta, viewport, language, charset, Open Graph, Twitter Cards, structured data, page speed, HTTPS, URL structure, content length, keyword density, favicon, sitemap, robots.txt, hreflang, deprecated tags
- 🔗 **Broken Link Checker** — parallel HTTP checking with configurable workers
- 🗺️ **Sitemap Parser** — handles sitemap index files, validates URLs, detects issues
- 🏎️ **Google Lighthouse Integration** — performance, accessibility, best practices, SEO scores
- ↪️ **Redirect Chain Detector** — finds long chains, loops, HTTP→HTTPS, HTTPS→HTTP
- 📄 **HTML Report Generator** — dark-themed, styled report with all results
- 🖥️ **CLI Interface** — easy-to-use command-line tool with many options

## Installation

### Prerequisites

- Python 3.8+
- pip

### Install Dependencies

```bash
cd seo-tool
pip install -r requirements.txt
```

### Optional: Google Lighthouse

For Lighthouse audits, install the CLI globally:

```bash
npm install -g lighthouse
```

## Usage

### Basic Analysis

```bash
python main.py https://example.com
```

### Save HTML Report

```bash
python main.py https://example.com --output report.html
```

### Save JSON Results

```bash
python main.py https://example.com --json results.json
```

### Check for Broken Links

```bash
python main.py https://example.com --check-links
```

### Parse Sitemap

```bash
python main.py https://example.com --parse-sitemap
```

### Parse and Validate Sitemap URLs

```bash
python main.py https://example.com --validate-sitemap
```

### Run Google Lighthouse Audit

```bash
python main.py https://example.com --lighthouse
```

### Check Redirect Chains

```bash
python main.py https://example.com --check-redirects
```

### Run All Checks

```bash
python main.py https://example.com --full
```

### Custom Timeout and Workers

```bash
python main.py https://example.com --timeout 15 --max-workers 20
```

### All Options

```
positional arguments:
  url                   URL to analyze

optional arguments:
  --output FILE         Save HTML report to FILE
  --json FILE           Save JSON results to FILE
  --check-links         Enable broken link checking
  --parse-sitemap       Enable sitemap parsing
  --validate-sitemap    Parse and validate sitemap URLs
  --lighthouse          Run Lighthouse audit
  --check-redirects     Check redirect chains
  --full                Run all checks
  --timeout SECS        Request timeout in seconds (default: 10)
  --max-workers N       Max parallel workers for link checking (default: 10)
```

## Example Terminal Output

```
🔍 Analyzing: https://example.com
   Running core SEO checks… done

============================================================
  SEO Score: B+ (87.5/100)
============================================================
  ✅ Pass: 18   ⚠️  Warning: 4   ❌ Fail: 1   ℹ️  Info: 2

============================================================
  Core SEO Checks
============================================================

  📂 Content
  ✅ [Content] Title Tag
       Title length is 55 chars (ideal 50–60): 'Example Domain'
  ✅ [Content] Meta Description
       Meta description length is 155 chars (ideal 150–160).
  ✅ [Content] H1 Heading
       Exactly one H1: 'Welcome to Example'
  ...
```

## What Each Check Does

| Check | Description | Ideal |
|-------|-------------|-------|
| Title Tag | Page title presence and length | 50–60 characters |
| Meta Description | Description meta tag presence and length | 150–160 characters |
| H1 Heading | Exactly one H1 heading per page | Exactly 1 |
| Heading Hierarchy | No skipped heading levels (H1→H3) | Sequential |
| Image Alt Text | All images have descriptive alt text | 100% coverage |
| Image Dimensions | Images have explicit width/height | Reduces CLS |
| Link Analysis | Internal/external link counts, empty hrefs | No empty links |
| Canonical URL | `<link rel="canonical">` present | Required |
| Robots Meta | No unintended noindex/nofollow | index, follow |
| Viewport Meta | Mobile-friendly viewport declaration | Required |
| Language Attribute | `<html lang="...">` set | Required |
| Charset | UTF-8 charset declared | UTF-8 |
| Open Graph Tags | og:title, og:description, og:image, og:url, og:type | All 5 present |
| Twitter Card | twitter:card meta tag | Present |
| Structured Data | JSON-LD or Microdata schema | Present |
| Response Time | Time to first byte | < 1000ms |
| Page Size | Total HTML size | < 500 KB |
| HTTPS | Site uses HTTPS | Required |
| URL Structure | No uppercase, underscores, or long paths | Clean |
| Content Length | Sufficient word count | 300+ words |
| Keyword Density | Top keywords (excluding stop words) | Informational |
| Favicon | Favicon link tag present | Required |
| Sitemap.xml | sitemap.xml accessible at domain root | Accessible |
| robots.txt | robots.txt accessible at domain root | Accessible |
| Hreflang | Internationalization tags for multi-language | If multilingual |
| Deprecated Tags | No `<font>`, `<center>`, `<marquee>`, etc. | None |

## Scoring

The overall score is calculated as a percentage of points earned vs. maximum possible:

| Grade | Score Range |
|-------|-------------|
| A+    | 97–100      |
| A     | 93–96       |
| A-    | 90–92       |
| B+    | 87–89       |
| B     | 83–86       |
| B-    | 80–82       |
| C+    | 77–79       |
| C     | 73–76       |
| C-    | 70–72       |
| D+    | 67–69       |
| D     | 63–66       |
| D-    | 60–62       |
| F     | 0–59        |

## Project Structure

```
seo-tool/
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── seo_analyzer.py           # Core SEO analysis engine (23+ checks)
├── broken_link_checker.py    # Broken link detection module
├── sitemap_parser.py         # Sitemap.xml parsing & validation
├── lighthouse_runner.py      # Google Lighthouse integration
├── redirect_checker.py       # Redirect chain detection
├── report_generator.py       # HTML report generator (dark theme)
├── main.py                   # CLI entry point
└── tests/
    ├── __init__.py
    ├── test_seo_analyzer.py
    ├── test_broken_links.py
    ├── test_sitemap_parser.py
    └── test_redirect_checker.py
```

## Running Tests

```bash
cd seo-tool
python -m pytest tests/ -v
# or without pytest:
python -m unittest discover tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-new-check`
3. Write tests for your changes
4. Make sure all tests pass: `python -m unittest discover tests/`
5. Submit a pull request

## License

MIT License — see [LICENSE](../LICENSE) for details.
