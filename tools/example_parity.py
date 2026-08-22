"""Purpose: run every example through BOTH configurations, the engine alone
and the shipped Python library, and require identical verdicts. The example
corpus is the executable semantics documentation, and until this existed it
was only ever executed by the engine: check.sh ran `swipl -s engine/main.pl`,
test.sh and test_metta_examples.py shelled to run.sh, and the plunit suites
loaded engine/metta.pl without bindings/python/petta/shim.pl. So the configuration most
users come through was gated by unit tests alone, and two defects lived
there with green lanes above them [source: ai-audit-md-review.md section 4].

This module is also the one definition of what the corpus IS. Discovery and
the skip list used to be duplicated across test.sh and check.sh, matching on
basename rather than path, and the two copies disagreed. `--list` and
`--count` exist so a shell runner asks rather than re-deriving.

Assumes:
  - both configurations print a verdict line per `!(test ...)` in the same
    format, `is X, should Y. <mark>` [measured 2026-08-18: 12 lines each
    from examples/control/forall.metta, byte-identical]
  - an example is cheap enough to run in its own process in both
    configurations [measured 2026-08-18: 0.08s engine, 0.15s library]
Guarantees:
  - a difference in ANSWERS, in verdicts, or in exit status between the two
    configurations is reported, naming the example and the first differing
    line [tested test_example_parity_reports_a_planted_difference]
  - answers are compared as VALUES, not as text, so a difference in
    source SPELLING is not a difference in answer: `true` and `True` both
    parse to Grounded(True), while both shipped writers emit canonical `True`
    [tested: test_spelling_is_not_a_difference,
    test_swrite_writes_mettas_own_boolean_literal; commit=WORKTREE]
Decides:
  - process isolation per example, matching how the engine lane already
    works, rather than one engine over many spaces: it is affordable at the
    measured cost and it cannot leak state between examples
  - the engine is read through tests/conformance/leatta_run.pl, which
    already exists to print one answer GROUP per runnable form on a marker
    line "so a comparator can read them without having to tell an answer
    apart from the loader's own echo". The first version of this module
    printed a flat line per ANSWER instead and so could not tell
    `!(superpose (1 2 3))` then `!(+ 1 1)` from `!(superpose (1 2))` then
    `!(superpose (3 2))`; both emit `1 2 3 2`. That file's own comment says
    why: the grouping IS the observation
Fails when:
  - an example's answers are nondeterministically ordered: groups are
    compared in order, so a genuinely unordered answer set would report a
    difference that is not one. One in the corpus was, and this lane is
    what found it: examples/control/thin_forms.metta asserted `(2 4)` for a
    collapse over `hyperpose`, whose branches race, so the example's own
    `test` failed at 4 runs in 30 and the lane read a per-run coin flip as
    a library difference [measured 2026-08-18, engine alone]. It sorts now,
    and nothing else in the corpus does this today
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKIPS = REPO / "tests" / "example_skips.txt"
VERDICT = " should "

#: How long one example may take in one configuration. The slowest example
#: in the corpus runs well inside this; a hang is a defect, not a reason to
#: wait [assumed 2026-08-18].
TIMEOUT = 300

def skips() -> dict[str, str]:
    """The declared skips, path to reason. One definition, read by every
    runner, because two copies matching on basename already disagreed."""
    out: dict[str, str] = {}
    for line in SKIPS.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        path, _, reason = stripped.partition(" ")
        out[path] = reason.strip()
    return out


def corpus(root: Path = REPO) -> list[Path]:
    """Every example a runner runs, in a stable order.

    `_fixtures/` holds inputs rather than programs, and a symlink is an
    alias for a file already in the list, so neither is discovered.
    """
    declared = skips()
    found = [
        path
        for path in sorted((root / "examples").rglob("*.metta"))
        if not path.is_symlink()
        and "_fixtures" not in path.parts
        and str(path.relative_to(root)) not in declared
    ]
    return found


MARKER = "LEATTA-ANSWER "
FAILED = "LEATTA-ERROR "


@dataclass(frozen=True, slots=True)
class Outcome:
    """What one configuration made of one example: one written answer group
    per runnable form, in source order, or the error that stopped it."""

    groups: list[str]
    error: str | None


def _read(text: str) -> Outcome:
    groups = [
        line[len(MARKER):].strip()
        for line in text.splitlines()
        if line.startswith(MARKER)
    ]
    failure = next(
        (line[len(FAILED):].strip() for line in text.splitlines()
         if line.startswith(FAILED)),
        None,
    )
    return Outcome(groups, failure)


def _run(
    command: list[str], cwd: Path, env: dict[str, str] | None = None
) -> tuple[Outcome, str]:
    """One configuration's run, as the outcome the comparator reads and the
    raw text beside it. The text is returned rather than discarded because a
    runner may emit more than answers on its own marker lines: the twin
    coverage lane reads an inference count and the defined heads from the
    same output [tested: test_a_runner_returns_its_raw_text_beside_the_outcome].
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    try:
        done = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT, env=env
        )
    except subprocess.TimeoutExpired:
        return Outcome([], f"timed out after {TIMEOUT}s"), ""
    text = done.stdout + done.stderr
    outcome = _read(text)
    if outcome.error is None and done.returncode != 0:
        tail = text.strip().splitlines()
        outcome = Outcome(outcome.groups, tail[-1][:300] if tail else "no output")
    return outcome, text


def run_engine(path: Path, root: Path = REPO) -> Outcome:
    """The engine alone, read through the emitter that already exists for
    exactly this: one answer GROUP per runnable form on a marker line."""
    return _run(
        [
            "swipl", "--stack_limit=8g", "-q",
            "-g", 'consult("engine/metta.pl")',
            "-s", "tests/conformance/leatta_run.pl",
            "--", "--file", str(path.relative_to(root)), "backends",
        ],
        root,
    )[0]


def run_library(path: Path, root: Path = REPO) -> Outcome:
    """The shipped library, in its own process for the isolation the engine
    lane gets, emitting the same marker format so the two are comparable.

    `load()` already returns the per-form groups, so this preserves the
    structure rather than flattening it: an empty group prints as `()`
    because "no answers" is an observation and dropping it would misalign
    every group after it.
    """
    source = (
        "import sys; sys.path.insert(0, 'bindings/python')\n"
        "from petta import MeTTa\n"
        f"for group in MeTTa(petta_path='.').self.load({str(path.relative_to(root))!r}):\n"
        "    print('" + MARKER + "(' + ' '.join(str(a) for a in group) + ')')\n"
    )
    return _run([sys.executable, "-c", source], root)[0]


@dataclass(frozen=True, slots=True)
class Difference:
    """One example the two configurations disagree about."""

    path: Path
    reason: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}\n    {self.detail}"


def _value(written: str):
    """One written group as a VALUE, so a difference in spelling is not
    reported as a difference in answer: boolean source aliases parse to the
    same Grounded value. An unparsable group compares as its own text, which keeps
    malformed output visible instead of collapsing it to equal."""
    from petta.atoms import parse

    try:
        return parse(written)
    except Exception:
        return written


def compare(path: Path, root: Path = REPO) -> Difference | None:
    """Run one example both ways, once, and answer what differs."""
    engine, library = run_engine(path, root), run_library(path, root)
    relative = path.relative_to(root)

    if (engine.error is None) != (library.error is None):
        who = "library" if library.error else "engine"
        return Difference(
            relative,
            f"only the {who} failed",
            (library.error or engine.error or "")[:300],
        )
    if engine.error and library.error:
        return None

    if len(engine.groups) != len(library.groups):
        return Difference(
            relative,
            "a different number of forms answered",
            f"engine {len(engine.groups)} groups, library {len(library.groups)}",
        )
    for index, (left, right) in enumerate(zip(engine.groups, library.groups,
                                              strict=True)):
        if _value(left) != _value(right):
            return Difference(
                relative,
                f"form {index + 1} answers differently",
                f"engine {left!r} against library {right!r}",
            )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--list", action="store_true", help="print the corpus")
    parser.add_argument("--count", action="store_true", help="print its size")
    parser.add_argument("paths", nargs="*", help="examples, default all")
    args = parser.parse_args()

    paths = [Path(p).resolve() for p in args.paths] or corpus()

    if args.list:
        for path in paths:
            print(path.relative_to(REPO))
        return 0
    if args.count:
        print(len(paths))
        return 0

    sys.path.insert(0, str(REPO / "bindings" / "python"))
    with ThreadPoolExecutor() as pool:
        found = [d for d in pool.map(compare, paths) if d is not None]

    for difference in found:
        print(difference)
    print(
        f"{len(paths) - len(found)}/{len(paths)} examples agree "
        f"across both configurations"
    )
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
