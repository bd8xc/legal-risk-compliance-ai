from __future__ import annotations

import os
import tempfile
from typing import Dict

from fastapi import APIRouter, File, HTTPException, UploadFile

from .schemas import (
    CandidateUploadResponse,
    CompareRequest,
    ComparisonResult,
    RiskReportResponse,
    TemplateUploadResponse,
)
from .service import ContractRiskService

router = APIRouter(prefix="/contract-risk", tags=["contract-risk"])
service = ContractRiskService()


def _save_upload_to_temp(file: UploadFile) -> str:
    suffix = os.path.splitext(file.filename or "")[1] or ".bin"
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        temp.write(file.file.read())
        temp.flush()
        return temp.name
    finally:
        temp.close()


@router.post("/template/", response_model=TemplateUploadResponse)
async def upload_template(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    temp_path = _save_upload_to_temp(file)
    try:
        result = service.ingest_template(temp_path, file.filename)
        return TemplateUploadResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        await file.close()


@router.post("/contract/", response_model=CandidateUploadResponse)
async def upload_candidate(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    temp_path = _save_upload_to_temp(file)
    try:
        result = service.ingest_candidate(temp_path, file.filename)
        return CandidateUploadResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        await file.close()


@router.post("/compare/", response_model=ComparisonResult)
async def compare_contracts(body: CompareRequest):
    try:
        report = service.compare(body.template_id, body.candidate_id, body.top_k)
        return ComparisonResult(**report)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/report/{comparison_id}", response_model=RiskReportResponse)
async def get_risk_report(comparison_id: str):
    try:
        report = service.get_comparison_report(comparison_id)
        return RiskReportResponse(
            comparison_id=comparison_id,
            template_id=report["summary"]["template_id"],
            candidate_id=report["summary"]["candidate_id"],
            report=ComparisonResult(**report),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/templates/")
def list_templates() -> Dict[str, Dict[str, str]]:
    return service.state.list_templates()


@router.get("/candidates/")
def list_candidates() -> Dict[str, Dict[str, str]]:
    return service.state.list_candidates()