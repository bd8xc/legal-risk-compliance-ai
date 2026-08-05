"""Rule-based detector for confidential business content patterns."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Pattern


CONFIDENTIAL_CONTENT_PATTERNS: List[tuple[str, Pattern[str]]] = [
    (
        "CONFIDENTIAL_TRADE_SECRET",
        re.compile(r"\b(trade secret|proprietary information|intellectual property|source code|algorithm)\b", re.I),
    ),
    (
        "CONFIDENTIAL_FINANCIAL",
        re.compile(r"\b(costs?|profits?|pricing strategy|budgets?|turnover|market share|financial information|projections?)\b", re.I),
    ),
    (
        "CONFIDENTIAL_CUSTOMER",
        re.compile(r"\b(customer lists?|clients?|subscribers?|vendor lists?|sales plans?)\b", re.I),
    ),
    (
        "CONFIDENTIAL_STRATEGY",
        re.compile(r"\b(business plans?|strategy|strategies|research|work in progress|future development|forecasts?)\b", re.I),
    ),
    (
        "CONFIDENTIAL_PERSONNEL",
        re.compile(r"\b(personnel information|employee data|hr records?)\b", re.I),
    ),
]


def detect_confidential_content(text: str) -> List[Dict[str, Any]]:
    """Detect legal/business confidentiality phrases using local rules only."""

    if not text:
        return []

    detections: List[Dict[str, Any]] = []
    for content_type, pattern in CONFIDENTIAL_CONTENT_PATTERNS:
        # Keep one representative match per content category per clause to avoid
        # long legal definition sections inflating risk disproportionately.
        match = pattern.search(text)
        if not match:
            continue
        detections.append(
            {
                "type": content_type,
                "value": match.group(0),
                "start": match.start(),
                "end": match.end(),
                "source": "rules",
            }
        )
    return detections
