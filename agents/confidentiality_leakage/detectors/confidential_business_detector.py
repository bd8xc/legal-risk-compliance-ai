"""Detector for non-public business assets and secrets mentioned in clauses."""

from __future__ import annotations

import re
from typing import Any

from .dictionaries import BUSINESS_CONFIDENTIAL


class ConfidentialBusinessDetector:
    """Detect business-confidential concepts using a controlled vocabulary."""

    def detect(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        findings = []
        for detection_type, terms in BUSINESS_CONFIDENTIAL.items():
            expression = r"\b(?:" + "|".join(re.escape(term) for term in terms) + r")\b"
            for match in re.finditer(expression, text or "", re.IGNORECASE):
                findings.append({"type": detection_type, "value": match.group(0), "start": match.start(), "end": match.end(), "source": "business", "category": "business_confidential"})
        return findings


def detect_confidential_content(text: str) -> list[dict[str, Any]]:
    """Compatibility function for the original public detector API."""
    return ConfidentialBusinessDetector().detect(text)
