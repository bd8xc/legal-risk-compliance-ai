# ldi/tests/test_graph_schemas.py
import pytest
from pydantic import ValidationError
from ldi.graph.engine import Node, Relationship, KnowledgeGraphExtraction

def test_pydantic_valid_node_parsing():
    """Verifies that standard, approved node categories instantiate flawlessly."""
    node = Node(name="CANARA BANK", type="FINANCIAL_INSTITUTION")
    assert node.name == "CANARA BANK"
    assert node.type == "FINANCIAL_INSTITUTION"

def test_pydantic_invalid_node_type_rejection():
    """Ensures out-of-bounds entity types instantly trip a validation error."""
    with pytest.raises(ValidationError) as exc_info:
        Node(name="UNKNOWN NODE", type="UNAPPROVED_HALLUCINATED_TYPE")
    assert "rejected" in str(exc_info.value)

def test_pydantic_valid_relationship_parsing():
    """Checks that approved relationship channels connect without issues."""
    rel = Relationship(source="VANGUARD TECH GROUP", target="HORIZON HOLDINGS", type="SUBSIDIARY_OF")
    assert rel.type == "SUBSIDIARY_OF"

def test_pydantic_invalid_relationship_rejection():
    """Guarantees conversational edge text is rejected by the schema validation walls."""
    with pytest.raises(ValidationError) as exc_info:
        Relationship(source="COMPANY A", target="COMPANY B", type="AGREED_TO_PARTNER_WITH")
    assert "rejected" in str(exc_info.value)

def test_knowledge_graph_mesh_integrity():
    """Validates the parent mesh schema tracks node and edge sets cleanly."""
    mesh = KnowledgeGraphExtraction(
        nodes=[Node(name="TEST CORP", type="COMPANY")],
        relationships=[]
    )
    assert len(mesh.nodes) == 1
    assert isinstance(mesh.relationships, list)