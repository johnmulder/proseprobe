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
    AssertedSimplicityRule,
    CopulaAvoidanceRule,
    ExcessiveHedgingRule,
    FalseBalanceRule,
    FalseSuspenseTransitionRule,
    FalseVulnerabilityRule,
    FuturistInvitationRule,
    ParticipleChainsRule,
    PatronizingAnalogyRule,
    PedagogicalVoiceRule,
)
from slop_lint.rules.markup import (
    BrokenReferencesRule,
    ChatGPTMarkersRule,
    UTMParametersRule,
    WrongMarkupRule,
)
from slop_lint.rules.struct import (
    AnaphoraAbuseRule,
    AnecdoteAsEvidenceRule,
    ChallengeConclusionsRule,
    ContentDuplicationRule,
    DramaticCountdownRule,
    FalseRangesRule,
    FractalSummaryRule,
    GerundFragmentLitanyRule,
    HistoricalAnalogyStackingRule,
    InlineHeaderListsRule,
    ListicleInProseRule,
    NegativeParallelismRule,
    RhetoricalSelfAnswerRule,
    RuleOfThreeRule,
    SignificanceEmphasisRule,
    SignpostedConclusionRule,
    SuperficialAnalysisRule,
)
from slop_lint.rules.style import (
    BoldOveruseRule,
    ElegantVariationRule,
    EmDashOveruseRule,
    EmojiInProseRule,
    QuoteInconsistencyRule,
    ShortPunchyFragmentsRule,
    TitleCaseHeadingsRule,
)
from slop_lint.rules.vocab import (
    AIVocabularyRule,
    CollaborativePhrasesRule,
    GrandioseStakesRule,
    InventedConceptLabelsRule,
    KnowledgeCutoffRule,
    PromotionalLanguageRule,
    TrendOverclaimRule,
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
    "GrandioseStakesRule",
    "InventedConceptLabelsRule",
    "TrendOverclaimRule",
    # Structural rules (S)
    "RuleOfThreeRule",
    "NegativeParallelismRule",
    "ChallengeConclusionsRule",
    "InlineHeaderListsRule",
    "SignificanceEmphasisRule",
    "SuperficialAnalysisRule",
    "FalseRangesRule",
    "DramaticCountdownRule",
    "RhetoricalSelfAnswerRule",
    "AnaphoraAbuseRule",
    "GerundFragmentLitanyRule",
    "ListicleInProseRule",
    "HistoricalAnalogyStackingRule",
    "SignpostedConclusionRule",
    "FractalSummaryRule",
    "ContentDuplicationRule",
    "AnecdoteAsEvidenceRule",
    # Style rules (T)
    "TitleCaseHeadingsRule",
    "BoldOveruseRule",
    "EmDashOveruseRule",
    "QuoteInconsistencyRule",
    "EmojiInProseRule",
    "ElegantVariationRule",
    "ShortPunchyFragmentsRule",
    # Grammar rules (G)
    "CopulaAvoidanceRule",
    "ExcessiveHedgingRule",
    "ParticipleChainsRule",
    "FalseSuspenseTransitionRule",
    "PatronizingAnalogyRule",
    "FuturistInvitationRule",
    "FalseVulnerabilityRule",
    "AssertedSimplicityRule",
    "PedagogicalVoiceRule",
    "FalseBalanceRule",
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
        # Vocabulary (V001-V008)
        AIVocabularyRule(allowed=allowed, additional=additional, allowed_phrases=allowed_phrases),
        CollaborativePhrasesRule(),
        KnowledgeCutoffRule(),
        PromotionalLanguageRule(),
        WeaselWordsRule(),
        GrandioseStakesRule(),
        InventedConceptLabelsRule(),
        TrendOverclaimRule(),
        # Structural (S001-S017)
        RuleOfThreeRule(threshold=thresholds.rule_of_three),
        NegativeParallelismRule(),
        ChallengeConclusionsRule(),
        InlineHeaderListsRule(threshold=thresholds.inline_header_lists),
        SignificanceEmphasisRule(),
        SuperficialAnalysisRule(),
        FalseRangesRule(),
        DramaticCountdownRule(),
        RhetoricalSelfAnswerRule(),
        AnaphoraAbuseRule(),
        GerundFragmentLitanyRule(),
        ListicleInProseRule(),
        HistoricalAnalogyStackingRule(),
        SignpostedConclusionRule(),
        FractalSummaryRule(),
        ContentDuplicationRule(),
        AnecdoteAsEvidenceRule(),
        # Style (T001-T007)
        TitleCaseHeadingsRule(),
        BoldOveruseRule(threshold=thresholds.bold_overuse),
        EmDashOveruseRule(threshold=thresholds.em_dash_overuse),
        QuoteInconsistencyRule(),
        EmojiInProseRule(),
        ElegantVariationRule(),
        ShortPunchyFragmentsRule(),
        # Grammar (G001-G010)
        CopulaAvoidanceRule(),
        ExcessiveHedgingRule(),
        ParticipleChainsRule(),
        FalseSuspenseTransitionRule(),
        PatronizingAnalogyRule(),
        FuturistInvitationRule(),
        FalseVulnerabilityRule(),
        AssertedSimplicityRule(),
        PedagogicalVoiceRule(),
        FalseBalanceRule(),
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
