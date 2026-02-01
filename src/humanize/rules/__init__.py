"""Detection rules for AI content patterns."""

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


def get_all_rules() -> list[Rule]:
    """Get instances of all available rules.

    Returns:
        List of all rule instances.
    """
    return [
        # Vocabulary (V001-V005)
        AIVocabularyRule(),
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
        DocstringVocabularyRule(),
        VerboseCommentsRule(),
        CollaborativeCommentsRule(),
        AIPlaceholdersRule(),
        # Markup (M001-M004)
        WrongMarkupRule(),
        ChatGPTMarkersRule(),
        UTMParametersRule(),
        BrokenReferencesRule(),
    ]
