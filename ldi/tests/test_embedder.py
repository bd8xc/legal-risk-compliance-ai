import pytest
from chunking.semantic_repair import _get_cleanup_embedder

pytestmark = pytest.mark.requires_transformers


def test_get_cleanup_embedder_returns_model():
    embedder = _get_cleanup_embedder()
    assert embedder is not None


def test_embedder_produces_correct_dimensions():
    embedder = _get_cleanup_embedder()
    texts = ["This is a test sentence.", "Another legal clause here."]
    embeddings = embedder.encode(texts)
    assert embeddings.shape[0] == 2
    assert embeddings.shape[1] == 384  # all-MiniLM-L6-v2 dimension
