"""V001 recognizes record identities without hiding nearby generic vocabulary."""

import pytest

from proseprobe.rules.vocab import AIVocabularyRule


@pytest.mark.parametrize(
    "text",
    [
        "Reject a duplicate key in either input.",
        "Reject duplicate keys in either input.",
        "Resolve the key path before reading the record.",
        "Validate key paths before comparing records.",
        "Each record key identifies one input record.",
        "Record keys identify input records.",
        "The record identity key identifies its record.",
        "Record identity keys identify input records.",
        "Reject a DUPLICATE KEY in either input.",
        "The RECORD IDENTITY KEY identifies its record.",
    ],
)
def test_preserves_new_technical_key_noun_contexts(text: str) -> None:
    assert AIVocabularyRule().check(text, "guide.md") == []


@pytest.mark.parametrize(
    "text",
    [
        "Reject a duplicate\nkey in either input.",
        "Resolve the key\npath before reading the record.",
        "Each record\nkey identifies one input record.",
        "The record identity\nkey identifies its record.",
    ],
)
@pytest.mark.parametrize("style", ["markdown", "docstring", "comment", "blockquote"])
def test_technical_key_context_survives_prose_wrapping(text: str, style: str) -> None:
    if style == "markdown":
        source, filename = text, "guide.md"
    elif style == "docstring":
        source, filename = f'"""{text}"""', "guide.py"
    else:
        prefix = "# " if style == "comment" else "> "
        source = "\n".join(prefix + line for line in text.splitlines())
        filename = "guide.py" if style == "comment" else "guide.md"
    assert AIVocabularyRule().check(source, filename) == []


@pytest.mark.parametrize(
    "text",
    [
        "Pass --key id to select the record identity.",
        "Pass --key=id to select the record identity.",
        "Pass --array-key name when sorting arrays.",
        "Pass --array-key=name when sorting arrays.",
        "Select the record identity (--key).",
        "Select --key, then compare the records.",
        "Pass --other-key id to select the record identity.",
        "Pass --key-name id to select the record identity.",
        "Pass --KEY id to select the record identity.",
        "Pass --array-key-name id to select the record identity.",
        "Pass --key-key id to select the record identity.",
    ],
)
def test_preserves_complete_ascii_option_identifiers(text: str) -> None:
    assert AIVocabularyRule().check(text, "guide.md") == []


@pytest.mark.parametrize(
    "noun",
    [
        "benefit",
        "feature",
        "factor",
        "point",
        "idea",
        "element",
        "step",
        "role",
        "insight",
        "benefits",
        "features",
        "factors",
        "points",
        "ideas",
        "elements",
        "steps",
        "roles",
        "insights",
    ],
)
def test_generic_key_adjectives_still_receive_review(noun: str) -> None:
    text = f"This is a key {noun}."
    [issue] = AIVocabularyRule().check(text, "guide.md")
    assert text[issue.column - 1 : issue.end_column - 1] == "key"


@pytest.mark.parametrize("prefix", ["duplicate", "record", "record identity"])
@pytest.mark.parametrize(
    "noun",
    [
        "benefit",
        "feature",
        "factor",
        "point",
        "idea",
        "element",
        "step",
        "role",
        "insight",
        "benefits",
        "features",
        "factors",
        "points",
        "ideas",
        "elements",
        "steps",
        "roles",
        "insights",
    ],
)
def test_technical_prefix_cannot_exempt_a_generic_key_adjective(
    prefix: str, noun: str
) -> None:
    text = f"The report describes a {prefix} key {noun}."
    [issue] = AIVocabularyRule().check(text, "guide.md")
    assert issue.column == text.index("key") + 1
    assert issue.end_column == issue.column + 3


@pytest.mark.parametrize(
    "text",
    [
        "Duplicate key validation exposes a key benefit.",
        "The key path identifies a key role.",
        "The record key identifies a key factor.",
        "The record identity key identifies a key insight.",
        "Pass --key id and --array-key name to expose a key benefit.",
        "Reject a duplicate\nkey, then note the key insight.",
        "İ/O preserves the DUPLICATE KEY and describes a key benefit.",
    ],
)
def test_only_the_technical_occurrence_is_preserved(text: str) -> None:
    [issue] = AIVocabularyRule().check(text, "guide.md")
    line = text.splitlines()[issue.line - 1]
    assert issue.column == line.rindex("key") + 1
    assert issue.end_column == issue.column + 3
    assert line[issue.column - 1 : issue.end_column - 1] == "key"


@pytest.mark.parametrize("style", ["markdown", "docstring", "comment", "blockquote"])
def test_generic_occurrence_keeps_exact_unicode_source_coordinates(style: str) -> None:
    text = "İ/O rejects a duplicate\nkey but describes a key benefit."
    if style == "markdown":
        source, filename = text, "guide.md"
    elif style == "docstring":
        source, filename = f'"""{text}"""', "guide.py"
    else:
        prefix = "# " if style == "comment" else "> "
        source = "\n".join(prefix + line for line in text.splitlines())
        filename = "guide.py" if style == "comment" else "guide.md"
    [issue] = AIVocabularyRule().check(source, filename)
    line = source.splitlines()[1]
    assert issue.line == 2
    assert issue.column == line.rindex("key") + 1
    assert issue.end_column == issue.column + 3
    assert line[issue.column - 1 : issue.end_column - 1] == "key"


def test_technical_key_exception_does_not_hide_other_vocabulary() -> None:
    text = "Duplicate key validation supports robust defaults."
    [issue] = AIVocabularyRule().check(text, "guide.md")
    assert issue.column == text.index("robust") + 1
    assert issue.end_column == issue.column + len("robust")


def test_option_names_preserve_only_identifier_spans_not_values_or_other_words() -> (
    None
):
    text = "Use --key-key='key benefit' with robust defaults."
    issues = AIVocabularyRule().check(text, "guide.md")
    assert [text[issue.column - 1 : issue.end_column - 1] for issue in issues] == [
        "key",
        "robust",
    ]
    assert issues[0].column == text.index("key benefit") + 1


@pytest.mark.parametrize(
    "text",
    [
        "Follow a key path to success.",
        "Find a key path for growth.",
        "Follow a key path toward success.",
        "Follow a key path towards success.",
        "Follow a key\npath to success.",
        "Find a KEY PATH FOR growth.",
    ],
)
def test_figurative_key_paths_keep_review_prompts(text: str) -> None:
    [issue] = AIVocabularyRule().check(text, "guide.md")
    line = text.splitlines()[issue.line - 1]
    assert line[issue.column - 1 : issue.end_column - 1].casefold() == "key"


@pytest.mark.parametrize(
    "source",
    [
        "duplicate\n\nkey identifies the record.",
        "record\n\nkey identifies the record.",
        "record identity\n\nkey identifies the record.",
        "- duplicate\n- key identifies the record.",
        "- record identity\n- key identifies the record.",
        "> duplicate\n>\n> key identifies the record.",
        "duplicate `hidden` key identifies the record.",
        "record identity <code>hidden</code> key identifies the record.",
        "record `identity` key identifies the record.",
    ],
)
def test_disconnected_contexts_cannot_supply_a_technical_key_exemption(
    source: str,
) -> None:
    [issue] = AIVocabularyRule().check(source, "guide.md")
    line = source.splitlines()[issue.line - 1]
    assert line[issue.column - 1 : issue.end_column - 1] == "key"


@pytest.mark.parametrize(
    "text",
    [
        "Pass ---key id to the parser.",
        "Pass -- key id to the parser.",
        "Pass --array--key id to the parser.",
        "Pass prefix--key id to the parser.",
        "Pass --key/path to the parser.",
        "Pass --key.value to the parser.",
        "Pass --array-key.value to the parser.",
        "Pass --\nkey id to the parser.",
        "Pass --array-\nkey id to the parser.",
        "Pass --key- id to the parser.",
        "Pass --key--name id to the parser.",
        "Pass --é-key id to the parser.",
        "Pass --key-é id to the parser.",
    ],
)
def test_malformed_option_tokens_keep_review_prompts(text: str) -> None:
    [issue] = AIVocabularyRule().check(text, "guide.md")
    line = text.splitlines()[issue.line - 1]
    assert line[issue.column - 1 : issue.end_column - 1] == "key"
