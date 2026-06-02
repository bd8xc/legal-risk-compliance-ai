from chunking.clause_splitter import split_clauses


def test_empty_text_returns_empty_list():
    assert split_clauses("") == []


def test_whitespace_only_returns_empty():
    assert split_clauses("   \n\n  ") == []


def test_simple_article_and_clauses():
    text = (
        "ARTICLE 1 - SCOPE\n"
        "1.1 This is the first clause.\n"
        "1.2 This is the second clause.\n"
    )
    results = split_clauses(text)
    assert len(results) >= 1
    combined = " ".join(r["text"] for r in results)
    assert "first clause" in combined
    assert "second clause" in combined


def test_split_recitals():
    text = (
        "Preamble text before any articles.\n"
        "BETWEEN Party A and Party B.\n"
        "WHEREAS the parties agree.\n"
        "NOW THIS AGREEMENT WITNESSES.\n"
    )
    results = split_clauses(text)
    assert len(results) > 0


def test_alpha_subclauses():
    text = (
        "2.1 The Licensor grants a license.\n"
        "(a) Exclusive right to use.\n"
        "(b) Non-transferable.\n"
    )
    results = split_clauses(text)
    combined = " ".join(r["text"] for r in results)
    assert "Exclusive right to use" in combined
    assert "Non-transferable" in combined


def test_roman_subsubclauses():
    text = (
        "2.2 Fees.\n"
        "(a) Annual fee.\n"
        "(i) First year waived.\n"
        "(ii) Thereafter $100.\n"
    )
    results = split_clauses(text)
    combined = " ".join(r["text"] for r in results)
    assert "Annual fee" in combined
    assert "First year waived" in combined
    assert "Thereafter $100" in combined


def test_definitions():
    text = '"Effective Date" means the date of this agreement.\n"Confidential Information" shall mean proprietary data.\n'
    results = split_clauses(text)
    defs = [r for r in results if r.get("type") == "definition"]
    assert len(defs) >= 1
    assert any(r.get("term") == "Effective Date" for r in defs)


def test_annexure():
    text = "Annexure A - SERVICES\nA.1 Consulting.\nA.2 Support.\n"
    results = split_clauses(text)
    assert any("ANNEXA" in r["clause_id"] for r in results)


def test_schedule():
    text = "Schedule 1 - PRICING\n1.1 Fixed price.\n"
    results = split_clauses(text)
    assert any("ANNEX1" in r["clause_id"] for r in results)
