import re

def normalize_text(text: str) -> str:
    """
    Normalize text for robust NLP matching:
    - lowercase
    - remove punctuation
    - normalize whitespace
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)   # remove punctuation
    text = re.sub(r"\s+", " ", text)       # collapse spaces
    return text.strip()
