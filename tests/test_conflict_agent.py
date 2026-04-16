from __future__ import annotations

from typing import Any

import conflict_agent
from conflict_agent import (
    ConflictOfInterestAgent,
    KuzuGraphAdapter,
    Severity,
    _bfs_shortest_conflict_path,
)


class FakeGraph:
    def __init__(self, edges: list[tuple[str, str, str]]):
        self._neighbors: dict[str, list[tuple[str, str]]] = {}
        self.doc_ids: list[str] = []

        for left, right, rel in edges:
            self._neighbors.setdefault(left, []).append((right, rel))
            self._neighbors.setdefault(right, []).append((left, rel))

    def get_neighbors(self, entity_name: str, doc_id: str) -> list[tuple[str, str]]:
        self.doc_ids.append(doc_id)
        return list(self._neighbors.get(entity_name, []))


def test_bfs_returns_shortest_conflict_path_only() -> None:
    graph = FakeGraph(
        edges=[
            ("Client", "Bridge1", "AFFILIATED_WITH"),
            ("Bridge1", "Counterparty", "COMPETES_WITH"),
            ("Client", "Bridge2", "AFFILIATED_WITH"),
            ("Bridge2", "Bridge3", "AFFILIATED_WITH"),
            ("Bridge3", "Counterparty", "LITIGATING_AGAINST"),
        ]
    )

    path = _bfs_shortest_conflict_path(
        graph,
        start="Client",
        target="Counterparty",
        doc_id="DOC-1",
        max_hops=3,
    )

    assert path is not None
    assert path.hops == 2
    assert path.nodes == ["Client", "Bridge1", "Counterparty"]


def test_bfs_never_exceeds_three_hops() -> None:
    graph = FakeGraph(
        edges=[
            ("A", "B", "AFFILIATED_WITH"),
            ("B", "C", "AFFILIATED_WITH"),
            ("C", "D", "AFFILIATED_WITH"),
            ("D", "E", "LITIGATING_AGAINST"),
        ]
    )

    path = _bfs_shortest_conflict_path(
        graph,
        start="A",
        target="E",
        doc_id="DOC-2",
        max_hops=3,
    )

    assert path is None


def test_run_checks_all_required_entity_pairs() -> None:
    graph = FakeGraph(
        edges=[
            ("Supplier One", "Supplier Two", "DISPUTE_WITH"),
        ]
    )
    agent = ConflictOfInterestAgent(graph=graph)

    report = agent.run(
        doc_id="DOC-3",
        client_entity="Client Corp",
        counterparty_entity="Counterparty LLC",
        contract_entities=["Supplier One", "Supplier Two"],
    )

    assert report.conflict_detected is True
    assert report.conflict_path == ["Supplier One", "DISPUTE_WITH", "Supplier Two"]


def test_output_schema_is_strict() -> None:
    graph = FakeGraph(edges=[("Client", "Counterparty", "LITIGATING_AGAINST")])
    agent = ConflictOfInterestAgent(graph=graph)

    payload = agent.run(
        doc_id="DOC-4",
        client_entity="Client",
        counterparty_entity="Counterparty",
        contract_entities=[],
    ).to_dict()

    assert set(payload.keys()) == {"conflict_detected", "conflict_path", "severity"}


def test_non_trigger_relationship_does_not_trigger_conflict() -> None:
    graph = FakeGraph(
        edges=[
            ("Client", "Partner", "PARTNER_OF"),
            ("Partner", "Counterparty", "AFFILIATED_WITH"),
        ]
    )
    agent = ConflictOfInterestAgent(graph=graph)

    report = agent.run(
        doc_id="DOC-5",
        client_entity="Client",
        counterparty_entity="Counterparty",
    )

    assert report.conflict_detected is False
    assert report.conflict_path == []


def test_severity_mapping_high_medium_low() -> None:
    high_graph = FakeGraph(edges=[("A", "B", "LITIGATING_AGAINST")])
    medium_graph = FakeGraph(edges=[("A", "B", "COMPETES_WITH")])
    low_graph = FakeGraph(edges=[("A", "B", "SHARED_DIRECTOR")])

    high_report = ConflictOfInterestAgent(graph=high_graph).run(
        doc_id="DOC-H",
        client_entity="A",
        counterparty_entity="B",
    )
    medium_report = ConflictOfInterestAgent(graph=medium_graph).run(
        doc_id="DOC-M",
        client_entity="A",
        counterparty_entity="B",
    )
    low_report = ConflictOfInterestAgent(graph=low_graph).run(
        doc_id="DOC-L",
        client_entity="A",
        counterparty_entity="B",
    )

    assert high_report.severity == Severity.HIGH.value
    assert medium_report.severity == Severity.MEDIUM.value
    assert low_report.severity == Severity.LOW.value


def test_doc_id_is_used_in_neighbor_queries() -> None:
    graph = FakeGraph(edges=[("A", "B", "COMPETES_WITH")])
    agent = ConflictOfInterestAgent(graph=graph)

    agent.run(doc_id="DOC-XYZ", client_entity="A", counterparty_entity="B")

    assert graph.doc_ids
    assert all(doc_id == "DOC-XYZ" for doc_id in graph.doc_ids)


def test_kuzu_adapter_uses_cypher_queries(monkeypatch: Any) -> None:
    queries: list[tuple[str, dict[str, Any]]] = []

    class FakeQueryResult:
        def __init__(self, rows: list[list[Any]]):
            self._rows = rows
            self._idx = 0

        def has_next(self) -> bool:
            return self._idx < len(self._rows)

        def get_next(self) -> list[Any]:
            row = self._rows[self._idx]
            self._idx += 1
            return row

    class FakeConnection:
        def __init__(self, db: Any):
            self._db = db

        def execute(self, query: str, params: dict[str, Any]) -> FakeQueryResult:
            queries.append((query, params))
            return FakeQueryResult([["B", "COMPETES_WITH"]])

    class FakeDatabase:
        def __init__(self, path: str):
            assert path == "lexguard_db"
            self.path = path

    class FakeKuzu:
        Database = FakeDatabase
        Connection = FakeConnection

    monkeypatch.setattr(conflict_agent, "kuzu", FakeKuzu)

    adapter = KuzuGraphAdapter(db_path="lexguard_db")
    neighbors = adapter.get_neighbors("A", "DOC-777")

    assert neighbors == [("B", "COMPETES_WITH")]
    assert queries
    assert "MATCH (a:Entity)-[r:RELATES_TO]-(b:Entity)" in queries[0][0]
    assert queries[0][1]["name"] == "A"
