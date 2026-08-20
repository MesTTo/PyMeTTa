"""Purpose: pin three Phase 0 outcomes that were reached and then left
unpinned, so each one regresses loudly instead of silently. An outcome
nothing tests is an outcome that comes back: the performance oracles were
deleted rather than gated, `test.sh` computed a verdict summary it did not
print, and MeTTa's generated Prolog contains no cut, all of which are true
today and none of which anything checks.
Assumes:
    - the repository root is two directories above this file, the same way
      test_example_parity.py derives it
    - `m.disassemble/1` answers the Prolog text a MeTTa equation compiled
      to [source: bindings/python/petta/space.py:1645]
Guarantees:
    - each test fails if its outcome is reverted, which is what makes it
      evidence rather than decoration
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def test_no_ungated_prolog_performance_oracle_returns():
    """P0.8 asked that the eight Prolog performance oracles be gated
    against a committed baseline OR deleted, and the delete branch is what
    happened. Nothing stopped them coming back, and an oracle that runs
    against no baseline is a file that passes by existing.
    """
    oracles = sorted(p.relative_to(REPO) for p in (REPO / "tests" / "performance").rglob("*.pl"))
    assert not oracles, (
        f"{len(oracles)} Prolog performance oracle(s) are back and nothing "
        f"compares them to a baseline: {[str(p) for p in oracles]}"
    )


def test_the_runner_prints_every_assertion_it_collects():
    """P0.10. `test.sh` collected the `is ... should ...` lines into a
    variable and, at the time of the audit, never printed it. A verdict
    computed and dropped is worse than one never computed, because the run
    looks like it reported.
    """
    text = (REPO / "test.sh").read_text(encoding="utf-8")
    assigned = [n for n, line in enumerate(text.splitlines(), 1) if "assertions=" in line]
    assert assigned, "test.sh no longer collects assertions; this test guards the wrong thing now"
    used = [
        n
        for n, line in enumerate(text.splitlines(), 1)
        if '"$assertions"' in line and "assertions=" not in line
    ]
    assert used, (
        f"test.sh assigns assertions at line(s) {assigned} and never reads it back; "
        "the summary it computes is dropped"
    )


def test_a_generated_clause_carries_no_cut(metta):
    """P0.12. Generated code is worse than hand-written code for a stray
    cut, because nobody reads it: a cut in a compiled equation would make
    the second clause unreachable and the program would simply answer less.

    Two clauses for one name is the shape that shows it. `(f 0)` answers
    both `zero` and `other` only if neither clause cut, so this asserts the
    behaviour AND the text, and the behaviour is the part that matters.
    """
    metta.run("(= (petta-cut-probe 0) zero)")
    metta.run("(= (petta-cut-probe $x) other)")
    compiled = metta.disassemble("petta-cut-probe")
    assert "!" not in compiled, f"a generated clause contains a cut:\n{compiled}"
    answers = [str(a) for group in metta.run("!(petta-cut-probe 0)") for a in group]
    assert answers == ["zero", "other"], (
        f"both clauses should answer; got {answers}, which is what a cut looks like"
    )
