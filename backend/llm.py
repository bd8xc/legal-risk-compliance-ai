import requests
import json
from typing import List

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"


def build_prompt(
    question: str,
    domains: List[str],
    jurisdiction: str,
    jurisdiction_reason: str
) -> str:
    """
    Build a domain-aware and jurisdiction-aware prompt.
    Prevents statute hallucination for general guidance questions.
    """

    domain_context = ", ".join(domains) if domains else "general law"

    # ---- Explicit jurisdiction transparency ----
    if "defaulted" in jurisdiction_reason.lower():
        jurisdiction_intro = (
            f"Since no country was specified or clearly recognized, "
            f"this explanation is provided under {jurisdiction.upper()} law by default."
        )
    else:
        jurisdiction_intro = (
            f"This explanation is provided under {jurisdiction.upper()} law."
        )

    # ---- Jurisdiction framing (NO hard citations) ----
    if jurisdiction == "india":
        law_context = (
            "Base the explanation on general principles commonly applied under Indian law."
        )
    elif jurisdiction == "us":
        law_context = (
            "Base the explanation on general principles commonly applied under United States law."
        )
    elif jurisdiction == "uk":
        law_context = (
            "Base the explanation on general principles commonly applied under United Kingdom law."
        )
    elif jurisdiction == "eu":
        law_context = (
            "Base the explanation on general principles of EU legal harmonization "
            "and member-state responsibility."
        )
    elif jurisdiction == "canada":
        law_context = (
            "Base the explanation on general principles commonly applied under Canadian law."
        )
    elif jurisdiction == "china":
        law_context = (
            "Base the explanation on general principles commonly applied under Chinese law."
        )
    else:
        law_context = "Provide a jurisdiction-agnostic legal explanation."

    # ---- Domain specialization ----
    if "criminal_law" in domains and "cyber_law" in domains:
        role = "You are a legal assistant specializing in cybercrime and criminal law."
    elif "criminal_law" in domains:
        role = "You are a legal assistant specializing in criminal law."
    elif "contract_law" in domains:
        role = "You are a legal assistant specializing in contract law."
    elif "employment_law" in domains:
        role = "You are a legal assistant specializing in employment law."
    else:
        role = "You are a legal assistant."

    # ---- Safety instructions (CRITICAL) ----
    safety_rules = (
        "IMPORTANT RULES:\n"
        "- If the question asks for general guidance, checklists, or what to look into,\n"
        "  DO NOT cite statute names, section numbers, or act titles.\n"
        "- Explain legal principles, factors, and considerations at a high level.\n"
        "- Only mention specific laws if the question explicitly asks for them.\n"
        "- Do not invent or guess legal authorities.\n"
    )

    return (
        f"{role}\n"
        f"{jurisdiction_intro}\n"
        f"{law_context}\n"
        "Do not provide legal advice. Provide general informational guidance only.\n"
        f"{safety_rules}\n"
        f"Question: {question}\n"
        "Answer:"
    )


def generate_legal_answer(
    question: str,
    domains: List[str],
    jurisdiction: str,
    jurisdiction_reason: str
) -> str:
    """
    Calls Ollama locally using streaming to avoid timeouts.
    Fully verifier-compatible.
    """

    prompt = build_prompt(
        question,
        domains,
        jurisdiction,
        jurisdiction_reason
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
