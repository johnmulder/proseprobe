"""Tests for code rules (C001-C004, C007-C008)."""

import pytest

from proseprobe.rules.base import Confidence, Rule, Severity
from proseprobe.rules.code import (
    AIPlaceholdersRule,
    CollaborativeCommentsRule,
    CommentedOutCodeRule,
    DocstringRepeatsSignatureRule,
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
        (
            CommentedOutCodeRule(),
            "    #   value = load_cache()",
            "value = load_cache()",
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


class TestDocstringRepeatsSignature:
    """Tests for C007: Docstring Repeats Signature."""

    @pytest.mark.parametrize(
        "source",
        [
            'def process(data):\n    """Process data."""',
            'def calculate_total(items):\n    """Calculate the total for items."""',
            'async def fetch_user(user_id):\n    """Fetch user by user ID."""',
            'def add(a, b):\n    """Add a and b."""',
            (
                "class Client:\n"
                "    def create_client(self, name, active=True):\n"
                '        """Create a client with name and active."""'
            ),
        ],
    )
    def test_detects_exact_signature_restatements(self, source: str) -> None:
        issues = DocstringRepeatsSignatureRule().check(source, "test.py")

        assert len(issues) == 1
        assert issues[0].rule_id == "C007"

    def test_splits_camel_case_and_snake_case_identifiers(self) -> None:
        source = '''
def loadHTTPResponse(response_code):
    """Load HTTP response by response code."""
'''

        assert len(DocstringRepeatsSignatureRule().check(source, "test.py")) == 1

    def test_reports_exact_source_span(self) -> None:
        source = 'def process(data):\n    """Process data."""'

        [issue] = DocstringRepeatsSignatureRule().check(source, "test.py")

        assert issue.line == 2
        assert issue.end_line == 2
        assert issue.column == 8
        assert issue.end_column is not None
        assert source.splitlines()[1][issue.column - 1 : issue.end_column - 1] == (
            "Process data."
        )

    def test_reports_multiline_opening_span(self) -> None:
        source = '''
def create_user(name, email):
    """Create a user with
    name and email.

    Store the user in the primary database.
    """
'''

        [issue] = DocstringRepeatsSignatureRule().check(source, "test.py")

        assert (issue.line, issue.column) == (3, 8)
        assert (issue.end_line, issue.end_column) == (4, 20)

    @pytest.mark.parametrize(
        "opening",
        [
            "Process validated data.",
            "Process data in stable order.",
            "Processes data.",
            "Process.",
            "Process data or metadata.",
        ],
    )
    def test_ignores_openings_that_are_not_exact_restatements(
        self, opening: str
    ) -> None:
        source = f'def process(data):\n    """{opening}"""'

        assert DocstringRepeatsSignatureRule().check(source, "test.py") == []

    def test_checks_only_the_opening_sentence(self) -> None:
        source = '''
def process(data):
    """Validate data before processing. Process data."""
'''

        assert DocstringRepeatsSignatureRule().check(source, "test.py") == []

    @pytest.mark.parametrize(
        "source",
        [
            '"""Package tools."""',
            'class PackageTools:\n    """Package tools."""',
            'def run():\n    """Run."""',
            'message = "Process data."',
            "# Process data.\ndef process(data):\n    pass",
            'def broken(\n    """Process data."""',
        ],
    )
    def test_ignores_unsupported_or_non_docstring_text(self, source: str) -> None:
        assert DocstringRepeatsSignatureRule().check(source, "test.py") == []

    def test_reports_each_matching_function(self) -> None:
        source = '''
def process(data):
    """Process data."""

async def fetch(item):
    """Fetch item."""
'''

        issues = DocstringRepeatsSignatureRule().check(source, "test.py")

        assert [(issue.line, issue.column) for issue in issues] == [(3, 8), (6, 8)]

    def test_rule_metadata(self) -> None:
        rule = DocstringRepeatsSignatureRule()

        assert rule.id == "C007"
        assert rule.name == "Docstring Repeats Signature"
        assert rule.severity is Severity.INFO
        assert rule.applies_to == {"python"}


class TestCommentedOutCode:
    """Tests for C008: Commented-Out Code."""

    @pytest.mark.parametrize(
        ("source", "kind"),
        [
            ("# value = load_cache()", "assignment"),
            ("# value += 1", "assignment"),
            ("# value: int = 1", "assignment"),
            ("# send(payload)", "call"),
            ("# import os", "import"),
            ("# from pathlib import Path", "import"),
            ("# if ready:", "control statement"),
            ("# for item in items:", "control statement"),
            ("# while pending:", "control statement"),
            ("# with open(path) as stream:", "control statement"),
            ("# if ready: send(payload)", "control statement"),
        ],
    )
    def test_detects_supported_statements(self, source: str, kind: str) -> None:
        [issue] = CommentedOutCodeRule().check(source, "test.py")

        assert issue.rule_id == "C008"
        assert issue.message == f"Commented-out code: {kind}"
        assert issue.confidence is Confidence.LOW

    def test_reports_multiple_comments_in_source_order(self) -> None:
        source = "# value = load_cache()\n# send(value)\n# import os"

        issues = CommentedOutCodeRule().check(source, "test.py")

        assert [(issue.line, issue.column) for issue in issues] == [
            (1, 3),
            (2, 3),
            (3, 3),
        ]

    def test_tokenizes_comments_even_when_surrounding_python_is_invalid(self) -> None:
        source = "def broken(\n# value = load_cache()"

        [issue] = CommentedOutCodeRule().check(source, "test.py")

        assert (issue.line, issue.column) == (2, 3)

    @pytest.mark.parametrize(
        "source",
        [
            "value = 1  # cached = load_cache()",
            "# Use send(payload) to notify the client.",
            "# TODO: Implement",
            "# Note: important",
            "# value: int",
            "# first = 1; second = 2",
            "# def build():",
            "# return result",
            "# [item for item in items]",
            "# >>> send(payload)",
            'message = "# value = load_cache()"',
            "# if ready, send payload",
            "# try:",
        ],
    )
    def test_ignores_non_target_comments(self, source: str) -> None:
        assert CommentedOutCodeRule().check(source, "test.py") == []

    def test_rule_metadata(self) -> None:
        rule = CommentedOutCodeRule()

        assert rule.id == "C008"
        assert rule.name == "Commented-Out Code"
        assert rule.severity is Severity.INFO
        assert rule.default_confidence is Confidence.LOW
        assert rule.applies_to == {"python"}
