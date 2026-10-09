# Assessment finding dispositions

The original twelve false positives remain in the regression corpus with their
negative annotations and original inputs. This ledger distinguishes detector
corrections from explicit caller handling and residual limitations. The review
uses the fixtures' declared intent; it is not independent human evaluation.

| Original case | Rule | Disposition |
| --- | --- | --- |
| `technical-review.md:3`, hash-table key | V001 | Corrected by the matched technical-key construction. |
| `technical-review.md:5`, statistical result | V001 | Corrected by the statistically-significant construction. |
| `technical-review.md:9`, named theorem | V001 | Corrected by the fundamental-theorem construction. |
| `technical-review.md:11`, implementation language | V001 | Corrected by the directly stated implementation language. |
| `technical-review-heldout.md:11`, protocol conformance | V001 | Corrected by the directly named protocol construction. |
| `technical-review-heldout.md:13`, interface construction | V001 | Corrected by the directly named interface construction. |
| `technical-review-quotes.md:5`, archival quotation | V001 | Retained raw false positive; caller can preserve the exact quote with a narrow directive. |
| `technical-review-quotes.md:5`, archival quotation | V004 | Retained raw false positive; quote intent is not inferred from blockquote syntax. |
| `technical-review-quotes.md:6`, archival statement | V002 | Retained raw false positive; explicit preservation is supported separately. |
| `technical-review-heldout.md:21`, customer statement | V002 | Retained raw false positive; the literal statement remains unchanged. |
| `news-article.md:10`, following named experts | V005 | Retained low-confidence association limitation. Following evidence lowers confidence but does not prove attribution. |
| `news-article.md:6`, following quantified trend | V008 | Retained low-confidence association limitation. Following figures do not establish claim-local support automatically. |

Generic administrative uses and unsupported same-line vocabulary remain
positives. Span-scoped technical exceptions do not exempt other occurrences.
Configured `allowed_phrases` retains its existing whole-line contract.
Ordinary draft blockquotes still warn. Suppression tests show caller
handling without changing these raw negative cases or accepting baseline debt.

Two older judgments deliberately change under P10: adjacent measurements no
longer qualify the unbounded superlative in `unbounded-superlatives.md:17` or
the universal reliability assertion in `absolute-reliability-claims.md:17`.
Their source inputs remain; expected detections replace obsolete negative
judgments. This changes the regression denominator and is disclosed separately
from the six technical false-positive corrections.

The three new rules remain experimental. Purpose-written examples and sparse
legacy coverage cannot justify profile promotion. The frozen 300-unit natural
text pilot awaits blind human annotation, disagreement review, and usefulness
judgments. Grammar/simplification references are supplementary evidence, and
sentence inputs cannot measure document-structure recall. No pilot precision,
recall, or population-level effectiveness claim has been made.
