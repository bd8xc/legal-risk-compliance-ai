from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ldi.chunking.clause_splitter import split_clauses
from ldi.contract_risk.scoring import (
    assign_unique_matches,
    clause_penalty,
    compute_cosine_similarity_matrix,
    compute_overall_scores,
)
from ldi.contract_risk.storage import ContractRiskState
from ldi.embeddings.embedder import ClauseEmbedder
from ldi.embeddings.pipeline import _compute_document_hash, embed_and_store
from ldi.embeddings.vector_store import ClauseVectorStore
from ldi.ingestion.docx_loader import load_docx
from ldi.ingestion.pdf_table_loader import extract_pdf_text_and_tables

MIN_WORDS_FOR_COMPARISON = 4
PAGE_MARKER_RE = re.compile(r"^\s*page\s+\d+(?:\s+of\s+\d+)?\s*$", re.I)


class ContractRiskService:
    """Service layer for template, candidate, and risk comparison workflows."""

    def __init__(self):
        self.state = ContractRiskState()
        self.vector_store = ClauseVectorStore()
        self.embedder = ClauseEmbedder()

    def _load_document(self, file_path: str) -> Dict[str, Any]:
        if file_path.lower().endswith(".pdf"):
            payload = extract_pdf_text_and_tables(file_path)
        elif file_path.lower().endswith(".docx"):
            payload = load_docx(file_path)
        else:
            raise ValueError("Unsupported file type")

        if isinstance(payload, dict):
            text = payload.get("text", "")
            tables = payload.get("tables", []) or []
        else:
            text = str(payload or "")
            tables = []

        return {"text": str(text or ""), "tables": tables}

    def _table_to_text(self, table: Any) -> str:
        if isinstance(table, dict):
            rows = table.get("rows") or []
            headers = table.get("headers") or []
            if rows and isinstance(rows[0], dict):
                if not headers:
                    headers = list(rows[0].keys())
                lines = ["\t".join(str(h) for h in headers)]
                for row in rows:
                    lines.append("\t".join(str(row.get(h, "")) for h in headers))
                return "\n".join(lines).strip()
            table = rows

        if not table:
            return ""

        return "\n".join("\t".join(str(cell) for cell in row) for row in table).strip()

    def _prepare_clauses(
        self,
        text: str,
        tables: List[Any],
        source_type: str,
        document_id: str,
        file_name: str,
        template_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses = split_clauses(text)

        for table_index, table in enumerate(tables or [], start=1):
            table_text = self._table_to_text(table)
            if not table_text:
                continue
            clauses.append(
                {
                    "clause_id": f"TABLE_{table_index}",
                    "section": f"Table {table_index}",
                    "level": "table",
                    "text": table_text,
                }
            )

        prepared: List[Dict[str, Any]] = []
        for clause_index, clause in enumerate(clauses, start=1):
            metadata = dict(clause)
            metadata["source_type"] = source_type
            metadata["document_id"] = document_id
            metadata["file_name"] = file_name
            metadata["clause_index"] = clause_index
            if template_id is not None:
                metadata["template_id"] = template_id
            if candidate_id is not None:
                metadata["candidate_id"] = candidate_id
            prepared.append(metadata)

        return prepared

    def _create_entity_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:8]}"

    def _register_template(self, template_id: str, template_name: str, document_hash: str, clause_count: int) -> str:
        existing = self.state.find_template_by_hash(document_hash)
        if existing:
            template_id = existing
        self.state.register_template(template_id, template_name, document_hash, clause_count)
        return template_id

    def _register_candidate(self, candidate_id: str, candidate_name: str, document_hash: str, clause_count: int) -> str:
        existing = self.state.find_candidate_by_hash(document_hash)
        if existing:
            candidate_id = existing
        self.state.register_candidate(candidate_id, candidate_name, document_hash, clause_count)
        return candidate_id

    def ingest_template(self, file_path: str, file_name: str) -> Dict[str, Any]:
        raw_document = self._load_document(file_path)

        clauses = self._prepare_clauses(
            raw_document["text"],
            raw_document.get("tables", []),
            source_type="template",
            document_id="",
            file_name=file_name,
        )

        template_id = self._create_entity_id("template")
        for clause in clauses:
            clause["template_id"] = template_id
            clause["document_id"] = template_id

        document_hash = _compute_document_hash(clauses)
        template_id = self._register_template(template_id, file_name, document_hash, len(clauses))

        # Keep the stored metadata aligned with the effective ID.
        for clause in clauses:
            clause["template_id"] = template_id
            clause["document_id"] = template_id

        stats = embed_and_store(clauses, file_name, document_id=template_id)

        return {
            "template_id": template_id,
            "template_name": file_name,
            "clause_count": len(clauses),
            "cached": bool(stats.get("cached", False)),
            "document_hash": document_hash,
        }

    def ingest_candidate(self, file_path: str, file_name: str) -> Dict[str, Any]:
        raw_document = self._load_document(file_path)

        clauses = self._prepare_clauses(
            raw_document["text"],
            raw_document.get("tables", []),
            source_type="candidate",
            document_id="",
            file_name=file_name,
        )

        candidate_id = self._create_entity_id("candidate")
        for clause in clauses:
            clause["candidate_id"] = candidate_id
            clause["document_id"] = candidate_id

        document_hash = _compute_document_hash(clauses)
        candidate_id = self._register_candidate(candidate_id, file_name, document_hash, len(clauses))

        for clause in clauses:
            clause["candidate_id"] = candidate_id
            clause["document_id"] = candidate_id

        stats = embed_and_store(clauses, file_name, document_id=candidate_id)

        return {
            "candidate_id": candidate_id,
            "candidate_name": file_name,
            "clause_count": len(clauses),
            "cached": bool(stats.get("cached", False)),
            "document_hash": document_hash,
        }

    def _to_chroma_where(self, where: Dict[str, Any]) -> Dict[str, Any]:
        clean_where = {k: v for k, v in where.items() if v is not None and v != ""}
        if not clean_where:
            return {}
        if len(clean_where) == 1:
            key, value = next(iter(clean_where.items()))
            return {key: {"$eq": value}}
        return {"$and": [{k: {"$eq": v}} for k, v in clean_where.items()]}

    def _fetch_clauses(self, where: Dict[str, Any]) -> List[Dict[str, Any]]:
        chroma_where = self._to_chroma_where(where)
        raw = self.vector_store.get_clauses(where=chroma_where, limit=1000, include=["metadatas", "documents"])

        ids = raw.get("ids", [])
        metadatas = raw.get("metadatas", [])
        documents = raw.get("documents", [])

        rows: List[Dict[str, Any]] = []
        for idx in range(len(ids)):
            rows.append(
                {
                    "vector_id": ids[idx],
                    "metadata": metadatas[idx],
                    "text": documents[idx],
                }
            )
        return rows

    def _is_noise_clause(self, text: str) -> bool:
        cleaned = " ".join((text or "").split()).strip()
        if not cleaned:
            return True
        if PAGE_MARKER_RE.fullmatch(cleaned):
            return True
        if cleaned.isdigit():
            return True
        # Ignore extremely short fragments like isolated page numbers / footers.
        if len(cleaned.split()) < MIN_WORDS_FOR_COMPARISON and len(cleaned) <= 18:
            return True
        return False

    def compare(self, template_id: str, candidate_id: str, top_k: int = 5) -> Dict[str, Any]:
        template_record = self.state.get_template(template_id)
        candidate_record = self.state.get_candidate(candidate_id)

        if not template_record:
            raise ValueError(f"Template not found: {template_id}")
        if not candidate_record:
            raise ValueError(f"Candidate not found: {candidate_id}")

        template_rows = self._fetch_clauses({"source_type": "template", "template_id": template_id})
        candidate_rows = self._fetch_clauses({"source_type": "candidate", "candidate_id": candidate_id})

        template_rows = [row for row in template_rows if not self._is_noise_clause(row.get("text", ""))]
        candidate_rows = [row for row in candidate_rows if not self._is_noise_clause(row.get("text", ""))]

        if not template_rows or not candidate_rows:
            raise ValueError("Both template and candidate must contain at least one usable clause.")

        template_texts = [row["text"] for row in template_rows]
        candidate_texts = [row["text"] for row in candidate_rows]
        print("Template clauses:", len(template_rows))
        print("Candidate clauses:", len(candidate_rows))
        print("Template texts sample:", template_texts[:1])
        print("Candidate texts sample:", candidate_texts[:1])

        template_embeddings = self.embedder.embed(template_texts)
        candidate_embeddings = self.embedder.embed(candidate_texts)

        print("Template embeddings shape:", getattr(template_embeddings, "shape", None))
        print("Candidate embeddings shape:", getattr(candidate_embeddings, "shape", None))
        print("Template embedding sample:", template_embeddings[:1])
        print("Candidate embedding sample:", candidate_embeddings[:1])

        similarity_matrix = compute_cosine_similarity_matrix(candidate_embeddings, template_embeddings)
        print("Similarity matrix shape:", similarity_matrix.shape)
        print("Similarity matrix sample row:", similarity_matrix[:1])

        template_embeddings = self.embedder.embed(template_texts)
        candidate_embeddings = self.embedder.embed(candidate_texts)
        similarity_matrix = compute_cosine_similarity_matrix(candidate_embeddings, template_embeddings)

        matched_pairs, unmatched_candidate_indices, unmatched_template_indices = assign_unique_matches(similarity_matrix)

        candidate_matches: List[Dict[str, Any]] = []
        missing_clauses: List[Dict[str, Any]] = []
        extra_clauses: List[Dict[str, Any]] = []
        reorder_penalty_sum = 0.0

        for candidate_index, template_index, best_similarity in matched_pairs:
            candidate_row = candidate_rows[candidate_index]
            template_row = template_rows[template_index]

            penalty = clause_penalty(template_row["metadata"], candidate_row["metadata"], best_similarity)
            deviation = max(0.0, min(1.0, (1.0 - best_similarity) + penalty))

            order_diff = abs(candidate_index - template_index)
            reorder_penalty_sum += min(0.12, order_diff / max(len(template_rows), 1) * 0.08)

            explanation = None
            risk_flag = deviation >= 0.30

            if best_similarity < 0.65:
                explanation = "Clause does not semantically match the selected template segment."
                risk_flag = True
            elif penalty >= 0.10:
                explanation = "Clause is structurally similar but has section/type differences."

            candidate_matches.append(
                {
                    "candidate_clause_id": candidate_row["metadata"].get("clause_id"),
                    "template_clause_id": template_row["metadata"].get("clause_id"),
                    "candidate_section": candidate_row["metadata"].get("section"),
                    "template_section": template_row["metadata"].get("section"),
                    "candidate_text": candidate_row["text"],
                    "template_text": template_row["text"],
                    "similarity": round(best_similarity, 3),
                    "deviation": round(deviation, 3),
                    "risk_flag": risk_flag,
                    "explanation": explanation,
                }
            )

        for candidate_index in unmatched_candidate_indices:
            candidate_row = candidate_rows[candidate_index]
            extra_clauses.append(
                {
                    "candidate_clause_id": candidate_row["metadata"].get("clause_id"),
                    "candidate_section": candidate_row["metadata"].get("section"),
                    "candidate_text": candidate_row["text"],
                    "similarity": 0.0,
                    "explanation": "Candidate clause has no strong match in the template document.",
                }
            )
            candidate_matches.append(
                {
                    "candidate_clause_id": candidate_row["metadata"].get("clause_id"),
                    "template_clause_id": None,
                    "candidate_section": candidate_row["metadata"].get("section"),
                    "template_section": None,
                    "candidate_text": candidate_row["text"],
                    "template_text": None,
                    "similarity": 0.0,
                    "deviation": 1.0,
                    "risk_flag": True,
                    "explanation": "Candidate clause has no strong match in the template document.",
                }
            )
            reorder_penalty_sum += min(0.12, 0.08)

        for template_index in unmatched_template_indices:
            template_row = template_rows[template_index]
            missing_clauses.append(
                {
                    "template_clause_id": template_row["metadata"].get("clause_id"),
                    "template_section": template_row["metadata"].get("section"),
                    "template_text": template_row["text"],
                    "similarity": 0.0,
                    "explanation": "Template clause has no strong match in the candidate document.",
                }
            )

        full_matches = list(candidate_matches)
        candidate_deviations = [match["deviation"] for match in full_matches]

        overall = compute_overall_scores(
            candidate_deviations=candidate_deviations,
            missing_count=len(missing_clauses),
            extra_count=len(extra_clauses),
            reorder_penalty=reorder_penalty_sum,
        )

        major_explanations = [
            match["explanation"]
            for match in sorted(full_matches, key=lambda x: x["deviation"], reverse=True)
            if match["risk_flag"] and match["explanation"]
        ][:5]

        comparison_id = f"cmp-{uuid4().hex[:12]}"
        report = {
            "summary": {
                "template_id": template_id,
                "candidate_id": candidate_id,
                "comparison_id": comparison_id,
                "template_name": template_record["template_name"],
                "candidate_name": candidate_record["candidate_name"],
                "overall_similarity": round(overall["overall_similarity"], 3),
                "overall_deviation": round(overall["overall_deviation"], 3),
                "risk_score": overall["risk_score"],
                "missing_clause_count": len(missing_clauses),
                "extra_clause_count": len(extra_clauses),
                "major_deviation_count": len(major_explanations),
                "generated_at": datetime.utcnow().isoformat() + "Z",
            },
            "clause_matches": full_matches,
            "missing_template_clauses": missing_clauses,
            "extra_candidate_clauses": extra_clauses,
            "explanations": major_explanations,
        }

        # Store the full report.
        self.state.register_comparison(comparison_id, report)

        # Return a trimmed view if top_k is provided.
        if top_k and top_k > 0 and len(report["clause_matches"]) > top_k:
            report = dict(report)
            report["clause_matches"] = sorted(full_matches, key=lambda x: x["deviation"], reverse=True)[:top_k]

        return report

    def get_comparison_report(self, comparison_id: str) -> Dict[str, Any]:
        report = self.state.get_comparison(comparison_id)
        if not report:
            raise ValueError(f"Comparison not found: {comparison_id}")
        return report