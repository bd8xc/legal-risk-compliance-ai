import pytest
import os

pytestmark = pytest.mark.requires_pdfplumber

from ingestion.pdf_table_loader import extract_pdf_text_and_tables


TEST_DIR = os.path.join(os.path.dirname(__file__), "sample legal docs")


def _sample_path(name):
    path = os.path.join(TEST_DIR, name)
    if not os.path.exists(path):
        pytest.skip(f"Sample PDF not found: {path}")
    return path


def test_extract_pdf_returns_dict():
    path = _sample_path("SampleContract-Shuttle.pdf")
    result = extract_pdf_text_and_tables(path)
    assert isinstance(result, dict)
    assert "text" in result
    assert "tables" in result


def test_extract_pdf_text_non_empty():
    path = _sample_path("SampleContract-Shuttle.pdf")
    result = extract_pdf_text_and_tables(path)
    assert len(result["text"].strip()) > 0


def test_extract_pdf_tables_is_list():
    path = _sample_path("SampleContract-Shuttle.pdf")
    result = extract_pdf_text_and_tables(path)
    assert isinstance(result["tables"], list)


def test_extract_pdf_coe_sample():
    path = _sample_path("COE-Sample.pdf")
    result = extract_pdf_text_and_tables(path)
    assert len(result["text"].strip()) > 0
