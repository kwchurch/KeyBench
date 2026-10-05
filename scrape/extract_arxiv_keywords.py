#!/usr/bin/env python3
"""
extract_arxiv_keywords.py - Extract arXiv IDs and PDF keywords from Semantic Scholar keywords JSON.

Parses large Semantic Scholar keyword dumps (e.g., keywords7.json) and extracts pairs of
(arxiv_id, keywords_from_pdf). Supports cleaning boilerplate prefixes ("Author Keywords:", "Keywords:", etc.),
splitting into individual keyword lists, sampling for human judgment, and exporting to HTML, TSV, CSV, JSONL, or JSON.

Features:
  - Interactive Judge Verification Tool (--format html or -o output.html):
      * Generates a self-contained, standalone web interface for human evaluation.
      * Direct clickable links to arXiv abstract pages and arXiv PDFs (arxiv.org/pdf/...).
      * Keyword badges, paper title, authors, and collapsible abstract.
      * One-click judgment buttons: Approved (✅), Partial (⚠️), Rejected (❌).
      * Notes field, live progress tracking, filtering (All, Unjudged, Approved, etc.), and search.
      * Instant export of judgment results to CSV or JSON.
      * Auto-saves judgments to browser localStorage so progress is never lost.
  - Random Sampling: Use --sample N (and --seed S) to extract a representative sample for verification.
  - Robust Case-Insensitive ID Lookup: Handles both 'arxiv' and 'ArXiv' keys in externalids.
  - Prefix & Boilerplate Stripping: Cleans 'Keywords:', 'Author Keywords', 'Index Terms—', etc.
  - Empty Value Filtering: Automatically filters out stub records (e.g. "Keywords:" with no terms).
  - Multiple Output Formats: TSV, CSV, JSONL, JSON, and interactive HTML.

Usage:
  # 1. Generate an interactive HTML verification tool for a sample of 50 papers:
  python extract_arxiv_keywords.py \\
      -i /Users/kwc/Downloads/keywords7.json \\
      -o /Users/kwc/Downloads/verify_sample50.html \\
      --sample 50

  # 2. Extract to TSV (clean keywords, only records with both arxiv and keywords):
  python extract_arxiv_keywords.py -i /Users/kwc/Downloads/keywords7.json -o arxiv_keywords.tsv

  # 3. Extract to JSONL with parsed keyword lists:
  python extract_arxiv_keywords.py -i /Users/kwc/Downloads/keywords7.json -o arxiv_keywords.jsonl --format jsonl --split

  # 4. Keep raw uncleaned text:
  python extract_arxiv_keywords.py -i /Users/kwc/Downloads/keywords7.json -o raw_keywords.tsv --no-clean
"""

import argparse
import csv
import html
import json
import os
import random
import re
import signal
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Handle broken pipe errors gracefully when piping to head/grep
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):
    pass

PREFIX_PATTERN = re.compile(
    r"^(author\s+keywords?|index\s+terms|keywords\s+and\s+phrases|keywords?|key\s+words?)[\s:—–\-]+",
    re.IGNORECASE,
)


def clean_keywords(raw_text: str) -> str:
    """Strips leading boilerplate labels (e.g. 'Keywords:', 'Author Keywords') and edge punctuation."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    text = PREFIX_PATTERN.sub("", text).strip()
    text = text.strip(" :;—–-")
    if text.endswith(".") and not text.endswith(".."):
        text = text[:-1].strip()
    return text


def split_keyword_terms(text: str) -> List[str]:
    """Splits a cleaned keyword string into individual terms using semicolons, commas, or bullets."""
    if not text:
        return []
    if ";" in text:
        tokens = text.split(";")
    elif "•" in text:
        tokens = text.split("•")
    elif " - " in text or " – " in text or " — " in text:
        tokens = re.split(r"\s+[—–-]\s+", text)
    else:
        tokens = text.split(",")

    cleaned_tokens = []
    for tok in tokens:
        cleaned = tok.strip(" \t\n\r.;:—–-")
        if cleaned:
            cleaned_tokens.append(cleaned)
    return cleaned_tokens


def get_arxiv_id(record: Dict[str, Any]) -> Optional[str]:
    """Extracts arXiv ID from externalids dictionary, handling casing variations."""
    ext = record.get("externalids")
    if not isinstance(ext, dict):
        return None
    val = ext.get("arxiv") or ext.get("ArXiv") or ext.get("ARXIV")
    if isinstance(val, str) and val.strip():
        return val.strip()
    for k, v in ext.items():
        if str(k).lower() == "arxiv" and isinstance(v, str) and v.strip():
            return v.strip()
    return None


def generate_html_verification_page(
    records: List[Dict[str, Any]],
    title: str = "arXiv Keywords Verification Tool",
    total_pool_size: int = 0,
    sample_seed: Optional[int] = None,
) -> str:
    """
    Generates a standalone, dependency-free interactive HTML application for human judging.
    Features direct arXiv/PDF links, keyword chips, judgment buttons, progress tracking,
    localStorage persistence, search/filter controls, and CSV/JSON judgment export.
    """
    # Prepare JSON payload embedded into HTML for client-side functionality
    json_data = json.dumps(records, ensure_ascii=False)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
  :root {{
    --bg-page: #f8fafc;
    --bg-card: #ffffff;
    --border-card: #e2e8f0;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #94a3b8;
    --primary-color: #2563eb;
    --primary-hover: #1d4ed8;
    --badge-bg: #eff6ff;
    --badge-text: #1d4ed8;
    --badge-border: #bfdbfe;
    
    --success-bg: #f0fdf4;
    --success-border: #86efac;
    --success-text: #166534;
    --success-btn: #16a34a;
    
    --warning-bg: #fefce8;
    --warning-border: #fde047;
    --warning-text: #854d0e;
    --warning-btn: #ca8a04;
    
    --danger-bg: #fef2f2;
    --danger-border: #fca5a5;
    --danger-text: #991b1b;
    --danger-btn: #dc2626;

    --radius-md: 10px;
    --radius-sm: 6px;
    --shadow-card: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: var(--bg-page);
    color: var(--text-primary);
    line-height: 1.5;
    padding-bottom: 80px;
  }}

  /* Sticky Top Bar */
  header.top-bar {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: #ffffff;
    border-bottom: 1px solid var(--border-card);
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    padding: 12px 24px;
  }}

  .header-content {{
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }}

  .header-title-box h1 {{
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
  }}
  .header-title-box .meta-subtitle {{
    font-size: 0.82rem;
    color: var(--text-muted);
  }}

  .progress-section {{
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 260px;
  }}
  .progress-text {{
    display: flex;
    justify-content: space-between;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-secondary);
  }}
  .progress-bar-bg {{
    width: 100%;
    height: 8px;
    background: #e2e8f0;
    border-radius: 999px;
    overflow: hidden;
  }}
  .progress-bar-fill {{
    height: 100%;
    width: 0%;
    background: var(--primary-color);
    transition: width 0.3s ease;
  }}

  .controls-row {{
    max-width: 1200px;
    margin: 16px auto 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }}

  .filter-tabs {{
    display: inline-flex;
    background: #f1f5f9;
    padding: 3px;
    border-radius: var(--radius-sm);
    gap: 2px;
  }}
  .filter-tab {{
    border: none;
    background: transparent;
    padding: 6px 12px;
    font-size: 0.82rem;
    font-weight: 600;
    border-radius: 4px;
    cursor: pointer;
    color: var(--text-secondary);
    transition: all 0.15s;
  }}
  .filter-tab.active {{
    background: #ffffff;
    color: var(--primary-color);
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  }}

  .search-box input {{
    padding: 7px 12px;
    border: 1px solid var(--border-card);
    border-radius: var(--radius-sm);
    font-size: 0.85rem;
    width: 240px;
  }}
  .search-box input:focus {{
    outline: 2px solid var(--primary-color);
    border-color: transparent;
  }}

  .export-buttons {{
    display: flex;
    gap: 8px;
  }}
  .btn-action {{
    border: 1px solid var(--border-card);
    background: #ffffff;
    padding: 7px 12px;
    font-size: 0.82rem;
    font-weight: 600;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background 0.15s;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .btn-action:hover {{
    background: #f8fafc;
  }}

  /* Main Container */
  main.cards-container {{
    max-width: 1200px;
    margin: 24px auto;
    padding: 0 16px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }}

  /* Paper Card */
  article.paper-card {{
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-card);
    padding: 20px 24px;
    transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
    position: relative;
  }}

  article.paper-card.status-approved {{
    border-color: var(--success-border);
    background-color: #fafdfb;
  }}
  article.paper-card.status-partial {{
    border-color: var(--warning-border);
    background-color: #fefdf9;
  }}
  article.paper-card.status-rejected {{
    border-color: var(--danger-border);
    background-color: #fdfafa;
  }}

  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 10px;
  }}

  .card-meta-badges {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }}

  .badge-index {{
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-muted);
    background: #f1f5f9;
    padding: 2px 8px;
    border-radius: 4px;
  }}

  .badge-arxiv {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.85rem;
    font-weight: 700;
    color: #b91c1c;
    background: #fef2f2;
    padding: 3px 10px;
    border-radius: 6px;
    text-decoration: none;
    border: 1px solid #fecaca;
    transition: background 0.15s;
  }}
  .badge-arxiv:hover {{
    background: #fee2e2;
  }}

  .badge-link {{
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--primary-color);
    background: var(--badge-bg);
    padding: 3px 10px;
    border-radius: 6px;
    text-decoration: none;
    border: 1px solid var(--badge-border);
    transition: background 0.15s;
  }}
  .badge-link:hover {{
    background: #dbeafe;
  }}

  .badge-corpus {{
    font-size: 0.75rem;
    color: var(--text-muted);
  }}

  .paper-title {{
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 4px;
    line-height: 1.35;
  }}

  .paper-authors {{
    font-size: 0.88rem;
    color: var(--text-secondary);
    margin-bottom: 14px;
  }}

  /* Extracted Keywords Box */
  .keywords-block {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    margin-bottom: 14px;
  }}
  .keywords-block-title {{
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 700;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }}

  .keyword-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}
  .chip {{
    display: inline-block;
    background: #eff6ff;
    color: #1e40af;
    border: 1px solid #bfdbfe;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 16px;
  }}

  details.raw-keywords-details {{
    margin-top: 10px;
    font-size: 0.8rem;
    color: var(--text-muted);
  }}
  details.raw-keywords-details summary {{
    cursor: pointer;
    user-select: none;
  }}
  details.raw-keywords-details p {{
    margin-top: 4px;
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    font-size: 0.78rem;
    background: #ffffff;
    border: 1px dashed #cbd5e1;
    padding: 6px 10px;
    border-radius: 4px;
    color: #334155;
  }}

  /* Abstract */
  details.abstract-details {{
    margin-bottom: 16px;
  }}
  details.abstract-details summary {{
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;
    margin-bottom: 6px;
  }}
  .abstract-text {{
    font-size: 0.9rem;
    color: #334155;
    background: #ffffff;
    line-height: 1.6;
    padding: 8px 12px;
    border-left: 3px solid #cbd5e1;
  }}

  /* Verification Bar */
  .judgment-bar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-top: 14px;
    border-top: 1px solid #edf2f7;
  }}

  .btn-group-judge {{
    display: flex;
    gap: 8px;
  }}
  .btn-judge {{
    border: 1px solid transparent;
    padding: 6px 14px;
    font-size: 0.85rem;
    font-weight: 600;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.15s;
    background: #f1f5f9;
    color: #475569;
  }}
  .btn-judge:hover {{
    filter: brightness(0.95);
  }}

  .btn-judge.btn-approve.active {{
    background: var(--success-btn);
    color: #ffffff;
    border-color: var(--success-btn);
  }}
  .btn-judge.btn-partial.active {{
    background: var(--warning-btn);
    color: #ffffff;
    border-color: var(--warning-btn);
  }}
  .btn-judge.btn-reject.active {{
    background: var(--danger-btn);
    color: #ffffff;
    border-color: var(--danger-btn);
  }}

  .notes-input {{
    flex: 1;
    min-width: 220px;
    max-width: 450px;
    padding: 6px 10px;
    font-size: 0.82rem;
    border: 1px solid var(--border-card);
    border-radius: var(--radius-sm);
  }}
  .notes-input:focus {{
    outline: 2px solid var(--primary-color);
    border-color: transparent;
  }}

  .status-badge {{
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 3px 8px;
    border-radius: 4px;
    display: none;
  }}
  .paper-card.status-approved .status-badge.badge-approved {{ display: inline-block; background: #dcfce7; color: #15803d; }}
  .paper-card.status-partial .status-badge.badge-partial {{ display: inline-block; background: #fef9c3; color: #a16207; }}
  .paper-card.status-rejected .status-badge.badge-rejected {{ display: inline-block; background: #fee2e2; color: #b91c1c; }}

  /* Keyboard shortcut hint */
  .hotkey-hint {{
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-left: 6px;
  }}

  /* Toast Notification */
  #toast {{
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #1e293b;
    color: #ffffff;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 500;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    opacity: 0;
    transform: translateY(10px);
    transition: opacity 0.2s, transform 0.2s;
    pointer-events: none;
    z-index: 1000;
  }}
  #toast.show {{
    opacity: 1;
    transform: translateY(0);
  }}
</style>
</head>
<body>

<header class="top-bar">
  <div class="header-content">
    <div class="header-title-box">
      <h1>{html.escape(title)}</h1>
      <div class="meta-subtitle">
        Sample of {len(records):,} papers (from {total_pool_size:,} pool) | Direct arXiv &amp; PDF links
      </div>
    </div>

    <div class="progress-section">
      <div class="progress-text">
        <span>Judged: <span id="judged-count">0</span> / {len(records)} (<span id="judged-pct">0%</span>)</span>
        <span id="counts-breakdown">✅ 0 &nbsp;|&nbsp; ⚠️ 0 &nbsp;|&nbsp; ❌ 0</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="progress-fill"></div>
      </div>
    </div>
  </div>

  <div class="controls-row">
    <div class="filter-tabs">
      <button class="filter-tab active" data-filter="all">All ({len(records)})</button>
      <button class="filter-tab" data-filter="unjudged">Unjudged (<span id="tab-unjudged-count">{len(records)}</span>)</button>
      <button class="filter-tab" data-filter="approved">Approved (<span id="tab-approved-count">0</span>)</button>
      <button class="filter-tab" data-filter="partial">Partial (<span id="tab-partial-count">0</span>)</button>
      <button class="filter-tab" data-filter="rejected">Rejected (<span id="tab-rejected-count">0</span>)</button>
    </div>

    <div class="search-box">
      <input type="text" id="search-input" placeholder="Search keywords, title, arXiv ID..." />
    </div>

    <div class="export-buttons">
      <button class="btn-action" id="btn-export-csv">💾 Export CSV</button>
      <button class="btn-action" id="btn-export-json">💾 Export JSON</button>
      <button class="btn-action" id="btn-reset" title="Clear saved judgments for this session">↺ Reset</button>
    </div>
  </div>
</header>

<main class="cards-container" id="cards-container">
"""

    for idx, r in enumerate(records):
        corpus_id = r.get("corpus_id", "")
        arxiv_id = r.get("arxiv_id", "")
        title_text = r.get("title") or "Untitled Paper"
        raw_kw = r.get("raw_keywords") or ""
        clean_kw = r.get("keywords") or ""
        terms = r.get("terms") or []
        abstract_text = r.get("abstract") or "No abstract provided in dataset."
        authors_list = r.get("authors") or []
        url = r.get("url") or f"https://www.semanticscholar.org/paper/{corpus_id}"

        # Clean author string
        if isinstance(authors_list, list):
            auth_names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors_list]
            auth_str = ", ".join([a for a in auth_names if a]) or "Unknown Authors"
        else:
            auth_str = str(authors_list)

        # Keyword chips HTML
        if terms:
            chips_html = "".join([f'<span class="chip">{html.escape(t)}</span>' for t in terms])
        elif clean_kw:
            chips_html = f'<span class="chip">{html.escape(clean_kw)}</span>'
        else:
            chips_html = '<span style="color:var(--text-muted);font-size:0.85rem;">(No keywords)</span>'

        arxiv_abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        arxiv_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        html_template += f"""
  <article class="paper-card" id="card-{idx}" data-idx="{idx}" data-corpus="{html.escape(corpus_id)}" data-arxiv="{html.escape(arxiv_id)}">
    <div class="card-header">
      <div class="card-meta-badges">
        <span class="badge-index">#{idx + 1}</span>
        <a class="badge-arxiv" href="{arxiv_abs_url}" target="_blank" rel="noopener noreferrer" title="View abstract and metadata on arXiv">
          arXiv: {html.escape(arxiv_id)} ↗
        </a>
        <a class="badge-link" href="{arxiv_pdf_url}" target="_blank" rel="noopener noreferrer" title="Open full paper PDF in new tab" style="background:#fef2f2;color:#b91c1c;border-color:#fca5a5;">
          📄 Open PDF ↗
        </a>
        <a class="badge-link" href="{html.escape(url)}" target="_blank" rel="noopener noreferrer" title="View on Semantic Scholar">
          Semantic Scholar ↗
        </a>
        <span class="badge-corpus">ID: {html.escape(corpus_id)}</span>
      </div>

      <div>
        <span class="status-badge badge-approved">Approved</span>
        <span class="status-badge badge-partial">Partial</span>
        <span class="status-badge badge-rejected">Rejected</span>
      </div>
    </div>

    <h2 class="paper-title">{html.escape(title_text)}</h2>
    <div class="paper-authors">by {html.escape(auth_str)}</div>

    <div class="keywords-block">
      <div class="keywords-block-title">Extracted PDF Keywords:</div>
      <div class="keyword-chips">
        {chips_html}
      </div>
      <details class="raw-keywords-details">
        <summary>View raw uncleaned PDF string</summary>
        <p>{html.escape(raw_kw)}</p>
      </details>
    </div>

    <details class="abstract-details">
      <summary>Show / Hide Abstract</summary>
      <div class="abstract-text">{html.escape(abstract_text)}</div>
    </details>

    <div class="judgment-bar">
      <div class="btn-group-judge">
        <button class="btn-judge btn-approve" data-val="approved" title="Keywords are correct and match the paper (Hotkey: 1 or A)">
          ✅ Approved <span class="hotkey-hint">[1]</span>
        </button>
        <button class="btn-judge btn-partial" data-val="partial" title="Keywords are partially correct or have minor issues (Hotkey: 2 or P)">
          ⚠️ Partial <span class="hotkey-hint">[2]</span>
        </button>
        <button class="btn-judge btn-reject" data-val="rejected" title="Keywords are incorrect or junk (Hotkey: 3 or R)">
          ❌ Rejected <span class="hotkey-hint">[3]</span>
        </button>
      </div>

      <input type="text" class="notes-input" placeholder="Notes (e.g. missed key term, includes author name)..." />
    </div>
  </article>
"""

    html_template += f"""
</main>

<div id="toast">Saved!</div>

<script>
  const PAPERS = {json_data};
  const STORAGE_KEY = 'arxiv_keyword_judgments_' + location.pathname;

  let judgments = {{}};
  try {{
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) judgments = JSON.parse(saved);
  }} catch (e) {{
    console.warn('Could not load localStorage:', e);
  }}

  // Elements
  const container = document.getElementById('cards-container');
  const judgedCountEl = document.getElementById('judged-count');
  const judgedPctEl = document.getElementById('judged-pct');
  const breakdownEl = document.getElementById('counts-breakdown');
  const progressFillEl = document.getElementById('progress-fill');
  const searchInput = document.getElementById('search-input');
  const toastEl = document.getElementById('toast');

  let activeFilter = 'all';
  let activeSearch = '';

  function showToast(msg) {{
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    setTimeout(() => toastEl.classList.remove('show'), 2000);
  }}

  function saveJudgments() {{
    try {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify(judgments));
    }} catch (e) {{
      console.warn('Failed to save to localStorage:', e);
    }}
  }}

  function updateCardUI(card, data) {{
    card.classList.remove('status-approved', 'status-partial', 'status-rejected');
    card.querySelectorAll('.btn-judge').forEach(b => b.classList.remove('active'));

    const notesInput = card.querySelector('.notes-input');
    if (data) {{
      if (data.status) {{
        card.classList.add('status-' + data.status);
        const activeBtn = card.querySelector(`.btn-judge[data-val="${{data.status}}"]`);
        if (activeBtn) activeBtn.classList.add('active');
      }}
      if (data.notes !== undefined && notesInput.value !== data.notes) {{
        notesInput.value = data.notes;
      }}
    }} else {{
      notesInput.value = '';
    }}
  }}

  function updateGlobalStats() {{
    const total = PAPERS.length;
    let approved = 0, partial = 0, rejected = 0;

    Object.values(judgments).forEach(j => {{
      if (j.status === 'approved') approved++;
      else if (j.status === 'partial') partial++;
      else if (j.status === 'rejected') rejected++;
    }});

    const judged = approved + partial + rejected;
    const pct = total > 0 ? Math.round((judged / total) * 100) : 0;

    judgedCountEl.textContent = judged;
    judgedPctEl.textContent = pct + '%';
    progressFillEl.style.width = pct + '%';
    breakdownEl.innerHTML = `✅ ${{approved}} &nbsp;|&nbsp; ⚠️ ${{partial}} &nbsp;|&nbsp; ❌ ${{rejected}}`;

    document.getElementById('tab-unjudged-count').textContent = total - judged;
    document.getElementById('tab-approved-count').textContent = approved;
    document.getElementById('tab-partial-count').textContent = partial;
    document.getElementById('tab-rejected-count').textContent = rejected;
  }}

  function applyFilters() {{
    const cards = container.querySelectorAll('.paper-card');
    cards.forEach((card, idx) => {{
      const p = PAPERS[idx];
      const j = judgments[p.corpus_id] || {{}};
      const status = j.status || 'unjudged';

      // 1. Status Filter
      let matchesStatus = true;
      if (activeFilter === 'unjudged') matchesStatus = !j.status;
      else if (activeFilter !== 'all') matchesStatus = (j.status === activeFilter);

      // 2. Search Filter
      let matchesSearch = true;
      if (activeSearch) {{
        const textToSearch = [
          p.title || '',
          p.arxiv_id || '',
          p.keywords || '',
          (p.terms || []).join(' '),
          p.abstract || '',
          (p.authors || []).map(a => a.name || a).join(' ')
        ].join(' ').toLowerCase();
        matchesSearch = textToSearch.includes(activeSearch);
      }}

      card.style.display = (matchesStatus && matchesSearch) ? 'block' : 'none';
    }});
  }}

  // Setup Event Listeners
  container.addEventListener('click', (e) => {{
    const btn = e.target.closest('.btn-judge');
    if (!btn) return;
    const card = btn.closest('.paper-card');
    const idx = parseInt(card.dataset.idx, 10);
    const corpusId = card.dataset.corpus;
    const val = btn.dataset.val;

    const current = judgments[corpusId] || {{}};
    // Toggle off if already active
    if (current.status === val) {{
      delete judgments[corpusId].status;
    }} else {{
      judgments[corpusId] = {{
        ...current,
        status: val,
        arxiv_id: PAPERS[idx].arxiv_id,
        title: PAPERS[idx].title,
        keywords: PAPERS[idx].keywords,
        timestamp: new Date().toISOString()
      }};
    }}

    saveJudgments();
    updateCardUI(card, judgments[corpusId]);
    updateGlobalStats();
    if (activeFilter !== 'all') applyFilters();
  }});

  container.addEventListener('input', (e) => {{
    if (!e.target.classList.contains('notes-input')) return;
    const card = e.target.closest('.paper-card');
    const corpusId = card.dataset.corpus;
    const idx = parseInt(card.dataset.idx, 10);

    judgments[corpusId] = {{
      ...(judgments[corpusId] || {{}}),
      notes: e.target.value,
      arxiv_id: PAPERS[idx].arxiv_id,
      title: PAPERS[idx].title,
      keywords: PAPERS[idx].keywords,
      timestamp: new Date().toISOString()
    }};
    saveJudgments();
  }});

  // Filter tab buttons
  document.querySelectorAll('.filter-tab').forEach(tab => {{
    tab.addEventListener('click', () => {{
      document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeFilter = tab.dataset.filter;
      applyFilters();
    }});
  }});

  // Search input
  searchInput.addEventListener('input', (e) => {{
    activeSearch = e.target.value.trim().toLowerCase();
    applyFilters();
  }});

  // Export CSV
  document.getElementById('btn-export-csv').addEventListener('click', () => {{
    const rows = [
      ['corpus_id', 'arxiv_id', 'title', 'keywords', 'judgment', 'notes', 'timestamp']
    ];
    PAPERS.forEach(p => {{
      const j = judgments[p.corpus_id] || {{}};
      rows.push([
        p.corpus_id,
        p.arxiv_id,
        p.title,
        p.keywords,
        j.status || 'unjudged',
        j.notes || '',
        j.timestamp || ''
      ]);
    }});

    const csvContent = rows.map(r => r.map(cell => '"' + String(cell || '').replace(/"/g, '""') + '"').join(',')).join('\\n');
    const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'keyword_judgments_' + new Date().toISOString().slice(0,10) + '.csv';
    link.click();
    showToast('Exported CSV with ' + PAPERS.length + ' rows!');
  }});

  // Export JSON
  document.getElementById('btn-export-json').addEventListener('click', () => {{
    const exportData = PAPERS.map(p => {{
      const j = judgments[p.corpus_id] || {{}};
      return {{
        corpus_id: p.corpus_id,
        arxiv_id: p.arxiv_id,
        title: p.title,
        keywords: p.keywords,
        terms: p.terms,
        judgment: j.status || 'unjudged',
        notes: j.notes || '',
        timestamp: j.timestamp || null
      }};
    }});
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'keyword_judgments_' + new Date().toISOString().slice(0,10) + '.json';
    link.click();
    showToast('Exported JSON with ' + PAPERS.length + ' records!');
  }});

  // Reset
  document.getElementById('btn-reset').addEventListener('click', () => {{
    if (confirm('Are you sure you want to clear all judgments for this session?')) {{
      judgments = {{}};
      localStorage.removeItem(STORAGE_KEY);
      container.querySelectorAll('.paper-card').forEach(card => updateCardUI(card, null));
      updateGlobalStats();
      applyFilters();
      showToast('Judgments cleared.');
    }}
  }});

  // Keyboard Shortcuts (1=Approve, 2=Partial, 3=Reject, J/K=Navigate)
  let currentCardIndex = -1;
  document.addEventListener('keydown', (e) => {{
    // Don't intercept when typing in search or notes
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    const visibleCards = Array.from(container.querySelectorAll('.paper-card')).filter(c => c.style.display !== 'none');
    if (!visibleCards.length) return;

    if (e.key === 'j' || e.key === 'ArrowDown') {{
      e.preventDefault();
      currentCardIndex = Math.min(currentCardIndex + 1, visibleCards.length - 1);
      visibleCards[currentCardIndex].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }} else if (e.key === 'k' || e.key === 'ArrowUp') {{
      e.preventDefault();
      currentCardIndex = Math.max(currentCardIndex - 1, 0);
      visibleCards[currentCardIndex].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }} else if (['1', '2', '3', 'a', 'p', 'r'].includes(e.key.toLowerCase())) {{
      if (currentCardIndex >= 0 && currentCardIndex < visibleCards.length) {{
        const card = visibleCards[currentCardIndex];
        let btn;
        if (e.key === '1' || e.key.toLowerCase() === 'a') btn = card.querySelector('.btn-approve');
        else if (e.key === '2' || e.key.toLowerCase() === 'p') btn = card.querySelector('.btn-partial');
        else if (e.key === '3' || e.key.toLowerCase() === 'r') btn = card.querySelector('.btn-reject');
        if (btn) btn.click();
      }}
    }}
  }});

  // Initialize UI with existing judgments
  container.querySelectorAll('.paper-card').forEach(card => {{
    const corpusId = card.dataset.corpus;
    if (judgments[corpusId]) {{
      updateCardUI(card, judgments[corpusId]);
    }}
  }});
  updateGlobalStats();
</script>
</body>
</html>
"""
    return html_template


def extract_keywords(
    input_path: str,
    output_path: Optional[str] = None,
    output_format: str = "auto",
    clean: bool = True,
    split: bool = False,
    include_all_arxiv: bool = False,
    drop_empty: bool = True,
    sample: Optional[int] = None,
    seed: int = 42,
    html_title: str = "arXiv Keywords Verification Tool",
    verbose: bool = True,
) -> int:
    """Extracts arXiv IDs and keywords from JSON dump."""
    t0 = time.time()
    if verbose:
        print(f"Loading '{input_path}'...", file=sys.stderr)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if verbose:
        print(f"Loaded {len(data):,} records in {time.time() - t0:.2f}s. Extracting...", file=sys.stderr)

    # Determine format
    if output_format == "auto":
        if output_path:
            lower = output_path.lower()
            if lower.endswith(".html") or lower.endswith(".htm"):
                fmt = "html"
            elif lower.endswith(".jsonl"):
                fmt = "jsonl"
            elif lower.endswith(".json"):
                fmt = "json"
            elif lower.endswith(".csv"):
                fmt = "csv"
            else:
                fmt = "tsv"
        else:
            fmt = "tsv"
    else:
        fmt = output_format.lower()

    # If output is HTML, ensure terms are split for nice badge rendering
    if fmt == "html":
        split = True

    # Extract records
    extracted = []
    skipped_no_arxiv = 0
    skipped_no_kw = 0
    skipped_empty_after_clean = 0

    for corpus_id, item in data.items():
        arxiv_id = get_arxiv_id(item)
        raw_kw = item.get("keywords_from_pdf")

        if not arxiv_id:
            skipped_no_arxiv += 1
            continue

        if not raw_kw:
            skipped_no_kw += 1
            if not include_all_arxiv:
                continue
            final_kw = ""
            term_list = []
        else:
            final_kw = clean_keywords(raw_kw) if clean else raw_kw.strip()
            if drop_empty and not final_kw:
                skipped_empty_after_clean += 1
                if not include_all_arxiv:
                    continue
            term_list = split_keyword_terms(final_kw) if split else []

        extracted.append({
            "corpus_id": str(corpus_id),
            "arxiv_id": arxiv_id,
            "keywords": final_kw,
            "terms": term_list,
            "raw_keywords": raw_kw or "",
            "title": item.get("title") or "Untitled Paper",
            "authors": item.get("authors") or [],
            "abstract": item.get("abstract") or "",
            "url": item.get("url") or f"https://www.semanticscholar.org/paper/{corpus_id}",
        })

    total_extracted_pool = len(extracted)
    if verbose:
        print(f"Extracted {total_extracted_pool:,} valid records from pool.", file=sys.stderr)
        print(f"  -> Skipped without arXiv ID: {skipped_no_arxiv:,}", file=sys.stderr)
        print(f"  -> Skipped without keywords: {skipped_no_kw:,}", file=sys.stderr)
        if drop_empty:
            print(f"  -> Skipped empty after cleaning: {skipped_empty_after_clean:,}", file=sys.stderr)

    # Apply random sampling if requested
    if sample is not None and sample > 0 and len(extracted) > sample:
        random.seed(seed)
        extracted = random.sample(extracted, sample)
        if verbose:
            print(f"Randomly sampled {len(extracted):,} records (seed={seed}).", file=sys.stderr)

    # Open output handle
    out_fd = open(output_path, "w", encoding="utf-8") if output_path else sys.stdout

    try:
        if fmt == "html":
            html_content = generate_html_verification_page(
                records=extracted,
                title=html_title,
                total_pool_size=total_extracted_pool,
                sample_seed=seed if sample else None,
            )
            out_fd.write(html_content)

        elif fmt == "tsv":
            writer = csv.writer(out_fd, delimiter="\t", lineterminator="\n")
            writer.writerow(["arxiv_id", "keywords", "corpus_id"])
            for r in extracted:
                kw_val = "; ".join(r["terms"]) if (split and r["terms"]) else r["keywords"]
                writer.writerow([r["arxiv_id"], kw_val, r["corpus_id"]])

        elif fmt == "csv":
            writer = csv.writer(out_fd, lineterminator="\n")
            writer.writerow(["arxiv_id", "keywords", "corpus_id"])
            for r in extracted:
                kw_val = "; ".join(r["terms"]) if (split and r["terms"]) else r["keywords"]
                writer.writerow([r["arxiv_id"], kw_val, r["corpus_id"]])

        elif fmt == "jsonl":
            for r in extracted:
                row_dict = {
                    "corpus_id": r["corpus_id"],
                    "arxiv_id": r["arxiv_id"],
                    "keywords": r["keywords"],
                }
                if split:
                    row_dict["terms"] = r["terms"]
                if not clean:
                    row_dict["raw_keywords"] = r["raw_keywords"]
                out_fd.write(json.dumps(row_dict, ensure_ascii=False) + "\n")

        elif fmt == "json":
            out_dict = {}
            for r in extracted:
                if split:
                    out_dict[r["arxiv_id"]] = {
                        "corpus_id": r["corpus_id"],
                        "keywords": r["keywords"],
                        "terms": r["terms"],
                    }
                else:
                    out_dict[r["arxiv_id"]] = r["keywords"]
            json.dump(out_dict, out_fd, indent=2, ensure_ascii=False)
            out_fd.write("\n")

    finally:
        if output_path:
            out_fd.close()

    t_total = time.time() - t0
    if verbose:
        print(f"Done! Processed and wrote {len(extracted):,} records in {t_total:.2f}s.", file=sys.stderr)
        if output_path:
            out_sz_mb = os.path.getsize(output_path) / (1024**2)
            print(f"Output saved to: {output_path} ({out_sz_mb:.2f} MB)", file=sys.stderr)

    return len(extracted)


def main():
    parser = argparse.ArgumentParser(
        description="Extract arXiv IDs and PDF keywords from Semantic Scholar keywords JSON dump, with judge verification HTML output.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input", default="/Users/kwc/Downloads/keywords7.json",
        help="Path to input JSON file.",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Path to output file (.html, .tsv, .csv, .jsonl, .json, or stdout).",
    )
    parser.add_argument(
        "-f", "--format", choices=["auto", "html", "tsv", "csv", "jsonl", "json"], default="auto",
        help="Output format. 'html' creates an interactive judge verification interface.",
    )
    parser.add_argument(
        "--sample", "-n", type=int, default=None,
        help="Randomly sample N records for verification (e.g. 50 or 100).",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible sampling.",
    )
    parser.add_argument(
        "--title", default="arXiv Keywords Verification Tool",
        help="Title displayed in the generated HTML verification page.",
    )
    parser.add_argument(
        "--no-clean", dest="clean", action="store_false",
        help="Do NOT clean leading 'Keywords:' / 'Author Keywords' prefixes.",
    )
    parser.add_argument(
        "--split", action="store_true",
        help="Split keywords into structured lists of individual terms.",
    )
    parser.add_argument(
        "--all-arxiv", action="store_true",
        help="Include all records with an arXiv ID, even if keywords_from_pdf is missing.",
    )
    parser.add_argument(
        "--keep-empty", dest="drop_empty", action="store_false",
        help="Keep records whose keywords became empty after stripping boilerplate.",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"Error: Input file '{args.input}' not found.")

    extract_keywords(
        input_path=args.input,
        output_path=args.output,
        output_format=args.format,
        clean=args.clean,
        split=args.split,
        include_all_arxiv=args.all_arxiv,
        drop_empty=args.drop_empty,
        sample=args.sample,
        seed=args.seed,
        html_title=args.title,
        verbose=True,
    )


if __name__ == "__main__":
    main()
