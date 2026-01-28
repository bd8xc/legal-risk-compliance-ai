from typing import Dict, List
import re
from utils import normalize_text


SEVERITY = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

OVER_CERTAINTY_PATTERNS = [
    r"\balways\b",
    r"\bnever\b",
    r"\bguaranteed\b",
    r"\bwithout exception\b",
]

FAKE_AUTHORITY_PATTERNS = [
    r"\bsupreme court has ruled\b",
    r"\bsettled law\b",
    r"\bwell established\b",
]

STATUTE_PATTERN = re.compile(
    r"\b(section|sec|article)\s+\d+\b", re.IGNORECASE
)


def verify_answer(
    question: str,
    answer: str,
    jurisdiction: str,
    multi_jurisdiction: bool = False
) -> Dict:

    q = normalize_text(question)
    a = normalize_text(answer)

    signals: List[Dict] = []

    def add(signal, severity, fix):
        signals.append({
            "signal": signal,
            "severity": severity,
            "suggested_fix": fix
        })

    # Over-certainty
    if any(re.search(p, a) for p in OVER_CERTAINTY_PATTERNS):
        add(
            "Overly absolute legal language",
            SEVERITY["LOW"],
            "Use conditional or qualified legal phrasing"
        )

    # Fake authority
    if any(re.search(p, a) for p in FAKE_AUTHORITY_PATTERNS):
        add(
            "Unverifiable legal authority referenced",
            SEVERITY["HIGH"],
            "Remove uncited references to courts or precedents"
        )

    # Statute hallucination
    if STATUTE_PATTERN.search(a):
        add(
            "Specific statute numbers cited without verification",
            SEVERITY["CRITICAL"],
            "Replace statute numbers with high-level legal descriptions"
        )

    # Jurisdiction leakage
    leaks = {
        "india": ["cfaa", "united states", "uk law"],
        "us": ["ipc", "it act", "india"],
        "uk": ["cfaa", "ipc", "it act", "eu law"],
        "eu": ["ipc", "cfaa", "uk law"],
    }

    if any(w in a for w in leaks.get(jurisdiction, [])):
        add(
            "Jurisdictional inconsistency detected",
            SEVERITY["HIGH"],
            "Restrict legal analysis to the correct jurisdiction"
        )

    # EU category error
    if jurisdiction == "eu":
        if "gdpr" in a and any(w in a for w in ["crime", "criminal", "imprisonment"]):
            add(
                "EU law treated as criminal law",
                SEVERITY["CRITICAL"],
                "Clarify distinction between EU regulations and member-state criminal law"
            )

    # Topic drift
    overlap = len(set(q.split()) & set(a.split()))
    if overlap < 5:
        add(
            "Answer may not directly address the question",
            SEVERITY["MEDIUM"],
            "Refocus answer on the legal issue raised"
        )

    max_severity = max([s["severity"] for s in signals], default=0)

    return {
        "verification": "PASSED" if max_severity < SEVERITY["HIGH"] else "FAILED",
        "max_severity": max_severity,
        "hallucination_signals": signals
    }
