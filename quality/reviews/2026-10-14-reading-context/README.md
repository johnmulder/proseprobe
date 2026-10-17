# Bounded diagnostic context

P32D.5b adds source-bound context beside diagnostic readings. The linked
[design reading](design-reading.md) and [agent review](design-review.json)
precede behavior changes. Separate agents also inspected Python ownership and
Markdown/native-context APIs. This is exposed engineering review; no human
effectiveness or annotation evidence is inferred.

The existing region renderer stays compatible. The new benchmark helper
selects raw lexical Python headers and supplies complete Markdown source/target
companions with derived structural inventories. Local target facts must come
from the existing offline native validator. Each numbered reading includes a
direct link and stays within 80 lines of 80 Unicode code points. Overflow must
paginate exact mapped chunks or fail explicitly; required context cannot vanish.

The execution record separates actual failing tests from characterization
checks. Generated examples use declared authored data; no reserved holdout or
earlier review labels are selected. Historical source bytes, frozen readings,
reports, splits, baselines and rule policies stay intact.

## Results and review

P32D.5b is complete. The [execution record](EXECUTION.md) explains the actual
test sequence, including the initial Python characterization checks.
Exact [Markdown/native evidence](tdd-markdown.json) binds the final source digest
to 169 focused tests and the full 3755-test repository gate. The three concrete
[code-review findings](code-review.json) received failing regression tests;
the [follow-up review](code-review-followup.json) accepts their corrections.

A fresh [packet reviewer](packet-review.json) read every generated page and
checked navigation, row mappings and bytes. The two engineering examples have
eight pages; their observed maxima are 33 lines and 79 Unicode code points.
The [selection](examples/selection.json) names previously exposed root-authored
development sources, chosen from metadata before the new source reads. An
[index](examples/index.json) binds exact bundles and the generator runtime.

Open the [Python focus](/private/tmp/p32d5b-python-0001.txt) and
[Markdown focus](/private/tmp/p32d5b-links-0001.txt); follow every adjacent link.
Those temporary files can be recreated from the retained JSON bundles:

```sh
rtk proxy .venv/bin/python - <<'PY'
import json
from pathlib import Path

folder = Path("quality/reviews/2026-10-14-reading-context/examples")
for name in ("p32d5b-python.json", "p32d5b-links.json"):
    bundle = json.loads((folder / name).read_text())
    for page in bundle["readings"]:
        Path(page["path"]).write_bytes(page["rendered_text"].encode("utf-8"))
PY
```

The review accepts the supplied owner signature, source/target heading and
anchor membership, and pinned target status within the declared static scope.
Its four limits remain explicit: Python ownership comes from derived parser
metadata without the intervening body; source columns have exclusive endpoints;
wrapped metadata is a display rather than independently parseable JSON; and
absence depends on the validated pinned inventory. The usage guide explains
these conventions. No clean coverage, final rule labels, human agreement or
effectiveness estimates are inferred.
