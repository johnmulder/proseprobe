"""Tests for code rules (C001-C009)."""

import pytest

from proseprobe.rules import code
from proseprobe.rules.base import Confidence, Rule, Severity
from proseprobe.rules.code import (
    AIPlaceholdersRule,
    CollaborativeCommentsRule,
    CommentedOutCodeRule,
    CommentRestatesCodeRule,
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
            CommentRestatesCodeRule(),
            "def load():\n    # Return cached value\n    return cached_value",
            "Return cached value",
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
        assert len(issues) == 1
        assert "bespoke" in issues[0].message

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

    @pytest.mark.parametrize("marker", ["TODO", "FIXME:", "xxx"])
    def test_detects_context_free_comment_markers(self, marker: str) -> None:
        source = f"    # {marker}"

        [issue] = AIPlaceholdersRule().check(source, "test.py")

        assert issue.message == "Formulaic placeholder: marker without context"
        assert issue.line == 1
        assert issue.column == 5
        assert issue.end_column == len(source) + 1
        assert source[issue.column - 1 : issue.end_column - 1] == f"# {marker}"

    def test_reports_one_finding_for_inline_bare_marker(self) -> None:
        source = "def pending():\n    pass  # TODO"

        [issue] = AIPlaceholdersRule().check(source, "test.py")

        assert issue.line == 2
        assert (
            source.splitlines()[1][issue.column - 1 : issue.end_column - 1] == "# TODO"
        )

    @pytest.mark.parametrize(
        "source",
        [
            "# TODO: Retry HTTP 503 after issue #42 defines the limit.",
            "# FIXME: Remove the compatibility branch after Python 3.11 support ends.",
            "# XXX: The protocol sends a zero-length keepalive frame.",
            'value = "# TODO"',
            'TODO = "assigned owner"',
        ],
    )
    def test_ignores_contextual_markers_and_non_comments(self, source: str) -> None:
        assert AIPlaceholdersRule().check(source, "test.py") == []

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


class TestCommentRestatesCode:
    """Tests for C006: Comment Restates Code."""

    @pytest.mark.parametrize(
        ("source", "comment"),
        [
            (
                "def load():\n    # Return cached value.\n    return cached_value",
                "Return cached value.",
            ),
            (
                "def load():\n    # Return cached value\n    return state.cachedValue",
                "Return cached value",
            ),
            ("# Set retry count\nretry_count = 3", "Set retry count"),
            (
                "# Assign retry count\nretry_count: int = 3",
                "Assign retry count",
            ),
            (
                "# Call send request\nclient.sendRequest(payload)",
                "Call send request",
            ),
        ],
    )
    def test_detects_exact_restatements(self, source: str, comment: str) -> None:
        [issue] = CommentRestatesCodeRule().check(source, "test.py")

        assert issue.rule_id == "C006"
        assert issue.message == f"Comment restates code: '{comment}'"
        assert issue.confidence is Confidence.LOW

    def test_reports_multiple_comments_in_source_order(self) -> None:
        source = """\
def load():
    # Set cached value
    cached_value = fetch()
    # Call record result
    record_result(cached_value)
    # Return cached value
    return cached_value
"""

        issues = CommentRestatesCodeRule().check(source, "test.py")

        assert [(issue.line, issue.column) for issue in issues] == [
            (2, 7),
            (4, 7),
            (6, 7),
        ]

    def test_exact_fixture_does_not_duplicate_neighboring_code_rules(self) -> None:
        source = "def load():\n    # Return cached value\n    return cached_value"
        neighboring_rules = (
            VerboseCommentsRule(),
            CollaborativeCommentsRule(),
            AIPlaceholdersRule(),
            CommentedOutCodeRule(),
        )

        assert all(rule.check(source, "test.py") == [] for rule in neighboring_rules)

    @pytest.mark.parametrize(
        "source",
        [
            "def load():\n    # Return cached value without copying\n    return cached_value",
            "def load():\n    # Return result\n    return cached_value",
            "def load():\n    # Return result\n\n    return result",
            "def load():\n    return result  # Return result",
            "def load():\n# Return result\n    return result",
            "# Set values\nleft, right = pair",
            "# Set retry count\nretry_count += 1",
            "# Call send request\nresult = send_request()",
            "# Call send request\nif ready: send_request()",
            'message = "# Return result"',
            "def broken(\n# Return result\nreturn result",
        ],
    )
    def test_ignores_non_exact_or_unsupported_cases(self, source: str) -> None:
        assert CommentRestatesCodeRule().check(source, "test.py") == []

    def test_rule_metadata(self) -> None:
        rule = CommentRestatesCodeRule()

        assert rule.id == "C006"
        assert rule.name == "Comment Restates Code"
        assert rule.severity is Severity.INFO
        assert rule.default_confidence is Confidence.LOW
        assert rule.applies_to == {"python"}


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


class TestStaleDocstringParameter:
    """Tests for C009 explicit stale Sphinx parameter declarations."""

    def test_reports_stale_parameter_name_with_exact_source_span(self) -> None:
        source = '''\
def fetch(url, timeout):
    """Fetch a response.

    :param retries: The retry budget.
    """
'''

        [issue] = code.StaleDocstringParameterRule().check(source, "test.py")

        assert issue.rule_id == "C009"
        assert (issue.line, issue.column, issue.end_column) == (4, 12, 19)
        assert (
            source.splitlines()[3][issue.column - 1 : issue.end_column - 1] == "retries"
        )
        assert issue.severity is Severity.INFO
        assert issue.confidence is Confidence.HIGH

    @pytest.mark.parametrize("field", [":param retries:", ":param timeot:"])
    def test_reports_renamed_or_misspelled_parameters(self, field: str) -> None:
        source = f'def fetch(url, timeout):\n    """{field} Value."""'

        [issue] = code.StaleDocstringParameterRule().check(source, "test.py")

        assert issue.rule_id == "C009"

    def test_typed_field_reports_only_the_name(self) -> None:
        source = 'def fetch(url):\n    """:param int retries: Retry budget."""'

        [issue] = code.StaleDocstringParameterRule().check(source, "test.py")

        assert (
            source.splitlines()[1][issue.column - 1 : issue.end_column - 1] == "retries"
        )

    @pytest.mark.parametrize(
        "source",
        [
            'def fetch(url, /, timeout=3, *, active=True):\n    """:param url: Target.\n    :param int timeout: Budget.\n    :param active: Flag."""',
            'def fetch(url):\n    """Fetch a response."""',
            "def fetch(url):\n    return None",
            'def fetch(self, cls):\n    """:param self: Input.\n    :param cls: Input."""',
            'def fetch(*args, **kwargs):\n    """:param *args: Values.\n    :param **kwargs: Options."""',
            'def fetch(url, **options):\n    """:param retries: Delegated option."""',
            'def fetch(url, **options):\n    """:param int retries: Delegated option."""',
            '""":param retries: A module description."""',
            'class Fetch:\n    """:param retries: Constructor documentation."""',
            'message = ":param retries: ordinary data"',
            "# :param retries: comment\ndef fetch(url):\n    pass",
            'def fetch(url):\n    """Prose mentions :param retries: fields."""',
            'def fetch(url):\n    """`:param retries:` is literal syntax."""',
            'def fetch(url):\n    """Args:\n        retries: Google format."""',
            'def fetch(url):\n    """Parameters\n    ----------\n    retries : int\n        NumPy format."""',
            'def fetch(url):\n    r"""\\:param retries: Escaped field."""',
            'def fetch(url):\n    """:param \\u0072etries: Escaped name."""',
            'def fetch(url): ":param retr" "ies: Split name."',
            'def fetch(url): ":param " "retries: Split field."',
            '@wrap_signature\ndef fetch(url):\n    """:param retries: Runtime interface."""',
            '@wrap_signature()\nasync def fetch(url):\n    """:param retries: Runtime interface."""',
            'def broken(\n    """:param retries: Invalid syntax."""',
            'def fetch(\u00b5):\n    """:param \u00b5: Input."""',
            'def fetch(\u00b5):\n    """:param \u03bc: Input."""',
            'def fetch(n\u0303):\n    """:param n\u0303: Input."""',
        ],
    )
    def test_preserves_valid_declarations_and_unsupported_contexts(
        self, source: str
    ) -> None:
        assert code.StaleDocstringParameterRule().check(source, "test.py") == []

    def test_multiline_description_does_not_change_field_name(self) -> None:
        source = '''\
def fetch(url):
    """Fetch a response.

    :param retries: Retry budget, which is described
        on another physical line.
    :param url: Target URL.
    """
'''

        [issue] = code.StaleDocstringParameterRule().check(source, "test.py")

        assert issue.line == 4
        assert (
            source.splitlines()[3][issue.column - 1 : issue.end_column - 1] == "retries"
        )

    @pytest.mark.parametrize(
        "source",
        [
            'def fetch(*args):\n    """:param retries: Named option."""',
            'def fetch(**options):\n    """:param **optionz: Misspelled catch-all."""',
            'async def résumé(entrée):\n    """:param retríes: Missing."""',
            'def résumé(url): "" ":param retríes: Missing."',
            'def résumé(url): ":param retríes: Missing." " Extra text."',
            'class Client:\n    def fetch(self, url):\n        """:param retries: Missing."""',
            'class Client:\n    @classmethod\n    def fetch(cls, url):\n        """:param retries: Missing."""',
            'class Client:\n    @staticmethod\n    def fetch(url):\n        """:param retries: Missing."""',
        ],
    )
    def test_preserves_unicode_method_and_variadic_source_spans(
        self, source: str
    ) -> None:
        [issue] = code.StaleDocstringParameterRule().check(source, "test.py")
        line = source.splitlines()[issue.line - 1]

        assert line[issue.column - 1 : issue.end_column - 1] in {
            "retries",
            "retríes",
            "optionz",
        }
        assert issue.end_line is None

    def test_nested_declarations_use_only_their_own_signature(self) -> None:
        source = '''\
def outer(url, **options):
    """:param retries: Delegated option."""
    def inner(timeout):
        """:param retries: Missing.
        :param timeout: Budget.
        """
    return inner
'''

        [issue] = code.StaleDocstringParameterRule().check(source, "test.py")

        assert issue.line == 4

    @pytest.mark.parametrize(
        "example",
        [
            "Example::\n\n        :param retries: Literal field.\n",
            ".. code-block:: python\n\n        :param retries: Literal field.\n",
            ".. code:: text\n\n        :param retries: Literal field.\n",
            ".. parsed-literal::\n\n        :param retries: Literal field.\n",
            ".. doctest::\n\n        :param retries: Literal field.\n",
            "```text\n    :param retries: Literal field.\n    ```\n",
            "~~~text\n    :param retries: Literal field.\n    ~~~\n",
            ">>> print('field')\n    :param retries: Literal output.\n",
        ],
    )
    def test_recognized_literal_examples_are_excluded(self, example: str) -> None:
        source = f'def fetch(url):\n    """{example}\n    :param url: Target.\n    """'

        assert code.StaleDocstringParameterRule().check(source, "test.py") == []

    def test_field_after_literal_example_remains_checked(self) -> None:
        source = '''\
def fetch(url):
    """Example::

        :param url: Literal field.

    :param retries: Missing.
    """
'''

        [issue] = code.StaleDocstringParameterRule().check(source, "test.py")

        assert issue.line == 6

    @pytest.mark.parametrize("closing", ["```", "````"])
    def test_field_after_fenced_example_remains_checked(self, closing: str) -> None:
        source = f'''\
def fetch(url):
    """```text title="example"
    :param retries: Literal field.
    {closing}
    :param timeot: Missing.
    """
'''

        [issue] = code.StaleDocstringParameterRule().check(source, "test.py")

        assert issue.line == 5
        assert (
            source.splitlines()[4][issue.column - 1 : issue.end_column - 1] == "timeot"
        )

    def test_wrong_fence_delimiter_does_not_end_literal_context(self) -> None:
        source = '''\
def fetch(url):
    """```text
    ~~~
    :param retries: Literal field.
    ```
    :param timeot: Missing.
    """
'''

        [issue] = code.StaleDocstringParameterRule().check(source, "test.py")

        assert issue.line == 6

    def test_rule_metadata(self) -> None:
        rule = code.StaleDocstringParameterRule()

        assert rule.id == "C009"
        assert rule.name == "Stale Docstring Parameter"
        assert rule.severity is Severity.INFO
        assert rule.default_confidence is Confidence.HIGH
        assert rule.applies_to == {"python"}
        assert rule.content_scope == "raw"
        assert rule.config_key is None


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
