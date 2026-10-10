"""Offline provenance validation and readers for external evaluation material."""

import argparse
import hashlib
import json
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

SPLITS = frozenset({"development", "holdout"})
FORMATS = frozenset({"markdown", "codesearchnet", "jfleg", "asset", "m2"})


class CorpusError(ValueError):
    """An external sample lacks valid provenance or native structure."""


@dataclass(frozen=True)
class Source:
    identity: str
    source_group: str
    pair_group: str
    path: str
    sha256: str
    split: str
    format: str
    provenance: dict[str, object]


@dataclass(frozen=True)
class TextSample:
    identity: str
    source_group: str
    pair_group: str
    split: str
    original: str
    references: tuple[str, ...] = ()


def _text(record: dict[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CorpusError(f"missing or invalid {field}")
    return value


def _path(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise CorpusError(f"path escapes corpus location: {relative}")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise CorpusError(f"path escapes corpus location: {relative}")
    return resolved


def _checked_bytes(source: Source, root: Path) -> bytes:
    path = _path(root, source.path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CorpusError(f"unreadable sample path: {source.path}") from error
    if hashlib.sha256(raw).hexdigest() != source.sha256:
        raise CorpusError(f"checksum mismatch: {source.identity}")
    return raw


def load_sources(manifest: Path, corpus_root: Path) -> tuple[Source, ...]:
    """Validate local bytes and keep related identities in one frozen split."""
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CorpusError("invalid source manifest") from error
    if not isinstance(data, dict) or data.get("version") != 1:
        raise CorpusError("unsupported source manifest version")
    records = data.get("samples")
    if not isinstance(records, list) or not records:
        raise CorpusError("samples must be a nonempty list")
    artifacts = data.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise CorpusError("artifacts must be a list")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise CorpusError("artifact must be an object")
        path = _path(corpus_root, _text(artifact, "path"))
        digest = _text(artifact, "sha256")
        parsed = urlsplit(_text(artifact, "url"))
        if parsed.scheme != "https" or not parsed.netloc:
            raise CorpusError("invalid artifact url")
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise CorpusError(f"unreadable artifact path: {path.name}") from error
        if hashlib.sha256(raw).hexdigest() != digest:
            raise CorpusError(f"artifact checksum mismatch: {path.name}")
    sources: list[Source] = []
    identities: set[str] = set()
    locators: set[tuple[str, str, str]] = set()
    groups: dict[tuple[str, str], str] = {}
    fingerprints: dict[str, str] = {}
    for record in records:
        if not isinstance(record, dict):
            raise CorpusError("sample must be an object")
        fields = {
            key: _text(record, key)
            for key in (
                "id",
                "source_group",
                "pair_group",
                "url",
                "revision",
                "license",
                "license_url",
                "attribution",
                "sha256",
                "path",
                "locator",
                "format",
                "split",
                "review_status",
            )
        }
        if fields["split"] not in SPLITS:
            raise CorpusError("invalid split")
        if fields["format"] not in FORMATS:
            raise CorpusError("invalid format")
        if fields["review_status"] != "unreviewed":
            raise CorpusError("source acquisition must remain unreviewed")
        if not re.fullmatch(r"[0-9a-f]{64}", fields["sha256"]):
            raise CorpusError("invalid sha256")
        for field in ("url", "license_url"):
            parsed = urlsplit(fields[field])
            if parsed.scheme != "https" or not parsed.netloc:
                raise CorpusError(f"invalid {field}")
        locator = (fields["source_group"], fields["revision"], fields["locator"])
        if fields["id"] in identities or locator in locators:
            raise CorpusError("duplicate sample identity or locator")
        identities.add(fields["id"])
        locators.add(locator)
        for field in ("source_group", "pair_group", "near_duplicate_group"):
            value = record.get(field)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise CorpusError(f"invalid {field}")
                key = (field, value)
                if key in groups and groups[key] != fields["split"]:
                    raise CorpusError(f"{field} crosses split: {value}")
                groups[key] = fields["split"]
        source = Source(
            fields["id"],
            fields["source_group"],
            fields["pair_group"],
            fields["path"],
            fields["sha256"],
            fields["split"],
            fields["format"],
            record,
        )
        original = read_sample(source, corpus_root).original
        normalized = " ".join(original.casefold().split())
        fingerprint = hashlib.sha256(normalized.encode()).hexdigest()
        if fingerprint in fingerprints and fingerprints[fingerprint] != source.split:
            raise CorpusError("normalized duplicate crosses split")
        fingerprints[fingerprint] = source.split
        sources.append(source)
    return tuple(sources)


def read_markdown(source: Source, corpus_root: Path) -> TextSample:
    """Preserve exact UTF-8 Markdown without executing template content."""
    if source.format != "markdown":
        raise CorpusError("expected markdown format")
    original = _checked_bytes(source, corpus_root).decode("utf-8")
    return TextSample(
        source.identity, source.source_group, source.pair_group, source.split, original
    )


@dataclass(frozen=True)
class CodeSample:
    original: str
    docstring: str
    repository: str
    metadata: dict[str, object]
    context: str = "function-only; surrounding module unavailable"


def read_codesearchnet(text: str) -> tuple[CodeSample, ...]:
    """Read Python JSON Lines while retaining native source metadata."""
    samples: list[CodeSample] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError as error:
            raise CorpusError(f"invalid CodeSearchNet JSON on line {number}") from error
        if not isinstance(record, dict):
            raise CorpusError("CodeSearchNet record must be an object")
        for field in ("repo", "path", "original_string", "docstring", "sha", "url"):
            _text(record, field)
        if record.get("language") != "python":
            raise CorpusError("CodeSearchNet sample must be Python")
        samples.append(
            CodeSample(
                record["original_string"], record["docstring"], record["repo"], record
            )
        )
    return tuple(samples)


def read_pairs(
    originals: Sequence[str],
    references: Sequence[Sequence[str]],
    dataset: str,
    source_group: str,
    split: str,
) -> tuple[TextSample, ...]:
    """Keep each JFLEG/ASSET original and every human reference together."""
    required = {"jfleg": 4, "asset": 10}.get(dataset)
    if required is None or len(references) != required:
        raise CorpusError(f"{dataset} requires {required} references")
    if split not in SPLITS:
        raise CorpusError("invalid split")
    if any(len(reference) != len(originals) for reference in references):
        raise CorpusError("reference files must be aligned with originals")
    return tuple(
        TextSample(
            f"{source_group}:{index + 1}",
            source_group,
            f"{source_group}:{index + 1}",
            split,
            original,
            tuple(reference[index] for reference in references),
        )
        for index, original in enumerate(originals)
    )


@dataclass(frozen=True)
class M2Edit:
    start: int
    end: int
    error_type: str
    correction: str
    annotator: str

    @property
    def is_noop(self) -> bool:
        return self.error_type == "noop"


@dataclass(frozen=True)
class M2Sentence:
    original: str
    edits: tuple[M2Edit, ...]
    tokenized: bool = True

    def source_span(self, edit: M2Edit) -> tuple[int, int] | None:
        """Map native token spans to this tokenized source, without detokenizing."""
        if edit.is_noop:
            return None
        tokens = list(re.finditer(r"\S+", self.original))
        start = (
            tokens[edit.start].start()
            if edit.start < len(tokens)
            else len(self.original)
        )
        end = start if edit.start == edit.end else tokens[edit.end - 1].end()
        return start, end


def read_m2(text: str) -> tuple[M2Sentence, ...]:
    """Preserve tokenized sources and annotator-specific M2 edits separately."""
    sentences: list[M2Sentence] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        if not block:
            continue
        lines = block.splitlines()
        if not lines[0].startswith("S "):
            raise CorpusError("M2 block must start with a source sentence")
        original = lines[0][2:]
        count = len(original.split())
        edits: list[M2Edit] = []
        for line in lines[1:]:
            fields = line.split("|||")
            if len(fields) != 6 or not fields[0].startswith("A "):
                raise CorpusError("invalid M2 edit")
            try:
                start, end = map(int, fields[0][2:].split())
            except ValueError as error:
                raise CorpusError("invalid M2 token span") from error
            noop = fields[1] == "noop"
            if (noop and (start, end) != (-1, -1)) or (
                not noop and not 0 <= start <= end <= count
            ):
                raise CorpusError("invalid M2 token span")
            if not fields[5] or not fields[1]:
                raise CorpusError("missing M2 annotator or error type")
            edits.append(M2Edit(start, end, fields[1], fields[2], fields[5]))
        sentences.append(M2Sentence(original, tuple(edits)))
    return tuple(sentences)


def read_sample(source: Source, corpus_root: Path) -> TextSample:
    """Verify bytes before adapting one manifest sample to an original text."""
    try:
        text = _checked_bytes(source, corpus_root).decode("utf-8")
    except UnicodeError as error:
        raise CorpusError(f"sample is not UTF-8: {source.identity}") from error
    references: tuple[str, ...] = ()
    if source.format == "markdown":
        original = text
    elif source.format == "codesearchnet":
        samples = read_codesearchnet(text)
        if len(samples) != 1:
            raise CorpusError("one manifest identity must name one CodeSearchNet row")
        original = samples[0].original
    elif source.format == "m2":
        sentences = read_m2(text)
        if len(sentences) != 1:
            raise CorpusError("one manifest identity must name one M2 sentence")
        original = sentences[0].original
    elif source.format in {"jfleg", "asset"}:
        try:
            record = json.loads(text)
        except ValueError as error:
            raise CorpusError("invalid reference bundle") from error
        if not isinstance(record, dict):
            raise CorpusError("reference bundle must be an object")
        original = _text(record, "original")
        variants = record.get("references")
        required = 4 if source.format == "jfleg" else 10
        if (
            not isinstance(variants, list)
            or len(variants) != required
            or not all(isinstance(value, str) for value in variants)
        ):
            raise CorpusError(f"{source.format} requires {required} string references")
        references = tuple(variants)
    else:
        raise CorpusError("unsupported format")
    return TextSample(
        source.identity,
        source.source_group,
        source.pair_group,
        source.split,
        original,
        references,
    )


def export_review_packet(
    sources: tuple[Source, ...], corpus_root: Path, output: Path
) -> None:
    """Create a fresh offline packet without predictions, revisions, or labels."""
    from benchmarks.evaluation_identity import rule_contract_snapshot

    if output.exists():
        raise CorpusError("review packet already exists; choose a new versioned path")
    files = {}
    contexts = {}
    originals = []
    for index, source in enumerate(sources):
        sample = read_sample(source, corpus_root)
        suffix = ".py" if source.format == "codesearchnet" else ".md"
        relative = f"originals/{index:04d}{suffix}"
        raw = sample.original.encode("utf-8")
        binding = {
            "source_id": sample.identity,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        files[relative] = binding
        contexts[relative] = {
            "source_group": sample.source_group,
            "pair_group": sample.pair_group,
            "split": sample.split,
            "format": source.format,
        }
        originals.append((relative, raw, sample.source_group))
    index_bytes = (
        json.dumps(
            {"version": 1, "files": files, "context": contexts},
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode()
    contracts_bytes = (
        json.dumps(rule_contract_snapshot(), sort_keys=True, indent=2) + "\n"
    ).encode()
    manifest = {
        "version": 3,
        "review": {
            "packet_index": {
                "path": "index.json",
                "sha256": hashlib.sha256(index_bytes).hexdigest(),
            },
            "rule_contracts": {
                "path": "contracts.json",
                "sha256": hashlib.sha256(contracts_bytes).hexdigest(),
            },
            "protocol_revision": "unreviewed-template-v1",
            "policy": {
                "mode": "all-rules",
                "profile": "default",
                "severity": "info",
                "min_confidence": "low",
            },
            "reviewers": [],
        },
        "files": {
            relative: {
                **files[relative],
                "source_group": group,
                "reviewed_rules": [],
                "regions": [],
                "expected": [],
                "negative_cases": [],
            }
            for relative, _raw, group in originals
        },
    }
    (output / "originals").mkdir(parents=True)
    for relative, raw, _group in originals:
        (output / relative).write_bytes(raw)
    (output / "index.json").write_bytes(index_bytes)
    (output / "contracts.json").write_bytes(contracts_bytes)
    (output / "annotations.unreviewed.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Validate cached provenance and optionally export blind original prose."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--export-blind", help="output path relative to the cache")
    parser.add_argument(
        "--export-review-packet", help="fresh packet directory relative to the cache"
    )
    args = parser.parse_args(argv)
    try:
        sources = load_sources(args.manifest, args.cache)
        if args.export_review_packet:
            export_review_packet(
                sources, args.cache, _path(args.cache, args.export_review_packet)
            )
        if args.export_blind:
            output = _path(args.cache, args.export_blind)
            output.parent.mkdir(parents=True, exist_ok=True)
            records = []
            for source in sources:
                sample = read_sample(source, args.cache)
                records.append(
                    json.dumps(
                        {
                            "id": sample.identity,
                            "source_group": sample.source_group,
                            "pair_group": sample.pair_group,
                            "split": sample.split,
                            "format": source.format,
                            "original": sample.original,
                            "review_status": "unreviewed",
                        },
                        ensure_ascii=False,
                    )
                )
            output.write_text("\n".join(records) + "\n", encoding="utf-8")
    except CorpusError as error:
        parser.exit(1, f"{error}\n")
    print(
        json.dumps(
            {
                "samples": len(sources),
                "by_format": dict(
                    sorted(Counter(source.format for source in sources).items())
                ),
                "by_split": dict(
                    sorted(Counter(source.split for source in sources).items())
                ),
                "review_status": "unreviewed",
                "findings_generated": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
