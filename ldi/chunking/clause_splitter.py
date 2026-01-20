from __future__ import annotations

import re
from typing import Any, List

import spacy

from ldi.chunking.normalizer import (
    normalize_text,
    normalize_heading,
    normalize_clause_number,
    make_clause_id,
    ensure_unique_ids,
)

# ============================================================
# REGEX PATTERNS
# ============================================================

# Clause numbers like: 1. / 1.1 / (1)
CLAUSE_NUM_RE = re.compile(r"^\(?\d+(?:\.\d+)*\)?\.?$")

# ALL CAPS headings
HEADING_RE = re.compile(r"^[A-Z][A-Z\s\-&,]{3,}\.?$")

# Combined: "1. HEADING"
COMBINED_RE = re.compile(
    r"^\(?(\d+(?:\.\d+)*)\)?\.?\s+([A-Z][A-Z\s\-&,]{3,})\.?$"
)

# Page noise
PAGE_NOISE_RE = re.compile(r"Legal Services Agreement Page \d+ of \d+", re.IGNORECASE)

# Bullet / list markers
BULLET_RE = re.compile(r"^(G|•|-)\s+")

# ============================================================
# spaCy (fallback only)
# ============================================================

_nlp = None
def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_lg")
    return _nlp

# ============================================================
# LAYOUT RECONSTRUCTION (CRITICAL)
# ============================================================

def rebuild_layout(text: str) -> str:
    """
    Rebuild legal document layout from broken PDF text.

    This step is NON-OPTIONAL for real contracts.
    """
    # Force clause numbers onto new lines
    text = re.sub(r'(?<!\n)(\s*)(\d+\.)\s*', r'\n\2 ', text)

    # Force ALL CAPS headings onto new lines
    text = re.sub(
        r'(?<!\n)([A-Z][A-Z\s\-&,]{5,})\.',
        r'\n\1.',
        text
    )

    return text

# ============================================================
# CORE CLAUSE SPLITTER
# ============================================================

def split_clauses(text: str) -> List[dict[str, Any]]:
    """
    Split legal document into real legal clauses.

    Clause definition:
    ------------------
    Clause = (number + heading) + body paragraphs + lists
    """
    if not text:
        return []

    # 🔴 DO NOT sentence-split before this
    text = normalize_text(text)
    text = rebuild_layout(text)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    clauses = []

    current_section = None
    current_number = None
    buffer: list[str] = []

    def flush():
        nonlocal buffer, current_number
        if not buffer:
            return

        clauses.append({
            "section": current_section,
            "clause_number": normalize_clause_number(current_number),
            "text": normalize_text(" ".join(buffer)),
        })

        buffer = []
        current_number = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Drop page headers
        if PAGE_NOISE_RE.search(line):
            i += 1
            continue

        # Case 1: "1. HEADING"
        m = COMBINED_RE.match(line)
        if m:
            flush()
            current_number = m.group(1)
            current_section = normalize_heading(m.group(2))
            i += 1
            continue

        # Case 2: "1." followed by heading
        if CLAUSE_NUM_RE.match(line):
            flush()
            current_number = line

            if i + 1 < len(lines) and HEADING_RE.match(lines[i + 1]):
                current_section = normalize_heading(lines[i + 1])
                i += 2
            else:
                i += 1
            continue

        # Case 3: Standalone heading (rare but valid)
        if HEADING_RE.match(line):
            current_section = normalize_heading(line)
            i += 1
            continue

        # Case 4: Bullet/list → stay inside clause
        if BULLET_RE.match(line):
            buffer.append(line)
            i += 1
            continue

        # Case 5: Normal body text
        buffer.append(line)
        i += 1

    flush()

    # Fallback ONLY if structure totally failed
    if len(clauses) <= 1:
        doc = get_nlp()(text)
        clauses = [{
            "section": None,
            "clause_number": None,
            "text": normalize_text(sent.text)
        } for sent in doc.sents if normalize_text(sent.text)]

    # Final shaping
    output = []
    for idx, c in enumerate(clauses, start=1):
        output.append({
            "clause_id": make_clause_id(c["section"], c["clause_number"], idx),
            "section": c["section"],
            "text": c["text"],
        })

    return ensure_unique_ids(output)
