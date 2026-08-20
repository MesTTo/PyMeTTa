"""Purpose: the acceptance criteria of the typed development build. A PlDoc
    mode line above a clause becomes a checked `the/2` goal while developing,
    and under `swipl -O` the same clause compiles to the unannotated one. Four
    claims are checked by running both builds rather than by reading either:
    the planted violation is refused in one and not the other, the engine's own
    funnels gain their checks, `-O` leaves no residue, and no production lane
    gains a dependency.
Assumes:
  - swipl is on PATH and the Prolog lanes' working-directory convention holds:
    tests/prolog/dev_typed.pl is run from tests/prolog.
Guarantees:
  - the planted-violation test reads the CLAUSE comparison, not only the error:
    under -O the annotated clause body must be identical to an unannotated
    control's, which is what "compiles to nothing extra" means.
  - the dependency test reads every shipped Prolog source rather than a list of
    the ones this item touched, so a later annotation that reaches for mavis
    fails here.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Every funnel the dev loader lists as annotated. A predicate that lost its
# mode line reports zero checks instead of vanishing, which is the point of the
# loader naming them rather than discovering them.
FUNNELS = (
    "metta_remove_atom/3",
    "unstore_atom/3",
    "remove_equation/6",
    "translate_clause/3",
)


def _dev(repo_root: Path, goal: str, *, optimise: bool = False) -> str:
    command = ["swipl"]
    if optimise:
        command.append("-O")
    command += ["-q", "--on-error=status", "-g", goal, "-t", "halt(0)", "dev_typed.pl"]
    finished = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    )
    return finished.stdout


def test_the_dev_build_checks_a_planted_type_violation_and_optimise_strips_it(repo_root):
    development = _dev(repo_root, "dev_typed_selftest")
    optimised = _dev(repo_root, "dev_typed_selftest", optimise=True)

    # The development build inserts the checks and refuses the call naming the
    # DECLARED type, where the same body unannotated reports the arithmetic.
    assert "build: development" in development
    assert "annotated clause checks: 2" in development
    assert "unannotated clause checks: 0" in development
    assert "clause bodies: different" in development
    assert "error(type_error(integer,abc)" in development
    assert "verdict: checked" in development

    # And under -O the annotated clause IS the unannotated one: the clause/2
    # comparison, not just an error that happens to differ.
    assert "build: optimised" in optimised
    assert "annotated clause checks: 0" in optimised
    assert "clause bodies: identical" in optimised
    assert "error(type_error(integer,abc)" not in optimised
    assert "verdict: stripped" in optimised


@pytest.mark.parametrize("funnel", FUNNELS)
def test_the_engines_funnels_are_checked_in_the_development_build(repo_root, funnel):
    report = _dev(repo_root, "dev_typed_report")
    assert "build: development" in report
    line = next(row for row in report.splitlines() if row.startswith(f"{funnel}:"))
    # "N clause(s), M inserted check(s)" with M above zero.
    checks = int(line.rsplit(",", 1)[1].split()[0])
    assert checks > 0, line


def test_optimise_leaves_no_check_anywhere_in_the_engine(repo_root):
    report = _dev(repo_root, "dev_typed_report", optimise=True)
    assert "build: optimised" in report
    assert f"typed: {len(FUNNELS)} predicates, 0 inserted checks" in report


def test_no_shipped_prolog_source_depends_on_the_development_build(repo_root):
    """The mode lines are comments and nothing else.

    mavis inserts through a GLOBAL user:term_expansion, so the whole opt-in is
    the dev loader importing it before the engine is consulted. A production
    run loads neither, and a `:- use_module(library(mavis))` anywhere under
    engine/, lib/, backends/ or bindings/python/petta/ would make that false.
    """
    roots = [repo_root / name for name in ("engine", "lib", "backends")]
    roots.append(repo_root / "bindings" / "python" / "petta")
    sources = [path for root in roots if root.is_dir() for path in root.rglob("*.pl")]
    assert sources, "no Prolog source found to check"
    for path in sources:
        text = path.read_text()
        assert "library(mavis)" not in text, path
        assert "library(quickcheck)" not in text, path
