"""
ClauseRetriever: Semantic search over embedded legal clauses in ChromaDB.
"""
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

class ClauseRetriever:
    """
    Retrieves most similar legal clauses to a query using embeddings and ChromaDB.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", persist_directory: str = "./chroma", collection_name: str = "clauses"):
        self._model = SentenceTransformer(model_name)
        self._client = chromadb.PersistentClient(path=persist_directory, settings=Settings(allow_reset=True))
        self._collection = self._client.get_or_create_collection(collection_name)

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for the top-k most similar clauses to the query string.
        Args:
            query (str): Query text.
            k (int): Number of results to return.
        Returns:
            List[Dict]: List of matching clause dicts with metadata and score.
        """
        if not query:
            return []
        query_emb = self._model.encode([query], show_progress_bar=False, convert_to_numpy=True)[0]
        try:
            results = self._collection.query(query_embeddings=[query_emb.tolist()], n_results=k)
        except Exception:
            return []
        matches = []
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        documents = results.get("documents", [[]])[0]
        scores = results.get("distances", [[]])[0] if "distances" in results else [None]*len(ids)
        for i in range(len(ids)):
            meta = metadatas[i] if i < len(metadatas) else {}
            matches.append({
                "clause_id": meta.get("clause_id"),
                "section": meta.get("section"),
                "level": meta.get("level"),
                "file_name": meta.get("file_name"),
                "text": documents[i] if i < len(documents) else None,
                "score": float(scores[i]) if scores and i < len(scores) and scores[i] is not None else None
            })
        return matches
