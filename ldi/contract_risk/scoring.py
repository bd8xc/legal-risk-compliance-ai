from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

MIN_MATCH_SIMILARITY = 0.65
MAJOR_DEVIATION_THRESHOLD = 0.30


def normalize_text_for_section(value: Optional[str]) -> str:
    if not value:
        return ""
    value = str(value).lower().strip()
    return " ".join(value.split())


def compute_cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Returns a candidate x template cosine similarity matrix with values in [0, 1].
    """
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=float)

    a_norm = np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = np.linalg.norm(b, axis=1, keepdims=True)

    a_safe = np.divide(a, a_norm, out=np.zeros_like(a), where=a_norm != 0)
    b_safe = np.divide(b, b_norm, out=np.zeros_like(b), where=b_norm != 0)

    return np.clip(np.matmul(a_safe, b_safe.T), 0.0, 1.0)


def clause_penalty(template_meta: Dict[str, Any], candidate_meta: Dict[str, Any], similarity: float) -> float:
    """
    Penalizes matches when structure or section labels differ.
    """
    penalty = 0.0

    template_section = normalize_text_for_section(template_meta.get("section"))
    candidate_section = normalize_text_for_section(candidate_meta.get("section"))
    if template_section and candidate_section and template_section != candidate_section:
        penalty += 0.08

    template_level = str(template_meta.get("level") or "").lower()
    candidate_level = str(candidate_meta.get("level") or "").lower()
    if template_level != candidate_level:
        penalty += 0.06
        if "table" in template_level or "table" in candidate_level:
            penalty += 0.05

    if similarity < 0.70:
        penalty += 0.05

    return min(penalty, 0.35)


def normalize_score(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def compute_overall_scores(
    candidate_deviations: List[float],
    missing_count: int,
    extra_count: int,
    reorder_penalty: float,
) -> Dict[str, float]:
    """
    Overall deviation is based on the full matched set plus missing/extra/reorder penalties.
    """
    if not candidate_deviations:
        base_deviation = 1.0
    else:
        base_deviation = float(np.mean(candidate_deviations))

    missing_penalty = min(0.35, missing_count * 0.06)
    extra_penalty = min(0.25, extra_count * 0.04)

    overall_deviation = normalize_score(base_deviation + missing_penalty + extra_penalty + reorder_penalty)
    overall_similarity = normalize_score(1.0 - overall_deviation)

    return {
        "overall_similarity": overall_similarity,
        "overall_deviation": overall_deviation,
        "risk_score": int(round(overall_deviation * 100)),
    }


def assign_unique_matches(similarity_matrix: np.ndarray) -> Tuple[List[Tuple[int, int, float]], List[int], List[int]]:
    """
    Greedy one-to-one matcher with a minimum similarity threshold.
    Returns:
      matches: list of (candidate_index, template_index, similarity)
      unmatched_candidates: candidate indices not assigned
      unmatched_templates: template indices not assigned
    """
    if similarity_matrix.size == 0:
        candidate_count = similarity_matrix.shape[0] if similarity_matrix.ndim >= 1 else 0
        template_count = similarity_matrix.shape[1] if similarity_matrix.ndim >= 2 else 0
        return [], list(range(candidate_count)), list(range(template_count))

    candidate_count, template_count = similarity_matrix.shape
    scored_pairs: List[Tuple[int, int, float]] = []

    for c_idx in range(candidate_count):
        for t_idx in range(template_count):
            scored_pairs.append((c_idx, t_idx, float(similarity_matrix[c_idx, t_idx])))

    scored_pairs.sort(key=lambda item: item[2], reverse=True)

    used_candidates = set()
    used_templates = set()
    matches: List[Tuple[int, int, float]] = []

    for c_idx, t_idx, score in scored_pairs:
        if score < MIN_MATCH_SIMILARITY:
            break
        if c_idx in used_candidates or t_idx in used_templates:
            continue
        used_candidates.add(c_idx)
        used_templates.add(t_idx)
        matches.append((c_idx, t_idx, score))

    unmatched_candidates = [i for i in range(candidate_count) if i not in used_candidates]
    unmatched_templates = [j for j in range(template_count) if j not in used_templates]

    return matches, unmatched_candidates, unmatched_templates