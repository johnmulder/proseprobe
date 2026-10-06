"""Tests for shared source-mapped prose sentences."""

import pytest

from proseprobe.parsers.prose import ProseSentence, iter_prose_sentences


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


@pytest.mark.parametrize(
    ("source", "first_sentence"),
    [
        (
            "Use a stable format, e.g. JSON. Continue.",
            "Use a stable format, e.g. JSON.",
        ),
        (
            "The format is text, i.e. UTF-8. Continue.",
            "The format is text, i.e. UTF-8.",
        ),
        (
            "Keep logs, metrics, etc. during rollout. Continue.",
            "Keep logs, metrics, etc. during rollout.",
        ),
    ],
)
def test_sentence_boundaries_keep_conventional_latin_abbreviations(
    source: str,
    first_sentence: str,
) -> None:
    sentences = iter_prose_sentences(source, "notes.md")

    assert [sentence.text for sentence in sentences] == [first_sentence, "Continue."]


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


def test_original_sentence_windows_share_one_source_split() -> None:
    class CountedSource(str):
        split_calls = 0

        def split(self, sep: str | None = None, maxsplit: int = -1) -> list[str]:
            self.split_calls += 1
            return super().split(sep, maxsplit)

    source = CountedSource(
        "First `quoted` sentence.\nSecond [linked](https://example.test/path) sentence."
    )
    sentences = iter_prose_sentences(source, "source-windows.md")
    parser_splits = source.split_calls
    for _pass in range(5):
        assert [sentence.source_text(source) for sentence in sentences] == [
            "First `quoted` sentence.",
            "Second [linked](https://example.test/path) sentence.",
        ]
    assert source.split_calls - parser_splits == 1
