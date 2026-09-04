"""Purpose: run every example through both configurations and require identical verdicts.

The two configurations are the engine alone and the shipped Python library.
The example
corpus is the executable semantics documentation, and until this existed it
was only ever executed by the engine: check.sh ran `swipl -s engine/main.pl`,
test.sh and test_metta_examples.py shelled to run.sh, and the plunit suites
loaded engine/metta.pl without extensions/python/metta/shim.pl. So the configuration most
users come through was gated by unit tests alone, and two defects lived
there with green lanes above them [source: ai-audit-md-review.md section 4].

This module is also the one definition of what the corpus IS. Discovery and
the skip list used to be duplicated across test.sh and check.sh, matching on
basename rather than path, and the two copies disagreed. `--list` and
`--count` exist so a shell runner asks rather than re-deriving.

Assumes:
  - both configurations print a verdict line per `!(test ...)` in the same
    format, `is X, should Y. <mark>` [measured 2026-08-18: 12 lines each
    from examples/ch07-control-flow/07-04-bounded-and-committed-searches/01-forall.metta, byte-identical]
  - an example is cheap enough to run in its own process in both
    configurations [measured 2026-08-18: 0.08s engine, 0.15s library]
Guarantees:
  - a difference in ANSWERS, in verdicts, or in exit status between the two
    configurations is reported, naming the example and the first differing
    line [tested: test_example_parity_reports_a_planted_difference,
    test_compare_reports_a_planted_exit_status_difference,
    test_compare_reports_a_planted_verdict_difference,
    test_compare_accepts_equivalent_passing_verdicts; commit=835925ee1c55d2267aa54f0a5ccbdfcdb6fc003c]
  - the library configuration closes the MeTTa engine after loading each
    example, and a teardown failure is part of that configuration's outcome
    [tested: test_the_library_runner_reports_a_teardown_failure;
    commit=835925ee1c55d2267aa54f0a5ccbdfcdb6fc003c]
  - answers are compared as VALUES, not as text, so a difference in
    source SPELLING is not a difference in answer: `true` and `True` both
    parse to Grounded(True), while both shipped writers emit canonical `true`
    [tested: test_spelling_is_not_a_difference,
    test_swrite_writes_the_engines_own_boolean_literal; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Decides:
  - process isolation per example, matching how the engine lane already
    works, rather than one engine over many spaces: it is affordable at the
    measured cost and it cannot leak state between examples
  - the engine is read through tests/conformance/answer_groups.pl, which
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
    what found it: examples/ch17-concurrency-and-the-loop/04-thin_forms.metta asserted `(2 4)` for a
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
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKIPS = REPO / "tests" / "data" / "example_skips.txt"
VERDICT = " should "

#: How long one example may take in one configuration. The slowest example
#: in the corpus runs well inside this; a hang is a defect, not a reason to
#: wait [assumed 2026-08-18].
TIMEOUT = 300

#: How far ABOVE TIMEOUT the child's own bound sits. The parent must still be
#: the one that gives up first, so `except subprocess.TimeoutExpired` below
#: keeps firing at TIMEOUT exactly as it did; the child's bound is not a
#: second opinion about how long an example may take, it is what remains when
#: nobody is waiting
#: [tested: test_a_process_this_suite_starts_reports_a_wrapper_as_its_parent;
#: commit=WORKTREE].
CHILD_GRACE = 60


def _bounded(command: list[str]) -> list[str]:
    """The same command, bounded by a process that shares its fate rather than the caller's.

    `subprocess.run(timeout=)` is enforced in the PARENT's wait loop. Kill the
    parent and nothing enforces it: the child keeps running with no bound at
    all. Two `swipl` children spawned here survived that way from 2026-09-01
    to 2026-09-03, spinning at 100% for 122 CPU-hours between them.

    GNU `timeout` puts the bound in a wrapper process that is the child's own
    parent, so an orphaned wrapper still counts down, and it runs the child in
    its own process group and signals the GROUP, which is what reaches the
    engine's own children [measured 2026-09-03: a child that spawns a
    grandchild leaves no survivor when the wrapper fires].

    `PR_SET_PDEATHSIG` is the other candidate and is wrong here twice over:
    it is set through `preexec_fn`, which CPython documents as unsafe in the
    presence of threads, and this module spawns from a `ThreadPoolExecutor`;
    and the kernel sends the parent-death signal when the parent THREAD exits
    rather than the process, so a pool worker finishing would kill a live
    child.
    """
    if TIMEOUT_COMMAND is None:
        refusal = (
            "example_parity needs GNU `timeout` on PATH to bound the children "
            "it spawns. Without it a killed runner leaves them running with no "
            "bound at all, which has already cost 122 CPU-hours. Install "
            "coreutils rather than removing this check."
        )
        raise RuntimeError(refusal)
    return [TIMEOUT_COMMAND, "--preserve-status", "-k", "5",
            str(TIMEOUT + CHILD_GRACE), *command]


TIMEOUT_COMMAND = shutil.which("timeout")

def skips() -> dict[str, str]:
    """The declared skips, path to reason.

    One definition, read by every runner, because two copies matching on
    basename already disagreed.
    """
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
    return [
        path
        for path in sorted((root / "examples").rglob("*.metta"))
        if not path.is_symlink()
        and "_fixtures" not in path.parts
        and str(path.relative_to(root)) not in declared
    ]


MARKER = "ANSWER-GROUP "
FAILED = "ANSWER-ERROR "


@dataclass(frozen=True, slots=True)
class Outcome:
    """What one configuration made of one example.

    One written answer group per runnable form, in source order, or the error
    that stopped it.
    """

    groups: list[str]
    error: str | None
    # Appended defaults preserve the positional two-field construction used by
    # the twin-coverage tests while making the two previously discarded
    # observations part of the comparison.
    verdicts: tuple[str, ...] = ()
    returncode: int | None = 0


def _read(text: str, returncode: int | None = 0) -> Outcome:
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
    verdicts = tuple(line.strip() for line in text.splitlines() if VERDICT in line)
    return Outcome(groups, failure, verdicts, returncode)


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
        done = subprocess.run(  # noqa: S603 -- commands are built by repository runners
            _bounded(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Outcome([], f"timed out after {TIMEOUT}s", returncode=None), ""
    text = done.stdout + done.stderr
    outcome = _read(text, done.returncode)
    if outcome.error is None and done.returncode != 0:
        tail = text.strip().splitlines()
        outcome = Outcome(
            outcome.groups,
            tail[-1][:300] if tail else "no output",
            outcome.verdicts,
            outcome.returncode,
        )
    return outcome, text


def run_engine(path: Path, root: Path = REPO) -> Outcome:
    """The engine alone, read through the emitter that already exists for this.

    One answer GROUP per runnable form, on a marker line.
    """
    return _run(
        [
            "swipl", "--stack_limit=8g", "-q",
            "-g", 'consult("engine/metta.pl")',
            "-s", "tests/conformance/answer_groups.pl",
            "--", "--file", str(path.relative_to(root)), "extensions",
        ],
        root,
    )[0]


def run_library(path: Path, root: Path = REPO) -> Outcome:
    """The shipped library, in its own process, emitting the same marker format.

    The separate process is the isolation the engine lane gets, and the shared
    format is what makes the two comparable.

    `load()` already returns the per-form groups, so this preserves the
    structure rather than flattening it: an empty group prints as `()`
    because "no answers" is an observation and dropping it would misalign
    every group after it.
    """
    source = (
        "import sys; sys.path.insert(0, 'extensions/python')\n"
        "from metta import MeTTa\n"
        "with MeTTa(metta_path='.') as metta:\n"
        f"    for group in metta.self.load({str(path.relative_to(root))!r}):\n"
        "        print('" + MARKER + "(' + ' '.join(str(a) for a in group) + ')')\n"
    )
    return _run([sys.executable, "-c", source], root)[0]


@dataclass(frozen=True, slots=True)
class Difference:
    """One example the two configurations disagree about."""

    path: Path
    reason: str
    detail: str

    def __str__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name
        return f"{self.path}: {self.reason}\n    {self.detail}"


def _value(written: str):
    """One written group as a VALUE, so a spelling difference is not an answer difference.

    Boolean source aliases parse to the same Grounded value. An unparsable
    group compares as its own text, which keeps malformed output visible
    instead of collapsing it to equal.
    """
    from metta.atoms import parse  # noqa: PLC0415  -- the package is imported only to compare

    try:
        return parse(written)
    except Exception:  # noqa: BLE001  -- any parse failure means compare as text
        return written


def _verdict_decision(line: str) -> bool | str:
    """The pass/fail decision, retaining unknown output as its own value.

    A verdict's displayed atoms may contain the current home-space name, which
    is ``&self`` through the engine CLI and an allocated ``&pyspace_N`` through
    the library. Those are equivalent contexts, while the final mark is the
    verdict the two configurations must share.
    """
    if line.endswith("✅"):
        return True
    if line.endswith("❌"):
        return False
    return line


def compare(path: Path, root: Path = REPO) -> Difference | None:
    """Run one example both ways, once, and answer what differs."""
    engine, library = run_engine(path, root), run_library(path, root)
    relative = path.relative_to(root)

    if engine.returncode != library.returncode:
        return Difference(
            relative,
            "the configurations exited differently",
            f"engine {engine.returncode!r} against library {library.returncode!r}",
        )
    if (engine.error is None) != (library.error is None):
        who = "library" if library.error else "engine"
        return Difference(
            relative,
            f"only the {who} failed",
            (library.error or engine.error or "")[:300],
        )
    if len(engine.verdicts) != len(library.verdicts):
        return Difference(
            relative,
            "a different number of test verdicts was printed",
            f"engine {len(engine.verdicts)} verdicts, "
            f"library {len(library.verdicts)}",
        )
    for index, (left, right) in enumerate(
        zip(engine.verdicts, library.verdicts, strict=True)
    ):
        if _verdict_decision(left) != _verdict_decision(right):
            return Difference(
                relative,
                f"test verdict {index + 1} differs",
                f"engine {left!r} against library {right!r}",
            )

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
    """Run the corpus through both configurations and report any disagreement."""
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

    sys.path.insert(0, str(REPO / "extensions" / "python"))
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
