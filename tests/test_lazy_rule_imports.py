"""Verify lightweight commands defer rule implementation imports."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from proseprobe import __version__

_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
_IMPLEMENTATIONS = ("code", "grammar", "markup", "struct", "style", "vocab")


def _run_isolated(code: str, *args: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_SOURCE_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", code, *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return dict(json.loads(result.stdout))


@pytest.mark.parametrize("command", ["version", "--help"])
def test_lightweight_cli_commands_do_not_import_rule_implementations(
    command: str,
) -> None:
    result = _run_isolated(
        """
import contextlib
import io
import json
import runpy
import sys

sys.argv = ['proseprobe', *sys.argv[1:]]
output = io.StringIO()
with contextlib.redirect_stdout(output):
    try:
        runpy.run_module('proseprobe', run_name='__main__')
    except SystemExit as exc:
        exit_code = exc.code
print(json.dumps({'exit_code': exit_code, 'output': output.getvalue(),
                  'modules': sorted(sys.modules)}))
""",
        command,
    )

    assert result["exit_code"] == 0
    if command == "version":
        assert result["output"] == f"proseprobe {__version__}\n"
    else:
        assert "usage: proseprobe" in result["output"]
        assert "check" in result["output"]
    assert not {f"proseprobe.rules.{name}" for name in _IMPLEMENTATIONS}.intersection(
        result["modules"]
    )


def test_registry_construction_loads_implementations_and_keeps_scanning() -> None:
    result = _run_isolated(
        r"""
import json
import sys
from pathlib import Path

from proseprobe.config import Config
from proseprobe.core.policy import prepare_scan
from proseprobe.rules import get_all_rules

before = sorted(sys.modules)
rules = get_all_rules()
_, linter, _ = prepare_scan(Config(), select='V009', severity='info')
issues = linter.check_content('We act in order to finish.\n', Path('example.md'))
print(json.dumps({'before': before, 'after': sorted(sys.modules),
                  'ids': [rule.id for rule in rules],
                  'issues': [issue.rule_id for issue in issues]}))
"""
    )

    for name in _IMPLEMENTATIONS:
        module = f"proseprobe.rules.{name}"
        assert module not in result["before"]
        assert module in result["after"]
    assert len(result["ids"]) == len(set(result["ids"])) == 100
    assert result["ids"] == sorted(result["ids"])
    assert result["issues"] == ["V009"]
