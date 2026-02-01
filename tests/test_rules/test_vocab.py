"""Tests for vocabulary rules (V001-V005)."""

import pytest

from humanize.rules.vocab import (
    AIVocabularyRule,
    CollaborativePhrasesRule,
    KnowledgeCutoffRule,
    PromotionalLanguageRule,
    WeaselWordsRule,
)


class TestAIVocabularyRule:
    """Tests for V001: AI Vocabulary."""

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

    def test_fix_preserves_case(self, rule: AIVocabularyRule) -> None:
        content = "Let's Delve into this topic."
        issues = rule.check(content, "test.md")

        assert len(issues) == 1
        fixed = rule.fix(content, issues[0])
        assert "Explore" in fixed
        assert "Delve" not in fixed


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
