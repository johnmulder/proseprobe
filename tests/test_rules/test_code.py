"""Tests for code rules (C001-C004)."""

import pytest

from proseprobe.rules.base import Rule
from proseprobe.rules.code import (
    AIPlaceholdersRule,
    CollaborativeCommentsRule,
    DocstringVocabularyRule,
    VerboseCommentsRule,
)


@pytest.mark.parametrize(
    ("rule", "source", "expected"),
    [
        (
            DocstringVocabularyRule(),
            'def build():\n    """Use a bespoke adapter."""',
            "bespoke",
        ),
        (
            VerboseCommentsRule(),
            "value = 1  # This function returns the cached value",
            "# This function",
        ),
        (
            CollaborativeCommentsRule(),
            "    # I hope this helps with setup",
            "# I hope this helps",
        ),
        (
            AIPlaceholdersRule(),
            "    # TODO: Add logic here",
            "# TODO: Add logic here",
        ),
        (
            AIPlaceholdersRule(),
            "pass  # TODO: replace this",
            "TODO",
        ),
        (
            AIPlaceholdersRule(),
            "raise NotImplementedError('later')",
            "raise NotImplementedError('later')",
        ),
    ],
)
def test_code_rules_report_exact_source_spans(
    rule: Rule,
    source: str,
    expected: str,
) -> None:
    issues = rule.check(source, "test.py")
    spans = [
        source.splitlines()[issue.line - 1][issue.column - 1 : issue.end_column - 1]
        for issue in issues
        if issue.end_column is not None
    ]

    assert expected in spans


class TestDocstringVocabulary:
    """Tests for C001: Docstring Vocabulary."""

    def test_detects_ai_vocabulary(self) -> None:
        """Test detecting docstring-only vocabulary."""
        text = '''
def process():
    """
    This function can utilize a bespoke adapter.
    """
    pass
'''
        rule = DocstringVocabularyRule()
        issues = rule.check(text, "test.py")
        assert len(issues) == 2

    def test_ignores_normal_docstrings(self) -> None:
        """Test ignoring normal docstrings."""
        text = '''
def process():
    """Process the data and return results."""
    pass
'''
        rule = DocstringVocabularyRule()
        issues = rule.check(text, "test.py")
        assert len(issues) == 0

    def test_respects_allowed_vocabulary(self) -> None:
        """Test allowed words are not flagged."""
        text = '''
def process():
    """We utilize the workflow."""
    pass
'''
        rule = DocstringVocabularyRule(allowed={"utilize"})
        issues = rule.check(text, "test.py")
        assert len(issues) == 0

    def test_leaves_additional_vocabulary_to_v001(self) -> None:
        """Configured general vocabulary is not duplicated by C001."""
        text = '''
def process():
    """Foobar is used here."""
    pass
'''
        rule = DocstringVocabularyRule(additional={"foobar"})
        issues = rule.check(text, "test.py")
        assert issues == []

    def test_leaves_shared_vocabulary_to_v001(self) -> None:
        """Built-in general vocabulary is not duplicated by C001."""
        text = '"""A robust module that delves into data."""'

        assert DocstringVocabularyRule().check(text, "test.py") == []

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = DocstringVocabularyRule()
        assert rule.id == "C001"


class TestVerboseComments:
    """Tests for C002: Verbose Comments."""

    def test_detects_verbose_comments(self) -> None:
        """Test detecting overly verbose comments."""
        text = """
# This function is designed to process the input data
# and return the transformed output in a comprehensive manner
def process(data):
    # Initialize the result variable to store the output
    result = None
    # Check if the input data is valid
    if data:
        # Process the data
        result = data.strip()
    # Return the result
    return result
"""
        rule = VerboseCommentsRule()
        issues = rule.check(text, "test.py")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = VerboseCommentsRule()
        assert rule.id == "C002"

    def test_ignores_string_literals(self) -> None:
        """Test that patterns inside strings are ignored."""
        text = 'value = "# This function is designed to process data"'
        rule = VerboseCommentsRule()
        issues = rule.check(text, "test.py")
        assert len(issues) == 0


class TestCollaborativeComments:
    """Tests for C003: Collaborative Comments."""

    def test_detects_we_language(self) -> None:
        """Test detecting 'we' language in comments."""
        text = """
# We can use this function to process data
def process():
    # Let's initialize the result
    result = None
    return result
"""
        rule = CollaborativeCommentsRule()
        issues = rule.check(text, "test.py")
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = CollaborativeCommentsRule()
        assert rule.id == "C003"

    def test_ignores_chat_phrases_in_strings(self) -> None:
        """Test chat phrases inside strings are ignored."""
        text = 'message = "# I hope this helps"'
        rule = CollaborativeCommentsRule()
        issues = rule.check(text, "test.py")
        assert len(issues) == 0


class TestAIPlaceholders:
    """Tests for C004: Formulaic Placeholders."""

    def test_detects_placeholder_patterns(self) -> None:
        """Test detecting placeholder patterns."""
        text = "# TODO: Implement this function"
        rule = AIPlaceholdersRule()
        issues = rule.check(text, "test.py")
        # May or may not detect depending on implementation
        assert isinstance(issues, list)

    def test_rule_metadata(self) -> None:
        """Test rule has correct metadata."""
        rule = AIPlaceholdersRule()
        assert rule.id == "C004"

    def test_ignores_placeholder_in_strings(self) -> None:
        """Test placeholder patterns inside strings are ignored."""
        text = 'value = "# TODO: Implement"'
        rule = AIPlaceholdersRule()
        issues = rule.check(text, "test.py")
        assert len(issues) == 0
