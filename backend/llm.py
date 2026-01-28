import requests
import json
from typing import List, Optional, Dict

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"


def build_prompt(
    question: str,
    domains: List[str],
    jurisdiction: str,
    jurisdiction_reason: str,
    grounding: Optional[Dict] = None
) -> str:
    """
    Build a domain-aware, jurisdiction-aware, and GROUNDED prompt.
    """

    domain_context = ", ".join(domains) if domains else "general law"

    # ---- Explicit jurisdiction transparency ----
    if "defaulted" in jurisdiction_reason.lower():
        jurisdiction_intro = (
            f"Since no country was specified or recognized in the question, "
            f"this explanation is provided under {jurisdiction.upper()} law by default."
        )
    else:
        jurisdiction_intro = (
            f"This explanation is provided under {jurisdiction.upper()} law."
        )

    # ---- Grounding constraints (Tier 4) ----
    grounding_text = ""
    if grounding:
        for domain, info in grounding.items():
            grounding_text += (
                f"\nDomain: {domain}\n"
                f"Legal category: {info['category']}\n"
                f"Allowed concepts: {', '.join(info['allowed_concepts'])}\n"
                f"Do NOT reference: {', '.join(info['forbidden'])}\n"
            )

    # ---- Domain specialization ----
    if "criminal_law" in domains and "cyber_law" in domains:
        role = "You are a legal assistant specializing in cyber crime and criminal law."
    elif "criminal_law" in domains:
        role = "You are a legal assistant specializing in criminal law."
    elif "contract_law" in domains:
        role = "You are a legal assistant specializing in contract law."
    elif "employment_law" in domains:
        role = "You are a legal assistant specializing in employment law."
    else:
        role = "You are a legal assistant."

    return (
        f"{role}\n"
        f"{jurisdiction_intro}\n"
        f"{grounding_text}\n"
        "Rules:\n"
        "- Provide general informational guidance only\n"
        "- Do NOT cite statute numbers or section identifiers\n"
        "- Use high-level legal descriptions\n"
        "- Stay within the legal category provided\n"
        "- Do not mention laws from other jurisdictions\n\n"
        f"Question: {question}\n"
        "Answer:"
    )


def generate_legal_answer(
    question: str,
    domains: List[str],
    jurisdiction: str,
    jurisdiction_reason: str,
    grounding: Optional[Dict] = None
) -> str:
    """
    Calls Ollama locally using streaming to avoid timeouts.
    Fully grounded (Tier 4).
    """

    prompt = build_prompt(
        question,
        domains,
        jurisdiction,
        jurisdiction_reason,
        grounding=grounding
    )

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        stream=True,
        timeout=None
    )
    response.raise_for_status()

    answer_parts = []

    for line in response.iter_lines():
        if not line:
            continue

        data = json.loads(line.decode("utf-8"))

        if "response" in data:
            answer_parts.append(data["response"])

        if data.get("done", False):
            break

    return "".join(answer_parts).strip()
