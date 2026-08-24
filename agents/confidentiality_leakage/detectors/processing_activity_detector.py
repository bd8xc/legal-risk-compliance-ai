"""Detector for personal-data processing operations."""

from __future__ import annotations

import re
from typing import Any

from .dictionaries import PROCESSING_ACTIVITIES


class ProcessingActivityDetector:
    """Return each processing verb or transfer concept with clause context."""

    def detect(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        findings = []
        expression = r"\b(?:" + "|".join(re.escape(term) for term in PROCESSING_ACTIVITIES) + r")\b"
        for match in re.finditer(expression, text or "", re.IGNORECASE):
            findings.append({"type": "PROCESSING_ACTIVITY", "value": match.group(0), "activity": match.group(0).lower(), "start": match.start(), "end": match.end(), "source": "processing", "category": "processing_activity"})
        return findings
