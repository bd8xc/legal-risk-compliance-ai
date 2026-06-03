"""
ClauseVectorStore: Handles persistent storage and retrieval of clause embeddings using ChromaDB.
"""
from typing import List, Dict, Any
import json
import os
import numpy as np
import chromadb
from chromadb.config import Settings

class ClauseVectorStore:
    """
    Stores and retrieves clause embeddings and metadata in a persistent ChromaDB collection.
    """
    def __init__(self, persist_directory: str | None = None, collection_name: str = "clauses"):
        # Default to a workspace-local data folder under the contract_risk package
        if persist_directory is None:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_risk", "data")
            persist_directory = os.path.join(base_dir, "chroma")
        # ensure directory exists for chroma persistence and cache
        os.makedirs(persist_directory, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_directory, settings=Settings(allow_reset=True))
        self._collection = self._client.get_or_create_collection(collection_name)
        self._document_cache_path = os.path.join(persist_directory, "document_hash_cache.json")
        self._document_cache = self._load_document_cache()

    def _load_document_cache(self) -> Dict[str, Any]:
        if not os.path.exists(self._document_cache_path):
            return {"known_hashes": [], "file_name_to_hash": {}}
        try:
            with open(self._document_cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {"known_hashes": [], "file_name_to_hash": {}}
        if not isinstance(data, dict):
            return {"known_hashes": [], "file_name_to_hash": {}}
        return {
            "known_hashes": list(data.get("known_hashes", [])),
            "file_name_to_hash": dict(data.get("file_name_to_hash", {})),
        }

    def _save_document_cache(self) -> None:
        temp_path = f"{self._document_cache_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self._document_cache, f, indent=2)
        os.replace(temp_path, self._document_cache_path)

    def is_document_indexed(self, document_hash: str) -> bool:
        return document_hash in self._document_cache.get("known_hashes", [])

    def register_document(self, document_hash: str, file_name: str) -> None:
        if document_hash not in self._document_cache["known_hashes"]:
            self._document_cache["known_hashes"].append(document_hash)
        self._document_cache["file_name_to_hash"][file_name] = document_hash
        self._save_document_cache()

    def add(self, ids: List[str], texts: List[str], embeddings: np.ndarray, metadatas: List[Dict[str, Any]]):
        """
        Add embeddings and metadata to the vector store.
        Args:
            ids (List[str]): Unique IDs for each clause.
            texts (List[str]): Clause texts.
            embeddings (np.ndarray): Embeddings array.
            metadatas (List[Dict[str, Any]]): Metadata dicts for each clause.
        """
        if not ids or len(ids) != len(texts) or len(ids) != len(embeddings) or len(ids) != len(metadatas):
            raise ValueError("Input lists must be non-empty and of equal length.")
        # Use upsert so re-indexing the same IDs updates rows instead of failing.
        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings.tolist(),
            metadatas=metadatas
        )

    def get_clauses(self, where: Dict[str, Any] = None, limit: int = 1000, offset: int = 0, include=None) -> Dict[str, Any]:
        """Retrieve clauses from the vector store matching a metadata filter."""
        if include is None:
            include = ["ids", "metadatas", "documents"]
        return self._collection.get(where=where or {}, limit=limit, offset=offset, include=include)

    def search(self, query_embedding: np.ndarray, k: int = 5, where: Dict[str, Any] = None):
        """
        Search for the top-k most similar clauses to the query embedding.
        Args:
            query_embedding (np.ndarray): Query embedding vector.
            k (int): Number of results to return.
            where (Dict[str, Any]): Optional metadata filter.
        Returns:
            List[Dict]: List of matching clause metadata and scores.
        """
        results = self._collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=k,
            where=where,
        )
        return results
