"""Purpose: the metatheory cluster's acceptance criteria, each checked against
    behaviour rather than against prose. The confluence checker is an
    ADAPTATION whose provenance and whose termination caveat are both recorded
    and both true.
Assumes:
  - swipl is on PATH and the working directory conventions of the Prolog lanes
    hold: a module under src/ is loaded by relative path from tests/prolog.
Guarantees:
  - the provenance test does not stop at the header text: it RUNS the
    counter-example the header names and observes both halves of the caveat,
    the loop and the normal form the loop misses.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _unwrapped(path: Path) -> str:
    """A Prolog file's prose with comment markers and line breaks taken out.

    A header claim that happens to be wrapped across two lines is still one
    claim, and a test that reads it should not go red when someone reflows the
    paragraph around it.
    """
    stripped = (line.lstrip("%").strip() for line in path.read_text().splitlines())
    return " ".join(" ".join(stripped).split())


def test_the_confluence_checker_records_its_provenance_and_its_termination_caveat(
    repo_root,
):
    checker = _unwrapped(repo_root / "src" / "trs.pl")

    # An adaptation says whose work it adapts, under what terms, and what the
    # port changed. Without the last one the header is a courtesy rather than
    # something a reader can check the file against.
    assert "Markus Triska" in checker
    assert "PUBLIC DOMAIN" in checker
    assert "https://www.metalevel.at/trs/trs.pl" in checker
    assert "library(clpz) becomes library(clpfd)" in checker

    # The original's own honesty about normal_form/3, kept word for word, with
    # the counter-example it names.
    assert "May not terminate!" in checker
    assert "a ==> a, f(X) ==> b" in checker

    # And the caveat is TRUE, both halves of it. The reduction loops, and the
    # term it loops on does have a normal form, which is what makes this a
    # documented limit rather than a defect report.
    finished = subprocess.run(
        [
            "swipl",
            "-q",
            "-g",
            "use_module('../../src/trs.pl'), "
            "call_with_inference_limit("
            "  normal_form([a ==> a, f(_) ==> b], f(a), _), 100000, Limit), "
            "format('LOOP ~w~n', [Limit]), "
            "step([f(_) ==> b, a ==> a], f(a), T), format('NORMAL ~w~n', [T])",
            "-t",
            "halt",
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    )
    assert "LOOP inference_limit_exceeded" in finished.stdout
    assert "NORMAL b" in finished.stdout


