"""Tests for vocabulary rules (V001-V005)."""

import pytest

from slop_lint.config import Config
from slop_lint.rules import get_all_rules
from slop_lint.rules.base import Confidence, Severity
from slop_lint.rules.vocab import (
    AIVocabularyRule,
    CollaborativePhrasesRule,
    KnowledgeCutoffRule,
    PromotionalLanguageRule,
    WeaselWordsRule,
)


class TestAIVocabularyRule:
    """Tests for V001: Overused Vocabulary."""

    @pytest.fixture
    def rule(self) -> AIVocabularyRule:
        return AIVocabularyRule()

    def test_detects_delve(self, rule: AIVocabularyRule) -> None:
        content = "This article delves into the topic."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert issues[0].rule_id == "V001"
        assert "delves" in issues[0].message.lower()
        assert issues[0].suggestion == "explore"

    def test_detects_multiple_words(self, rule: AIVocabularyRule) -> None:
        content = "The tapestry of modern development is multifaceted."
        issues = rule.check(content, "test.md")

        assert len(issues) >= 2
        words_found = {i.message.split("'")[1].lower() for i in issues}
        assert "tapestry" in words_found
        assert "multifaceted" in words_found

    def test_ignores_clean_content(self, rule: AIVocabularyRule) -> None:
        content = "This is a simple document about programming."
        issues = rule.check(content, "test.md")

        assert len(issues) == 0

    def test_respects_allowed_vocabulary(self) -> None:
        rule = AIVocabularyRule(allowed={"delve"})
        content = "This article delves into the topic."
        issues = rule.check(content, "test.md")

        assert len(issues) == 0

    def test_flags_additional_vocabulary(self) -> None:
        rule = AIVocabularyRule(additional={"foobar"})
        content = "The foobar feature is enabled."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert "foobar" in issues[0].message.lower()

    def test_ignores_code_fences_in_markdown(self) -> None:
        rule = AIVocabularyRule()
        content = "```python\n# delve\n```\nThis delves into topics."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1

    def test_ignores_inline_code_in_markdown(self) -> None:
        rule = AIVocabularyRule()
        content = "Use `delve` sparingly in docs."
        issues = rule.check(content, "test.md")

        assert len(issues) == 0

    def test_severity_override_from_config(self) -> None:
        config = Config(severity_overrides={"V001": "error"})
        rules = get_all_rules(config)
        rule = next(r for r in rules if r.id == "V001")
        assert rule.severity == Severity.ERROR

    def test_tier1_word_has_high_confidence(self, rule: AIVocabularyRule) -> None:
        content = "Let's delve into this topic."
        issues = rule.check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.HIGH

    def test_tier2_word_has_medium_confidence(self, rule: AIVocabularyRule) -> None:
        content = "This is a crucial decision."
        issues = rule.check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.MEDIUM

    def test_tier3_word_has_low_confidence(self, rule: AIVocabularyRule) -> None:
        content = "This is a notable achievement."
        issues = rule.check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.LOW

    def test_example_heading_downgrades_confidence(self) -> None:
        rule = AIVocabularyRule()
        content = "## Example (bad)\n\nThis article delves into the topic."
        issues = rule.check(content, "test.md")
        assert len(issues) >= 1
        assert issues[0].confidence == Confidence.LOW

    def test_allowed_phrases_skip_matching_line(self) -> None:
        rule = AIVocabularyRule(allowed_phrases={"all notable changes"})
        content = "All notable changes to this project."
        issues = rule.check(content, "test.md")
        assert len(issues) == 0


class TestCollaborativePhrasesRule:
    """Tests for V002: Collaborative Phrases."""

    @pytest.fixture
    def rule(self) -> CollaborativePhrasesRule:
        return CollaborativePhrasesRule()

    def test_detects_i_hope_this_helps(self, rule: CollaborativePhrasesRule) -> None:
        content = "Here's the solution. I hope this helps!"
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert "I hope this helps" in issues[0].message

    def test_detects_let_me_know(self, rule: CollaborativePhrasesRule) -> None:
        content = "Let me know if you need more information."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1


class TestKnowledgeCutoffRule:
    """Tests for V003: Knowledge Cutoff."""

    @pytest.fixture
    def rule(self) -> KnowledgeCutoffRule:
        return KnowledgeCutoffRule()

    def test_detects_knowledge_cutoff(self, rule: KnowledgeCutoffRule) -> None:
        content = "As of my last update, this information is accurate."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert issues[0].rule_id == "V003"


class TestPromotionalLanguageRule:
    """Tests for V004: Promotional Language."""

    @pytest.fixture
    def rule(self) -> PromotionalLanguageRule:
        return PromotionalLanguageRule()

    def test_detects_promotional_phrases(self, rule: PromotionalLanguageRule) -> None:
        content = "This world-class solution boasts cutting-edge features."
        issues = rule.check(content, "test.md")

        assert len(issues) >= 1


class TestWeaselWordsRule:
    """Tests for V005: Weasel Words."""

    @pytest.fixture
    def rule(self) -> WeaselWordsRule:
        return WeaselWordsRule()

    def test_detects_weasel_phrases(self, rule: WeaselWordsRule) -> None:
        content = "Experts say this approach is effective."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        assert issues[0].rule_id == "V005"
