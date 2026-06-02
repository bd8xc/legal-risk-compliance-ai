from chunking.semantic_repair import semantic_cleanup


class TestSemanticCleanup:
    def test_single_line_unchanged(self):
        text = "This is a single line."
        result = semantic_cleanup(text)
        assert "single line" in result

    def test_empty_string(self):
        assert semantic_cleanup("") == ""

    def test_whitespace_only(self):
        assert semantic_cleanup("   ") == ""

    def test_removes_placeholder_underscore_dot(self):
        text = "_____ . 2024"
        result = semantic_cleanup(text)
        assert "2024" in result

    def test_converts_underscore_dot_to_space(self):
        text = "_____ . 2024"
        result = semantic_cleanup(text)
        assert ". 2024" not in result

    def test_removes_ellipsis(self):
        text = "Some text…more text"
        result = semantic_cleanup(text)
        assert "…" not in result

    def test_removes_multiple_dots(self):
        text = "Some text.....more text"
        result = semantic_cleanup(text)
        assert "..." not in result or "....." not in result

    def test_removes_dt_dot(self):
        text = "dt. 2024"
        result = semantic_cleanup(text)
        assert "dt. " not in result
        assert "2024" in result

    def test_no_embedder_fallback_merges_continuation_lines(self):
        text = "This line ends\nthe next line continues"
        result = semantic_cleanup(text)
        assert "line ends the" in result.lower()
        assert "continues" in result
