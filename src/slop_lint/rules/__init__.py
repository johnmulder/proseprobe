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
    GapRitualRule,
    ImpersonalCorporatePassiveRule,
    NominalizationOverloadRule,
    ParticipleChainsRule,
    PassiveVoiceOveruseRule,
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
    AlignmentRitualRule,
    AnaphoraAbuseRule,
    AnecdoteAsEvidenceRule,
    ChallengeConclusionsRule,
    CitationNameDroppingRule,
    ContentDuplicationRule,
    CorporateEuphemismRule,
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
    SlideDeckFragmentRule,
    SuperficialAnalysisRule,
)
from slop_lint.rules.style import (
    BoldOveruseRule,
    ElegantVariationRule,
    EmDashOveruseRule,
    EmojiInProseRule,
    QuoteInconsistencyRule,
    SentenceLengthRule,
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
    "AIPlaceholdersRule",
    # Vocabulary rules (V)
    "AIVocabularyRule",
    "AlignmentRitualRule",
    "AnaphoraAbuseRule",
    "AnecdoteAsEvidenceRule",
    "AssertedSimplicityRule",
    "BoldOveruseRule",
    "BrokenReferencesRule",
    "ChallengeConclusionsRule",
    "ChatGPTMarkersRule",
    "CitationNameDroppingRule",
    "CollaborativeCommentsRule",
    "CollaborativePhrasesRule",
    # Base classes
    "Confidence",
    "ContentDuplicationRule",
    # Grammar rules (G)
    "CopulaAvoidanceRule",
    "CorporateEuphemismRule",
    # Code rules (C)
    "DocstringVocabularyRule",
    "DramaticCountdownRule",
    "ElegantVariationRule",
    "EmDashOveruseRule",
    "EmojiInProseRule",
    "ExcessiveHedgingRule",
    "FalseBalanceRule",
    "FalseRangesRule",
    "FalseSuspenseTransitionRule",
    "FalseVulnerabilityRule",
    "FractalSummaryRule",
    "FuturistInvitationRule",
    "GapRitualRule",
    "GerundFragmentLitanyRule",
    "GrandioseStakesRule",
    "HistoricalAnalogyStackingRule",
    "ImpersonalCorporatePassiveRule",
    "InlineHeaderListsRule",
    "InventedConceptLabelsRule",
    "Issue",
    "KnowledgeCutoffRule",
    "ListicleInProseRule",
    "NegativeParallelismRule",
    "NominalizationOverloadRule",
    "ParticipleChainsRule",
    "PassiveVoiceOveruseRule",
    "PatronizingAnalogyRule",
    "PedagogicalVoiceRule",
    "PromotionalLanguageRule",
    "QuoteInconsistencyRule",
    "RhetoricalSelfAnswerRule",
    "Rule",
    # Structural rules (S)
    "RuleOfThreeRule",
    "SentenceLengthRule",
    "Severity",
    "ShortPunchyFragmentsRule",
    "SignificanceEmphasisRule",
    "SignpostedConclusionRule",
    "SlideDeckFragmentRule",
    "SuperficialAnalysisRule",
    # Style rules (T)
    "TitleCaseHeadingsRule",
    "TrendOverclaimRule",
    "UTMParametersRule",
    "VerboseCommentsRule",
    "WeaselWordsRule",
    # Markup rules (M)
    "WrongMarkupRule",
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
        AIVocabularyRule(
            allowed=allowed, additional=additional, allowed_phrases=allowed_phrases
        ),
        CollaborativePhrasesRule(),
        KnowledgeCutoffRule(),
        PromotionalLanguageRule(),
        WeaselWordsRule(),
        GrandioseStakesRule(),
        InventedConceptLabelsRule(),
        TrendOverclaimRule(),
        # Structural (S001-S018)
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
        CitationNameDroppingRule(threshold=thresholds.citation_name_drop),
        CorporateEuphemismRule(),
        AlignmentRitualRule(),
        SlideDeckFragmentRule(),
        # Style (T001-T008)
        TitleCaseHeadingsRule(),
        BoldOveruseRule(threshold=thresholds.bold_overuse),
        EmDashOveruseRule(threshold=thresholds.em_dash_overuse),
        QuoteInconsistencyRule(),
        EmojiInProseRule(),
        ElegantVariationRule(),
        ShortPunchyFragmentsRule(),
        SentenceLengthRule(threshold=thresholds.sentence_length_max),
        # Grammar (G001-G013)
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
        NominalizationOverloadRule(threshold=thresholds.nominalization_overload),
        PassiveVoiceOveruseRule(threshold=thresholds.passive_voice_overuse),
        GapRitualRule(),
        ImpersonalCorporatePassiveRule(),
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
