"""Conservative spaCy context detector; NER never drives risk severity."""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Any

from .dictionaries import LEGAL_BOILERPLATE

_ALLOWED = {"PERSON", "ORG", "GPE", "LOC", "MONEY", "DATE"}


@lru_cache(maxsize=1)
def _load_nlp():
    try:
        import spacy
    except ImportError:  # NER is optional; deterministic detectors remain usable.
        return None
    try:
        return spacy.load("en_core_web_sm")
    except OSError as exc:  # pragma: no cover
        raise RuntimeError("spaCy model 'en_core_web_sm' is missing. Install it with: python -m spacy download en_core_web_sm") from exc


def _valid(label: str, value: str) -> bool:
    normalized = re.sub(r"\s+", " ", value.strip(" \"'`.,;:()[]{}"))
    lowered = normalized.lower()
    if not normalized or lowered in LEGAL_BOILERPLATE or any(lowered.startswith(term + " ") for term in LEGAL_BOILERPLATE):
        return False
    if label == "PERSON":
        return len(re.findall(r"[A-Za-z]+", normalized)) >= 2 and not re.search(r"\b(?:company|employee|party|section|schedule)\b", lowered)
    if label == "MONEY":
        return bool(re.search(r"\d|[$€£₹]", normalized))
    if label in {"GPE", "LOC"}:
        return len(normalized) >= 3
    if label == "ORG":
        return len(normalized) >= 4 and not lowered.startswith(("the ", "a "))
    return True


class NERDetector:
    """Supplement deterministic detectors with validated named-entity context."""

    def detect(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        findings = []
        nlp = _load_nlp()
        if nlp is None:
            # Keep the engine usable in minimal deployments; this narrow fallback
            # only recognizes explicit person names and corporate suffixes.
            for match in re.finditer(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", text or ""):
                if _valid("PERSON", match.group(0)):
                    findings.append({"type": "PERSON", "value": match.group(0), "start": match.start(), "end": match.end(), "source": "ner", "category": "context"})
            for match in re.finditer(r"\b[A-Z][A-Za-z& ]{2,60}\b(?:PRIVATE LIMITED|PVT\.? LTD\.?|LIMITED|CORPORATION|CORP\.?)", text or ""):
                findings.append({"type": "ORG", "value": match.group(0).strip(), "start": match.start(), "end": match.end(), "source": "ner", "category": "context"})
            return findings
        for entity in nlp(text or "").ents:
            if entity.label_ not in _ALLOWED or not _valid(entity.label_, entity.text):
                continue
            findings.append({"type": entity.label_, "value": entity.text.strip(), "start": entity.start_char, "end": entity.end_char, "source": "ner", "category": "context"})
        return findings


def detect_ner_sensitive_info(text: str) -> list[dict[str, Any]]:
    """Compatibility function for the original public detector API."""
    return NERDetector().detect(text)
