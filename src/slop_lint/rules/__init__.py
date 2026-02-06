"""Detection rules for bad writing practices."""

from slop_lint.config import Config, ThresholdsConfig
from slop_lint.rules.base import Confidence, Issue, Rule, Severity, severity_from_str
from slop_lint.rules.code import (
    AIPlaceholdersRule,
    CollaborativeCommentsRule,
    DocstringVocabularyRule,
    VerboseCommentsRule,
)
from slop_lint.rules.grammar import (
    CopulaAvoidanceRule,
    ExcessiveHedgingRule,
    ParticipleChainsRule,
)
from slop_lint.rules.markup import (
    BrokenReferencesRule,
    ChatGPTMarkersRule,
    UTMParametersRule,
    WrongMarkupRule,
)
from slop_lint.rules.struct import (
    ChallengeConclusionsRule,
    FalseRangesRule,
    InlineHeaderListsRule,
    NegativeParallelismRule,
    RuleOfThreeRule,
    SignificanceEmphasisRule,
    SuperficialAnalysisRule,
)
from slop_lint.rules.style import (
    BoldOveruseRule,
    ElegantVariationRule,
    EmDashOveruseRule,
    EmojiInProseRule,
    QuoteInconsistencyRule,
    TitleCaseHeadingsRule,
)
from slop_lint.rules.vocab import (
    AIVocabularyRule,
    CollaborativePhrasesRule,
    KnowledgeCutoffRule,
    PromotionalLanguageRule,
    WeaselWordsRule,
)

__all__ = [
    # Base classes
    "Confidence",
    "Issue",
    "Rule",
    "Severity",
    # Vocabulary rules (V)
    "AIVocabularyRule",
    "CollaborativePhrasesRule",
    "KnowledgeCutoffRule",
    "PromotionalLanguageRule",
    "WeaselWordsRule",
    # Structural rules (S)
    "RuleOfThreeRule",
    "NegativeParallelismRule",
    "ChallengeConclusionsRule",
    "InlineHeaderListsRule",
    "SignificanceEmphasisRule",
    "SuperficialAnalysisRule",
    "FalseRangesRule",
    # Style rules (T)
    "TitleCaseHeadingsRule",
    "BoldOveruseRule",
    "EmDashOveruseRule",
    "QuoteInconsistencyRule",
    "EmojiInProseRule",
    "ElegantVariationRule",
    # Grammar rules (G)
    "CopulaAvoidanceRule",
    "ExcessiveHedgingRule",
    "ParticipleChainsRule",
    # Code rules (C)
    "DocstringVocabularyRule",
    "VerboseCommentsRule",
    "CollaborativeCommentsRule",
    "AIPlaceholdersRule",
    # Markup rules (M)
    "WrongMarkupRule",
    "ChatGPTMarkersRule",
    "UTMParametersRule",
    "BrokenReferencesRule",
]


def _apply_severity_overrides(
    rules: list[Rule], overrides: dict[str, str]
) -> list[Rule]:
    for rule in rules:
        override = overrides.get(rule.id)
        if override:
            new_severity = severity_from_str(override)
            if new_severity is not None:
                rule.severity = new_severity
    return rules


def get_all_rules(config: Config | None = None) -> list[Rule]:
    """Get instances of all available rules.

    Returns:
        List of all rule instances.
    """
    allowed: set[str] = set()
    additional: set[str] = set()
    allowed_phrases: set[str] = set()
    severity_overrides: dict[str, str] = {}
    thresholds = ThresholdsConfig()
    if config is not None:
        allowed = {w.lower() for w in config.vocabulary.allowed}
        additional = {w.lower() for w in config.vocabulary.additional}
        allowed_phrases = set(config.vocabulary.allowed_phrases)
        severity_overrides = config.severity_overrides
        thresholds = config.thresholds

    rules = [
        # Vocabulary (V001-V005)
        AIVocabularyRule(allowed=allowed, additional=additional, allowed_phrases=allowed_phrases),
        CollaborativePhrasesRule(),
        KnowledgeCutoffRule(),
        PromotionalLanguageRule(),
        WeaselWordsRule(),
        # Structural (S001-S007)
        RuleOfThreeRule(threshold=thresholds.rule_of_three),
        NegativeParallelismRule(),
        ChallengeConclusionsRule(),
        InlineHeaderListsRule(threshold=thresholds.inline_header_lists),
        SignificanceEmphasisRule(),
        SuperficialAnalysisRule(),
        FalseRangesRule(),
        # Style (T001-T006)
        TitleCaseHeadingsRule(),
        BoldOveruseRule(threshold=thresholds.bold_overuse),
        EmDashOveruseRule(threshold=thresholds.em_dash_overuse),
        QuoteInconsistencyRule(),
        EmojiInProseRule(),
        ElegantVariationRule(),
        # Grammar (G001-G003)
        CopulaAvoidanceRule(),
        ExcessiveHedgingRule(),
        ParticipleChainsRule(),
        # Code (C001-C004)
        DocstringVocabularyRule(allowed=allowed, additional=additional),
        VerboseCommentsRule(),
        CollaborativeCommentsRule(),
        AIPlaceholdersRule(),
        # Markup (M001-M004)
        WrongMarkupRule(),
        ChatGPTMarkersRule(),
        UTMParametersRule(),
        BrokenReferencesRule(),
    ]

    if severity_overrides:
        rules = _apply_severity_overrides(rules, severity_overrides)

    return rules
