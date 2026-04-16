"""
test_conflict_agent.py
======================
Test suite for the LEXGUARD Conflict of Interest Agent.

Prerequisites:
    pip install kuzu spacy
    python -m spacy download en_core_web_sm
    python synthetic_graph.py --reset   # seeds the test DB

Run:
    pytest test_conflict_agent.py -v
    # or directly:
    python test_conflict_agent.py
"""

import sys
import os
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_KG_ROOT = os.path.join(_HERE, "..", "kg",
                        "legal-risk-compliance-ai-feature-knowledge-graph-ingestion")
if os.path.isdir(_KG_ROOT):
    sys.path.insert(0, _KG_ROOT)

from conflict_agent import ConflictOfInterestAgent, Severity

DB_PATH = os.path.join(_HERE, "test_lexguard_db")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def seed_db():
    """Seed a fresh test database before any test in this module runs."""
    from synthetic_graph import seed
    seed(db_path=DB_PATH, reset=True)
    yield
    # Cleanup after all tests
    import shutil
    if os.path.isdir(DB_PATH):
        shutil.rmtree(DB_PATH)


@pytest.fixture(scope="module")
def agent():
    return ConflictOfInterestAgent(db_path=DB_PATH)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestHighSeverityConflict:
    """
    Scenario: Alpha Corp ← contracts with → Beta Technologies
              Beta Technologies ─SUBSIDIARY_OF─▶ Gamma Holdings
              Gamma Holdings ─LITIGATING_AGAINST─▶ Alpha Corp
    Expected: conflict_detected=True, severity=HIGH (3-hop path)
    """

    def test_conflict_detected(self, agent):
        report = agent.run(
            doc_id="TEST_001",
            client_entity="Alpha Corp",
            counterparty_entity="Beta Technologies",
        )
        assert report.conflict_detected is True

    def test_severity_is_high(self, agent):
        report = agent.run(
            doc_id="TEST_001",
            client_entity="Alpha Corp",
            counterparty_entity="Beta Technologies",
        )
        assert report.conflict_severity == Severity.HIGH

    def test_path_contains_litigation_rel(self, agent):
        report = agent.run(
            doc_id="TEST_001",
            client_entity="Alpha Corp",
            counterparty_entity="Beta Technologies",
        )
        assert any(
            "LITIGATING_AGAINST" in p.relationships
            for p in report.conflict_paths
        ), "Expected a LITIGATING_AGAINST edge in at least one conflict path"

    def test_conflict_flag_is_one(self, agent):
        report = agent.run(
            doc_id="TEST_001",
            client_entity="Alpha Corp",
            counterparty_entity="Beta Technologies",
        )
        assert report.conflict_flag == 1


class TestNoConflict:
    """
    Scenario: Two unrelated entities – Zeta Industries and Vendor Three LLC
    Expected: conflict_detected=False, severity=NONE
    """

    def test_no_conflict(self, agent):
        report = agent.run(
            doc_id="TEST_002",
            client_entity="Zeta Industries",
            counterparty_entity="Vendor Three LLC",
        )
        assert report.conflict_detected is False
        assert report.conflict_severity == Severity.NONE
        assert report.conflict_flag == 0
        assert len(report.conflict_paths) == 0


class TestMediumSeverityConflict:
    """
    Scenario: Alpha Corp vs Delta Solutions (COMPETES_WITH)
    Expected: conflict_detected=True, severity=MEDIUM
    """

    def test_competition_conflict(self, agent):
        report = agent.run(
            doc_id="TEST_003",
            client_entity="Alpha Corp",
            counterparty_entity="Delta Solutions",
        )
        assert report.conflict_detected is True
        assert report.conflict_severity == Severity.MEDIUM

    def test_path_contains_competes_with(self, agent):
        report = agent.run(
            doc_id="TEST_003",
            client_entity="Alpha Corp",
            counterparty_entity="Delta Solutions",
        )
        assert any(
            "COMPETES_WITH" in p.relationships
            for p in report.conflict_paths
        )


class TestLowSeverityConflict:
    """
    Scenario: Alpha Corp vs Kappa Group (SHARED_DIRECTOR)
    Expected: conflict_detected=True, severity=LOW
    """

    def test_shared_director_conflict(self, agent):
        report = agent.run(
            doc_id="TEST_004",
            client_entity="Alpha Corp",
            counterparty_entity="Kappa Group",
        )
        assert report.conflict_detected is True
        assert report.conflict_severity == Severity.LOW


class TestLexStateOutput:
    """Verify the LexState-compatible dict has correct structure and types."""

    def test_lex_state_keys(self, agent):
        report = agent.run(
            doc_id="TEST_005",
            client_entity="Alpha Corp",
            counterparty_entity="Beta Technologies",
        )
        update = report.to_lex_state_update()
        assert "conflict_detected"  in update
        assert "conflict_flag"      in update
        assert "conflict_severity"  in update
        assert "conflict_paths"     in update
        assert isinstance(update["conflict_paths"], list)

    def test_path_dict_structure(self, agent):
        report = agent.run(
            doc_id="TEST_005",
            client_entity="Alpha Corp",
            counterparty_entity="Beta Technologies",
        )
        for p in report.to_lex_state_update()["conflict_paths"]:
            assert "nodes"         in p
            assert "relationships" in p
            assert "severity"      in p
            assert "description"   in p


class TestHopLimit:
    """Paths longer than 3 hops must NOT be returned."""

    def test_max_hops_respected(self, agent):
        report = agent.run(
            doc_id="TEST_006",
            client_entity="Alpha Corp",
            counterparty_entity="Vendor Five Co",
        )
        for p in report.conflict_paths:
            # number of hops = number of edges = len(nodes) - 1
            assert len(p.nodes) - 1 <= 3, (
                f"Path with {len(p.nodes)-1} hops exceeded MAX_HOPS=3: {p.nodes}"
            )


# ---------------------------------------------------------------------------
# Standalone runner (no pytest required)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Seed once
    from synthetic_graph import seed
    seed(db_path=DB_PATH, reset=True)

    ag = ConflictOfInterestAgent(db_path=DB_PATH)

    scenarios = [
        ("TEST_001", "Alpha Corp",    "Beta Technologies", "3-hop litigation via Gamma Holdings"),
        ("TEST_002", "Zeta Industries","Vendor Three LLC",  "No conflict expected"),
        ("TEST_003", "Alpha Corp",    "Delta Solutions",    "Direct competition"),
        ("TEST_004", "Alpha Corp",    "Kappa Group",        "Shared director (low risk)"),
    ]

    for doc_id, client, counterparty, label in scenarios:
        print(f"\n{'─'*60}")
        print(f"Scenario: {label}")
        r = ag.run(doc_id=doc_id, client_entity=client, counterparty_entity=counterparty)
        print(r.summary())

    # Cleanup
    import shutil
    shutil.rmtree(DB_PATH, ignore_errors=True)
    print("\nAll scenarios complete.")
