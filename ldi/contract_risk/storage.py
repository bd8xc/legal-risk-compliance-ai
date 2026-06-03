from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class ContractRiskState:
    """Persistent registry for templates, candidates, and comparison reports."""

    def __init__(self, state_path: Optional[str] = None):
        default_dir = os.path.join(os.path.dirname(__file__), "data")
        self.state_path = state_path or os.path.join(default_dir, "risk_state.json")
        self._state = self._load_state()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "templates": {},
            "template_hashes": {},
            "candidates": {},
            "candidate_hashes": {},
            "comparisons": {},
        }

    def _load_state(self) -> Dict[str, Any]:
        if not os.path.exists(self.state_path):
            return self._default_state()

        try:
            with open(self.state_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            if not isinstance(data, dict):
                return self._default_state()

            return {
                "templates": data.get("templates", {}),
                "template_hashes": data.get("template_hashes", {}),
                "candidates": data.get("candidates", {}),
                "candidate_hashes": data.get("candidate_hashes", {}),
                "comparisons": data.get("comparisons", {}),
            }
        except Exception:
            return self._default_state()

    def _save_state(self) -> None:
        directory = os.path.dirname(self.state_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        temp_path = f"{self.state_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)
        os.replace(temp_path, self.state_path)

    def find_template_by_hash(self, document_hash: str) -> Optional[str]:
        return self._state["template_hashes"].get(document_hash)

    def find_candidate_by_hash(self, document_hash: str) -> Optional[str]:
        return self._state["candidate_hashes"].get(document_hash)

    def register_template(self, template_id: str, template_name: str, document_hash: str, clause_count: int) -> None:
        existing = self.find_template_by_hash(document_hash)
        if existing:
            template_id = existing

        self._state["templates"][template_id] = {
            "template_id": template_id,
            "template_name": template_name,
            "document_hash": document_hash,
            "clause_count": clause_count,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        self._state["template_hashes"][document_hash] = template_id
        self._save_state()

    def register_candidate(self, candidate_id: str, candidate_name: str, document_hash: str, clause_count: int) -> None:
        existing = self.find_candidate_by_hash(document_hash)
        if existing:
            candidate_id = existing

        self._state["candidates"][candidate_id] = {
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "document_hash": document_hash,
            "clause_count": clause_count,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        self._state["candidate_hashes"][document_hash] = candidate_id
        self._save_state()

    def register_comparison(self, comparison_id: str, comparison_record: Dict[str, Any]) -> None:
        self._state["comparisons"][comparison_id] = comparison_record
        self._save_state()

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        return self._state["templates"].get(template_id)

    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        return self._state["candidates"].get(candidate_id)

    def get_comparison(self, comparison_id: str) -> Optional[Dict[str, Any]]:
        return self._state["comparisons"].get(comparison_id)

    def list_templates(self) -> Dict[str, Any]:
        return self._state["templates"]

    def list_candidates(self) -> Dict[str, Any]:
        return self._state["candidates"]

    def list_comparisons(self) -> Dict[str, Any]:
        return self._state["comparisons"]