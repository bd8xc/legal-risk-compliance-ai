"""Sensitivity classification and deduplication logic."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

CRITICAL_TYPES = {
    "API_KEY", "PRIVATE_KEY", "JWT_TOKEN", "ACCESS_TOKEN", "OAUTH_TOKEN", "SECRET_KEY",
    "DATABASE_PASSWORD", "CONNECTION_STRING", "AWS_ACCESS_KEY", "AZURE_KEY", "GOOGLE_API_KEY",
    "BANK_ACCOUNT", "CREDIT_CARD", "MEDICAL_HISTORY", "DIAGNOSIS", "PRESCRIPTION", "BIOMETRIC_DATA",
    "CONFIDENTIAL_TRADE_SECRET", "CONFIDENTIAL_FINANCIAL", "CONFIDENTIAL_CREDENTIAL",
}
HIGH_TYPES = {
    "AADHAAR_NUMBER",
    "PAN_NUMBER",
    "BANK_ACCOUNT",
    "IBAN",
    "CREDIT_CARD",
    "CONFIDENTIAL_TRADE_SECRET",
    "CONFIDENTIAL_FINANCIAL", "PASSPORT", "PASSPORT_NUMBER", "DRIVING_LICENSE", "DRIVING_LICENSE_NUMBER", "GST", "TAX_ID", "SALARY",
}
MEDIUM_TYPES = {
    "EMAIL",
    "PHONE_NUMBER",
    "IP_ADDRESS",
    "ADDRESS",
    "POSTAL_CODE",
    "CONFIDENTIAL_CUSTOMER",
    "CONFIDENTIAL_STRATEGY",
    "CONFIDENTIAL_PERSONNEL",
}
CONTEXT_TYPES = {"ORG", "GPE", "LOC", "MONEY"}


def sensitivity_for_detection(detection_type: str) -> str:
    if detection_type in CRITICAL_TYPES:
        return "CRITICAL"
    if detection_type in HIGH_TYPES:
        return "HIGH"
    if detection_type in MEDIUM_TYPES:
        return "MEDIUM"
    if detection_type in {"ORG", "GPE", "LOC", "MONEY", "DATE"}:
        return "CONTEXT_DEPENDENT"
    return "LOW"


def _priority(finding: Dict[str, Any]) -> Tuple[int, int]:
    source_rank = 0 if finding.get("source") != "ner" else 1
    sensitivity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "CONTEXT_DEPENDENT": 4}.get(
        finding.get("sensitivity", "CONTEXT_DEPENDENT"),
        5,
    )
    return source_rank, sensitivity_rank


def _overlaps(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    return not (left["end"] <= right["start"] or right["end"] <= left["start"])


def classify_findings(findings: Iterable[Dict[str, Any]], clause_id: str = "", section: str = "") -> List[Dict[str, Any]]:
    """Attach sensitivity and remove duplicates / overlapping weaker findings."""

    classified: List[Dict[str, Any]] = []
    for finding in findings:
        item = dict(finding)
        item["sensitivity"] = sensitivity_for_detection(str(item.get("type", "")))
        item["clause_id"] = clause_id
        item["section"] = section
        classified.append(item)

    classified.sort(key=lambda item: (item["start"], item["end"], _priority(item)))
    deduped: List[Dict[str, Any]] = []

    for item in classified:
        replaced = False
        for index, kept in enumerate(list(deduped)):
            same_span = item["start"] == kept["start"] and item["end"] == kept["end"]
            same_identity = item["type"] == kept["type"] and item["value"] == kept["value"]
            if same_span or same_identity or _overlaps(item, kept):
                if _priority(item) < _priority(kept):
                    deduped[index] = item
                replaced = True
                break
        if not replaced:
            deduped.append(item)

    deduped.sort(key=lambda item: (item["start"], item["end"], item["type"], item["value"]))
    return deduped
