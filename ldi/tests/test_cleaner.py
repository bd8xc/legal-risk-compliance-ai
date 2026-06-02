from ingestion.cleaner import clean_text


def test_clean_text_removes_extra_whitespace():
    result = clean_text("hello    world\n\n\nfoo   bar")
    assert result == "hello world foo bar"


def test_clean_text_handles_empty_string():
    assert clean_text("") == ""


def test_clean_text_handles_whitespace_only():
    assert clean_text("   \n\n   ") == ""


def test_clean_text_preserves_single_word():
    assert clean_text("hello") == "hello"


def test_clean_text_normalizes_newlines():
    result = clean_text("line1\nline2\nline3")
    assert result == "line1 line2 line3"


def test_clean_text_strips_leading_trailing():
    result = clean_text("  hello world  ")
    assert result == "hello world"


def test_clean_text_handles_tabs():
    result = clean_text("hello\tworld")
    assert result == "hello world"
