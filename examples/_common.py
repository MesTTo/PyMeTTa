"""Purpose: make metta importable from a repository checkout regardless of
the example's folder depth, point PETTA_PATH at that checkout, and provide
small helpers that make each example self-verifying rather than a printout
to trust.
Guarantees:
  - a wrong value stops the example under `python -O` as well as without it
    [tested: test_a_wrong_value_fails_under_optimization_too;
    commit=8bfe05c3850776543ece25a85038242f10b1d841]
  - the OK line an example prints means at least one check ran since the
    previous OK, and every one of them held
    [tested: test_an_example_that_checks_nothing_does_not_report_success;
    commit=8bfe05c3850776543ece25a85038242f10b1d841]
  - claim() binds runtime emission and execution to adjacent checked comments,
    while doctest() verifies emitted examples in both languages
    [tested: test_every_gallery_program_runs; commit=8bfe05c3850776543ece25a85038242f10b1d841]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import inspect
import os
import sys
from pathlib import Path


def _find_repo(start: Path) -> Path:
    """Find the repository by its Python project and engine library markers."""
    for candidate in start.resolve().parents:
        if (candidate / "bindings" / "python" / "pyproject.toml").is_file() and (
            candidate / "lib"
        ).is_dir():
            return candidate
    raise RuntimeError(f"cannot find the PeTTa repository above {start}")


REPO = _find_repo(Path(__file__))
sys.path.insert(0, str(REPO / "bindings" / "python"))
sys.path.insert(0, str(REPO / "bindings" / "python" / "tools"))
os.environ.setdefault("PETTA_PATH", str(REPO))

from executable_docs import (  # noqa: E402  -- checkout paths must be installed first
    render_answers,
    verify_claim,
    verify_defined_examples,
)


class CheckFailed(Exception):
    """An example claimed a value and the value was something else.

    Not an assert. `python -O` strips assert statements outright, and the
    print below one still runs, so an asserted check reported a wrong value
    as a successful one under the very flag a reader might run an example
    with [source https://docs.python.org/3/using/cmdline.html#cmdoption-O].
    """


# The labels of the checks that held, which is what lets done() refuse to
# print OK for an example that verified nothing. A list rather than a
# counter, so check() needs no `global`.
_VERIFIED: list[str] = []


def _record(label, got):
    """Record and print one result after its checker has accepted it."""
    _VERIFIED.append(label)
    print(f"  {label}: {got}")


def check(label, got, expected=None):
    """Print one result and verify it: a claim must check itself."""
    if expected is not None:
        if got != expected:
            raise CheckFailed(f"{label}: expected {expected!r}, got {got!r}")
    elif not got:
        raise CheckFailed(f"{label}: expected a truthy result, got {got!r}")
    _record(label, got)


def claim(label, emitted, execute):
    """Execute one emitted atom and check its adjacent source comments."""
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    if caller is None:
        raise RuntimeError("claim cannot locate its caller's source span")
    try:
        answers = verify_claim(
            emitted,
            execute,
            path=caller.f_code.co_filename,
            line=caller.f_lineno,
        )
    finally:
        del frame
    _record(label, render_answers(answers))
    return list(answers)


def doctest(label, defined):
    """Verify every emitted @example through its MeTTa and Python sides."""
    count = verify_defined_examples(defined)
    _record(label, f"{count} bilingual example(s)")
    return count


def skip(reason):
    print(f"SKIP: {reason}")
    raise SystemExit(0)


def done(name):
    """The line the runner reads as proof the example verified itself, which
    an example that verified nothing must not be able to print. Emptied
    afterwards so a second example imported into the same process cannot
    ride on the first one's checks."""
    if not _VERIFIED:
        raise CheckFailed(f"{name}: checked nothing, so OK would claim nothing")
    print(f"OK {name}")
    _VERIFIED.clear()
