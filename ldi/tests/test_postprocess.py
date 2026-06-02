import pytest
from chunking.postprocess import (
    merge_small_children,
    merge_short_heading_into_first_child,
    pack_small_preamble,
    pack_small_siblings,
)


def make_item(clause_id: str, text: str, level: str = "clause", section: str = "Document"):
    return {"clause_id": clause_id, "text": text, "level": level, "section": section}


class TestMergeSmallChildren:
    def test_merges_small_subclause_into_parent(self):
        items = [
            make_item("1", "Parent clause with some content here for testing.", level="clause"),
            make_item("1.1", "Small child.", level="subclause"),
        ]
        result = merge_small_children(items)
        assert len(result) == 1
        assert "[1.1]" in result[0]["text"]

    def test_skips_large_subclause(self):
        items = [
            make_item("1", "Parent."),
            make_item("1.1", "X" * 1000),
        ]
        result = merge_small_children(items)
        assert len(result) == 2

    def test_skips_clause_level_items(self):
        items = [
            make_item("1", "First clause."),
            make_item("2", "Second clause."),
        ]
        result = merge_small_children(items)
        assert len(result) == 2

    def test_empty_input(self):
        assert merge_small_children([]) == []

    def test_handles_items_without_clause_id(self):
        items = [{"text": "no id", "level": "subclause"}]
        result = merge_small_children(items)
        assert len(result) == 1


class TestMergeShortHeadingIntoFirstChild:
    def test_merges_short_heading(self):
        items = [
            make_item("2", "Governance"),
            make_item("2.1", "The board shall oversee."),
            make_item("2.2", "Management shall report."),
        ]
        result = merge_short_heading_into_first_child(items)
        assert len(result) == 2
        assert result[0]["text"].startswith("Governance")

    def test_skips_long_heading(self):
        items = [
            make_item("1", "A" * 200),
            make_item("1.1", "Child content."),
        ]
        result = merge_short_heading_into_first_child(items)
        assert len(result) == 2

    def test_skips_heading_with_newline(self):
        items = [
            make_item("1", "Multi\nline"),
            make_item("1.1", "Child."),
        ]
        result = merge_short_heading_into_first_child(items)
        assert len(result) == 2

    def test_empty_input(self):
        assert merge_short_heading_into_first_child([]) == []


class TestPackSmallPreamble:
    def test_merges_small_preamble_chunks(self):
        items = [
            make_item("P1", "Short preamble text.", level="clause"),
            make_item("P2", "Another short bit.", level="clause"),
            make_item("1", "First real clause.", level="clause"),
        ]
        result = pack_small_preamble(items)
        assert len(result) == 2
        assert result[0]["clause_id"] == "P1"

    def test_does_not_merge_non_preamble(self):
        items = [
            make_item("1", "First clause."),
            make_item("2", "Second clause."),
        ]
        result = pack_small_preamble(items)
        assert len(result) == 2

    def test_single_preamble_chunk(self):
        items = [make_item("P1", "This is a longer preamble text that exceeds the minimum word count threshold easily.", level="clause")]
        result = pack_small_preamble(items)
        assert len(result) == 1

    def test_empty_input(self):
        assert pack_small_preamble([]) == []


class TestPackSmallSiblings:
    def test_merges_small_siblings(self):
        items = [
            make_item("1.A", "Short a.", level="subclause"),
            make_item("1.B", "Short b.", level="subclause"),
            make_item("1.C", "Short c.", level="subclause"),
        ]
        result = pack_small_siblings(items)
        assert len(result) == 1

    def test_does_not_merge_large_siblings(self):
        items = [
            make_item("1.A", "Word " * 100, level="subclause"),
            make_item("1.B", "Word " * 100, level="subclause"),
        ]
        result = pack_small_siblings(items)
        assert len(result) == 2

    def test_skips_non_subclause_level(self):
        items = [make_item("1", "Some clause.")]
        result = pack_small_siblings(items)
        assert len(result) == 1

    def test_empty_input(self):
        assert pack_small_siblings([]) == []
