import re
from typing import Optional, Tuple
from utils import normalize_text


def infer_jurisdiction(question: str) -> Tuple[str, str]:
    q = normalize_text(question)

    if re.search(r"\b(us|usa|u s|united states)\b", q):
        return "us", "Inferred from United States–specific terms in the question"

    if re.search(r"\b(uk|u k|united kingdom|britain|england)\b", q):
        return "uk", "Inferred from UK-specific terms in the question"

    if re.search(r"\b(eu|e u|european union)\b", q):
        return "eu", "Inferred from EU-specific terms in the question"

    if re.search(r"\b(india|indian|ipc|it act)\b", q):
        return "india", "Inferred from India-specific legal terms in the question"

    return "india", "No jurisdiction recognized in the query; defaulted to India"


def resolve_jurisdiction(
    question: str,
    provided_jurisdiction: Optional[str]
) -> Tuple[str, str]:
    if provided_jurisdiction:
        return provided_jurisdiction.lower(), "Explicitly provided in request"

    return infer_jurisdiction(question)
