
# Hybrid clause parser:
# 1) Rule-based structural anchoring (regex + formatting)
# 2) spaCy sentence fallback for unstructured docs
# 3) Optional semantic validation/merge using LegalBERT embeddings
#
# This module provides robust clause segmentation for legal documents, combining rule-based and NLP methods.
# Key features:
#   - Regex-based detection of sections, headings, and clause numbers
#   - Fallback to spaCy sentence segmentation for unstructured text
#   - Optional semantic validation/merging using LegalBERT embeddings
#   - Normalization and unique clause ID generation

from __future__ import annotations

import math
import os
import re
from functools import lru_cache
from typing import Any

import spacy

from ldi.chunking.normalizer import (
	ensure_unique_ids,      # Ensures all clause IDs are unique
	make_clause_id,         # Generates a clause ID from section, number, and index
	normalize_clause_number,# Normalizes clause numbers (e.g., '1.1' -> '1.1')
	normalize_heading,      # Normalizes section/heading text
	normalize_text,         # Cleans and normalizes general text
)



# Regex for section/heading detection (e.g., 'SECTION 1: Title')
_SECTION_RE = re.compile(
	r"^(?:\s*)(SECTION|ARTICLE|SCHEDULE|ANNEX|APPENDIX)\s+([A-Z0-9IVXLCM]+)\s*[:\.-]?\s*(.*)$",
	re.IGNORECASE,
)

# Regex for ALLCAPS headings (e.g., 'DEFINITIONS')
_ALLCAPS_HEADING_RE = re.compile(r"^[A-Z0-9][A-Z0-9\s\-_,.]{3,}$")

# Regex for clause starters: 1. / 1.1 / (1) / 1) / IV. / A)
_CLAUSE_START_RE = re.compile(
	r"^\s*(\(?\s*(?:\d+(?:\.\d+)*|[IVXLCM]+|[A-Z])\s*\)?)[\.)]\s+(\S.*)$",
	re.IGNORECASE,
)



# Load and cache the spaCy model (large English model by default)
@lru_cache(maxsize=1)
def _get_nlp(model: str = "en_core_web_lg"):
	return spacy.load(model)



# Detect if a line is a section/heading (returns normalized heading or None)
def _is_heading_line(line: str) -> str | None:
	s = normalize_text(line)
	if not s:
		return None

	m = _SECTION_RE.match(s)
	if m:
		label = m.group(1).upper()
		num = m.group(2).strip()
		rest = m.group(3).strip()
		text = f"{label} {num}" + (f": {rest}" if rest else "")
		return normalize_heading(text)

	# Heuristic for ALLCAPS headings (e.g., 'DEFINITIONS')
	if _ALLCAPS_HEADING_RE.match(s) and len(s.split()) <= 12:
		return normalize_heading(s)

	# Numbered ALLCAPS headings (e.g., '1. DEFINITIONS')
	if re.match(r"^\s*\d+\.?\s+[A-Z][A-Z\s\-]{2,}$", s):
		return normalize_heading(s)

	return None




# Preprocess text for splitting: normalize line breaks for better clause detection
def _preprocess_text(text: str) -> str:
	lines = text.splitlines()
	if len(lines) < 5:
		# If the document is mostly one line, split on likely sentence boundaries
		text = re.sub(r"(?<=[.?!])\s+(?=[A-Z])", "\n", text)
	return text




# Main rule-based clause splitter: detects sections, clause numbers, and splits text accordingly
def _initial_structural_split(text: str) -> list[dict[str, Any]]:
	text = _preprocess_text(text)
	lines = [ln.rstrip() for ln in text.splitlines()]

	clauses: list[dict[str, Any]] = []
	current_section: str | None = None
	current_number_raw: str | None = None
	current_lines: list[str] = []

	# Regex for clause starters (e.g., '2. COMPENSATION.')
	clause_starter_regex = re.compile(r"(\d+(?:\.\d+)*|[IVXLCM]+)\.\s+([A-Z][^\n]*)", re.IGNORECASE)
	subclause_regex = re.compile(r"([A-Z])\.\s+([A-Z][^\n]*)", re.IGNORECASE)

	def flush():
		# Helper to finalize and store the current clause buffer
		nonlocal current_lines, current_number_raw
		if not current_lines:
			current_number_raw = None
			return
		raw_text = "\n".join(current_lines)
		clause_text = normalize_text(raw_text)
		if clause_text:
			clause_number = normalize_clause_number(current_number_raw) if current_number_raw else None
			# Only allow single-letter clause_number if previous clause_number is numbered (e.g., '1. A.')
			if clause_number and len(clause_number) == 1 and (not clause_number.isdigit() and not clause_number.isupper()):
				clause_number = None
			clauses.append(
				{
					"section": current_section,
					"clause_number": clause_number,
					"text": clause_text,
				}
			)
		current_lines = []
		current_number_raw = None

	for ln in lines:
		heading = _is_heading_line(ln)
		# Stricter section heading detection: only match ALLCAPS or known patterns
		if heading and (heading.isupper() or heading.startswith("SECTION") or heading.startswith("ARTICLE")):
			flush()
			current_section = heading
			continue

		m = _CLAUSE_START_RE.match(ln)
		if m:
			flush()
			current_number_raw = m.group(1)
			current_lines = [m.group(2)]
			continue

		# Improved: match clause starters for numbered clauses only (e.g., '2. COMPENSATION.')
		m2 = clause_starter_regex.search(ln)
		if m2:
			flush()
			current_number_raw = m2.group(1)
			current_lines = [m2.group(2)]
			continue

		# Ignore single-letter clause starters unless part of a numbered clause
		# m3 = subclause_regex.search(ln)
		# if m3:
		#     continue

		# Regular line: append to current clause buffer
		if ln.strip() == "":
			if current_lines:
				current_lines.append("")
			continue
		current_lines.append(ln)

	flush()
	# Post-process: filter out clauses with ambiguous IDs (single letters not part of numbered clause)
	filtered = []
	for c in clauses:
		cid = c.get("clause_number")
		if cid and len(cid) == 1 and cid.isalpha():
			continue
		filtered.append(c)
	return filtered



# Fallback: Use spaCy sentence segmentation if rule-based splitting fails or is insufficient
def _spacy_sentence_fallback(text: str, section: str | None = None, model: str = "en_core_web_lg") -> list[dict[str, Any]]:
	nlp = _get_nlp(model)
	doc = nlp(text)
	sents = [normalize_text(s.text) for s in doc.sents if normalize_text(s.text)]

	clauses: list[dict[str, Any]] = []
	buf: list[str] = []
	max_chars = 900  # Limit clause size for readability

	def flush():
		# Helper to finalize and store the current buffer as a clause
		nonlocal buf
		if not buf:
			return
		clauses.append({"section": section, "clause_number": None, "text": normalize_text(" ".join(buf))})
		buf = []

	for sent in sents:
		if sum(len(x) for x in buf) + len(sent) + len(buf) > max_chars:
			flush()
		buf.append(sent)
	flush()
	return clauses



# Compute cosine similarity between two vectors
def _cosine(a: list[float], b: list[float]) -> float:
	dot = sum(x * y for x, y in zip(a, b))
	na = math.sqrt(sum(x * x for x in a))
	nb = math.sqrt(sum(y * y for y in b))
	if na == 0.0 or nb == 0.0:
		return 0.0
	return dot / (na * nb)



# Load and cache the LegalBERT model and tokenizer
@lru_cache(maxsize=1)
def _load_legalbert(model_name: str = "nlpaueb/legal-bert-base-uncased"):
	from transformers import AutoModel, AutoTokenizer

	tokenizer = AutoTokenizer.from_pretrained(model_name)
	model = AutoModel.from_pretrained(model_name)
	model.eval()
	return tokenizer, model



# Embed a list of texts using LegalBERT (returns list of vectors)
def _embed_texts(texts: list[str], model_name: str) -> list[list[float]]:
	import torch

	tokenizer, model = _load_legalbert(model_name)
	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
	model = model.to(device)

	vectors: list[list[float]] = []
	with torch.no_grad():
		for t in texts:
			enc = tokenizer(t, truncation=True, max_length=256, return_tensors="pt")
			enc = {k: v.to(device) for k, v in enc.items()}
			out = model(**enc)
			# Mean pooling over tokens (masked)
			last = out.last_hidden_state  # (1, seq, hid)
			mask = enc.get("attention_mask")
			if mask is None:
				vec = last.mean(dim=1).squeeze(0)
			else:
				mask_f = mask.unsqueeze(-1).expand(last.size()).float()
				summed = (last * mask_f).sum(dim=1)
				denom = mask_f.sum(dim=1).clamp(min=1e-9)
				vec = (summed / denom).squeeze(0)
			vectors.append(vec.detach().cpu().tolist())
	return vectors



# Optional: Use LegalBERT embeddings to merge short, low-similarity clauses (semantic validation)
def _semantic_validate_and_merge(
	clauses: list[dict[str, Any]],
	model_name: str = "nlpaueb/legal-bert-base-uncased",
	similarity_threshold: float = 0.20,
	short_clause_chars: int = 90,
) -> list[dict[str, Any]]:
	# Lightweight merge strategy:
	# If a very short clause has low similarity to both neighbors, it's probably a bad split -> merge.
	if len(clauses) < 2:
		return clauses

	texts = [c["text"] for c in clauses]
	vectors = _embed_texts(texts, model_name)

	merged: list[dict[str, Any]] = []
	i = 0
	while i < len(clauses):
		cur = clauses[i]
		cur_text = cur["text"]
		cur_vec = vectors[i]

		prev_sim = None
		next_sim = None
		if merged:
			prev_sim = _cosine(_embed_texts([merged[-1]["text"]], model_name)[0], cur_vec)
		if i + 1 < len(clauses):
			next_sim = _cosine(cur_vec, vectors[i + 1])

		is_short = len(cur_text) < short_clause_chars
		low_prev = prev_sim is None or prev_sim < similarity_threshold
		low_next = next_sim is None or next_sim < similarity_threshold

		if is_short and low_prev and (i + 1 < len(clauses)):
			# Merge short clause forward
			nxt = clauses[i + 1]
			nxt["text"] = normalize_text(cur_text + " " + nxt["text"])
			# Prefer preserving clause_number if next lacks it
			if nxt.get("clause_number") is None and cur.get("clause_number") is not None:
				nxt["clause_number"] = cur.get("clause_number")
			i += 1
			continue

		if is_short and low_next and merged:
			# Merge short clause backward
			merged[-1]["text"] = normalize_text(merged[-1]["text"] + " " + cur_text)
			i += 1
			continue

		merged.append(cur)
		i += 1

	return merged




# Main entry point: split text into clauses with unique IDs and normalized structure
def split_clauses(
	text: str,
	*,
	spacy_model: str = "en_core_web_lg",
	semantic_validation: bool = False,
	legalbert_model: str = "nlpaueb/legal-bert-base-uncased",
) -> list[dict[str, Any]]:
	"""
	Return list of {clause_id, section, text}.

	Strategy:
	  - Preprocess for line breaks
	  - Regex-based anchors for section headings + clause numbering
	  - More flexible clause starter detection
	  - spaCy sentence fallback if no anchors are found or only one clause is found
	  - Optional LegalBERT embedding-based merge pass
	"""
	text = normalize_text(text)
	if not text:
		return []

	# First, try rule-based splitting
	clauses = _initial_structural_split(text)
	# Fallback: if only one clause, run aggressive spaCy sentence split
	if not clauses or len(clauses) == 1:
		clauses = _spacy_sentence_fallback(text, section=None, model=spacy_model)

	# Optionally merge/validate using LegalBERT embeddings
	if semantic_validation:
		# If model isn't available locally yet, this will download it.
		clauses = _semantic_validate_and_merge(clauses, model_name=legalbert_model)

	# Final shaping: ensure IDs and output schema
	out: list[dict[str, Any]] = []
	for idx, c in enumerate(clauses, start=1):
		cid = make_clause_id(c.get("section"), c.get("clause_number"), idx)
		out.append({"clause_id": cid, "section": c.get("section"), "text": c.get("text")})

	return ensure_unique_ids(out)
