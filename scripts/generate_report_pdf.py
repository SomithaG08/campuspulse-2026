#!/usr/bin/env python3
"""
Generate a publication-quality PDF report from docs/report/implementation-report.md
Uses mistune, pygments, and headless Google Chrome for pixel-perfect PDF rendering.
"""

import os
import re
import sys
import shutil
import base64
import subprocess
from pathlib import Path
import mistune
from bs4 import BeautifulSoup
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
REPORT_MD = WORKSPACE_DIR / "docs" / "report" / "implementation-report.md"
OUTPUT_HTML = WORKSPACE_DIR / "docs" / "report" / "report_styled.html"
OUTPUT_PDF_DOCS = WORKSPACE_DIR / "docs" / "report" / "CampusPulse-2026-Report.pdf"
OUTPUT_PDF_ROOT = WORKSPACE_DIR / "CampusPulse-2026-Report.pdf"

class CustomHTMLRenderer(mistune.HTMLRenderer):
    def block_code(self, code, info=None):
        info = (info or "").strip().lower()
        if not info:
            lexer = TextLexer()
        else:
            try:
                lexer = get_lexer_by_name(info)
            except Exception:
                lexer = TextLexer()
        formatter = HtmlFormatter(nowrap=True)
        highlighted = highlight(code, lexer, formatter)
        lang_class = f"language-{info}" if info else "language-text"
        return f'<div class="code-block-wrapper"><div class="code-lang-tag">{info.upper() if info else "CODE"}</div><pre><code class="{lang_class}">{highlighted}</code></pre></div>\n'

def build_html():
    with open(REPORT_MD, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Separate metadata preamble and revision note from main text
    # In implementation-report.md:
    # Lines before "## 1. Introduction" contain title, meta, blockquote, and "---"
    parts = re.split(r'\n(?=## 1\. Introduction)', md_text, maxsplit=1)
    preamble = parts[0] if len(parts) > 1 else ""
    main_body = parts[1] if len(parts) > 1 else md_text

    # Extract revision blockquote from preamble if present
    revision_match = re.search(r'(>\s*\*\*Revision.*?(?=\n\n|\n---))', preamble, re.DOTALL)
    revision_note_html = ""
    if revision_match:
        rev_md = revision_match.group(1)
        rev_parser = mistune.create_markdown(plugins=['url', 'strikethrough'])
        revision_note_html = f'<div class="executive-revision-box"><div class="rev-badge">Project Review Revision</div>{rev_parser(rev_md)}</div>'

    # Create markdown parser for main body
    markdown = mistune.create_markdown(
        renderer=CustomHTMLRenderer(),
        plugins=['table', 'url', 'strikethrough']
    )
    body_html = markdown(main_body)

    # Post-process with BeautifulSoup
    soup = BeautifulSoup(body_html, "html.parser")

    # Resolve and base64 embed images
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src and not src.startswith("data:") and not src.startswith("http"):
            img_path = (WORKSPACE_DIR / "docs" / "report" / src).resolve()
            if img_path.exists():
                with open(img_path, "rb") as img_f:
                    data = base64.b64encode(img_f.read()).decode("utf-8")
                ext = img_path.suffix.lower().replace(".", "")
                if ext == "jpg": ext = "jpeg"
                img["src"] = f"data:image/{ext};base64,{data}"
                
                # Wrap in figure with caption
                alt_text = img.get("alt", "")
                figure = soup.new_tag("figure")
                img.wrap(figure)
                if alt_text:
                    caption = soup.new_tag("figcaption")
                    caption.string = alt_text
                    figure.append(caption)

    # Style blockquotes
    for bq in soup.find_all("blockquote"):
        bq["class"] = bq.get("class", []) + ["callout-box"]

    # Extract Table of Contents
    toc_items = []
    headers = soup.find_all(["h2", "h3"])
    for h in headers:
        text = h.get_text().strip()
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
        h["id"] = slug
        level = 2 if h.name == "h2" else 3
        toc_items.append((level, text, slug))

    # Split TOC into 2 columns
    mid = (len(toc_items) + 1) // 2
    col1_items = toc_items[:mid]
    col2_items = toc_items[mid:]

    def render_col(items):
        out = ['<ul class="toc-list">']
        for level, text, slug in items:
            cls = "toc-item-h2" if level == 2 else "toc-item-h3"
            out.append(f'<li class="{cls}"><a href="#{slug}"><span class="toc-text">{text}</span><span class="toc-spacer"></span></a></li>')
        out.append('</ul>')
        return "".join(out)

    toc_string = f"""
    <div class="toc-container">
        <h2 class="toc-title">Table of Contents</h2>
        <div class="toc-columns">
            <div class="toc-col">{render_col(col1_items)}</div>
            <div class="toc-col">{render_col(col2_items)}</div>
        </div>
        {revision_note_html}
    </div>
    """

    # Generate Pygments CSS
    pygments_css = HtmlFormatter(style="friendly").get_style_defs('.code-block-wrapper')

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CampusPulse 2026 — Final Implementation Report</title>
<style>
/* Page Setup */
@page {{
    size: A4;
    margin: 20mm 18mm 22mm 18mm;
    @top-right {{
        content: "CampusPulse 2026 — Final Implementation Report";
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 7.5pt;
        color: #94A3B8;
        letter-spacing: 0.3px;
    }}
    @bottom-center {{
        content: counter(page);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 8.5pt;
        color: #64748B;
        font-weight: 500;
    }}
}}

@page:first {{
    margin: 0;
    @top-right {{ content: normal; }}
    @bottom-center {{ content: normal; }}
}}

* {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1E293B;
    background-color: #FFFFFF;
    line-height: 1.5;
    font-size: 9.5pt;
    margin: 0;
    padding: 0;
}}

/* Cover Page */
.cover-page {{
    page-break-after: always;
    height: 100vh;
    padding: 36mm 24mm 26mm 24mm;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: linear-gradient(135deg, #0B132B 0%, #1C2541 55%, #1E3A8A 100%);
    color: #FFFFFF;
}}

.cover-badge {{
    display: inline-block;
    padding: 6px 14px;
    background: rgba(37, 99, 235, 0.4);
    border: 1px solid rgba(96, 165, 250, 0.5);
    border-radius: 20px;
    font-size: 8.5pt;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #BFDBFE;
    margin-bottom: 22px;
}}

.cover-title {{
    font-size: 34pt;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin: 0 0 14px 0;
    color: #FFFFFF;
}}

.cover-subtitle {{
    font-size: 15pt;
    font-weight: 400;
    color: #CBD5E1;
    line-height: 1.35;
    margin: 0 0 24px 0;
}}

.cover-divider {{
    height: 3px;
    width: 60px;
    background: #3B82F6;
    margin: 0 0 32px 0;
    border-radius: 2px;
}}

.cover-meta-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 30px;
}}

.meta-item {{
    font-size: 9pt;
}}

.meta-label {{
    color: #94A3B8;
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    margin-bottom: 2px;
}}

.meta-value {{
    color: #F8FAFC;
    font-weight: 600;
}}

.meta-value a {{
    color: #60A5FA;
    text-decoration: none;
}}

.cover-footer {{
    border-top: 1px solid rgba(255, 255, 255, 0.15);
    padding-top: 18px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    font-size: 8.5pt;
    color: #94A3B8;
}}

.team-members-list {{
    font-size: 11pt;
    font-weight: 600;
    color: #FFFFFF;
    margin-top: 4px;
}}

/* Table of Contents */
.toc-container {{
    page-break-before: always;
    page-break-after: always;
    padding: 8px 0 16px 0;
}}

.toc-title {{
    font-size: 15pt;
    font-weight: 700;
    color: #0F172A;
    border-bottom: 2px solid #2563EB;
    padding-bottom: 6px;
    margin-top: 0;
    margin-bottom: 16px;
}}

.toc-columns {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    column-gap: 24px;
}}

.toc-list {{
    list-style: none;
    padding-left: 0;
    margin: 0;
}}

.toc-list li {{
    margin-bottom: 5px;
    page-break-inside: avoid;
}}

.toc-list a {{
    text-decoration: none;
    color: #1E293B;
    display: flex;
    align-items: baseline;
}}

.toc-item-h2 {{
    font-weight: 600;
    font-size: 8.8pt;
    margin-top: 8px;
}}

.toc-item-h3 {{
    font-weight: 400;
    font-size: 8pt;
    padding-left: 12px;
    color: #475569;
}}

.toc-spacer {{
    flex-grow: 1;
    border-bottom: 1px dotted #CBD5E1;
    margin: 0 6px;
    position: relative;
    top: -3px;
}}

/* Executive Revision Notice */
.executive-revision-box {{
    margin-top: 24px;
    padding: 14px 18px;
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-left: 4px solid #16A34A;
    border-radius: 6px;
    color: #166534;
    font-size: 8.5pt;
    line-height: 1.45;
}}

.rev-badge {{
    font-weight: 700;
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #15803D;
    margin-bottom: 4px;
}}

.executive-revision-box p {{
    margin: 0;
    text-align: left;
}}

/* Headings */
h1 {{
    display: none;
}}

h2 {{
    font-size: 14pt;
    font-weight: 700;
    color: #0F172A;
    border-bottom: 1.5px solid #E2E8F0;
    padding-bottom: 5px;
    margin-top: 28px;
    margin-bottom: 12px;
    page-break-after: avoid;
    letter-spacing: -0.01em;
}}

/* Major Chapter Breaks */
h2[id^="1-"], h2[id^="2-"], h2[id^="3-"], h2[id^="4-"], 
h2[id^="5-"], h2[id^="6-"], h2[id^="7-"], h2[id^="8-"], 
h2[id^="9-"], h2[id^="10-"], h2[id^="11-"], h2[id^="12-"], 
h2[id^="13-"], h2[id^="appendix"] {{
    page-break-before: always;
    margin-top: 0;
    padding-top: 6px;
}}

h3 {{
    font-size: 10.5pt;
    font-weight: 600;
    color: #1E293B;
    margin-top: 18px;
    margin-bottom: 8px;
    page-break-after: avoid;
}}

h4 {{
    font-size: 9.5pt;
    font-weight: 600;
    color: #334155;
    margin-top: 14px;
    margin-bottom: 6px;
    page-break-after: avoid;
}}

p {{
    margin-top: 0;
    margin-bottom: 8px;
    text-align: justify;
    text-justify: inter-word;
}}

/* Callout / Blockquotes */
.callout-box {{
    margin: 14px 0;
    padding: 12px 16px;
    background: #EFF6FF;
    border-left: 3.5px solid #3B82F6;
    border-radius: 0 6px 6px 0;
    color: #1E3A8A;
    font-size: 9pt;
    page-break-inside: avoid;
}}

.callout-box p:last-child {{
    margin-bottom: 0;
}}

/* Tables */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0 16px 0;
    font-size: 8pt;
    page-break-inside: avoid;
}}

th, td {{
    padding: 6px 8px;
    text-align: left;
    border: 1px solid #E2E8F0;
    vertical-align: top;
}}

th {{
    background-color: #F1F5F9;
    color: #0F172A;
    font-weight: 600;
    border-bottom: 2px solid #CBD5E1;
}}

tr:nth-child(even) td {{
    background-color: #F8FAFC;
}}

/* Code Blocks */
.code-block-wrapper {{
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    margin: 12px 0 16px 0;
    page-break-inside: avoid;
    position: relative;
    overflow: hidden;
}}

.code-lang-tag {{
    position: absolute;
    top: 5px;
    right: 8px;
    font-size: 6pt;
    font-weight: 700;
    color: #94A3B8;
    letter-spacing: 0.5px;
}}

pre {{
    margin: 0;
    padding: 10px 12px;
    overflow-x: auto;
    font-family: "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 7.5pt;
    line-height: 1.4;
    color: #334155;
    white-space: pre-wrap;
    word-break: break-all;
}}

code {{
    font-family: "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 8pt;
    background-color: #F1F5F9;
    padding: 1.5px 4px;
    border-radius: 3px;
    color: #0F172A;
}}

pre code {{
    background-color: transparent;
    padding: 0;
    border-radius: 0;
    font-size: 7.5pt;
}}

/* Figures and Images */
figure {{
    margin: 16px 0 20px 0;
    text-align: center;
    page-break-inside: avoid;
}}

figure img {{
    max-width: 95%;
    max-height: 440px;
    object-fit: contain;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.06);
}}

figcaption {{
    margin-top: 6px;
    font-size: 7.5pt;
    color: #64748B;
    font-style: italic;
}}

/* Links */
a {{
    color: #2563EB;
    text-decoration: none;
}}

/* Horizontal rule */
hr {{
    border: none;
    border-top: 1px solid #E2E8F0;
    margin: 20px 0;
}}

/* Pygments Syntax Highlighting Styles */
{pygments_css}
</style>
</head>
<body>

<!-- Cover Page -->
<div class="cover-page">
    <div>
        <div class="cover-badge">Big Data & Cloud Computing — S2 2026</div>
        <div class="cover-title">CampusPulse 2026</div>
        <div class="cover-subtitle">A Cloud-Native Smart Campus Operations Platform<br><span style="font-size: 13pt; color: #93C5FD; font-weight: 500;">Final Implementation Report</span></div>
        <div class="cover-divider"></div>
        
        <div class="cover-meta-grid">
            <div class="meta-item">
                <div class="meta-label">Academic Program</div>
                <div class="meta-value">EPITA Graduate School — AY 2025-2026</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Cloud Infrastructure</div>
                <div class="meta-value">Amazon Web Services (AWS) · eu-west-3 (Paris)</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Git Repository</div>
                <div class="meta-value"><a href="https://github.com/SomithaG08/campuspulse-2026">github.com/SomithaG08/campuspulse-2026</a></div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Live API Endpoint</div>
                <div class="meta-value"><a href="https://wsjs04q4yi.execute-api.eu-west-3.amazonaws.com/">https://wsjs04q4yi.execute-api.eu-west-3...</a></div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Review Status</div>
                <div class="meta-value" style="color: #4ADE80;">✓ 100% Deployed, Tested & Verified (All 5 Professor Corrections)</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Submission Date</div>
                <div class="meta-value">October 2026</div>
            </div>
        </div>
    </div>
    
    <div class="cover-footer">
        <div>
            <div class="meta-label" style="color: #94A3B8;">Project Engineering Team</div>
            <div class="team-members-list">Somitha Gudivada · Manimegalai · Madhavan · MD Mazadul</div>
        </div>
        <div style="text-align: right;">
            <div style="font-weight: 600; color: #FFFFFF;">NorthBridge University Prototype</div>
            <div style="font-size: 8pt; color: #94A3B8;">Serverless · Private VPC · DynamoDB PITR · Cognito RBAC</div>
        </div>
    </div>
</div>

<!-- Table of Contents & Executive Revision Notice -->
{toc_string}

<!-- Report Body -->
<div class="report-content">
{str(soup)}
</div>

</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"Generated HTML report at: {OUTPUT_HTML}")
    return OUTPUT_HTML

def generate_pdf(html_path):
    chrome_binary = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_binary):
        print(f"Chrome binary not found at {chrome_binary}")
        sys.exit(1)

    cmd = [
        chrome_binary,
        "--headless=new",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--enable-local-file-accesses",
        f"--print-to-pdf={OUTPUT_PDF_DOCS}",
        f"file://{html_path.resolve()}"
    ]

    print(f"Running Chrome command to generate PDF: {OUTPUT_PDF_DOCS}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Chrome error:", res.stderr)
        sys.exit(1)

    if OUTPUT_PDF_DOCS.exists():
        shutil.copy2(OUTPUT_PDF_DOCS, OUTPUT_PDF_ROOT)
        print(f"Successfully generated PDF!")
        print(f"  Primary: {OUTPUT_PDF_DOCS} ({OUTPUT_PDF_DOCS.stat().st_size} bytes)")
        print(f"  Root:    {OUTPUT_PDF_ROOT} ({OUTPUT_PDF_ROOT.stat().st_size} bytes)")
    else:
        print("PDF was not produced.")
        sys.exit(1)

if __name__ == "__main__":
    html_file = build_html()
    generate_pdf(html_file)
