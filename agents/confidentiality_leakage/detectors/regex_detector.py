"""Structured identifier and credential detector."""

from __future__ import annotations

import re
from typing import Any

from .patterns import PATTERNS


def _valid_luhn(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    checksum = sum((digit * 2 - 9 if digit * 2 > 9 else digit * 2) if index % 2 == len(digits) % 2 else digit for index, digit in enumerate(digits))
    return checksum % 10 == 0


class RegexDetector:
    """Detect formatted identifiers and secrets without classifying prose."""

    def detect(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        type_names = {"PAN": "PAN_NUMBER", "AADHAAR": "AADHAAR_NUMBER", "PASSPORT": "PASSPORT_NUMBER", "DRIVING_LICENSE": "DRIVING_LICENSE_NUMBER"}
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(text or ""):
                if name == "PHONE" and re.fullmatch(r"\d{4}[ -]?\d{4}[ -]?\d{4}", match.group(0)):
                    continue
                if name == "CREDIT_CARD" and not _valid_luhn(match.group(0)):
                    continue
                if name == "PHONE" and len(re.sub(r"\D", "", match.group(0))) < 10:
                    continue
                if name == "POSTAL_CODE" and not re.search(r"(?i)(?:pin|postal|zip|address|office).{0,30}" + re.escape(match.group(0)), text[max(0, match.start() - 40):match.end() + 1]):
                    continue
                findings.append({"type": type_names.get(name, "PHONE_NUMBER" if name == "PHONE" else name), "value": match.group(0), "start": match.start(), "end": match.end(), "source": "regex", "category": "personal_data"})
        return findings


def detect_regex_sensitive_info(text: str) -> list[dict[str, Any]]:
    """Compatibility function for the original public detector API."""
    return RegexDetector().detect(text)
