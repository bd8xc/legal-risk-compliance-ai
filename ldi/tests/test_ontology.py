# ldi/tests/test_ontology.py
import pytest
from ldi.config.ontology import ALLOWED_NODE_TYPES, ALLOWED_RELATIONSHIP_TYPES

def test_ontology_structures_are_populated():
    """Ensures that the expanded 50-element legal ontology arrays load successfully."""
    assert isinstance(ALLOWED_NODE_TYPES, list)
    assert isinstance(ALLOWED_RELATIONSHIP_TYPES, list)
    assert len(ALLOWED_NODE_TYPES) == 25
    assert len(ALLOWED_RELATIONSHIP_TYPES) == 25

def test_ontology_enforces_strict_uppercase():
    """Guarantees all ontology string tokens are normalized uppercase to protect database matches."""
    for node_type in ALLOWED_NODE_TYPES:
        assert node_type == node_type.upper().strip()
        assert " " not in node_type  # Must use underscores, no spaces allowed
        
    for rel_type in ALLOWED_RELATIONSHIP_TYPES:
        assert rel_type == rel_type.upper().strip()
        assert " " not in rel_type

def test_critical_compliance_types_exist():
    """Verifies that mandatory nodes and relationships for LEXGUARD are present."""
    assert "FINANCIAL_INSTITUTION" in ALLOWED_NODE_TYPES
    assert "OUTBOUND_SHIPMENT" in ALLOWED_NODE_TYPES
    assert "PROCESSES_DATA_FOR" in ALLOWED_RELATIONSHIP_TYPES
    assert "LITIGATING_AGAINST" in ALLOWED_RELATIONSHIP_TYPES