"""Code-specific detection rules (C001-C009)."""

import ast
import re
import unicodedata
from collections import Counter
from collections.abc import Iterator
from typing import ClassVar

from proseprobe.data.code_patterns import (
    AI_PLACEHOLDER_COMMENT_PATTERNS,
    AI_PLACEHOLDER_INLINE_PATTERNS,
    AI_PLACEHOLDER_MESSAGES,
    COLLABORATIVE_COMMENT_PATTERNS,
    VERBOSE_COMMENT_PATTERNS,
)
from proseprobe.data.vocabulary import AI_VOCABULARY, DOCSTRING_AI_VOCABULARY
from proseprobe.parsers.prose import ProseBlock
from proseprobe.parsers.python import Docstring, _get_cached_parser
from proseprobe.rules.base import Confidence, Issue, Rule, Severity

_IDENTIFIER_WORD = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|[A-Z]+|\d+")
_SIGNATURE_CONNECTIVES = frozenset(
    {"a", "an", "and", "by", "for", "from", "of", "the", "to", "with"}
)


class DocstringVocabularyRule(Rule):
    """C001: Detect Python-specific vocabulary in docstrings."""

    id = "C001"
    name = "Docstring-Only Vocabulary"
    description = "Detects Python docstring terms not covered by V001"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"python"}

    def __init__(
        self,
        allowed: set[str] | None = None,
        additional: set[str] | None = None,
    ) -> None:
        super().__init__()
        self._allowed = {w.lower() for w in (allowed or set())}
        general_words = AI_VOCABULARY | {
            word.lower() for word in (additional or set()) if isinstance(word, str)
        }
        self._ai_words = [
            item
            for item in DOCSTRING_AI_VOCABULARY
            if item[1].lower() not in general_words
        ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for overused vocabulary in docstrings."""
        issues: list[Issue] = []

        parser = _get_cached_parser(content)
        if not parser.parse():
            return issues

        for block in parser.get_docstring_prose_blocks():
            for pattern, word, replacement in self._ai_words:
                if word.lower() in self._allowed:
                    continue
                found: tuple[int, re.Match[str]] | None = None
                for line_num, line in block.lines:
                    if match := re.search(pattern, line, re.IGNORECASE):
                        found = (line_num, match)
                        break
                if found is None:
                    continue
                line_num, match = found
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Overused word in docstring: '{word}'",
                        line=line_num,
                        column=match.start() + 1,
                        end_column=match.end() + 1,
                        severity=self.severity,
                        suggestion=replacement,
                    )
                )

        return issues


class VerboseCommentsRule(Rule):
    """C002: Detect over-explained code comments."""

    id = "C002"
    name = "Verbose Comments"
    description = "Detects comments with excessive verbosity patterns"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"python"}

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for verbose comments."""
        issues: list[Issue] = []

        parser = _get_cached_parser(content)
        comments = parser.get_comments()

        lines = content.split("\n")
        for comment in comments:
            source_comment = lines[comment.line - 1][comment.column - 1 :]
            for pattern, reason in VERBOSE_COMMENT_PATTERNS:
                match = re.search(pattern, source_comment, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Verbose comment: {reason}",
                            line=comment.line,
                            column=comment.column + match.start(),
                            end_column=comment.column + match.end(),
                            severity=self.severity,
                        )
                    )
                    break  # Only one issue per line

        return issues


class CollaborativeCommentsRule(Rule):
    """C003: Detect chat phrases in code comments."""

    id = "C003"
    name = "Collaborative Comments"
    description = "Detects 'I hope this helps' in # comments"
    severity = Severity.WARNING
    applies_to: ClassVar[set[str]] = {"python"}

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for collaborative comments."""
        issues: list[Issue] = []
        parser = _get_cached_parser(content)
        comments = parser.get_comments()

        lines = content.split("\n")
        for comment in comments:
            source_comment = lines[comment.line - 1][comment.column - 1 :]
            for pattern, phrase in COLLABORATIVE_COMMENT_PATTERNS:
                match = re.search(pattern, source_comment, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Chat phrase in comment: '{phrase}'",
                            line=comment.line,
                            column=comment.column + match.start(),
                            end_column=comment.column + match.end(),
                            severity=self.severity,
                        )
                    )
                    break

        return issues


class AIPlaceholdersRule(Rule):
    """C004: Detect formulaic placeholders."""

    id = "C004"
    name = "Formulaic Placeholders"
    description = "Detects context-free markers, generic TODOs, and boilerplate"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"python"}

    @staticmethod
    def _contract_statements(tree: ast.Module | None) -> set[ast.stmt]:
        """Recognize simple contract stubs with unambiguous source imports."""
        if tree is None:
            return set()
        imported: dict[str, str] = {}
        supported = {"abc.abstractmethod", "typing.overload", "typing.Protocol"}
        for statement in tree.body:
            if isinstance(statement, ast.Import):
                for alias in statement.names:
                    if alias.name in {"abc", "typing", "builtins"}:
                        imported[alias.asname or alias.name] = alias.name
            elif isinstance(statement, ast.ImportFrom) and statement.level == 0:
                for alias in statement.names:
                    name = f"{statement.module}.{alias.name}"
                    if name in supported:
                        imported[alias.asname or alias.name] = name
        if not imported:
            return set()

        bindings: Counter[str] = Counter()
        mutated: set[str] = set()
        for node in ast.walk(tree):
            for parameter in getattr(node, "type_params", ()):
                bindings[parameter.name] += 1
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name == "*":
                        return set()
                    name = alias.asname or (
                        alias.name.split(".")[0]
                        if isinstance(node, ast.Import)
                        else alias.name
                    )
                    bindings[name] += 1
            elif isinstance(node, ast.Name) and isinstance(
                node.ctx, (ast.Store, ast.Del)
            ):
                bindings[node.id] += 1
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                bindings[node.name] += 1
            elif isinstance(node, ast.arg):
                bindings[node.arg] += 1
            elif isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
                if node.name is not None:
                    bindings[node.name] += 1
            elif isinstance(node, ast.MatchMapping) and node.rest is not None:
                bindings[node.rest] += 1
            elif isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
                node.ctx, (ast.Store, ast.Del)
            ):
                root = node.value
                while isinstance(root, (ast.Attribute, ast.Subscript)):
                    root = root.value
                if isinstance(root, ast.Name):
                    mutated.add(root.id)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id
                in {"exec", "eval", "globals", "locals", "vars", "setattr", "delattr"}
            ):
                return set()
        proven = {
            name: symbol
            for name, symbol in imported.items()
            if bindings[name] == 1 and name not in mutated
        }
        builtin_namespace_mutated = any(
            symbol == "builtins" and name in mutated
            for name, symbol in imported.items()
        )

        def resolve(expression: ast.expr) -> str | None:
            if isinstance(expression, ast.Name):
                if (
                    expression.id in {"classmethod", "staticmethod"}
                    and (bindings[expression.id] == 0)
                    and not builtin_namespace_mutated
                ):
                    return f"builtins.{expression.id}"
                return proven.get(expression.id)
            if isinstance(expression, ast.Attribute) and isinstance(
                expression.value, ast.Name
            ):
                module = proven.get(expression.value.id)
                symbol = f"{module}.{expression.attr}"
                return symbol if symbol in supported else None
            return None

        protocol_methods = {
            method
            for owner in ast.walk(tree)
            if isinstance(owner, ast.ClassDef)
            and len(owner.bases) == 1
            and resolve(owner.bases[0]) == "typing.Protocol"
            and not owner.keywords
            and not owner.decorator_list
            for method in owner.body
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        protected: set[ast.stmt] = set()
        decorator_contracts = {"abc.abstractmethod", "typing.overload"}
        allowed_decorators = decorator_contracts | {
            "builtins.classmethod",
            "builtins.staticmethod",
        }
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = [resolve(decorator) for decorator in function.decorator_list]
            if any(decorator not in allowed_decorators for decorator in decorators):
                continue
            if not (
                decorator_contracts.intersection(decorators)
                or function in protocol_methods
            ):
                continue
            body = function.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                body = body[1:]
            if len(body) != 1:
                continue
            statement = body[0]
            if (
                isinstance(statement, ast.Pass)
                or (
                    isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and statement.value.value is Ellipsis
                )
                or (
                    isinstance(statement, ast.Raise)
                    and isinstance(statement.exc, ast.Call)
                    and isinstance(statement.exc.func, ast.Name)
                    and statement.exc.func.id == "NotImplementedError"
                )
            ):
                protected.add(statement)
        return protected

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for formulaic placeholders."""
        issues: list[Issue] = []

        lines = content.split("\n")
        parser = _get_cached_parser(content)
        comments = parser.get_comments()

        # Comment-only placeholders
        tree = parser.get_syntax_tree()
        contract_statements = self._contract_statements(tree)
        statements = (
            [node for node in ast.walk(tree) if isinstance(node, ast.stmt)]
            if tree is not None
            else []
        )
        last_statements: dict[int, ast.stmt] = {}
        for node in statements:
            if (node.end_lineno or node.lineno) != node.lineno:
                continue
            previous = last_statements.get(node.lineno)
            if previous is None or (
                node.end_col_offset or node.col_offset,
                node.col_offset,
            ) > (previous.end_col_offset or previous.col_offset, previous.col_offset):
                last_statements[node.lineno] = node
        for comment in comments:
            source_comment = lines[comment.line - 1][comment.column - 1 :]
            matched_comment = False
            for pattern, kind in AI_PLACEHOLDER_COMMENT_PATTERNS:
                match = re.search(pattern, source_comment, re.IGNORECASE)
                if match:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Formulaic placeholder: {kind}",
                            line=comment.line,
                            column=comment.column + match.start(),
                            end_column=comment.column + match.end(),
                            severity=self.severity,
                        )
                    )
                    matched_comment = True
                    break

            # Inline code + comment placeholders
            if matched_comment:
                continue
            line_text = lines[comment.line - 1]
            source_comment = line_text[comment.column - 1 :]
            statement = last_statements.get(comment.line)
            code = ""
            if (
                statement is not None
                and statement not in contract_statements
                and parser.get_node_span(statement)[3] <= comment.column
                and (
                    isinstance(statement, ast.Pass)
                    or (
                        isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and statement.value.value is Ellipsis
                    )
                )
            ):
                code = ast.get_source_segment(content, statement) or ""
            for code_pattern, todo_pattern, kind in AI_PLACEHOLDER_INLINE_PATTERNS:
                todo_match = re.search(todo_pattern, source_comment, re.IGNORECASE)
                if re.search(code_pattern, code) and todo_match is not None:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Formulaic placeholder: {kind}",
                            line=comment.line,
                            column=comment.column + todo_match.start(),
                            end_column=comment.column + todo_match.end(),
                            severity=self.severity,
                        )
                    )
                    break

        # Code-only placeholders
        reported_lines: set[int] = set()
        for node in sorted(statements, key=lambda item: (item.lineno, item.col_offset)):
            if (
                not isinstance(node, ast.Raise)
                or node in contract_statements
                or not isinstance(node.exc, ast.Call)
                or not isinstance(node.exc.func, ast.Name)
                or node.exc.func.id != "NotImplementedError"
                or len(node.exc.args) != 1
                or node.exc.keywords
                or not isinstance(node.exc.args[0], ast.Constant)
                or not isinstance(node.exc.args[0].value, str)
                or node.lineno in reported_lines
            ):
                continue
            message = re.sub(r"\s+", " ", node.exc.args[0].value, flags=re.ASCII).strip(
                " "
            )
            message = message.casefold().removesuffix(".")
            if message not in AI_PLACEHOLDER_MESSAGES:
                continue
            start_line, start_column, _, _ = parser.get_node_span(node)
            end_line, end_column = parser.get_node_span(node.exc)[2:]
            issues.append(
                Issue(
                    rule_id=self.id,
                    message="Formulaic placeholder: template error",
                    line=start_line,
                    column=start_column,
                    end_line=end_line if end_line != start_line else None,
                    end_column=end_column,
                    severity=self.severity,
                )
            )
            reported_lines.add(node.lineno)

        return issues


class CommentRestatesCodeRule(Rule):
    """C006: Detect exact comments that restate the next statement."""

    id = "C006"
    name = "Comment Restates Code"
    description = "Detects exact comments that restate the next Python statement"
    severity = Severity.INFO
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"python"}

    @staticmethod
    def _name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    @staticmethod
    def _words(text: str) -> tuple[str, ...]:
        return tuple(
            match.group().casefold() for match in _IDENTIFIER_WORD.finditer(text)
        )

    @classmethod
    def _expected_comments(cls, statement: ast.stmt) -> set[tuple[str, ...]]:
        name: str | None = None
        verbs: tuple[str, ...] = ()
        if isinstance(statement, ast.Return) and statement.value is not None:
            name = cls._name(statement.value)
            verbs = ("return",)
        elif isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            name = cls._name(statement.targets[0])
            verbs = ("assign", "set")
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            name = cls._name(statement.target)
            verbs = ("assign", "set")
        elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            name = cls._name(statement.value.func)
            verbs = ("call",)

        words = cls._words(name or "")
        return {(verb, *words) for verb in verbs} if words else set()

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check adjacent full-line comments against supported statements."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        supported = (ast.Return, ast.Assign, ast.AnnAssign, ast.Expr)
        statements = {
            (node.lineno, node.col_offset): node
            for node in ast.walk(tree)
            if isinstance(node, supported)
        }
        lines = content.split("\n")
        issues: list[Issue] = []
        for comment in _get_cached_parser(content).get_comments():
            if comment.is_inline:
                continue
            statement = statements.get((comment.line + 1, comment.column - 1))
            if statement is None or self._words(comment.content) not in (
                self._expected_comments(statement)
            ):
                continue
            after_hash = lines[comment.line - 1][comment.column :]
            leading_space = len(after_hash) - len(after_hash.lstrip())
            column = comment.column + leading_space + 1
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Comment restates code: '{comment.content}'",
                    line=comment.line,
                    column=column,
                    end_column=column + len(comment.content),
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Delete it or explain why the code exists",
                )
            )
        return issues


class DocstringRepeatsSignatureRule(Rule):
    """C007: Detect opening docstring sentences that repeat the signature."""

    id = "C007"
    name = "Docstring Repeats Signature"
    description = "Detects function docstrings that only repeat signature words"
    severity = Severity.INFO
    applies_to: ClassVar[set[str]] = {"python"}

    @staticmethod
    def _words(text: str) -> set[str]:
        return {match.group().casefold() for match in _IDENTIFIER_WORD.finditer(text)}

    @classmethod
    def _repeats_signature(cls, opening: str, docstring: Docstring) -> bool:
        signature = cls._words(
            " ".join((docstring.owner_name or "", *docstring.parameters))
        )
        if len(signature) < 2:
            return False
        opening_words = cls._words(opening)
        opening_words.difference_update(_SIGNATURE_CONNECTIVES - signature)
        return opening_words == signature

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check function docstring openings against their signatures."""
        parser = _get_cached_parser(content)
        if not parser.parse():
            return []

        sentences = parser.get_prose_sentences()
        issues: list[Issue] = []
        for docstring in parser.get_docstrings():
            if docstring.node_type != "function":
                continue
            opening = next(
                (
                    sentence
                    for sentence in sentences
                    if docstring.line <= sentence.start_line <= docstring.end_line
                ),
                None,
            )
            if opening is None or not self._repeats_signature(opening.text, docstring):
                continue
            line, column = opening.source_position()
            end_line, end_column = opening.source_position(len(opening.text))
            issues.append(
                Issue(
                    rule_id=self.id,
                    message="Docstring opening repeats the function signature",
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    severity=self.severity,
                    suggestion="Describe behavior, results, or constraints",
                )
            )
        return issues


class StaleDocstringParameterRule(Rule):
    """C009: Detect explicit docstring fields absent from a source signature."""

    id = "C009"
    name = "Stale Docstring Parameter"
    description = (
        "Detects Sphinx parameter names or explicit kinds that conflict with signatures"
    )
    severity = Severity.INFO
    default_confidence = Confidence.HIGH
    applies_to: ClassVar[set[str]] = {"python"}
    _field = re.compile(
        r"^[ \t]*:param[ \t]+(?:[\w.]+[ \t]+)?(?P<name>\*{0,2}[^\s:]+)[ \t]*:"
    )
    _literal_directive = re.compile(
        r"^\.\.[ \t]+(?:code(?:-block)?|parsed-literal|doctest)::(?:\s|$)"
    )
    _kind_labels: ClassVar[dict[str, str]] = {
        "positional_only": "a positional-only parameter",
        "positional": "a positional parameter",
        "keyword_only": "a keyword-only parameter",
        "var_positional": "variadic positional arguments",
        "var_keyword": "variadic keyword arguments",
    }

    @classmethod
    def _declaration_lines(
        cls, block: ProseBlock, source_lines: list[str]
    ) -> Iterator[tuple[int, str]]:
        fence = ""
        literal_indent: int | None = None
        doctest = False
        for index, (line_num, line) in enumerate(block.lines):
            stripped = line.strip()
            if fence:
                if re.fullmatch(
                    re.escape(fence[0]) + "{" + str(len(fence)) + r",}", stripped
                ):
                    fence = ""
                continue
            if opener := re.match(r"(`{3,}|~{3,})", stripped):
                fence = opener.group(1)
                continue
            if not stripped:
                doctest = False
                continue
            if doctest or stripped.startswith(">>>"):
                doctest = True
                continue
            source = source_lines[line_num - 1] if index == 0 else line
            indent = len(source) - len(source.lstrip())
            if literal_indent is not None:
                if indent > literal_indent:
                    continue
                literal_indent = None
            if cls._literal_directive.match(stripped):
                literal_indent = indent
                continue
            yield line_num, line
            if stripped.endswith("::"):
                literal_indent = indent

    def check(self, content: str, filename: str) -> list[Issue]:
        """Compare physical Sphinx fields against their own source signatures."""
        parser = _get_cached_parser(content)
        if not parser.parse():
            return []
        blocks = {
            block.start_line: block for block in parser.get_docstring_prose_blocks()
        }
        source_lines = content.split("\n")
        issues: list[Issue] = []
        for docstring in parser.get_docstrings():
            if docstring.node_type != "function" or docstring.has_dynamic_decorators:
                continue
            block = blocks.get(docstring.line)
            if block is None:
                continue
            parameters = dict(docstring.signature_parameters)
            for line_num, line in self._declaration_lines(block, source_lines):
                match = self._field.match(line)
                if match is None:
                    continue
                raw_name = match.group("name")
                name = raw_name.lstrip("*")
                if not name.isidentifier():
                    continue
                field_start = line.index(":param", match.start(), match.end())
                raw_field = source_lines[line_num - 1][field_start : match.end()]
                if '"' in raw_field or "'" in raw_field:
                    continue
                kind = parameters.get(unicodedata.normalize("NFKC", name))
                explicit_kind = (
                    "var_keyword"
                    if raw_name.startswith("**")
                    else "var_positional"
                    if raw_name.startswith("*")
                    else None
                )
                if kind is not None:
                    if explicit_kind is None or explicit_kind == kind:
                        continue
                    message = (
                        f"Docstring parameter '{raw_name}' declares "
                        f"{self._kind_labels[explicit_kind]}, but the function signature "
                        f"declares {self._kind_labels[kind]}"
                    )
                    suggestion = "Check the field's stars and the parameter kind in the signature"
                else:
                    if docstring.accepts_kwargs and explicit_kind is None:
                        continue
                    message = f"Docstring parameter '{name}' is absent from the function signature"
                    suggestion = (
                        "Update the field to match the parameter name, or remove it"
                    )
                start = match.start("name") + len(raw_name) - len(name)
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=message,
                        line=line_num,
                        column=start + 1,
                        end_column=match.end("name") + 1,
                        severity=self.severity,
                        confidence=self.default_confidence,
                        suggestion=suggestion,
                    )
                )
        return issues


class ExplicitReturnTypeConflictRule(Rule):
    """C010: Detect the supported explicit None-versus-int return conflict."""

    id = "C010"
    name = "Explicit Return Type Conflict"
    description = (
        "Detects explicit None annotations conflicting with Sphinx int return types"
    )
    severity = Severity.INFO
    default_confidence = Confidence.MEDIUM
    applies_to: ClassVar[set[str]] = {"python"}
    _field = re.compile(r"^[ \t]*:rtype:[ \t]*(?P<type>\S.*?)[ \t]*$")

    @staticmethod
    def _supported_bindings(tree: ast.Module) -> bool:
        names = {"int", "classmethod", "staticmethod"}
        for node in ast.walk(tree):
            if any(
                getattr(parameter, "name", None) in names
                for parameter in getattr(node, "type_params", ())
            ):
                return False
            if isinstance(node, ast.Name) and (
                (node.id in names and isinstance(node.ctx, (ast.Store, ast.Del)))
                or node.id
                in {
                    "globals",
                    "locals",
                    "vars",
                    "exec",
                    "eval",
                    "setattr",
                    "delattr",
                    "__import__",
                    "__builtins__",
                }
            ):
                return False
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name in names
            ):
                return False
            if isinstance(node, ast.arg) and node.arg in names:
                return False
            if (
                isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar))
                and node.name in names
            ):
                return False
            if isinstance(node, ast.MatchMapping) and node.rest in names:
                return False
            if isinstance(node, ast.ImportFrom) and (
                node.module == "builtins"
                or any(alias.name == "*" for alias in node.names)
            ):
                return False
            if isinstance(node, (ast.Import, ast.ImportFrom)) and any(
                (alias.asname or alias.name.split(".")[0]) in names
                or alias.name == "builtins"
                for alias in node.names
            ):
                return False
        return True

    def check(self, content: str, filename: str) -> list[Issue]:
        """Compare physical fields without inferring intended runtime returns."""
        parser = _get_cached_parser(content)
        tree = parser.get_syntax_tree()
        if tree is None or not self._supported_bindings(tree):
            return []
        blocks = {
            block.start_line: block for block in parser.get_docstring_prose_blocks()
        }
        source_lines = content.split("\n")
        issues: list[Issue] = []
        for docstring in parser.get_docstrings():
            if docstring.return_annotation is None or docstring.has_dynamic_decorators:
                continue
            block = blocks.get(docstring.line)
            if block is None:
                continue
            declarations = list(
                StaleDocstringParameterRule._declaration_lines(block, source_lines)
            )
            fields = [
                (index, line_num, line, match)
                for index, (line_num, line) in enumerate(declarations)
                if (match := self._field.match(line)) is not None
            ]
            if len(fields) != 1:
                continue
            index, line_num, line, match = fields[0]
            if match.group("type") != "int":
                continue
            field_start = line.index(":rtype", match.start(), match.end())
            raw_field = source_lines[line_num - 1][field_start : match.end("type")]
            if "'" in raw_field or '"' in raw_field:
                continue
            indent = len(line) - len(line.lstrip())
            if index + 1 < len(declarations):
                _, following = declarations[index + 1]
                following_indent = len(following) - len(following.lstrip())
                if following_indent > indent and not following.lstrip().startswith(":"):
                    continue
            issues.append(
                Issue(
                    rule_id=self.id,
                    message="Explicit return declarations conflict: annotation 'None', Sphinx type 'int'",
                    line=line_num,
                    column=match.start("type") + 1,
                    end_column=match.end("type") + 1,
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Check both explicit return declarations",
                )
            )
        return issues


class CommentedOutCodeRule(Rule):
    """C008: Detect full-line comments that parse as code statements."""

    id = "C008"
    name = "Commented-Out Code"
    description = "Detects full-line comments containing exact Python statements"
    severity = Severity.INFO
    default_confidence = Confidence.LOW
    applies_to: ClassVar[set[str]] = {"python"}

    @staticmethod
    def _statement_kind(text: str) -> str | None:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            if not text.rstrip().endswith(":"):
                return None
            try:
                tree = ast.parse(f"{text}\n    pass")
            except SyntaxError:
                return None

        if len(tree.body) != 1:
            return None
        statement = tree.body[0]
        if isinstance(statement, (ast.Assign, ast.AugAssign)) or (
            isinstance(statement, ast.AnnAssign) and statement.value is not None
        ):
            return "assignment"
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            return "call"
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            return "import"
        if isinstance(statement, (ast.If, ast.For, ast.While, ast.With)):
            return "control statement"
        return None

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check full-line Python comments for exact statement syntax."""
        lines = content.split("\n")
        issues: list[Issue] = []
        for comment in _get_cached_parser(content).get_comments():
            if comment.is_inline:
                continue
            kind = self._statement_kind(comment.content)
            if kind is None:
                continue
            after_hash = lines[comment.line - 1][comment.column :]
            leading_space = len(after_hash) - len(after_hash.lstrip())
            column = comment.column + leading_space + 1
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Commented-out code: {kind}",
                    line=comment.line,
                    column=column,
                    end_column=column + len(comment.content),
                    severity=self.severity,
                    confidence=self.default_confidence,
                    suggestion="Delete it or restore it as executable code",
                )
            )
        return issues
