from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from issue_extractor import extract_domains
from jurisdiction import resolve_jurisdiction
from llm import generate_legal_answer
from confidence import (
    classification_confidence,
    domain_confidence,
    jurisdiction_confidence
)
from logger import log_request

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
    domain_confidence: dict
    jurisdiction: str
    jurisdiction_reason: str
    jurisdiction_confidence: float
    status: str
    timestamp: str
    answer: Optional[str] = None


# ------------------
# Legal classification gate
# ------------------

LEGAL_KEYWORDS = [
    "law", "legal", "court", "crime", "criminal", "civil",
    "contract", "agreement", "document", "sign", "signing",
    "rights", "liability", "act", "section",
    "ipc", "fir", "bail", "arrest", "trial", "judgment",
    "computer", "cyber", "unauthorized", "access"
]

def is_legal_question(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in LEGAL_KEYWORDS)


# ------------------
# Routes
# ------------------

@app.get("/")
def health_check():
    return {"status": "running"}


@app.post("/ask", response_model=QuestionResponse)
def ask(payload: QuestionRequest):
    question = payload.question

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

    # ---- Build response ----
    response = {
        "question": question,
        "classification": classification,
        "classification_confidence": classification_confidence(is_legal),
        "domains": domains,
        "domain_confidence": domain_confidence(domains),
        "jurisdiction": jurisdiction,
        "jurisdiction_reason": jurisdiction_reason,
        "jurisdiction_confidence": jurisdiction_confidence(jurisdiction_reason),
        "status": "success",
        "timestamp": datetime.utcnow().isoformat()
    }

    # ---- LLM call (gated) ----
    llm_called = False
    if payload.generate_answer and classification == "legal":
        response["answer"] = generate_legal_answer(
            question,
            domains,
            jurisdiction,
            jurisdiction_reason
        )
        llm_called = True

    # ---- Structured logging ----
    log_request({
        "question": question,
        "classification": classification,
        "domains": domains,
        "jurisdiction": jurisdiction,
        "llm_called": llm_called
    })

    return response
