"""Regex-based detector for structured sensitive information."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Pattern


EMAIL_RE: Pattern[str] = re.compile(
    r"(?<![\w.+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![\w-])"
)
PHONE_RE: Pattern[str] = re.compile(
    r"(?<!\d)(?:\+?91[\s-]?)?(?:\d{5}[\s-]?\d{5}|\d{10}|(?:\(?\d{3,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{4})(?!\d)"
)
AADHAAR_RE: Pattern[str] = re.compile(r"(?<!\d)(\d{4}[\s-]?\d{4}[\s-]?\d{4})(?!\d)")
PAN_RE: Pattern[str] = re.compile(r"(?<![A-Z0-9])([A-Z]{5}[0-9]{4}[A-Z])(?![A-Z0-9])")
BANK_ACCOUNT_RE: Pattern[str] = re.compile(r"(?<!\d)(?:A/c\s*)?(?:Account(?: Number)?[:\s-]*)?(\d{9,18})(?!\d)", re.I)
IBAN_RE: Pattern[str] = re.compile(r"\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b")
CREDIT_CARD_RE: Pattern[str] = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
IP_ADDRESS_RE: Pattern[str] = re.compile(
    r"(?<!\d)(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}(?!\d)"
)
POSTAL_CODE_RE: Pattern[str] = re.compile(r"\b[1-9][0-9]{5}\b")
LEGAL_ENTITY_RE: Pattern[str] = re.compile(
    r"\b([A-Z][A-Z0-9&.,'\- ]{2,100}?(?:PRIVATE\s+LIMITED|PVT\.?\s+LTD\.?|LIMITED|LTD\.?|LLP|INC\.?|CORP\.?|CORPORATION))\b",
    re.I,
)
ADDRESS_RE: Pattern[str] = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.,'()\- ]{3,120}?(?:Road|Rd\.?|Street|St\.?|Lane|Ln\.?|Avenue|Ave\.?|Marg|Nagar|Estate|House|Building|Block|Floor)\b(?:[A-Za-z0-9.,'()\- ]{0,120})",
    re.I,
)


def _normalize_value(value: str) -> str:
    return re.sub(r"[\s-]", "", value.strip())


def _luhn_is_valid(number: str) -> bool:
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _build_detection(match: re.Match[str], detection_type: str, source: str) -> Dict[str, Any]:
    return {
        "type": detection_type,
        "value": match.group(0),
        "start": match.start(),
        "end": match.end(),
        "source": source,
    }


def detect_regex_sensitive_info(text: str) -> List[Dict[str, Any]]:
    """Return conservative structured sensitive-information detections."""

    if not text:
        return []

    detections: List[Dict[str, Any]] = []

    for match in EMAIL_RE.finditer(text):
        detections.append(_build_detection(match, "EMAIL", "regex"))

    for match in PHONE_RE.finditer(text):
        detections.append(_build_detection(match, "PHONE_NUMBER", "regex"))

    for match in AADHAAR_RE.finditer(text):
        detections.append(_build_detection(match, "AADHAAR_NUMBER", "regex"))

    for match in PAN_RE.finditer(text):
        detections.append(_build_detection(match, "PAN_NUMBER", "regex"))

    for match in BANK_ACCOUNT_RE.finditer(text):
        detections.append(_build_detection(match, "BANK_ACCOUNT", "regex"))

    for match in IBAN_RE.finditer(text):
        detections.append(_build_detection(match, "IBAN", "regex"))

    for match in CREDIT_CARD_RE.finditer(text):
        normalized = _normalize_value(match.group(0))
        if _luhn_is_valid(normalized):
            detections.append(_build_detection(match, "CREDIT_CARD", "regex"))

    for match in IP_ADDRESS_RE.finditer(text):
        detections.append(_build_detection(match, "IP_ADDRESS", "regex"))

    for match in POSTAL_CODE_RE.finditer(text):
        detections.append(_build_detection(match, "POSTAL_CODE", "regex"))

    for match in LEGAL_ENTITY_RE.finditer(text):
        detections.append(_build_detection(match, "ORG", "regex"))

    for match in ADDRESS_RE.finditer(text):
        detections.append(_build_detection(match, "ADDRESS", "regex"))

    return detections
