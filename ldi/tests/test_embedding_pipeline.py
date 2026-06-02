import pytest

pytestmark = pytest.mark.requires_chromadb

from embeddings.pipeline import embed_and_store


def test_embed_and_store_empty_clauses():
    result = embed_and_store([], "test_file.txt")
    assert result == {"clauses": 0, "embedding_dim": 0}


def test_embed_and_store_with_clauses():
    clauses = [
        {"clause_id": "1", "text": "This is the first test clause for embedding.", "section": "ART1", "level": "clause"},
        {"clause_id": "2", "text": "This is the second test clause for embedding purposes.", "section": "ART2", "level": "clause"},
    ]
    result = embed_and_store(clauses, "test_doc.txt")
    assert result["clauses"] == 2
    assert result["embedding_dim"] == 384


def test_embed_and_store_skips_empty_text():
    clauses = [
        {"clause_id": "1", "text": "", "section": "ART1", "level": "clause"},
        {"clause_id": "2", "text": "Valid text here.", "section": "ART2", "level": "clause"},
    ]
    result = embed_and_store(clauses, "test.txt")
    assert result["clauses"] == 1


def test_embed_and_store_deduplicates_ids():
    clauses = [
        {"clause_id": "1", "text": "First clause text.", "section": "ART1", "level": "clause"},
        {"clause_id": "1", "text": "Duplicate ID clause.", "section": "ART1", "level": "clause"},
    ]
    result = embed_and_store(clauses, "doc.txt")
    assert result["clauses"] == 2


def test_embed_and_store_metadata_includes_table_context():
    clauses = [
        {"clause_id": "T1", "text": "a\tb\tc", "section": "ART1", "level": "table", "table_context": "ARTICLE 1"},
    ]
    result = embed_and_store(clauses, "doc.txt")
    assert result["clauses"] == 1
