# ==============================================================================
# LEGAL DOCUMENT CHUNKER (GENERIC + DYNAMIC TABLES)
# ==============================================================================
#
# WHAT IT DOES:
# 1. Structure-First Parsing: Identifies the document hierarchy (Article -> Clause).
# 2. Dynamic Table Extraction: Auto-detects tables based on spacing/tabs,
#    inferring headers from the first row found (no hardcoded column names).
# 3. Semantic Repair: Fixes broken lines using vector similarity.
#
# ==============================================================================

from __future__ import annotations

import re
import numpy as np
from typing import List, Dict, Any, Optional

# Used for semantic similarity to merge broken lines (PDF artifacts)
from sentence_transformers import SentenceTransformer

# ==============================================================================
# 1. CONFIGURATION & REGEX GRAMMAR
# ==============================================================================

# EMBEDDING MODEL
# Loaded once. Used strictly for cleanup, NOT for final vector storage.
_embedder = SentenceTransformer("all-MiniLM-L6-v2")

# HIERARCHY PATTERNS
# These regexes define the "skeleton" of the document.
ARTICLE_RE = re.compile(r"^ARTICLE[\s\-–—]*([0-9IVXLCDM]+)", re.I)
ANNEX_RE   = re.compile(r"^(Annexure|Appendix|Schedule)[\s\-–—]*([A-Za-z0-9]*)", re.I)
MAIN_RE    = re.compile(r"^(\d+(?:\.\d+)*)[\.\)]?\s+(.*)")
ALPHA_RE   = re.compile(r"^\(?([a-z])[\)\.]?\s+(.*)", re.I)
ROMAN_RE   = re.compile(r"^\(?([ivxlcdm]+)[\)\.]?\s+(.*)", re.I)
# Numeric bullets inside subclauses (e.g., 1) Labor ... under a lettered item)
SUBNUM_RE  = re.compile(r"^\(?([0-9]+)[\)\.]?\s+(.*)")

# GENERIC TABLE DETECTION
# Matches lines containing tabs OR sequences of 3+ spaces.
# Why 3 spaces? It's a common heuristic for visually aligned columns in plain text.
TABLE_SPLIT_RE = re.compile(r"\t+|\s{3,}")


# ==============================================================================
# 2. HELPER FUNCTIONS: SEMANTIC SIMILARITY
# ==============================================================================

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculates cosine similarity between two vectors.
    Range: -1 (opposite) to 1 (identical).
    """
    # 
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def semantic_cleanup(text: str, threshold: float = 0.92) -> str:
    """
    Merges lines within a clause if they are semantically continuous.
    
    HOW:
    - If Line A and Line B have similarity > 0.92, we assume Line B
      is a continuation of Line A (broken by PDF formatting).
    - If similarity is lower, Line B is likely a new thought/bullet.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) <= 1:
        return text.strip()

    emb = _embedder.encode(lines)
    merged = [lines[0]]
    
    for i in range(1, len(lines)):
        if cosine(emb[i - 1], emb[i]) > threshold:
            merged[-1] += " " + lines[i]
        else:
            merged.append(lines[i])

    return "\n".join(merged)


# ==============================================================================
# 3. GENERIC TABLE EXTRACTION (DYNAMIC SCHEMA)
# ==============================================================================

def looks_like_table_row(line: str) -> bool:
    """
    Heuristic: Does this line look like a table row?
    Criteria: Must split into at least 3 distinct columns based on spacing/tabs.
    """
    parts = TABLE_SPLIT_RE.split(line.strip())
    # Filter empty strings that might result from splitting
    parts = [p for p in parts if p.strip()]
    return len(parts) >= 3


def extract_tables(lines: List[str]):
    """
    Extracts tables without knowing the schema beforehand.
    
    ALGORITHM:
    1. Scan lines for `looks_like_table_row`.
    2. If found, start collecting subsequent lines that also look like rows.
    3. ASSUMPTION: The first line of the block is the Header.
    4. Construct JSON: Map subsequent rows to the headers found in line 1.
    """
    tables = []
    cleaned = []

    i = 0
    # Context tracking: attach tables to the last known section header
    last_section = "Document"

    while i < len(lines):
        line = lines[i].strip()

        # Update context if we see a header
        if MAIN_RE.match(line) or ARTICLE_RE.match(line) or ANNEX_RE.match(line):
            last_section = line

        # CHECK: Is this the start of a table?
        if looks_like_table_row(line):
            table_lines = []
            
            # Consume all consecutive lines that look like table rows
            while i < len(lines) and looks_like_table_row(lines[i]):
                table_lines.append(lines[i].strip())
                i += 1

            # We need at least 2 lines (Header + Data) to form a valid table
            if len(table_lines) >= 2:
                # Split all rows by the separator regex
                rows = [TABLE_SPLIT_RE.split(r) for r in table_lines]
                
                # HEADERS: Inferred from the first row found
                # Normalize: "Unit Price" -> "unit_price"
                headers = [h.lower().strip().replace(" ", "_") for h in rows[0] if h.strip()]
                
                structured_rows = []
                for row_data in rows[1:]:
                    # Clean empty splits
                    row_data = [d for d in row_data if d.strip()]
                    
                    # Safety: Ensure row length matches header length. 
                    # Pad with empty strings if short (common in messy OCR).
                    if len(row_data) < len(headers):
                        row_data += [""] * (len(headers) - len(row_data))
                    
                    # Create the dictionary for this row
                    # zip stops at the shortest length, so we handle mapping safely
                    structured_rows.append(dict(zip(headers, row_data)))

                tables.append({
                    "type": "table",
                    "section": last_section, # Contextual metadata
                    "headers": headers,      # The inferred schema
                    "rows": structured_rows  # The data
                })
            
            # Continue main loop (we already incremented i inside the inner while)
            continue

        # If not a table, keep the line for text processing
        cleaned.append(lines[i])
        i += 1

    return tables, cleaned


# ==============================================================================
# 4. CORE LOGIC: HIERARCHICAL SPLITTER
# ==============================================================================

def split_clauses(text: str) -> List[Dict[str, Any]]:
    """
    Parses the document into a tree of clauses (Article > Clause > Subclause).
    
    THE STACK:
    We maintain a 'stack' state to track depth. 
    
    This allows us to assign IDs like "A1.2.b" automatically.
    """
    if not text:
        return []

    # 1. Pre-process: Clean whitespace
    raw_lines = [l.rstrip() for l in text.splitlines()]

    # 2. Extract Tables (so they don't break the text parser)
    tables, lines = extract_tables(raw_lines)

    results: List[Dict[str, Any]] = []

    # State Machine Variables
    section_name = "Document"

    # Sequential counters keep IDs unique and ordered, independent of the raw labels
    article_counter = 0
    main_counter = 0
    alpha_counter = 0
    roman_counter = 0
    loose_counter = 0  # for unanchored text blocks

    # Hierarchy Stack stores the rendered token at each depth
    stack = {"article": None, "main": None, "alpha": None, "roman": None}
    
    # Text Buffer for current clause
    buffer: List[str] = []

    # --- HELPERS ---

    def int_to_roman(n: int) -> str:
        """Best-effort roman numeral conversion for sub-sub clauses."""
        numerals = [
            (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"),
            (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
            (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
        ]
        result = ""
        value = n
        for val, sym in numerals:
            while value >= val:
                result += sym
                value -= val
        return result

    def num_to_alpha(n: int) -> str:
        """1 -> A, 2 -> B ... wraps after Z to AA."""
        letters = ""
        num = n
        while num > 0:
            num -= 1
            letters = chr(ord("A") + (num % 26)) + letters
            num //= 26
        return letters

    def build_id(current_level_parts: List[str]) -> str:
        """Constructs unique ID from current stack (e.g., '1.B.iii')."""
        parts = [p for p in current_level_parts if p]
        return ".".join(parts) if parts else ""

    def flush(level="clause"):
        """Commits the current buffer to the results list."""
        nonlocal buffer, loose_counter
        if not buffer:
            return

        text_block = "\n".join(buffer).strip()
        buffer = []

        id_parts = [stack.get("article"), stack.get("main"), stack.get("alpha"), stack.get("roman")]
        clause_id = build_id(id_parts)
        if not clause_id:
            loose_counter += 1
            clause_id = f"P{loose_counter}"

        results.append({
            "clause_id": clause_id,
            "section": section_name,
            "level": level,
            "text": semantic_cleanup(text_block) # Fix broken lines before saving
        })

    # --- MAIN PARSER LOOP ---

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # LEVEL 1: ARTICLES ("ARTICLE 1")
        m = ARTICLE_RE.match(line)
        if m:
            flush() # Save previous work
            article_counter += 1
            main_counter = alpha_counter = roman_counter = 0
            section_name = line
            stack = {
                "article": f"ART{article_counter}",
                "main": None,
                "alpha": None,
                "roman": None,
            }
            continue

        # LEVEL 1 (Alternate): ANNEXURES ("Annexure A")
        m = ANNEX_RE.match(line)
        if m:
            flush()
            article_counter += 1
            main_counter = alpha_counter = roman_counter = 0
            section_name = line
            stack = {
                "article": f"ANNEX{article_counter}",
                "main": None,
                "alpha": None,
                "roman": None,
            }
            continue

        # LEVEL 2: MAIN CLAUSES ("1.", "2.1")
        # Context-aware: if we are inside an alpha item, a bare number is treated as a deeper sub-item
        if stack["alpha"] and SUBNUM_RE.match(line):
            flush("subsubclause")
            roman_counter += 1
            stack["roman"] = int_to_roman(roman_counter)
            m_num = SUBNUM_RE.match(line)
            buffer.append(m_num.group(2))
            continue

        m = MAIN_RE.match(line)
        if m:
            flush("clause")
            main_counter += 1
            alpha_counter = 0
            roman_counter = 0
            stack["main"] = str(main_counter)
            stack["alpha"] = None  # Reset lower levels
            stack["roman"] = None
            buffer.append(m.group(2))
            continue

        # LEVEL 3: ALPHA SUBCLAUSES ("(a)", "b.")
        m = ALPHA_RE.match(line)
        if m:
            flush("subclause")
            alpha_counter += 1
            roman_counter = 0
            stack["alpha"] = num_to_alpha(alpha_counter)
            stack["roman"] = None # Reset lower levels
            buffer.append(m.group(2))
            continue

        # LEVEL 4: ROMAN SUBSUBCLAUSES ("(i)", "ii")
        m = ROMAN_RE.match(line)
        if m:
            flush("subsubclause")
            roman_counter += 1
            stack["roman"] = int_to_roman(roman_counter)
            buffer.append(m.group(2))
            continue

        # PLAIN TEXT: Append to current buffer
        buffer.append(line)

    # Final flush to catch the last clause in the document
    flush()

    return results + tables