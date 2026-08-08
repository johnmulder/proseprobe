"""Tests for shared source-mapped prose sentences."""

import pytest

from slop_lint.parsers.prose import ProseSentence, iter_prose_sentences


def test_wrapped_sentences_preserve_source_positions() -> None:
    content = (
        "Dr. Rivera measured 3.14 ms at https://example.com.\n"
        "The result may\n"
        "possibly improve."
    )

    first, second = iter_prose_sentences(content, "notes.md")

    assert isinstance(first, ProseSentence)
    assert first.text == "Dr. Rivera measured 3.14 ms at https://example.com."
    assert (first.start_line, first.start_column) == (1, 1)
    assert second.text == "The result may\npossibly improve."
    assert (
        second.start_line,
        second.start_column,
        second.end_line,
        second.end_column,
    ) == (2, 1, 3, 18)
    assert second.source_position(second.text.index("possibly")) == (3, 1)
    assert second.source_text(content) == "The result may\npossibly improve."


def test_sentence_boundaries_keep_abbreviations_and_trailing_quotes() -> None:
    content = 'Prof. Chen works in the U.S. office. She said "Wait." Then left.'

    sentences = iter_prose_sentences(content, "notes.md")

    assert [sentence.text for sentence in sentences] == [
        "Prof. Chen works in the U.S. office.",
        'She said "Wait."',
        "Then left.",
    ]


def test_prose_blocks_become_hard_sentence_scopes() -> None:
    content = "First fragment\n\n> Second sentence.\n\n- Third sentence."

    sentences = iter_prose_sentences(content, "notes.md")

    assert [sentence.context for sentence in sentences] == [
        "body",
        "blockquote",
        "list_item",
    ]
    assert [sentence.scope_id for sentence in sentences] == [0, 1, 2]
    assert [sentence.break_before for sentence in sentences] == [False, True, True]


def test_break_before_marks_scopes_not_each_sentence() -> None:
    content = "First sentence. Second sentence.\n\nThird sentence."

    sentences = iter_prose_sentences(content, "notes.md")

    assert [sentence.break_before for sentence in sentences] == [False, False, True]


def test_plain_text_dispatch_preserves_unterminated_final_sentence() -> None:
    [sentence] = iter_prose_sentences("A final fragment", "notes.txt")

    assert sentence.text == "A final fragment"
    assert (sentence.start_line, sentence.start_column) == (1, 1)
    assert (sentence.end_line, sentence.end_column) == (1, 17)


def test_source_position_rejects_out_of_range_offsets() -> None:
    [sentence] = iter_prose_sentences("Short.", "notes.md")

    with pytest.raises(ValueError, match="outside sentence"):
        sentence.source_position(len(sentence.text) + 1)
