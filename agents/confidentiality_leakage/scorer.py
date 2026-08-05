"""Deterministic document-level risk scoring."""

from __future__ import annotations

from collections import Counter
from math import exp
from typing import Dict, Iterable, Tuple

WEIGHTS: Dict[str, int] = {
    "HIGH": 3,
    "MEDIUM": 2,
    "CONTEXT_DEPENDENT": 1,
}

RISK_LEVELS: Tuple[Tuple[int, int, str], ...] = (
    (0, 19, "LOW"),
    (20, 49, "MEDIUM"),
    (50, 74, "HIGH"),
    (75, 100, "CRITICAL"),
)


def _risk_level(score: int) -> str:
    for low, high, label in RISK_LEVELS:
        if low <= score <= high:
            return label
    return "CRITICAL"


def score_confidentiality(findings: Iterable[Dict[str, object]]) -> Dict[str, object]:
    """Return a capped 0-100 risk score and discrete risk level."""

    counts = Counter(str(finding.get("sensitivity", "CONTEXT_DEPENDENT")) for finding in findings)
    high = counts.get("HIGH", 0)
    medium = counts.get("MEDIUM", 0)
    context = counts.get("CONTEXT_DEPENDENT", 0)

    if (high + medium + context) <= 0:
        return {"risk_score": 0, "risk_level": "LOW"}

    # Saturating components keep the score bounded and prevent context-only
    # entities from dominating large legal documents.
    high_component = 60.0 * (1.0 - exp(-high / 1.5))
    medium_component = 30.0 * (1.0 - exp(-medium / 3.0))
    context_component = 10.0 * (1.0 - exp(-context / 15.0))

    score = int(round(min(100.0, high_component + medium_component + context_component)))
    return {"risk_score": score, "risk_level": _risk_level(score)}
