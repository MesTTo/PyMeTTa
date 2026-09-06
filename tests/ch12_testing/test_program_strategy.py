"""Purpose: the acceptance criteria of `metta.testing.programs`, the strategy
    the arbiter fuzz lane draws from. The lane's own self-test plants engines
    and checks the classification; these are the DOOR's obligations, which a
    caller writing their own differential meets first: a program that both
    engines can read, a refusal that says where a census comes from, and the
    same draw twice from the same seed.
Assumes:
  - the committed census at tests/conformance/petta/HEADS.json, which is what
    `programs()` reads when it is given none.
Guarantees:
  - every drawn program parses, and its equations and queries are the shapes
    the lane's classifier reads back
    [tested: test_every_drawn_program_reads_back_as_metta;
    commit=WORKTREE]
  - a census recording no reducing head is refused with the command that
    writes one, rather than answering a strategy that draws nothing
    [tested: test_a_census_with_nothing_reducible_is_refused; commit=WORKTREE]
  - the shipped census is reachable without arguments from a checkout
    [tested: test_the_committed_census_is_what_programs_reads_by_default;
    commit=WORKTREE]
  - a query never carries a variable no line binds, which is what makes the
    generated program a closed question for both engines
    [tested: test_a_query_binds_every_variable_it_writes; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, Phase, given, settings

from metta import testing

ROOT = Path(__file__).resolve().parents[4]
CENSUS = ROOT / "tests" / "conformance" / "petta" / "HEADS.json"
sys.path.insert(0, str(ROOT / "tests" / "conformance"))

from petta_capture import forms  # noqa: E402  -- the path is installed above

#: How the strategy is driven here: enough draws to see every branch, no
#: shrinking (there is nothing failing to shrink), and no deadline, because a
#: draw walks a census of fifty calls.
DRAWS = settings(max_examples=60, phases=[Phase.generate], database=None,
                 deadline=None, derandomize=True,
                 suppress_health_check=list(HealthCheck))


@DRAWS
@given(testing.programs())
def test_every_drawn_program_reads_back_as_metta(source: str) -> None:
    """A drawn program is one fact, equation or query per line, and it parses."""
    for line in source.splitlines():
        read = forms(line.removeprefix("!"))
        assert len(read) == 1, f"a line is not one form: {line!r}"
        assert isinstance(read[0], list) or line.startswith("!"), f"a bare token: {line!r}"
        if line.startswith("(= "):
            assert len(read[0]) == 3, f"an equation is not (= head body): {line!r}"
            assert "$x" in line.split(")", 1)[-1], f"a body ignores its argument: {line!r}"


@DRAWS
@given(testing.programs())
def test_a_query_binds_every_variable_it_writes(source: str) -> None:
    """A query's variables are its own: a name it opens, never one from a body.

    The equations' `$x` is the parameter, so a QUERY naming `$x` would be
    asking about a variable nothing binds and both engines would answer their
    own idea of an open term rather than a value.
    """
    for line in source.splitlines():
        if line.startswith("!"):
            assert "$x" not in line, f"a query names the equations' parameter: {line!r}"


def test_a_census_with_nothing_reducible_is_refused() -> None:
    """A census whose every head was left standing is refused, with the remedy."""
    census = {"heads": {"nope": {"uses": 4, "files": 4, "arities": {
        "1": {"uses": 4, "positions": [{"number": 4}], "verdict": "unreduced",
              "result": None, "probe": "!(nope 1)", "answer": "(nope 1)"}}}}}
    with pytest.raises(ValueError, match=re.escape("petta_capture.py")):
        testing.programs(census=census)


def test_the_committed_census_is_what_programs_reads_by_default() -> None:
    """`programs()` with no census calls only heads the committed one reduces.

    The heads asked about are the OUTERMOST ones: a query's own head and an
    equation body's own head. A nested `(a c)` is a data list and a nested
    `(+ 1 2)` is a call, and nothing in the written text tells them apart, so
    asking about every head in the tree would be asking a question the text
    cannot answer.
    """
    committed = json.loads(CENSUS.read_text(encoding="utf-8"))
    reducing = {
        head for head, entry in committed["heads"].items()
        for row in entry["arities"].values() if row["verdict"] == "reduces"
    }
    assert reducing, "the committed census records no reducing head"
    minted = re.compile(r"^(?:rel|f)\d+$")
    called: set[str] = set()

    @DRAWS
    @given(testing.programs())
    def collect(source: str) -> None:
        for line in source.splitlines():
            if line.startswith("!"):
                called.add(forms(line[1:])[0][0])
            elif line.startswith("(= "):
                called.add(forms(line)[0][2][0])

    collect()
    assert called, "the default census drew nothing"
    outside = {one for one in called if one not in reducing and not minted.match(one)}
    assert not outside, f"called from outside the census: {sorted(outside)}"
