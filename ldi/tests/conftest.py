from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_transformers: skip if sentence_transformers not importable")
    config.addinivalue_line("markers", "requires_chromadb: skip if chromadb not importable")
    config.addinivalue_line("markers", "requires_ollama: skip if ollama not importable")
    config.addinivalue_line("markers", "requires_pdfplumber: skip if pdfplumber not importable")
    config.addinivalue_line("markers", "requires_docx: skip if python-docx not importable")
    config.addinivalue_line("markers", "requires_pypdf: skip if pypdf not importable")


def _import_version(mod: str) -> str | None:
    try:
        import importlib
        m = importlib.import_module(mod)
        return getattr(m, "__version__", None) or "present"
    except ImportError:
        return None


def pytest_runtest_setup(item):
    deps = {
        "requires_transformers": "sentence_transformers",
        "requires_chromadb": "chromadb",
        "requires_ollama": "ollama",
        "requires_pdfplumber": "pdfplumber",
        "requires_docx": "docx",
        "requires_pypdf": "pypdf",
    }
    for marker, mod in deps.items():
        if item.get_closest_marker(marker):
            if _import_version(mod) is None:
                pytest.skip(f"requires {mod}")


SAMPLE_ARTICLE_TEXT = (
    "THIS AGREEMENT is made on this 1st day of January 2024.\n\n"
    "BETWEEN Party A and Party B.\n\n"
    "WHEREAS the parties wish to enter into this agreement.\n\n"
    "ARTICLE 1 - DEFINITIONS\n"
    "1.1 'Confidential Information' means any proprietary information.\n"
    "1.2 'Effective Date' means the date of this agreement.\n\n"
    "ARTICLE 2 - SCOPE\n"
    "2.1 The Licensor grants a license to the Licensee.\n"
    "2.2 The Licensee shall pay fees as set out herein.\n"
    "(a) Annual base fee of $100,000.\n"
    "(b) Additional fees for overage.\n"
    "(i) First 1000 units are free.\n"
    "(ii) Thereafter $10 per unit.\n"
    "2.3 This clause has no subparts.\n\n"
    "IN WITNESS WHEREOF the parties have executed this agreement.\n"
)

SAMPLE_DEFINITION_TEXT = (
    '"Effective Date" means the date of this agreement.\n'
    '"Confidential Information" shall mean all proprietary data.\n'
    '"Term" refers to the duration of this agreement.\n'
)

SAMPLE_WITH_TABLES = (
    "ARTICLE 1 - FEES\n"
    "1.1 The following fee schedule applies:\n"
    "Name\tType\tAmount\tCurrency\n"
    "Setup\tOne-time\t5000\tUSD\n"
    "Annual\tRecurring\t12000\tUSD\n"
    "Support\tMonthly\t500\tUSD\n"
)

SAMPLE_PREAMBLE_ONLY = (
    "THIS AGREEMENT is made on 1 Jan 2024 between ABC Corp and XYZ Ltd.\n\n"
    "WHEREAS ABC Corp is a technology company.\n\n"
    "WHEREAS XYZ Ltd desires to use the software.\n\n"
    "NOW THIS AGREEMENT WITNESSES as follows:\n"
)

SAMPLE_ANNEX_TEXT = (
    "Annexure A - SERVICES\n"
    "A.1 Consulting Services\n"
    "A.2 Support Services\n\n"
    "Schedule B - PRICING\n"
    "B.1 Fixed Price\n"
    "B.2 Variable Price\n"
)
