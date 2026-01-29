from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
import re

from issue_extractor import extract_domains
from jurisdiction import resolve_jurisdiction
from llm import generate_legal_answer
from confidence import (
    classification_confidence,
    domain_confidence,
    jurisdiction_confidence
)
from logger import log_request
from verifier import verify_answer
from utils import normalize_text
from premise_validator import validate_premise
from feedback import build_feedback


app = FastAPI(title="Legal Question Backend")

# ------------------
# Models
# ------------------

class QuestionRequest(BaseModel):
    question: str
    generate_answer: bool = False
    jurisdiction: Optional[str] = None


class QuestionResponse(BaseModel):
    question: str
    classification: str
    classification_confidence: float
    domains: List[str]
    domain_confidence: Dict[str, float]
    jurisdiction: str
    jurisdiction_reason: str
    jurisdiction_confidence: float
    status: str
    timestamp: str
    verification: Optional[str] = None
    hallucination_signals: Optional[List[Dict[str, Any]]] = None
    feedback: Optional[Dict[str, str]] = None
    answer: Optional[str] = None


# ------------------
# Legal classification gate
# ------------------

LEGAL_KEYWORDS = [
    "law", "legal", "court", "crime", "criminal", "civil",
    "contract", "agreement", "document", "sign", "signing",
    "rights", "liability", "act", "section",
    "ipc", "fir", "bail", "arrest", "trial", "judgment",
    "computer", "cyber", "unauthorized", "access", "hacking"
]


def is_legal_question(question: str) -> bool:
    q = normalize_text(question)
    return any(word in q.split() for word in LEGAL_KEYWORDS)


# ------------------
# Routes
# ------------------

@app.get("/")
def health_check():
    return {"status": "running"}


@app.post("/ask", response_model=QuestionResponse)
def ask(payload: QuestionRequest):
    question = payload.question
    q_norm = normalize_text(question)

    # ---- Classification ----
    is_legal = is_legal_question(question)
    classification = "legal" if is_legal else "general"

    # ---- Domain extraction ----
    domains = extract_domains(question) if is_legal else []

    # ---- Jurisdiction resolution ----
    jurisdiction, jurisdiction_reason = resolve_jurisdiction(
        question,
        payload.jurisdiction
    )

    response: Dict[str, Any] = {
        "question": question,
        "classification": classification,
        "classification_confidence": classification_confidence(is_legal),
        "domains": domains,
        "domain_confidence": domain_confidence(domains),
        "jurisdiction": jurisdiction,
        "jurisdiction_reason": jurisdiction_reason,
        "jurisdiction_confidence": jurisdiction_confidence(jurisdiction_reason),
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # ======================================================
    # STEP 2 — Premise validation (SEMANTIC-FIRST)
    # ======================================================
    if classification == "legal":
        premise_check = validate_premise(
            question=question,
            jurisdiction=jurisdiction,
            domains=domains
        )

        if premise_check["status"] != "premise_valid":
            response.update({
                "status": premise_check["status"],
                "verification": "FAILED",
                "answer": None,
                "hallucination_signals": [{
                    "signal": premise_check["reason"],
                    "severity": 5,
                    "suggested_fix": premise_check["suggested_action"]
                }],
                "feedback": build_feedback(
                    premise_check["reason"],
                    premise_check["suggested_action"]
                )
            })
            return response

    # ======================================================
    # HARD SAFETY — explicit jurisdiction but unresolved
    # ======================================================
    if (
        classification == "legal"
        and jurisdiction_reason.startswith("No jurisdiction")
        and re.search(
            r"\b(us|uk|eu|united states|united kingdom|european union|canada|china)\b",
            q_norm
        )
    ):
        response.update({
            "status": "jurisdiction_unresolved",
            "verification": "FAILED",
            "answer": None,
            "hallucination_signals": [{
                "signal": "Explicit jurisdiction mentioned but not resolved",
                "severity": 4,
                "suggested_fix": "Improve jurisdiction detection before answering"
            }],
            "feedback": build_feedback(
                "Explicit jurisdiction mentioned but not resolved",
                "Specify a recognized country or remove jurisdictional assumptions."
            )
        })
        return response

    # ---- LLM invocation ----
    llm_called = False

    if payload.generate_answer and classification == "legal":
        llm_called = True

        candidate = generate_legal_answer(
            question,
            domains,
            jurisdiction,
            jurisdiction_reason
        )

        verification = verify_answer(
            question,
            candidate,
            jurisdiction,
            multi_jurisdiction=bool(
                re.search(r"\b(and|or|vs|versus)\b", q_norm)
            )
        )

        response["verification"] = verification["verification"]
        response["hallucination_signals"] = verification["hallucination_signals"]

        if verification["verification"] == "PASSED":
            response["answer"] = candidate
        else:
            response["status"] = "verification_failed"
            response["answer"] = None

    # ---- Logging ----
    log_request({
        "question": question,
        "classification": classification,
        "domains": domains,
        "jurisdiction": jurisdiction,
        "llm_called": llm_called,
        "verification": response.get("verification"),
    })
    
    return response
