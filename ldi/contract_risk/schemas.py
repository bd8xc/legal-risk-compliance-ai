from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TemplateUploadResponse(BaseModel):
    template_id: str
    template_name: str
    clause_count: int
    cached: bool
    document_hash: str


class CandidateUploadResponse(BaseModel):
    candidate_id: str
    candidate_name: str
    clause_count: int
    cached: bool
    document_hash: str


class CompareRequest(BaseModel):
    template_id: str
    candidate_id: str
    top_k: int = 5


class ClauseMatch(BaseModel):
    candidate_clause_id: str
    template_clause_id: Optional[str]
    candidate_section: Optional[str]
    template_section: Optional[str]
    candidate_text: str
    template_text: Optional[str]
    similarity: float
    deviation: float
    risk_flag: bool
    explanation: Optional[str] = None


class MissingClause(BaseModel):
    template_clause_id: str
    template_section: Optional[str]
    template_text: str
    similarity: float
    explanation: str


class ExtraClause(BaseModel):
    candidate_clause_id: str
    candidate_section: Optional[str]
    candidate_text: str
    similarity: float
    explanation: str


class RiskSummary(BaseModel):
    template_id: str
    candidate_id: str
    comparison_id: str
    template_name: str
    candidate_name: str
    overall_similarity: float
    overall_deviation: float
    risk_score: int
    missing_clause_count: int
    extra_clause_count: int
    major_deviation_count: int
    generated_at: datetime


class ComparisonResult(BaseModel):
    summary: RiskSummary
    clause_matches: List[ClauseMatch]
    missing_template_clauses: List[MissingClause]
    extra_candidate_clauses: List[ExtraClause]
    explanations: List[str]


class RiskReportResponse(BaseModel):
    comparison_id: str
    template_id: str
    candidate_id: str
    report: ComparisonResult