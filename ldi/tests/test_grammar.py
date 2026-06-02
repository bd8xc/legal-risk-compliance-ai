from chunking.grammar import (
    ALPHA_RE,
    ANNEX_RE,
    ARTICLE_RE,
    DEFINITION_RE,
    MAIN_RE,
    ROMAN_RE,
    SUBNUM_RE,
    TABLE_SPLIT_RE,
)


class TestArticleRE:
    def test_matches_article_number(self):
        m = ARTICLE_RE.match("ARTICLE 1 - DEFINITIONS")
        assert m is not None
        assert m.group(1) == "1"

    def test_matches_article_roman(self):
        m = ARTICLE_RE.match("ARTICLE IV - SCOPE")
        assert m is not None
        assert m.group(1) == "IV"

    def test_matches_lowercase_article(self):
        m = ARTICLE_RE.match("Article 2")
        assert m is not None
        assert m.group(1) == "2"

    def test_no_match_for_plain_text(self):
        assert ARTICLE_RE.match("This is a sentence.") is None

    def test_matches_with_dash_variant(self):
        m = ARTICLE_RE.match("ARTICLE 1—SCOPE")
        assert m is not None
        assert m.group(1) == "1"


class TestAnnexRE:
    def test_matches_annexure(self):
        m = ANNEX_RE.match("Annexure A - SERVICES")
        assert m is not None
        assert m.group(2) == "A"

    def test_matches_appendix(self):
        m = ANNEX_RE.match("Appendix I")
        assert m is not None
        assert m.group(2) == "I"

    def test_matches_schedule(self):
        m = ANNEX_RE.match("Schedule 1 - PRICING")
        assert m is not None
        assert m.group(2) == "1"

    def test_no_match_for_article(self):
        assert ANNEX_RE.match("ARTICLE 1") is None


class TestMainRE:
    def test_matches_single_digit(self):
        m = MAIN_RE.match("1. Scope")
        assert m is not None
        assert m.group(1) == "1"
        assert m.group(2) == "Scope"

    def test_matches_double_digit(self):
        m = MAIN_RE.match("2.1 Subclause")
        assert m is not None
        assert m.group(1) == "2.1"
        assert m.group(2) == "Subclause"

    def test_matches_triple_digit(self):
        m = MAIN_RE.match("3.1.2 Sub-subclause")
        assert m is not None
        assert m.group(1) == "3.1.2"
        assert m.group(2) == "Sub-subclause"

    def test_matches_with_parenthesis(self):
        m = MAIN_RE.match("1) First item")
        assert m is not None
        assert m.group(1) == "1"

    def test_no_match_for_plain_text(self):
        assert MAIN_RE.match("This is a sentence.") is None


class TestAlphaRE:
    def test_matches_parenthesized_letter(self):
        m = ALPHA_RE.match("(a) First subclause")
        assert m is not None
        assert m.group(1) == "a"
        assert m.group(2) == "First subclause"

    def test_matches_dot_letter(self):
        m = ALPHA_RE.match("b. Second item")
        assert m is not None
        assert m.group(1) == "b"

    def test_no_match_for_word_starting_with_letter(self):
        assert ALPHA_RE.match("a minimum of 10 units") is None

    def test_no_match_for_bare_letter(self):
        assert ALPHA_RE.match("a") is None


class TestRomanRE:
    def test_matches_parenthesized_roman(self):
        m = ROMAN_RE.match("(i) First sub-item")
        assert m is not None
        assert m.group(1) == "i"
        assert m.group(2) == "First sub-item"

    def test_matches_dot_roman(self):
        m = ROMAN_RE.match("ii. Second item")
        assert m is not None

    def test_matches_uppercase_roman(self):
        m = ROMAN_RE.match("(I) First")
        assert m is not None
        assert m.group(1) == "I"

    def test_no_match_for_arabic_number(self):
        assert ROMAN_RE.match("1) item") is None


class TestSubnumRE:
    def test_matches_parenthesized_number(self):
        m = SUBNUM_RE.match("(1) First bullet")
        assert m is not None
        assert m.group(1) == "1"

    def test_no_match_for_dotted_number(self):
        assert SUBNUM_RE.match("1. item") is None


class TestDefinitionRE:
    def test_matches_means(self):
        m = DEFINITION_RE.match('"Effective Date" means the date hereof.')
        assert m is not None
        assert m.group(1) == "Effective Date"

    def test_matches_shall_mean(self):
        m = DEFINITION_RE.match('"Confidential Information" shall mean all data.')
        assert m is not None
        assert m.group(1) == "Confidential Information"

    def test_matches_refers_to(self):
        m = DEFINITION_RE.match('"Term" refers to the duration.')
        assert m is not None
        assert m.group(1) == "Term"

    def test_no_match_for_unquoted(self):
        assert DEFINITION_RE.match("Effective Date means the date.") is None


class TestTableSplitRE:
    def test_splits_on_tab(self):
        parts = TABLE_SPLIT_RE.split("a\tb\tc")
        assert len(parts) == 3

    def test_splits_on_multiple_spaces(self):
        parts = TABLE_SPLIT_RE.split("a   b   c")
        assert len(parts) == 3

    def test_does_not_split_single_space(self):
        parts = TABLE_SPLIT_RE.split("a b c")
        assert len(parts) == 1

    def test_does_not_split_double_space(self):
        parts = TABLE_SPLIT_RE.split("a  b  c")
        assert len(parts) == 1
