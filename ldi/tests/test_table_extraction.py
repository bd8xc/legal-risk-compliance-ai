from chunking.table_extraction import extract_tables, looks_like_table_row


class TestLooksLikeTableRow:
    def test_tab_separated_returns_true(self):
        assert looks_like_table_row("Name\tType\tAmount")

    def test_space_separated_returns_true(self):
        assert looks_like_table_row("Name    Type    Amount")

    def test_single_column_returns_false(self):
        assert not looks_like_table_row("Just a single column of text")

    def test_two_columns_returns_false(self):
        assert not looks_like_table_row("Name    Type")

    def test_empty_string_returns_false(self):
        assert not looks_like_table_row("")

    def test_short_cells_heuristic(self):
        assert looks_like_table_row("a\tb\tc\td")

    def test_long_cells_no_match(self):
        assert not looks_like_table_row("a" * 50 + "\t" + "b" * 50 + "\t" + "c" * 50)


class TestExtractTables:
    def test_extracts_simple_table(self):
        lines = [
            "Some header text.",
            "Name\tType\tAmount",
            "Setup\tOne-time\t5000",
            "Annual\tRecurring\t12000",
        ]
        tables, cleaned = extract_tables(lines)
        assert len(tables) == 1
        assert tables[0]["level"] == "table"
        assert "Name" in tables[0]["text"]

    def test_skipped_invalid_table(self):
        lines = [
            "Name\tType",
            "Setup\tOne-time",
        ]
        tables, cleaned = extract_tables(lines)
        assert len(tables) == 0

    def test_returns_cleaned_non_table_lines(self):
        lines = [
            "Normal paragraph line.",
            "Name\tType\tAmount",
            "Setup\tOne-time\t5000",
            "Annual\tRecurring\t12000",
            "Another normal line.",
        ]
        tables, cleaned = extract_tables(lines)
        assert len(tables) == 1
        assert "Normal paragraph line." in cleaned
        assert "Another normal line." in cleaned

    def test_no_table_lines(self):
        lines = ["Just some text.", "More text here."]
        tables, cleaned = extract_tables(lines)
        assert len(tables) == 0
        assert len(cleaned) == 2

    def test_empty_input(self):
        tables, cleaned = extract_tables([])
        assert tables == []
        assert cleaned == []

    def test_table_after_article_heading(self):
        lines = [
            "ARTICLE 1 - FEES",
            "Name\tType\tAmount",
            "Setup\tOne-time\t5000",
            "Annual\tRecurring\t12000",
        ]
        tables, cleaned = extract_tables(lines)
        assert len(tables) == 1
        assert tables[0]["table_context"] == "ARTICLE 1 - FEES"
