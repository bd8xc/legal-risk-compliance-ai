import pytest

pytestmark = pytest.mark.requires_chromadb

from search.retriever import ClauseRetriever


def test_search_empty_query():
    retriever = ClauseRetriever(persist_directory="./chroma", collection_name="empty_test")
    results = retriever.search("", k=5)
    assert results == []


def test_search_empty_collection():
    retriever = ClauseRetriever(persist_directory="./chroma", collection_name="empty_test2")
    results = retriever.search("some query", k=5)
    assert results == []


def test_table_prioritization_heuristic():
    retriever = ClauseRetriever(persist_directory="./chroma", collection_name="heuristic_test")
    assert retriever._should_prioritize_tables("show table of fees")
    assert retriever._should_prioritize_tables("tabular format")
    assert retriever._should_prioritize_tables("rows and columns")
    assert not retriever._should_prioritize_tables("what are the fees")
    assert not retriever._should_prioritize_tables("")


def test_format_table_text():
    retriever = ClauseRetriever(persist_directory="./chroma", collection_name="format_test")
    table_text = "Name\tType\tAmount\nSetup\tOne-time\t5000"
    formatted = retriever._format_table_text(table_text)
    assert " | " in formatted
    assert "Name | Type | Amount" in formatted
    assert "Setup | One-time | 5000" in formatted
