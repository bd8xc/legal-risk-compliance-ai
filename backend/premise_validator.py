import re
from typing import Dict, List

# Known fake / suspicious law name patterns
FAKE_LAW_PATTERNS = [
    r"supreme .* act",
    r"federal internet crimes act",
    r"global cybersecurity act",
    r"international hacking act",
]

# Laws that are jurisdiction-bound
JURISDICTION_LAW_MAP = {
    "india": ["indian penal code", "ipc"],
    "uk": ["indian penal code", "ipc"],
    "us": ["indian penal code", "ipc"],
}

def validate_premise(
    question: str,
    jurisdiction: str,
    domains: List[str]
) -> Dict[str, str]:
    """
    Strict premise validation.
    Blocks invalid assumptions BEFORE LLM invocation.
    """

    q = question.lower()

    # ---- 1. Fake / fabricated legal authority ----
    for pattern in FAKE_LAW_PATTERNS:
        if re.search(pattern, q):
            return {
                "status": "premise_invalid",
                "reason": "The question assumes a law that does not exist.",
                "suggested_action": (
                    "Please rephrase your question without relying on a non-existent statute."
                )
            }

    # ---- 2. Jurisdiction-law mismatch (hard contradiction) ----
    for jur, laws in JURISDICTION_LAW_MAP.items():
        if jurisdiction != "india":
            for law in laws:
                if law in q:
                    return {
                        "status": "premise_invalid",
                        "reason": (
                            f"The referenced law applies to a different jurisdiction "
                            f"and cannot be applied under {jurisdiction.upper()} law."
                        ),
                        "suggested_action": (
                            "Please align the law and jurisdiction correctly."
                        )
                    }

    # ---- 3. EU criminal authority error ----
    if jurisdiction == "eu":
        if re.search(r"\b(prison|jail|sentenced|imprisoned)\b", q):
            return {
                "status": "premise_invalid",
                "reason": (
                    "EU law does not directly impose criminal penalties such as imprisonment."
                ),
                "suggested_action": (
                    "Please ask about how EU law requires member states to regulate cybercrime."
                )
            }

    # ---- 4. Constitution-as-statute error (US) ----
    if jurisdiction == "us":
        if "constitution" in q and "hacking" in q:
            return {
                "status": "premise_invalid",
                "reason": (
                    "The U.S. Constitution does not directly criminalize conduct."
                ),
                "suggested_action": (
                    "Please ask about federal or state statutes regulating hacking."
                )
            }

    return {"status": "premise_valid"}
