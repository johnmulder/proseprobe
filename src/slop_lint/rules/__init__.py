"""Detection rules for bad writing practices.

Rule classes are auto-discovered from the modules listed in ``_RULE_MODULES``.
To add a new rule, create a ``Rule`` subclass in one of those modules — no
edits to this file are needed unless the rule's threshold must be wired to
:class:`~slop_lint.config.ThresholdsConfig` (one line in ``_THRESHOLD_KEYS``).
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any

from slop_lint.config import Config, ThresholdsConfig
from slop_lint.rules.base import Confidence, Issue, Rule, Severity, severity_from_str

__all__ = [
    "Confidence",
    "Issue",
    "Rule",
    "Severity",
    "get_all_rules",
    "severity_from_str",
]

# Modules containing Rule subclasses.
# To register rules from a new module, append its dotted path here.
_RULE_MODULES: tuple[str, ...] = (
    "slop_lint.rules.vocab",
    "slop_lint.rules.style",
    "slop_lint.rules.struct",
    "slop_lint.rules.grammar",
    "slop_lint.rules.code",
    "slop_lint.rules.markup",
)

# Maps rule ID → ThresholdsConfig field name for rules wired to config.
# Rules with a ``threshold`` parameter not listed here use their class default.
_THRESHOLD_KEYS: dict[str, str] = {
    "S001": "rule_of_three",
    "S004": "inline_header_lists",
    "S010": "anaphora_abuse",
    "S011": "gerund_fragment_litany",
    "S013": "historical_analogy_stacking",
    "S018": "citation_name_drop",
    "T002": "bold_overuse",
    "T003": "em_dash_overuse",
    "T007": "short_punchy_fragments",
    "T008": "sentence_length_max",
    "G011": "nominalization_overload",
    "G012": "passive_voice_overuse",
    "V007": "invented_concept_labels",
}


def _discover_rule_classes() -> list[type[Rule]]:
    """Auto-discover all Rule subclasses from registered modules."""
    classes: list[type[Rule]] = []
    for module_path in _RULE_MODULES:
        module = importlib.import_module(module_path)
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Rule)
                and obj is not Rule
                and obj.__module__ == module_path
            ):
                classes.append(obj)
    return sorted(classes, key=lambda c: c.id)


def _instantiate_rule(
    cls: type[Rule],
    thresholds: ThresholdsConfig,
    vocab_kwargs: dict[str, Any],
) -> Rule:
    """Instantiate a rule, injecting config values for recognized parameters."""
    sig = inspect.signature(cls.__init__)
    params = sig.parameters
    kwargs: dict[str, Any] = {}

    if "threshold" in params:
        key = _THRESHOLD_KEYS.get(cls.id)
        if key is not None:
            kwargs["threshold"] = getattr(thresholds, key)

    for name in ("allowed", "additional", "allowed_phrases"):
        if name in params and name in vocab_kwargs:
            kwargs[name] = vocab_kwargs[name]

    return cls(**kwargs)


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
    """Get instances of all available rules."""
    severity_overrides: dict[str, str] = {}
    thresholds = ThresholdsConfig()
    vocab_kwargs: dict[str, Any] = {}

    if config is not None:
        vocab_kwargs = {
            "allowed": {w.lower() for w in config.vocabulary.allowed},
            "additional": {w.lower() for w in config.vocabulary.additional},
            "allowed_phrases": set(config.vocabulary.allowed_phrases),
        }
        severity_overrides = config.severity_overrides
        thresholds = config.thresholds

    rule_classes = _discover_rule_classes()
    rules = [_instantiate_rule(cls, thresholds, vocab_kwargs) for cls in rule_classes]

    if severity_overrides:
        rules = _apply_severity_overrides(rules, severity_overrides)

    return rules
