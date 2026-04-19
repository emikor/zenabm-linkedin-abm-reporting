#!/usr/bin/env python3
"""
export_pdf.py — Convert an ABM report markdown file to a styled PDF

Usage:
  python export_pdf.py <path/to/report.md>

Output: same directory, same filename with .pdf extension.

Dependencies: weasyprint, markdown (both in requirements.txt)

Design choices:
  - White background, clean sans-serif body
  - Dark (#1a1a2e) headings with coloured accents
  - Zebra-striped tables with coloured header row
  - Emoji-friendly font stack (system-ui / Segoe UI Emoji / Apple Color Emoji)
  - Page numbers in footer
  - A4 page size
"""

import sys
import os
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _check_dependencies():
    missing = []
    try:
        import markdown  # noqa: F401
    except ImportError:
        missing.append("markdown")
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        missing.append("weasyprint")
    if missing:
        print(
            f"[ERROR] Missing dependencies: {', '.join(missing)}\n"
            f"Run: pip install {' '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# CSS styles
# ---------------------------------------------------------------------------

CSS = """
@page {
    size: A4;
    margin: 2cm 2cm 2.5cm 2cm;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #888;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
}

/* Base typography — emoji-friendly font stack */
body {
    font-family: 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji',
                 'Noto Color Emoji', system-ui, -apple-system, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #2d2d2d;
    background: #ffffff;
    margin: 0;
    padding: 0;
}

/* Headings */
h1 {
    font-size: 20pt;
    color: #1a1a2e;
    border-bottom: 3px solid #2d3748;
    padding-bottom: 0.3em;
    margin-top: 0;
    margin-bottom: 0.6em;
}

h2 {
    font-size: 14pt;
    color: #2d3748;
    border-left: 4px solid #4a5568;
    padding-left: 0.5em;
    margin-top: 1.4em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
}

h3 {
    font-size: 11pt;
    color: #1a1a2e;
    margin-top: 1em;
    margin-bottom: 0.3em;
    page-break-after: avoid;
}

h4 {
    font-size: 10pt;
    color: #444;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 0.8em;
    margin-bottom: 0.2em;
}

/* Paragraphs and lists */
p { margin: 0.4em 0 0.6em 0; }

ul, ol {
    margin: 0.3em 0 0.5em 1.2em;
    padding: 0;
}
li { margin-bottom: 0.2em; }

/* Code / inline code */
code {
    font-family: 'Courier New', Courier, monospace;
    font-size: 8.5pt;
    background: #f4f6f9;
    border: 1px solid #dde1e7;
    border-radius: 3px;
    padding: 0.05em 0.25em;
}

pre {
    background: #f4f6f9;
    border: 1px solid #dde1e7;
    border-radius: 4px;
    padding: 0.7em 1em;
    font-size: 8pt;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
}
pre code {
    background: none;
    border: none;
    padding: 0;
}

/* Blockquotes */
blockquote {
    border-left: 4px solid #718096;
    background: #f7f8fa;
    margin: 0.6em 0;
    padding: 0.4em 1em;
    color: #444;
    font-style: italic;
}

/* Horizontal rules */
hr {
    border: none;
    border-top: 1px solid #dde1e7;
    margin: 1em 0;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 0.7em 0 1em 0;
    font-size: 9pt;
    page-break-inside: avoid;
}

thead tr {
    background: #2d3748;
    color: #ffffff;
}
thead th {
    padding: 0.45em 0.7em;
    text-align: left;
    font-weight: 600;
    letter-spacing: 0.02em;
}

tbody tr:nth-child(even) { background: #f7f8fa; }
tbody tr:nth-child(odd)  { background: #ffffff; }

tbody td {
    padding: 0.38em 0.7em;
    border-bottom: 1px solid #e0e9f0;
    vertical-align: top;
}

tbody tr:hover { background: #edf2f7; }

/* Callout/flag spans — rendered as coloured text when preceded by emoji */
strong { color: #1a1a2e; }
em     { color: #555; }

/* Links */
a { color: #2d3748; text-decoration: none; }
a:hover { text-decoration: underline; }

/* Red flag / green flag sections */
h3:has(+ ul li:first-child) { /* section headers */ }

/* Print / page-break hints */
h2 { page-break-before: auto; }
table { orphans: 3; widows: 3; }
"""


# ---------------------------------------------------------------------------
# HTML wrapper
# ---------------------------------------------------------------------------

HTML_WRAPPER = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main conversion logic
# ---------------------------------------------------------------------------

def convert_md_to_pdf(md_path: str) -> str:
    """
    Convert a markdown file to a styled PDF.

    Returns the path to the generated PDF.
    """
    import markdown as md_module
    from weasyprint import HTML, CSS as WeasyCSS
    from weasyprint.text.fonts import FontConfiguration

    md_path = Path(md_path).resolve()
    if not md_path.exists():
        print(f"[ERROR] File not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    pdf_path = md_path.with_suffix(".pdf")

    # Read and convert markdown → HTML
    source = md_path.read_text(encoding="utf-8")
    md_converter = md_module.Markdown(
        extensions=["tables", "fenced_code", "toc", "nl2br", "sane_lists"]
    )
    body_html = md_converter.convert(source)

    # Derive a title from the first H1 if present
    import re
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", body_html, re.DOTALL)
    title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else md_path.stem

    full_html = HTML_WRAPPER.format(title=title, css=CSS, body=body_html)

    # Render to PDF
    font_config = FontConfiguration()
    html_obj = HTML(string=full_html, base_url=str(md_path.parent))
    css_obj = WeasyCSS(string="", font_config=font_config)  # CSS already embedded in HTML

    print(f"Rendering PDF...")
    html_obj.write_pdf(str(pdf_path), font_config=font_config)

    return str(pdf_path)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if sys.argv[1:] else 1)

    _check_dependencies()

    md_path = sys.argv[1]
    print(f"Converting: {md_path}")

    pdf_path = convert_md_to_pdf(md_path)

    print(f"\n[OK] PDF saved to:\n    {pdf_path}")


if __name__ == "__main__":
    main()
