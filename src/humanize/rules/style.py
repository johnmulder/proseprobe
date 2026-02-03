"""Style detection rules (T001-T006)."""

import re

from humanize.parsers.markdown import MarkdownParser, is_markdown_file, iter_prose_lines
from humanize.rules.base import Issue, Rule, Severity


class TitleCaseHeadingsRule(Rule):
    """T001: Detect improper title case in headings."""

    id = "T001"
    name = "Title Case Headings"
    description = "Detects improper capitalization in headings"
    severity = Severity.INFO
    fixable = False

    # Words that should not be capitalized in title case (except at start)
    _small_words = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "in",
        "nor",
        "of",
        "on",
        "or",
        "so",
        "the",
        "to",
        "up",
        "yet",
    }

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for title case headings."""
        issues: list[Issue] = []
        if not is_markdown_file(filename):
            return issues

        parser = MarkdownParser(content)
        for section in parser.get_headings():
            words = section.title.split()

            # Check if it looks like title case
            capitalized_count = sum(
                1
                for w in words
                if w[0].isupper() and w.lower() not in self._small_words
            )

            # If more than 60% of words are capitalized, it's likely title case
            if len(words) >= 3 and capitalized_count / len(words) > 0.6:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message="Title case heading (consider sentence case)",
                        line=section.start_line,
                        column=section.level + 2,
                        severity=self.severity,
                    )
                )

        return issues


class BoldOveruseRule(Rule):
    """T002: Detect excessive bold emphasis."""

    id = "T002"
    name = "Bold Overuse"
    description = "Detects excessive **bold** usage per paragraph"
    severity = Severity.INFO
    fixable = False

    # Threshold: max bold phrases per paragraph
    _threshold = 3

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for bold overuse."""
        issues: list[Issue] = []
        if is_markdown_file(filename):
            parser = MarkdownParser(content)
            paragraphs = parser.get_paragraphs()
        else:
            paragraphs = []
            lines = content.split("\n")
            start_line = 1
            current_lines: list[str] = []
            for line_num, line in enumerate(lines, start=1):
                if not line.strip():
                    if current_lines:
                        paragraphs.append(
                            (start_line, line_num - 1, "\n".join(current_lines))
                        )
                        current_lines = []
                    start_line = line_num + 1
                else:
                    if not current_lines:
                        start_line = line_num
                    current_lines.append(line)
            if current_lines:
                paragraphs.append((start_line, len(lines), "\n".join(current_lines)))

        for start_line, _, text in paragraphs:
            bold_count = len(re.findall(r"\*\*[^*]+\*\*", text))
            if bold_count > self._threshold:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Bold overuse: {bold_count} bold phrases in paragraph",
                        line=start_line,
                        column=1,
                        severity=self.severity,
                    )
                )

        return issues


class EmDashOveruseRule(Rule):
    """T003: Detect excessive em dash usage."""

    id = "T003"
    name = "Em Dash Overuse"
    description = "Detects excessive — for dramatic effect"
    severity = Severity.INFO
    fixable = False

    # Threshold: max em dashes per document
    _threshold = 5

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for em dash overuse."""
        issues: list[Issue] = []
        lines = iter_prose_lines(content, filename)

        # Find all em dashes
        em_dash_locations: list[tuple[int, int]] = []

        for line_num, line in lines:
            # Match em dash (—) or double hyphen (--)
            for match in re.finditer(r"—|--", line):
                em_dash_locations.append((line_num, match.start() + 1))

        if len(em_dash_locations) > self._threshold:
            # Report the first occurrence with a summary
            first_line, first_col = em_dash_locations[0]
            issues.append(
                Issue(
                    rule_id=self.id,
                    message=f"Em dash overuse: {len(em_dash_locations)} occurrences",
                    line=first_line,
                    column=first_col,
                    severity=self.severity,
                )
            )

        return issues


class QuoteInconsistencyRule(Rule):
    """T004: Detect mixed quote styles."""

    id = "T004"
    name = "Quote Inconsistency"
    description = "Detects mixed curly and straight quotes"
    severity = Severity.INFO
    fixable = True

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for quote inconsistency."""
        issues: list[Issue] = []
        lines = iter_prose_lines(content, filename)
        masked_content = "\n".join(line for _, line in lines)

        has_straight = '"' in masked_content or "'" in masked_content
        # Check for curly quotes using explicit Unicode
        curly_quotes = "\u201c\u201d\u2018\u2019"  # ""''
        has_curly = any(c in masked_content for c in curly_quotes)

        if has_straight and has_curly:
            # Find first curly quote to report
            for line_num, line in lines:
                for match in re.finditer(r"[\u201c\u201d\u2018\u2019]", line):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message="Mixed quote styles (curly and straight)",
                            line=line_num,
                            column=match.start() + 1,
                            severity=self.severity,
                            fixable=True,
                        )
                    )
                    return issues  # Only report once

        return issues

    def fix(self, content: str, issue: Issue) -> str:
        """Normalize curly quotes to straight quotes."""
        # Replace all curly quotes with straight quotes
        # Using explicit Unicode code points for reliability
        replacements = {
            "\u201c": '"',  # left double curly quote
            "\u201d": '"',  # right double curly quote
            "\u2018": "'",  # left single curly quote
            "\u2019": "'",  # right single curly quote
        }
        for curly, straight in replacements.items():
            content = content.replace(curly, straight)
        return content


class EmojiInProseRule(Rule):
    """T005: Detect non-technical emoji in prose."""

    id = "T005"
    name = "Emoji in Prose"
    description = "Detects 🚀, ✨, etc. in headings or body text"
    severity = Severity.INFO
    fixable = False

    # Common promotional/decorative emoji
    _emoji_pattern = r"[\U0001F300-\U0001F9FF]"

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for emoji in prose."""
        issues: list[Issue] = []
        lines = iter_prose_lines(content, filename)

        for line_num, line in lines:
            for match in re.finditer(self._emoji_pattern, line):
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message=f"Emoji in prose: '{match.group()}'",
                        line=line_num,
                        column=match.start() + 1,
                        severity=self.severity,
                    )
                )

        return issues


class ElegantVariationRule(Rule):
    """T006: Detect unnatural synonym usage."""

    id = "T006"
    name = "Elegant Variation"
    description = "Detects awkward synonyms to avoid repetition"
    severity = Severity.INFO
    fixable = False

    # Pairs of formal/informal synonyms often used by AI
    _synonym_pairs = [
        (r"\bsaid\b", r"\bstated\b"),
        (r"\bsaid\b", r"\bremarked\b"),
        (r"\bsaid\b", r"\bnoted\b"),
        (r"\bsaid\b", r"\bopined\b"),
        (r"\buse\b", r"\butilize\b"),
        (r"\buse\b", r"\bemploy\b"),
        (r"\bshow\b", r"\bdemonstrate\b"),
        (r"\bget\b", r"\bobtain\b"),
        (r"\bget\b", r"\bacquire\b"),
    ]

    def check(self, content: str, filename: str) -> list[Issue]:
        """Check for elegant variation."""
        issues: list[Issue] = []
        lines = iter_prose_lines(content, filename)
        content_lower = "\n".join(line for _, line in lines).lower()

        for simple, formal in self._synonym_pairs:
            has_simple = re.search(simple, content_lower)
            has_formal = re.search(formal, content_lower)

            if has_simple and has_formal:
                # Find first formal occurrence to flag
                for line_num, line in lines:
                    match = re.search(formal, line, re.IGNORECASE)
                    if match:
                        simple_word = simple.replace(r"\b", "")
                        formal_word = match.group()
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message=(
                                    f"Elegant variation: '{formal_word}' "
                                    f"(also uses '{simple_word}')"
                                ),
                                line=line_num,
                                column=match.start() + 1,
                                severity=self.severity,
                            )
                        )
                        break

        return issues
