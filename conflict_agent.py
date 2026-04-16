"""
Deterministic Conflict of Interest (COI) agent.

Implementation guarantees:
- True BFS using deque.
- Level-order traversal with shortest-path behavior.
- Hard max depth of 3 hops.
- Kuzu-backed neighbor expansion via Cypher.
- Deterministic output schema only.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Any, Optional, TypedDict

try:
    import kuzu
except Exception:  # pragma: no cover - handled at runtime when driver is required.
    kuzu = None


MAX_HOPS = 3

TRAVERSABLE_RELATIONSHIPS: set[str] = {
    "LITIGATING_AGAINST",
    "COMPETES_WITH",
    "DISPUTE_WITH",
    "SHARED_DIRECTOR",
    "SUBSIDIARY_OF",
    "PARENT_OF",
    "AFFILIATED_WITH",
    "PARTNER_OF",
    "CONTRACT_WITH",
    "JOINT_VENTURE_WITH",
    "MERGED_WITH",
    "ACQUIRES",
    "REPRESENTS",
    "AGENT_OF",
}

# Conflict trigger relationships used for deterministic conflict detection.
CONFLICT_TRIGGER_RELATIONSHIPS: set[str] = {
    "LITIGATING_AGAINST",
    "COMPETES_WITH",
    "DISPUTE_WITH",
    "SHARED_DIRECTOR",
}


class COIAgentError(Exception):
    """Base exception for deterministic COI failures."""


class GraphQueryError(COIAgentError):
    """Raised when graph queries fail."""


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class LexState(TypedDict, total=False):
    doc_id: str
    entities: dict[str, Any]
    conflict_detected: bool
    conflict_path: list[str]
    severity: str


@dataclass(frozen=True)
class PathResult:
    nodes: list[str]
    relationships: list[str]

    @property
    def hops(self) -> int:
        return len(self.relationships)


@dataclass
class ConflictReport:
    conflict_detected: bool
    conflict_path: list[str]
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_detected": self.conflict_detected,
            "conflict_path": self.conflict_path,
            "severity": self.severity,
        }

    def to_lex_state_update(self) -> dict[str, Any]:
        return self.to_dict()


class KuzuGraphAdapter:
    """Kuzu graph adapter used by the COI BFS."""

    def __init__(
        self,
        *,
        db_path: str = "lexguard_db",
    ):
        if kuzu is None:
            raise GraphQueryError("kuzu driver is not installed")

        try:
            self._db = kuzu.Database(db_path)
            self._conn = kuzu.Connection(self._db)
        except Exception as exc:  # pragma: no cover - depends on runtime driver errors.
            raise GraphQueryError(f"Unable to initialize Kuzu connection: {exc}") from exc

    def _run(self, query: str, params: Optional[dict[str, Any]] = None) -> list[list[Any]]:
        try:
            result = self._conn.execute(query, params or {})
            rows: list[list[Any]] = []
            while result.has_next():
                rows.append(result.get_next())
            return rows
        except Exception as exc:
            raise GraphQueryError(f"Kuzu query failed: {exc}") from exc

    def get_neighbors(self, entity_name: str, doc_id: str) -> list[tuple[str, str]]:
        del doc_id

        query = """
        MATCH (a:Entity)-[r:RELATES_TO]-(b:Entity)
        WHERE a.name = $name
          AND r.type IN $allowed_relationships
        RETURN DISTINCT b.name, r.type
        """
        rows = self._run(
            query,
            {
                "name": entity_name,
                "allowed_relationships": sorted(TRAVERSABLE_RELATIONSHIPS),
            },
        )

        neighbors: list[tuple[str, str]] = []
        for row in rows:
            neighbor = row[0] if len(row) > 0 else None
            rel_type = row[1] if len(row) > 1 else None
            if isinstance(neighbor, str) and isinstance(rel_type, str):
                neighbors.append((neighbor, rel_type))
        return neighbors


def _normalize_entity(name: str) -> str:
    cleaned = str(name).strip()
    if not cleaned:
        raise ValueError("Entity names must be non-empty strings")
    return cleaned


def _pairwise_entity_checks(
    client_entity: str,
    counterparty_entity: str,
    contract_entities: list[str],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_pair(left: str, right: str) -> None:
        if left == right:
            return
        ordered = (left, right) if left < right else (right, left)
        if ordered not in seen:
            seen.add(ordered)
            pairs.append(ordered)

    add_pair(client_entity, counterparty_entity)

    for entity in contract_entities:
        add_pair(client_entity, entity)
        add_pair(counterparty_entity, entity)

    for left, right in combinations(contract_entities, 2):
        add_pair(left, right)

    return pairs


def _path_is_conflict(relationships: list[str]) -> bool:
    return any(rel in CONFLICT_TRIGGER_RELATIONSHIPS for rel in relationships)


def _is_subsidiary_of_competitor(relationships: list[str]) -> bool:
    if "COMPETES_WITH" not in relationships:
        return False

    for idx, rel in enumerate(relationships):
        if rel != "COMPETES_WITH":
            continue
        prev_rel = relationships[idx - 1] if idx > 0 else None
        next_rel = relationships[idx + 1] if idx + 1 < len(relationships) else None
        if prev_rel in {"SUBSIDIARY_OF", "PARENT_OF"} or next_rel in {"SUBSIDIARY_OF", "PARENT_OF"}:
            return True
    return False


def _severity_for_path(relationships: list[str]) -> Severity:
    if "LITIGATING_AGAINST" in relationships:
        return Severity.HIGH

    if "COMPETES_WITH" in relationships or _is_subsidiary_of_competitor(relationships):
        return Severity.MEDIUM

    if "DISPUTE_WITH" in relationships:
        return Severity.MEDIUM

    if "SHARED_DIRECTOR" in relationships:
        return Severity.LOW

    return Severity.LOW


def _format_conflict_path(path: PathResult) -> list[str]:
    if not path.nodes:
        return []

    formatted: list[str] = [path.nodes[0]]
    for rel, node in zip(path.relationships, path.nodes[1:]):
        formatted.extend([rel, node])
    return formatted


def _bfs_shortest_conflict_path(
    graph: Any,
    *,
    start: str,
    target: str,
    doc_id: str,
    max_hops: int = MAX_HOPS,
) -> Optional[PathResult]:
    queue: deque[tuple[str, list[str], list[str], int]] = deque()
    queue.append((start, [start], [], 0))

    visited: set[tuple[str, int]] = {(start, 0)}

    while queue:
        current, node_path, rel_path, depth = queue.popleft()

        if depth >= max_hops:
            continue

        neighbors = graph.get_neighbors(current, doc_id)
        for neighbor, rel_type in neighbors:
            if neighbor in node_path:
                continue

            next_depth = depth + 1
            if next_depth > max_hops:
                continue

            next_nodes = node_path + [neighbor]
            next_rels = rel_path + [rel_type]

            if neighbor == target:
                if _path_is_conflict(next_rels):
                    return PathResult(nodes=next_nodes, relationships=next_rels)
                continue

            visited_key = (neighbor, next_depth)
            if visited_key in visited:
                continue
            visited.add(visited_key)
            queue.append((neighbor, next_nodes, next_rels, next_depth))

    return None


class ConflictOfInterestAgent:
    """Spec-compliant deterministic COI agent."""

    def __init__(
        self,
        *,
        max_hops: int = MAX_HOPS,
        graph: Optional[Any] = None,
        db_path: Optional[str] = None,
    ):
        if max_hops != MAX_HOPS:
            # Spec requires strict 3-hop ceiling.
            raise ValueError("max_hops is fixed at 3 by specification")

        self.max_hops = MAX_HOPS
        if graph is not None:
            self.graph = graph
            return

        self.graph = KuzuGraphAdapter(db_path=db_path or "lexguard_db")

    def run(
        self,
        *,
        client_entity: str,
        counterparty_entity: str,
        contract_entities: Optional[list[str]] = None,
        doc_id: str,
        additional_entities: Optional[list[str]] = None,
    ) -> ConflictReport:
        client = _normalize_entity(client_entity)
        counterparty = _normalize_entity(counterparty_entity)

        merged_contract_entities = list(contract_entities or [])
        if additional_entities:
            merged_contract_entities.extend(additional_entities)

        normalized_contract_entities: list[str] = []
        seen_entities: set[str] = {client, counterparty}
        for raw in merged_contract_entities:
            normalized = _normalize_entity(raw)
            if normalized not in seen_entities:
                seen_entities.add(normalized)
                normalized_contract_entities.append(normalized)

        pairs = _pairwise_entity_checks(client, counterparty, normalized_contract_entities)

        best_path: Optional[PathResult] = None
        best_hops = MAX_HOPS + 1

        for left, right in pairs:
            path = _bfs_shortest_conflict_path(
                self.graph,
                start=left,
                target=right,
                doc_id=doc_id,
                max_hops=MAX_HOPS,
            )
            if path is None:
                continue

            if path.hops < best_hops:
                best_hops = path.hops
                best_path = path
                if best_hops == 1:
                    break

        if best_path is None:
            return ConflictReport(
                conflict_detected=False,
                conflict_path=[],
                severity=Severity.LOW.value,
            )

        return ConflictReport(
            conflict_detected=True,
            conflict_path=_format_conflict_path(best_path),
            severity=_severity_for_path(best_path.relationships).value,
        )


def conflict_agent_node(
    state: LexState,
    agent: Optional[ConflictOfInterestAgent] = None,
) -> dict[str, Any]:
    entities = state.get("entities") or {}

    client_entity = (
        entities.get("client_entity")
        or entities.get("client")
        or entities.get("party_a")
        or ""
    )
    counterparty_entity = (
        entities.get("counterparty_entity")
        or entities.get("counterparty")
        or entities.get("party_b")
        or ""
    )

    contract_entities = entities.get("contract_entities")
    if not isinstance(contract_entities, list):
        fallback = entities.get("all_entities")
        contract_entities = fallback if isinstance(fallback, list) else []

    working_agent = agent or ConflictOfInterestAgent()
    report = working_agent.run(
        client_entity=str(client_entity),
        counterparty_entity=str(counterparty_entity),
        contract_entities=[str(item) for item in contract_entities],
        doc_id=str(state.get("doc_id", "")),
    )
    return report.to_dict()


__all__ = [
    "MAX_HOPS",
    "TRAVERSABLE_RELATIONSHIPS",
    "CONFLICT_TRIGGER_RELATIONSHIPS",
    "Severity",
    "LexState",
    "PathResult",
    "ConflictReport",
    "COIAgentError",
    "GraphQueryError",
    "KuzuGraphAdapter",
    "ConflictOfInterestAgent",
    "_bfs_shortest_conflict_path",
    "conflict_agent_node",
]
