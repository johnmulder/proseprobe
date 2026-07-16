"""Detection rule registration."""

from slop_lint.config import Config
from slop_lint.rules import code, grammar, markup, struct, style, vocab
from slop_lint.rules.base import Rule, severity_from_str

__all__ = ["get_all_rules"]


def get_all_rules(config: Config | None = None) -> list[Rule]:
    """Return all rules configured for a lint run."""
    config = config or Config()
    thresholds = config.thresholds
    allowed = {word.lower() for word in config.vocabulary.allowed}
    additional = {word.lower() for word in config.vocabulary.additional}
    rules: list[Rule] = [
        code.DocstringVocabularyRule(allowed, additional),
        code.VerboseCommentsRule(),
        code.CollaborativeCommentsRule(),
        code.AIPlaceholdersRule(),
        grammar.CopulaAvoidanceRule(),
        grammar.ExcessiveHedgingRule(),
        grammar.ParticipleChainsRule(),
        grammar.FalseSuspenseTransitionRule(),
        grammar.PatronizingAnalogyRule(),
        grammar.FuturistInvitationRule(),
        grammar.FalseVulnerabilityRule(),
        grammar.AssertedSimplicityRule(),
        grammar.PedagogicalVoiceRule(),
        grammar.FalseBalanceRule(),
        grammar.NominalizationOverloadRule(thresholds.nominalization_overload),
        grammar.PassiveVoiceOveruseRule(thresholds.passive_voice_overuse),
        grammar.GapRitualRule(),
        grammar.ImpersonalCorporatePassiveRule(),
        markup.WrongMarkupRule(),
        markup.ChatGPTMarkersRule(),
        markup.UTMParametersRule(),
        markup.BrokenReferencesRule(),
        struct.RuleOfThreeRule(thresholds.rule_of_three),
        struct.NegativeParallelismRule(),
        struct.ChallengeConclusionsRule(),
        struct.InlineHeaderListsRule(thresholds.inline_header_lists),
        struct.SignificanceEmphasisRule(),
        struct.SuperficialAnalysisRule(),
        struct.FalseRangesRule(),
        struct.DramaticCountdownRule(),
        struct.RhetoricalSelfAnswerRule(),
        struct.AnaphoraAbuseRule(thresholds.anaphora_abuse),
        struct.GerundFragmentLitanyRule(thresholds.gerund_fragment_litany),
        struct.ListicleInProseRule(),
        struct.HistoricalAnalogyStackingRule(thresholds.historical_analogy_stacking),
        struct.SignpostedConclusionRule(),
        struct.FractalSummaryRule(),
        struct.ContentDuplicationRule(),
        struct.AnecdoteAsEvidenceRule(),
        struct.CitationNameDroppingRule(thresholds.citation_name_drop),
        struct.CorporateEuphemismRule(),
        struct.AlignmentRitualRule(),
        struct.SlideDeckFragmentRule(),
        style.TitleCaseHeadingsRule(),
        style.BoldOveruseRule(thresholds.bold_overuse),
        style.EmDashOveruseRule(thresholds.em_dash_overuse),
        style.QuoteInconsistencyRule(),
        style.EmojiInProseRule(),
        style.ElegantVariationRule(),
        style.ShortPunchyFragmentsRule(thresholds.short_punchy_fragments),
        style.SentenceLengthRule(thresholds.sentence_length_max),
        vocab.AIVocabularyRule(
            allowed,
            additional,
            set(config.vocabulary.allowed_phrases),
        ),
        vocab.CollaborativePhrasesRule(),
        vocab.KnowledgeCutoffRule(),
        vocab.PromotionalLanguageRule(),
        vocab.WeaselWordsRule(),
        vocab.GrandioseStakesRule(),
        vocab.InventedConceptLabelsRule(thresholds.invented_concept_labels),
        vocab.TrendOverclaimRule(),
    ]
    for rule in rules:
        override = config.severity_overrides.get(rule.id)
        if override:
            rule.severity = severity_from_str(override, rule.severity) or rule.severity
    return sorted(rules, key=lambda rule: rule.id)
