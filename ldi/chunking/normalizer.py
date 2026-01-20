
# Clause normalization utilities
#
# This module provides helper functions for cleaning, normalizing, and generating IDs for legal document clauses.
# It ensures consistent formatting, robust clause number parsing, and unique clause identification.

from __future__ import annotations

import re
from dataclasses import dataclass



# Regex to match any sequence of whitespace characters
_WS_RE = re.compile(r"\s+")



# Normalize text by replacing non-breaking spaces, collapsing whitespace, and trimming
def normalize_text(text: str) -> str:
	text = text.replace("\u00a0", " ")
	text = _WS_RE.sub(" ", text)
	return text.strip()



# Normalize a heading: clean up whitespace and remove trailing colons
def normalize_heading(heading: str) -> str:
	heading = normalize_text(heading)
	heading = heading.rstrip(":")
	return heading



# (Unused) Regex for Roman numeral validation (for reference)
_ROMAN_RE = re.compile(r"^(?=[IVXLCDM]+$)IV|IX|XL|XC|CD|CM|I{1,3}|V|X{1,3}|L|C{1,3}|D|M{1,4}$", re.IGNORECASE)



# Convert a Roman numeral string to an integer (returns None if invalid)
def roman_to_int(value: str) -> int | None:
	s = value.strip().upper().rstrip(".)")
	if not s:
		return None
	# Quick sanity check: only valid Roman numeral characters
	if not re.fullmatch(r"[IVXLCDM]+", s):
		return None
	roman = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
	total = 0
	prev = 0
	for ch in reversed(s):
		val = roman[ch]
		if val < prev:
			total -= val
		else:
			total += val
			prev = val
	return total if total > 0 else None



# Regex for numeric clause numbers (e.g., '1', '1.2', '(1.2)')
_CLAUSE_NUM_RE = re.compile(r"^\(?\s*([0-9]+(?:\.[0-9]+)*)\s*\)?[\.)]?$")
# Regex for single-letter clause numbers (e.g., 'A)', '(b)')
_LETTER_NUM_RE = re.compile(r"^\(?\s*([A-Z])\s*\)?[\.)]?$", re.IGNORECASE)



# Normalize clause numbers to a standard format (handles numbers, Roman numerals, and letters)
def normalize_clause_number(raw: str) -> str | None:
	"""
	Normalize common clause numbering formats.

	Examples:
	  "1." -> "1"
	  "(1.2)" -> "1.2"
	  "IV." -> "4"
	  "A)" -> "A"
	"""
	if raw is None:
		return None
	raw = normalize_text(raw)
	raw = raw.strip(" ")

	# Numeric clause (e.g., '1', '1.2')
	m = _CLAUSE_NUM_RE.match(raw)
	if m:
		return m.group(1)

	# Roman numerals (e.g., 'IV')
	roman_val = roman_to_int(raw)
	if roman_val is not None:
		return str(roman_val)

	# Lettered clause (e.g., 'A')
	m2 = _LETTER_NUM_RE.match(raw)
	if m2:
		return m2.group(1).upper()

	return None



# Generate a unique clause ID based on clause number, section, or fallback to index

# Always generate clause IDs in the format 'clause_<index>' for consistency
def make_clause_id(section: str | None, clause_number: str | None, index: int) -> str:
	return f"clause_{index}"



# Ensure all clause IDs are unique by appending a suffix if needed
def ensure_unique_ids(clauses: list[dict]) -> list[dict]:
	seen: dict[str, int] = {}
	for clause in clauses:
		cid = clause["clause_id"]
		if cid not in seen:
			seen[cid] = 1
			continue
		seen[cid] += 1
		clause["clause_id"] = f"{cid}_{seen[cid]}"
	return clauses
