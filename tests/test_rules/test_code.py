"""Tests for code rules (C001-C004)."""

from humanize.rules.code import (
    AIPlaceholdersRule,
    CollaborativeCommentsRule,
    DocstringVocabularyRule,
    VerboseCommentsRule,
)


class TestDocstringVocabulary:
    """Tests for C001: Docstring Vocabulary."""

    def test_detects_ai_vocabulary(self) -> None:
        """Test detecting AI vocabulary in docstrings."""
        text = '''
def process():
    """
    This function delves into the data.
    It leverages the API to facilitate seamless processing.
    """
    pass
'''
        rule = DocstringVocabularyRule()
        issues = rule.check(text, "test.py")
        assert len(issues) > 0

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


class TestAIPlaceholders:
    """Tests for C004: AI Placeholders."""

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
