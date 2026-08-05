"""Main confidentiality leakage analysis agent."""

from __future__ import annotations

from typing import Any, Dict, List

from .classifier import classify_findings
from .content_detector import detect_confidential_content
from .masker import mask_value
from .ner_detector import detect_ner_sensitive_info
from .regex_detector import detect_regex_sensitive_info
from .scorer import score_confidentiality
from .schemas import ConfidentialityReport, SensitiveFinding, DocumentIndexItem
from ldi.embeddings.vector_store import ClauseVectorStore


class ConfidentialityLeakageAgent:
    """Analyze clause-level text for potentially sensitive information."""

    def __init__(self) -> None:
        self._vector_store = ClauseVectorStore()

    def _load_clauses_for_document(self, file_name: str) -> List[Dict[str, Any]]:
        clauses = self._vector_store.get_document_clauses(file_name)
        if not clauses:
            raise LookupError(
                f"No embedded clauses found for '{file_name}'. Index the document first, then retry with the same file name."
            )
        return clauses

    def list_documents(self) -> List[DocumentIndexItem]:
        documents = []
        for item in self._vector_store.list_documents():
            documents.append(DocumentIndexItem(**item))
        return documents

    def analyze(self, doc_id: str, clauses: List[Dict[str, Any]] | None = None):
        findings: List[Dict[str, Any]] = []
        clause_rows = clauses if clauses else self._load_clauses_for_document(doc_id)

        for clause in clause_rows:
            text = str(clause.get("text", "") or "")
            clause_id = str(clause.get("clause_id") or "")
            section = str(clause.get("section") or "")

            regex_findings = detect_regex_sensitive_info(text)
            ner_findings = detect_ner_sensitive_info(text)
            content_findings = detect_confidential_content(text)
            merged = classify_findings(regex_findings + ner_findings + content_findings, clause_id=clause_id, section=section)
            findings.extend(merged)

        score = score_confidentiality(findings)
        sensitive_data_detected = bool(findings)

    

        report = ConfidentialityReport(
            doc_id=doc_id,
            sensitive_data_detected=sensitive_data_detected,
            risk_score=int(score["risk_score"]),
            risk_level=str(score["risk_level"]),
            total_findings=len(findings),
            high_sensitivity_count=sum(1 for finding in findings if finding["sensitivity"] == "HIGH"),
            medium_sensitivity_count=sum(1 for finding in findings if finding["sensitivity"] == "MEDIUM"),
            context_dependent_count=sum(1 for finding in findings if finding["sensitivity"] == "CONTEXT_DEPENDENT"),
            findings=[SensitiveFinding(**finding) for finding in findings],
        )
        return report
