"""Offline identities for reviewed material and the implementation evaluating it."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from proseprobe.rules import get_rule_metadata


def rule_contract_snapshot(rule_ids: set[str] | None = None) -> dict[str, Any]:
    """Capture canonical declared rule contracts separately from implementation."""
    contracts = {}
    for metadata in get_rule_metadata():
        if rule_ids is not None and metadata.id not in rule_ids:
            continue
        record = asdict(metadata)
        record["default_severity"] = metadata.default_severity.value
        record["default_confidence"] = metadata.default_confidence.value
        record["applies_to"] = list(metadata.applies_to)
        record["profiles"] = list(metadata.profiles)
        contracts[metadata.id] = record
    return {"version": 1, "rules": contracts}
