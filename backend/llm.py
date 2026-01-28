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
    Explicitly states when a jurisdiction is defaulted.
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

    # ---- Jurisdiction-specific legal framing ----
    if jurisdiction == "india":
        law_context = (
            "Refer where relevant to the Information Technology Act, 2000 "
            "and the Indian Penal Code (IPC)."
        )
    elif jurisdiction == "us":
        law_context = (
            "Refer where relevant to United States federal law, "
            "including the Computer Fraud and Abuse Act (CFAA)."
        )
    elif jurisdiction == "eu":
        law_context = (
            "Refer where relevant to European Union regulations and directives, "
            "such as the GDPR."
        )
    elif jurisdiction == "canada":
        law_context = (
            "Refer where relevant to the Criminal Code of Canada "
            "and applicable federal statutes."
        )
    elif jurisdiction == "china":
        law_context = (
            "Refer where relevant to the Cybersecurity Law of the "
            "People’s Republic of China."
        )
    else:
        law_context = "Provide a general, jurisdiction-agnostic legal explanation."

    # ---- Domain specialization ----
    if "criminal_law" in domains and "cyber_law" in domains:
        role = (
            "You are a legal assistant specializing in cyber crime and criminal law."
        )
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
        f"{law_context}\n"
        "Do not provide legal advice. Provide general informational guidance only.\n\n"
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
    Domain + jurisdiction aware.
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
