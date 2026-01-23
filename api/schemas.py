"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    question: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Legal question (5-5000 characters)"
    )

class SafetyChecks(BaseModel):
    """Safety verification results with robustness metrics"""
    rules_passed: bool
    model_verified: bool
    violations: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0, description="Robustness score 0-100")
    hallucination_risk: str = Field(default="unknown", description="low|medium|high")
    claimed_facts: List[Dict[str, Any]] = Field(default_factory=list)
    # Enhanced robustness fields
    known_hallucinations: int = Field(default=0, description="Count of detected hallucinations")
    logical_contradictions: int = Field(default=0, description="Count of logical inconsistencies")
    recommendations: List[str] = Field(default_factory=list, description="Review recommendations")

class ChatResponse(BaseModel):
    """Response schema for chat endpoint"""
    question: str
    answer: str
    safety_checks: SafetyChecks
    debug_trace: List[str] = Field(default_factory=list)
    status: str = "success"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    status: str = "error"
    debug_trace: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

__all__ = [
    'ChatRequest',
    'ChatResponse',
    'ErrorResponse',
    'HealthResponse',
    'SafetyChecks'
]
