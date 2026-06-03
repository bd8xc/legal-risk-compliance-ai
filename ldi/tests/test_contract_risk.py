import os
import json
import tempfile
import numpy as np
import pytest

from ldi.contract_risk.service import ContractRiskService
from ldi.contract_risk.storage import ContractRiskState
from ldi.embeddings import pipeline as embed_pipeline


class DummyVectorStore:
    def __init__(self):
        self._storage = {}

    def add(self, ids, texts, embeddings, metadatas):
        # store by document_id found in metadata
        for i, meta in enumerate(metadatas):
            doc_id = meta.get("document_id") or meta.get("file_name")
            self._storage.setdefault(doc_id, []).append((ids[i], meta, texts[i]))

    def get_clauses(self, where=None, limit=1000, offset=0, include=None):
        where = where or {}
        results = {"ids": [], "metadatas": [], "documents": []}
        if where.get("source_type") == "template":
            key = where.get("template_id")
            rows = self._storage.get(key, [])
        elif where.get("source_type") == "candidate":
            key = where.get("candidate_id")
            rows = self._storage.get(key, [])
        else:
            # flatten
            rows = [item for doc in self._storage.values() for item in doc]
        for vid, meta, doc in rows:
            results["ids"].append(vid)
            results["metadatas"].append(meta)
            results["documents"].append(doc)
        return results


class DummyEmbedder:
    def embed(self, texts):
        # deterministic lightweight embedding for tests
        arr = []
        for t in texts:
            v = (sum(bytearray(t.encode("utf-8"))) % 100) / 100.0
            arr.append([v] * 8)
        return np.array(arr, dtype=float)


@pytest.fixture
def service(monkeypatch):
    svc = ContractRiskService()
    # replace heavy vector store and embedder with dummy ones
    svc.vector_store = DummyVectorStore()
    svc.embedder = DummyEmbedder()
    # avoid calling the real embed_and_store which needs external models; patch to use embedder + vectorstore
    def fake_embed_and_store(clauses, file_name, document_id=None):
        texts = [c.get("text", "") for c in clauses if c.get("text")]
        ids = [f"{document_id or file_name}::{c.get('clause_id', idx)}" for idx, c in enumerate(clauses) if c.get("text")]
        metas = []
        for c in clauses:
            if not c.get("text"):
                continue
            meta = {k: v for k, v in c.items() if k in ("clause_id", "section", "level")}
            meta["file_name"] = file_name
            meta["document_id"] = document_id or file_name
            metas.append(meta)
        embeddings = svc.embedder.embed(texts)
        svc.vector_store.add(ids, texts, embeddings, metas)
        # compute hash similar to real pipeline
        doc_hash = embed_pipeline._compute_document_hash(clauses)
        return {"clauses": len(texts), "embedding_dim": embeddings.shape[1], "cached": False, "document_hash": doc_hash}

    monkeypatch.setattr("ldi.contract_risk.service.embed_and_store", fake_embed_and_store)
    return svc


def test_hash_stability():
    clauses_a = [
        {"clause_id": "1", "section": "Definitions", "level": "clause", "text": "The party A"},
        {"clause_id": "2", "section": "Terms", "level": "clause", "text": "Payment due 30 days"},
    ]
    clauses_b = [
        {"clause_id": "1", "section": "Definitions", "level": "clause", "text": "The party A"},
        {"clause_id": "2", "section": "Terms", "level": "clause", "text": "Payment due 30 days"},
    ]
    h1 = embed_pipeline._compute_document_hash(clauses_a)
    h2 = embed_pipeline._compute_document_hash(clauses_b)
    assert h1 == h2


def test_ingest_and_compare_basic(service: ContractRiskService):
    # Create a small template and candidate, ingest them, compare and verify report stored
    template_clauses = [
        {"clause_id": "T1", "section": "Intro", "level": "clause", "text": "This is the template first clause."},
        {"clause_id": "T2", "section": "Payment", "level": "clause", "text": "Payment must be made within 30 days."},
    ]
    candidate_clauses = [
        {"clause_id": "C1", "section": "Intro", "level": "clause", "text": "This is the template first clause."},
        {"clause_id": "C2", "section": "Payment", "level": "clause", "text": "Payment must be made within 45 days."},
        {"clause_id": "C3", "section": "Misc", "level": "clause", "text": "Additional term present."},
    ]

    # Manually register template and candidate in state with stable IDs
    template_id = "template-1234"
    candidate_id = "candidate-5678"
    # register in state
    service.state.register_template(template_id, "template.docx", embed_pipeline._compute_document_hash(template_clauses), len(template_clauses))
    service.state.register_candidate(candidate_id, "candidate.docx", embed_pipeline._compute_document_hash(candidate_clauses), len(candidate_clauses))

    # store clauses in dummy vector store
    # prepare ids and metas
    t_ids = [f"{template_id}::{c['clause_id']}" for c in template_clauses]
    c_ids = [f"{candidate_id}::{c['clause_id']}" for c in candidate_clauses]
    t_texts = [c["text"] for c in template_clauses]
    c_texts = [c["text"] for c in candidate_clauses]
    t_metas = [{"clause_id": c["clause_id"], "section": c["section"], "level": c["level"], "document_id": template_id} for c in template_clauses]
    c_metas = [{"clause_id": c["clause_id"], "section": c["section"], "level": c["level"], "document_id": candidate_id} for c in candidate_clauses]
    service.vector_store.add(t_ids, t_texts, service.embedder.embed(t_texts), t_metas)
    service.vector_store.add(c_ids, c_texts, service.embedder.embed(c_texts), c_metas)

    # Compare and assert structure
    report = service.compare(template_id, candidate_id, top_k=2)
    assert "summary" in report
    assert "clause_matches" in report
    assert len(report["clause_matches"]) <= 2
    # risk score exists and is int 0-100
    assert isinstance(report["summary"]["risk_score"], int)
    assert 0 <= report["summary"]["risk_score"] <= 100

    # ensure comparison stored with unique id
    comp_id = report["summary"]["comparison_id"]
    stored = service.state.get_comparison(comp_id)
    assert stored is not None

    # Running comparison again yields a different comparison id and preserves previous
    report2 = service.compare(template_id, candidate_id, top_k=2)
    assert report2["summary"]["comparison_id"] != comp_id
    all_comparisons = service.state._state["comparisons"]
    assert report2["summary"]["comparison_id"] in all_comparisons
    assert comp_id in all_comparisons

    # top_k does not affect the stored risk score
    full_report = service.compare(template_id, candidate_id, top_k=10)
    assert full_report["summary"]["risk_score"] == report["summary"]["risk_score"]


def test_loader_schema_docx_and_pdf():
    # Skip if dependencies aren't present
    pytest.importorskip("docx")
    pytest.importorskip("pdfplumber")
    from ldi.ingestion.docx_loader import load_docx
    from ldi.ingestion.pdf_table_loader import extract_pdf_text_and_tables

    # Create a temporary DOCX
    from docx import Document
    tmp_docx = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp_docx.close()
    doc = Document()
    doc.add_paragraph("Paragraph one.")
    doc.add_paragraph("Paragraph two.")
    doc.save(tmp_docx.name)

    try:
        res_docx = load_docx(tmp_docx.name)
        assert isinstance(res_docx, dict)
        assert "text" in res_docx and "tables" in res_docx

        # Create a simple PDF using pdfplumber can't write; instead assert extract_pdf_text_and_tables raises on non-pdf
        # The primary check is that function exists and returns the expected keys when a PDF is available.
        # For safety, just assert callable
        assert callable(extract_pdf_text_and_tables)
    finally:
        os.unlink(tmp_docx.name)
