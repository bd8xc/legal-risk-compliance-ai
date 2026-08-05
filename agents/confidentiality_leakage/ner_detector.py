"""spaCy NER-based detector for potentially sensitive entities."""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Any, Dict, List

import spacy


LEGAL_BOILERPLATE_TERMS = {
    "agreement",
    "confidential information",
    "disclosing party",
    "recipient",
    "party",
    "parties",
    "purpose",
    "effective date",
    "clause",
    "clauses",
    "term",
    "notice",
    "notices",
    "attn",
    "address",
    "email",
    "name",
    "designation",
}

COMPANY_SUFFIXES = {
    "limited",
    "ltd",
    "private",
    "pvt",
    "inc",
    "corp",
    "corporation",
    "llc",
    "plc",
    "co",
}

ADDRESS_TERMS = {
    "road",
    "rd",
    "street",
    "st",
    "lane",
    "ln",
    "marg",
    "nagar",
    "estate",
    "house",
    "building",
    "floor",
    "block",
    "fort",
}


def _normalize_entity_value(value: str) -> str:
    value = (value or "").strip()
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = value.strip("\"'`“”‘’()[]{}")
    value = re.sub(r"[’']s\b", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value)
    return value


def _is_boilerplate_phrase(value: str) -> bool:
    lowered = value.lower().strip()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    lowered = re.sub(r"^(the|a|an)\s+", "", lowered)
    if lowered in LEGAL_BOILERPLATE_TERMS:
        return True
    if re.fullmatch(r"(?:either|neither|both|any|each)\s+party", lowered):
        return True
    if re.fullmatch(r"clauses?\s+[0-9]+(?:\s+[0-9]+)*", lowered):
        return True
    for term in LEGAL_BOILERPLATE_TERMS:
        if lowered.startswith(term + " "):
            return True
    if lowered.startswith("the ") and lowered[4:] in LEGAL_BOILERPLATE_TERMS:
        return True
    return False


def _tokenize_alpha(value: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z'.-]*", value)


def _is_probable_person(value: str) -> bool:
    if _is_boilerplate_phrase(value):
        return False
    tokens = _tokenize_alpha(value)
    if len(tokens) < 2:
        return False
    lowered_tokens = {token.lower() for token in tokens}
    if lowered_tokens.intersection(ADDRESS_TERMS):
        return False
    if lowered_tokens.intersection(LEGAL_BOILERPLATE_TERMS):
        return False

    titled_or_upper = sum(1 for token in tokens if token[:1].isupper() or token.isupper())
    return titled_or_upper >= 2


def _is_probable_org(value: str) -> bool:
    if _is_boilerplate_phrase(value):
        return False

    tokens = _tokenize_alpha(value)
    if not tokens:
        return False
    lowered_tokens = [token.lower() for token in tokens]

    if all(token in LEGAL_BOILERPLATE_TERMS for token in lowered_tokens):
        return False

    if any(token in ADDRESS_TERMS for token in lowered_tokens) and not any(token in COMPANY_SUFFIXES for token in lowered_tokens):
        return False

    if any(token in COMPANY_SUFFIXES for token in lowered_tokens):
        return True

    if value.lower().startswith("the ") and not any(token in COMPANY_SUFFIXES for token in lowered_tokens):
        return False

    # Accept common branded single-token ORGs like Google, Tata, Microsoft.
    if len(tokens) == 1 and len(tokens[0]) >= 4 and tokens[0][0].isupper():
        return True

    # Multi-token proper-noun phrase with at least one uppercase token.
    uppercase_tokens = sum(1 for token in tokens if token[:1].isupper() or token.isupper())
    return len(tokens) >= 2 and uppercase_tokens >= 1


def _is_probable_location(value: str) -> bool:
    return not _is_boilerplate_phrase(value)


def _is_probable_money(value: str) -> bool:
    if _is_boilerplate_phrase(value):
        return False
    return bool(re.search(r"[\d$€£₹]", value))


@lru_cache(maxsize=1)
def _load_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except OSError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is missing. Install it with: python -m spacy download en_core_web_sm"
        ) from exc


def detect_ner_sensitive_info(text: str) -> List[Dict[str, Any]]:
    """Return normalized NER detections from a single spaCy model load."""

    if not text:
        return []

    nlp = _load_nlp()
    doc = nlp(text)
    detections: List[Dict[str, Any]] = []

    entities = list(doc.ents)
    index = 0
    while index < len(entities):
        ent = entities[index]

        merged_start = ent.start_char
        merged_end = ent.end_char
        merged_text = ent.text
        merged_label = ent.label_

        # Merge adjacent ORG entities split by spaCy into a single company phrase.
        if merged_label == "ORG":
            next_index = index + 1
            while next_index < len(entities) and entities[next_index].label_ == "ORG":
                gap_text = text[merged_end:entities[next_index].start_char]
                if re.fullmatch(r"[\s,&/-]*", gap_text or ""):
                    merged_end = entities[next_index].end_char
                    merged_text = text[merged_start:merged_end]
                    next_index += 1
                    continue
                break
            index = next_index - 1

        if ent.label_ not in {"PERSON", "ORG", "GPE", "LOC", "MONEY"}:
            index += 1
            continue

        value = _normalize_entity_value(merged_text)
        if not value:
            index += 1
            continue

        if merged_label == "PERSON" and not _is_probable_person(value):
            index += 1
            continue
        if merged_label == "ORG" and not _is_probable_org(value):
            index += 1
            continue
        if merged_label in {"GPE", "LOC"} and not _is_probable_location(value):
            index += 1
            continue
        if merged_label == "MONEY" and not _is_probable_money(value):
            index += 1
            continue

        detections.append(
            {
                "type": merged_label,
                "value": value,
                "start": merged_start,
                "end": merged_end,
                "source": "ner",
            }
        )
        index += 1

    return detections
