# ldi/processing/semantic_repair.py
import re

def semantic_cleanup(text: str) -> str:
    """
    Advanced semantic text repair engine.
    Aggressively purges unpopulated template markers, spaced dots, broken line paths,
    and bullet noise artifacts from OCR/PDF extraction layers.
    """
    if not text or not text.strip():
        return ""

    # 🚫 1. Scrub spaced-out template blanks (e.g., '_ _ _ _', '_______')
    text = re.compile(r'_{2,}').sub(' ', text)
    text = re.compile(r'(_\s){2,}').sub(' ', text)

    # 🚫 2. Scrub spaced-out dot leaders and legal text trails (e.g., '. . . . . .')
    text = re.compile(r'\.{2,}').sub(' ', text)
    text = re.compile(r'(\.\s){2,}').sub(' ', text)

    # 🚫 3. Scrub hyphen lines and decorative border divider noise (e.g., '- - - - -')
    text = re.compile(r'-{2,}').sub(' ', text)
    text = re.compile(r'(-\s){2,}').sub(' ', text)

    # 🚫 4. Clean up trailing line anomalies left near numerical sequences (e.g., '_____ . 2024')
    # This specifically catches standalone dots hanging onto structural years or boundaries
    text = re.compile(r'\s+\.\s+(?=\d{4})').sub(' ', text)

    # ✨ 5. Final structural polish
    # Replace all whitespace variations with clean standalone spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text