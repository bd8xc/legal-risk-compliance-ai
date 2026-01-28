from typing import List, Dict

def classification_confidence(is_legal: bool) -> float:
    # Simple but honest
    return 0.95 if is_legal else 0.85


def domain_confidence(domains: List[str]) -> Dict[str, float]:
    """
    Assign confidence per detected domain.
    Rule-based confidence (transparent).
    """
    confidence = {}

    for domain in domains:
        if domain in ["criminal_law", "cyber_law"]:
            confidence[domain] = 0.9
        elif domain in ["contract_law", "employment_law"]:
            confidence[domain] = 0.85
        else:
            confidence[domain] = 0.8

    return confidence


def jurisdiction_confidence(reason: str) -> float:
    if "explicitly provided" in reason.lower():
        return 0.95
    if "inferred" in reason.lower():
        return 0.85
    if "defaulted" in reason.lower():
        return 0.7
    return 0.6
