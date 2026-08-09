"""Detection rule registration."""

from proseprobe.config import Config
from proseprobe.profiles import profile_names_for_rule
from proseprobe.rules import code, grammar, markup, struct, style, vocab
from proseprobe.rules.base import Rule, RuleMetadata, severity_from_str

__all__ = ["get_all_rules", "get_rule_metadata", "get_rule_metadata_by_id"]


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
        grammar.GenericSceneSettingOpenerRule(),
        grammar.EmptyItOpenerRule(),
        grammar.UnclearActorRequirementRule(),
        grammar.DoubleNegativeRule(),
        markup.WrongMarkupRule(),
        markup.ChatGPTMarkersRule(),
        markup.UTMParametersRule(),
        markup.BrokenReferencesRule(),
        markup.UnresolvedMarkdownReferencesRule(),
        markup.TemplateResidueRule(),
        markup.UnclosedCodeFenceRule(),
        markup.SkippedHeadingLevelRule(),
        markup.BareURLInProseRule(),
        markup.NonDescriptiveLinkTextRule(),
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
        struct.WallOfTextParagraphRule(thresholds.wall_of_text_sentences),
        struct.HeadingWithoutBodyRule(),
        struct.ExcessiveHeadingDepthRule(),
        style.TitleCaseHeadingsRule(),
        style.BoldOveruseRule(thresholds.bold_overuse),
        style.EmDashOveruseRule(thresholds.em_dash_overuse),
        style.QuoteInconsistencyRule(),
        style.EmojiInProseRule(),
        style.ElegantVariationRule(),
        style.ShortPunchyFragmentsRule(thresholds.short_punchy_fragments),
        style.SentenceLengthRule(thresholds.sentence_length_max),
        style.RepeatedOrMixedPunctuationRule(),
        style.RhetoricalEllipsisRule(),
        style.NestedParentheticalRule(),
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
        vocab.WordyPhraseRule(),
        vocab.RedundantPairRule(),
        vocab.VerboseVerbPhraseRule(),
        vocab.RedundantModifierRule(),
        vocab.ImpreciseQuantityRule(),
        vocab.AbsoluteReliabilityClaimRule(),
    ]
    for rule in rules:
        override = config.severity_overrides.get(rule.id)
        if override:
            rule.severity = severity_from_str(override, rule.severity) or rule.severity
    return sorted(rules, key=lambda rule: rule.id)


def get_rule_metadata() -> tuple[RuleMetadata, ...]:
    """Return immutable metadata for every registered rule."""
    return tuple(
        RuleMetadata(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            category=rule.category,
            default_severity=type(rule).severity,
            default_confidence=rule.default_confidence,
            applies_to=tuple(sorted(rule.applies_to)),
            content_scope=rule.content_scope,
            profiles=profile_names_for_rule(rule.id),
            config_key=rule.config_key,
        )
        for rule in get_all_rules()
    )


def get_rule_metadata_by_id(rule_id: str) -> RuleMetadata | None:
    """Return metadata for a rule ID, or None when the ID is unknown."""
    normalized = rule_id.upper()
    return next((item for item in get_rule_metadata() if item.id == normalized), None)
