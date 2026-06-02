import pytest
from pydantic import ValidationError

from graph.engine import Node, Relationship, KnowledgeGraphExtraction, run_scout_phase


class TestNodeValidation:
    def test_valid_node(self):
        node = Node(name="ACME CORP", type="COMPANY")
        assert node.name == "ACME CORP"
        assert node.type == "COMPANY"

    def test_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            Node(name="ACME CORP", type="INVALID_TYPE")

    def test_accepts_all_allowed_types(self):
        for t in ["COMPANY", "INDIVIDUAL", "CONTRACT", "LAW_FIRM", "COURT"]:
            node = Node(name="TEST", type=t)
            assert node.type == t


class TestRelationshipValidation:
    def test_valid_relationship(self):
        rel = Relationship(source="ACME CORP", target="BETA INC", type="CONTRACT_WITH")
        assert rel.source == "ACME CORP"
        assert rel.target == "BETA INC"
        assert rel.type == "CONTRACT_WITH"

    def test_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            Relationship(source="ACME CORP", target="BETA INC", type="INVALID_REL")


class TestKnowledgeGraphExtraction:
    def test_empty(self):
        kg = KnowledgeGraphExtraction()
        assert kg.nodes == []
        assert kg.relationships == []

    def test_with_data(self):
        kg = KnowledgeGraphExtraction(
            nodes=[Node(name="ACME CORP", type="COMPANY")],
            relationships=[Relationship(source="ACME CORP", target="BETA INC", type="CONTRACT_WITH")],
        )
        assert len(kg.nodes) == 1
        assert len(kg.relationships) == 1


class TestRunScoutPhase:
    def test_extracts_licensor(self):
        text = "ACME CORPORATION (hereinafter referred to as the 'Licensor')"
        aliases = run_scout_phase(text)
        assert aliases["LICENSOR"] == "ACME CORPORATION"
        assert aliases["LICENSEE"] == "UNKNOWN_LICENSEE"

    def test_extracts_licensee(self):
        text = "BETA LIMITED (hereinafter referred to as the 'Licensee')"
        aliases = run_scout_phase(text)
        assert aliases["LICENSEE"] == "BETA LIMITED"
        assert aliases["LICENSOR"] == "UNKNOWN_LICENSOR"

    def test_extracts_both(self):
        text = (
            "ACME CORP (hereinafter referred to as the 'Licensor') "
            "and BETA LTD (hereinafter referred to as the 'Licensee')"
        )
        aliases = run_scout_phase(text)
        assert aliases["LICENSOR"] == "ACME CORP"
        assert aliases["LICENSEE"] == "BETA LTD"

    def test_no_definitions(self):
        text = "This is a simple agreement with no definitions."
        aliases = run_scout_phase(text)
        assert aliases["LICENSOR"] == "UNKNOWN_LICENSOR"
        assert aliases["LICENSEE"] == "UNKNOWN_LICENSEE"

    def test_handles_empty_text(self):
        aliases = run_scout_phase("")
        assert aliases["LICENSOR"] == "UNKNOWN_LICENSOR"
        assert aliases["LICENSEE"] == "UNKNOWN_LICENSEE"
