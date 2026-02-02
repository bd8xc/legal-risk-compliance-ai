"""
Embedding pipeline for legal clause chunks.
"""
from typing import List, Dict, Any
from .embedder import ClauseEmbedder
from .vector_store import ClauseVectorStore


def embed_and_store(clauses: List[Dict[str, Any]], file_name: str) -> Dict[str, Any]:
    """
    Embeds clauses and stores them in the vector store with metadata.
    Args:
        clauses (List[Dict]): List of clause dicts.
        file_name (str): Name of the source file.
    Returns:
        Dict: Stats about the embedding process.
    """
    if not clauses:
        return {"clauses": 0, "embedding_dim": 0}

    texts = [c["text"] for c in clauses]
    ids = [c["clause_id"] for c in clauses]
    metadatas = [
        {
            "clause_id": c["clause_id"],
            "section": c.get("section"),
            "level": c.get("level"),
            "file_name": file_name
        }
        for c in clauses
    ]

    embedder = ClauseEmbedder()
    embeddings = embedder.embed(texts)
    vector_store = ClauseVectorStore()
    vector_store.add(ids, texts, embeddings, metadatas)

    return {"clauses": len(clauses), "embedding_dim": embeddings.shape[1] if embeddings.shape else 0}
