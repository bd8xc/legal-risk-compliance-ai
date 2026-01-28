from typing import Optional, Tuple

def infer_jurisdiction(question: str) -> Tuple[str, str]:
    q = question.lower()

    # India
    if any(word in q for word in ["india", "indian", "ipc", "it act", "crpc", "cpc"]):
        return "india", "Inferred from India-specific legal terms in the question"

    # United States
    if any(word in q for word in ["united states", "usa", "us law", "cfaa", "federal law"]):
        return "us", "Inferred from United States–specific legal terms in the question"

    # European Union
    if any(word in q for word in ["european union", "eu law", "gdpr"]):
        return "eu", "Inferred from European Union–specific legal terms in the question"

    # Canada
    if any(word in q for word in ["canada", "canadian", "criminal code of canada"]):
        return "canada", "Inferred from Canada-specific legal terms in the question"

    # China
    if any(word in q for word in ["china", "chinese", "prc law", "cybersecurity law of china"]):
        return "china", "Inferred from China-specific legal terms in the question"

    # Default
    return "india", "No jurisdiction recognized in the query; defaulted to India"


def resolve_jurisdiction(
    question: str,
    provided_jurisdiction: Optional[str]
) -> Tuple[str, str]:

    if provided_jurisdiction:
        return provided_jurisdiction.lower(), "Explicitly provided in request"

    return infer_jurisdiction(question)
