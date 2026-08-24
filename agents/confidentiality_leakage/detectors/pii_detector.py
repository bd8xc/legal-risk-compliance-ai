"""Detector for labelled personal information."""

from __future__ import annotations

import re
from typing import Any

_LABELS = {
    "DOB": r"\b(?:date of birth|dob|birth date)\s*[:=-]?\s*[^,;.\n]+",
    "AGE": r"\b(?:age)\s*[:=-]?\s*\d{1,3}\b",
    "GENDER": r"\b(?:gender|sex)\s*[:=-]?\s*(?:male|female|non-binary|other)\b",
    "NATIONALITY": r"\b(?:nationality|citizenship)\s*[:=-]?\s*[A-Za-z -]+",
    "ADDRESS": r"\b(?:residential|home|registered|mailing) address\s*[:=-]?\s*[^;\n]+",
    "SALARY": r"\b(?:salary|compensation|remuneration|pay)\s*[:=-]?\s*(?:[$€£₹]\s*)?[\d,]+(?:\.\d+)?",
    "EMERGENCY_CONTACT": r"\b(?:emergency contact|next of kin)\s*[:=-]?\s*[^;\n]+",
    "MARITAL_STATUS": r"\bmarital status\s*[:=-]?\s*[A-Za-z-]+",
    "DEPENDENT_INFORMATION": r"\bdependents?\s*[:=-]?\s*[^;\n]+",
    "EMPLOYEE_NUMBER": r"\b(?:employee|emp)\s*(?:number|no|id)\s*[:#=-]?\s*[A-Z0-9/-]+",
    "PAYROLL_ID": r"\bpayroll\s*(?:id|number|no)\s*[:#=-]?\s*[A-Z0-9/-]+",
}


class PIIDetector:
    """Detect personal attributes only when a clear label provides context."""

    def detect(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        findings = []
        for detection_type, expression in _LABELS.items():
            for match in re.finditer(expression, text or "", re.IGNORECASE):
                findings.append({"type": detection_type, "value": match.group(0), "start": match.start(), "end": match.end(), "source": "pii", "category": "personal_data"})
        return findings
