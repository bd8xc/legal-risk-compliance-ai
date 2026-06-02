from typing import List, Literal
from pydantic import BaseModel, Field

class ExtractedNode(BaseModel):
    name: str = Field(
        ..., 
        description="The official name of the entity, normalized to uppercase text strings without punctuation (e.g., 'ACME CORP')"
    )
    type: Literal["COMPANY", "DIRECTOR", "LAW_FIRM", "CONTRACT", "DISPUTE"]

class ExtractedRelationship(BaseModel):
    source: str = Field(..., description="Name of the source node exactly matching an extracted node name")
    target: str = Field(..., description="Name of the target node exactly matching an extracted node name")
    type: Literal["SUBSIDIARY_OF", "LITIGATING_AGAINST", "REPRESENTS", "CONTRACT_WITH"]

class KnowledgeGraphExtraction(BaseModel):
    nodes: List[ExtractedNode] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)