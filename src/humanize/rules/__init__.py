"""Detection rules for AI content patterns."""

from humanize.config import Config
from humanize.rules.base import Issue, Rule, Severity
from humanize.rules.code import (
    AIPlaceholdersRule,
    CollaborativeCommentsRule,
    DocstringVocabularyRule,
    VerboseCommentsRule,
)
from humanize.rules.grammar import (
    CopulaAvoidanceRule,
    ExcessiveHedgingRule,
    ParticipleChainsRule,
)
from humanize.rules.markup import (
    BrokenReferencesRule,
    ChatGPTMarkersRule,
    UTMParametersRule,
    WrongMarkupRule,
)
from humanize.rules.struct import (
    ChallengeConclusionsRule,
    FalseRangesRule,
    InlineHeaderListsRule,
    NegativeParallelismRule,
    RuleOfThreeRule,
    SignificanceEmphasisRule,
    SuperficialAnalysisRule,
)
from humanize.rules.style import (
    BoldOveruseRule,
    ElegantVariationRule,
    EmDashOveruseRule,
    EmojiInProseRule,
    QuoteInconsistencyRule,
    TitleCaseHeadingsRule,
)
from humanize.rules.vocab import (
    AIVocabularyRule,
    CollaborativePhrasesRule,
    KnowledgeCutoffRule,
    PromotionalLanguageRule,
    WeaselWordsRule,
)

__all__ = [
    # Base classes
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


def _severity_from_str(value: str) -> Severity | None:
    mapping = {
        "error": Severity.ERROR,
        "warning": Severity.WARNING,
        "info": Severity.INFO,
        "off": Severity.OFF,
    }
    return mapping.get(value.lower())


def _apply_severity_overrides(
    rules: list[Rule], overrides: dict[str, str]
) -> list[Rule]:
    for rule in rules:
        override = overrides.get(rule.id)
        if override:
            new_severity = _severity_from_str(override)
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
    severity_overrides: dict[str, str] = {}
    if config is not None:
        allowed = {w.lower() for w in config.vocabulary.allowed}
        additional = {w.lower() for w in config.vocabulary.additional}
        severity_overrides = config.severity_overrides

    rules = [
        # Vocabulary (V001-V005)
        AIVocabularyRule(allowed=allowed, additional=additional),
        CollaborativePhrasesRule(),
        KnowledgeCutoffRule(),
        PromotionalLanguageRule(),
        WeaselWordsRule(),
        # Structural (S001-S007)
        RuleOfThreeRule(),
        NegativeParallelismRule(),
        ChallengeConclusionsRule(),
        InlineHeaderListsRule(),
        SignificanceEmphasisRule(),
        SuperficialAnalysisRule(),
        FalseRangesRule(),
        # Style (T001-T006)
        TitleCaseHeadingsRule(),
        BoldOveruseRule(),
        EmDashOveruseRule(),
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
