from typing import Dict

def build_feedback(reason: str, suggested_fix: str) -> Dict[str, str]:
    """
    Step 3 feedback loop.
    No answering. No correction. Just guidance.
    """
    return {
        "reason": reason,
        "how_to_fix": suggested_fix,
        "example_rephrase": generate_example_rephrase(reason)
    }


def generate_example_rephrase(reason: str) -> str:
    """
    Deterministic examples based on failure type.
    No LLM usage.
    """
    reason = reason.lower()

    if "does not exist" in reason:
        return "Ask about applicable laws without naming a specific statute."

    if "different jurisdiction" in reason:
        return "Align the law and country, for example: 'Is hacking illegal in the UK?'"

    if "eu law does not directly impose" in reason:
        return "Ask how EU law influences member state cybercrime laws."

    if "constitution" in reason:
        return "Ask about federal or state statutes regulating hacking."

    return "Please rephrase the question with correct legal assumptions."
