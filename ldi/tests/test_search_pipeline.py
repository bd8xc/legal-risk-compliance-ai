import pytest

pytestmark = pytest.mark.requires_chromadb

from search.pipeline import search_clauses


def test_search_clauses_empty_result():
    results = search_clauses("nonexistent query for empty db", k=3)
    assert isinstance(results, list)
