import re
from typing import Dict, List, Any


# -----------------------------
# Known / allowed legal authorities (minimal, expandable)
# -----------------------------

KNOWN_LAWS = {
    "computer fraud and abuse act",
    "information technology act",
    "indian penal code",
    "computer misuse act",
    "criminal code of canada",
    "general data protection regulation",
    "cybersecurity act",
}

# Common hallucination-style law name patterns
SUSPICIOUS_TERMS = [
    "supreme",
    "fundamental",
    "attribution",
    "universal",
    "global cyber",
    "constitutional cyber",
]


# -----------------------------
# Fabricated legal authority detection (STEP 1)
# -----------------------------

def detect_fabricated_legal_authority(answer: str) -> List[Dict[str, Any]]:
    """
    Detect references to fabricated, suspicious, or unverifiable legal authorities.
    This is a Tier-5 hallucination check.
    """

    signals: List[Dict[str, Any]] = []

    # Detect capitalized law-like phrases
    matches = re.findall(
        r"([A-Z][A-Za-z\s]+?\s(?:Act|Law|Directive|Regulation|Code))",
        answer
    )

    for match in matches:
        law_name = match.lower().strip()

        # Strong hallucination smell
        if any(term in law_name for term in SUSPICIOUS_TERMS):
            signals.append({
                "signal": "Fabricated or suspicious legal authority detected",
                "severity": 5,
                "suggested_fix": (
                    "Remove reference to non-existent or suspiciously named legal authority "
                    "and replace with a high-level legal description"
                )
            })
            continue

        # Unverifiable / unknown law
        if law_name not in KNOWN_LAWS:
            signals.append({
                "signal": "Unverifiable legal authority referenced",
                "severity": 5,
                "suggested_fix": (
                    "Avoid naming specific statutes; describe the legal principle instead"
                )
            })

    return signals


# -----------------------------
# Existing verifier entrypoint
# -----------------------------

def verify_answer(
    question: str,
    answer: str,
    jurisdiction: str,
    multi_jurisdiction: bool = False
) -> Dict[str, Any]:
    """
    Verify the generated answer for hallucinations, inconsistencies,
    and unsafe legal claims.
    """

    hallucination_signals: List[Dict[str, Any]] = []

    # -----------------------------
    # STEP 1: Fabricated authority detection (HARD FAIL)
    # -----------------------------
    fabricated_signals = detect_fabricated_legal_authority(answer)
    if fabricated_signals:
        return {
            "verification": "FAILED",
            "hallucination_signals": fabricated_signals
        }

    # -----------------------------
    # Existing / softer checks
    # -----------------------------

    lowered = answer.lower()

    # Overly absolute language
    if any(word in lowered for word in ["always", "never", "guaranteed", "automatically"]):
        hallucination_signals.append({
            "signal": "Overly absolute legal language",
            "severity": 1,
            "suggested_fix": "Use conditional or qualified legal phrasing"
        })

    # Jurisdictional mismatch hints
    if jurisdiction == "eu" and any(word in lowered for word in ["prison", "imprisonment"]):
        hallucination_signals.append({
            "signal": "EU law treated as criminal law",
            "severity": 4,
            "suggested_fix": (
                "Clarify that EU law harmonizes rules but criminal penalties "
                "are imposed by member states"
            )
        })

    # Final decision
    if any(sig["severity"] >= 4 for sig in hallucination_signals):
        return {
            "verification": "FAILED",
            "hallucination_signals": hallucination_signals
        }

    return {
        "verification": "PASSED",
        "hallucination_signals": hallucination_signals
    }
