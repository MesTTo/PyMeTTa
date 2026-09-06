"""Purpose: run every example through both configurations and require identical verdicts.

The two configurations are the engine alone and the shipped Python library.
The example
corpus is the executable semantics documentation, and until this existed it
was only ever executed by the engine: check.sh ran `swipl -s engine/main.pl`,
test.sh and the metta_examples.txt items shelled to run.sh, and the plunit suites
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
    configurations. Half the corpus is under 0.69s and 95% of it under 2.0s;
    the one file that is not is 04-nilbc.metta, and the ceiling below is set
    by that file alone [measured 2026-09-06: 506 captures on a box at loadavg
    23, median 0.686s, p95 1.99s, maximum 26.69s]
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
  - a child's output is bounded in BYTES as well as in time, so an example
    printing without stopping is a reported outcome rather than an exhausted
    parent, and the streams still join stdout-then-stderr so the last line is
    the failure [tested: test_a_runaway_child_is_stopped_at_the_capture_ceiling,
    test_the_library_runner_reports_a_teardown_failure; commit=819393cb9608052a198ef0b2a8c0676d9ef9e824]
  - a child's output is read to EOF whatever its process does. Exit is not a
    reason to stop reading a pipe, and treating it as one made the lane's
    verdict depend on the box's load: `epoll_wait` seeing nothing and
    `waitpid` seeing the child gone are observations from two different
    instants, and on a loaded box a whole child fits between them
    [tested: test_a_child_that_writes_late_is_read_in_full; commit=b0d85db82c8069fa5c2bb864b1ce8a93bccf40f8]
  - a configuration that did not answer is run again, both doors, and if it
    still does not answer it is reported as `no verdict` with what stopped it,
    what it cost, the ceiling and the loadavg, and counted apart from the
    disagreements. Two configurations that were BOTH stopped are that too,
    where before they compared equal and passed
    [tested: test_a_stopped_run_is_reported_as_unanswered_with_its_load,
    test_two_stopped_configurations_do_not_agree,
    test_an_unanswered_configuration_is_run_again; commit=b0d85db82c8069fa5c2bb864b1ce8a93bccf40f8]
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
import contextlib
import os
import selectors
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKIPS = REPO / "tests" / "data" / "example_skips.txt"
VERDICT = " should "

#: How long one example may take in one configuration: a wall ceiling one cost
#: class above the corpus's slowest member on a QUIET box, which is where this
#: repository's other per-item ceilings sit -- test.sh gives each example 290s
#: over the same corpus.
#:
#: DERIVED rather than assumed, which is what it was until 2026-09-06. The
#: slowest member is
#: examples/ch22-a-reasoner-you-can-serve/22-01-logic-programs/04-nilbc.metta
#: through the library, and it is the same file on either door at every load,
#: so the corpus has one worst case rather than a spread of them. It runs
#: 26.7s on a quiet box, which puts 300s eleven times above it. Under load the
#: margin is what the load leaves: 39.8s to 69.4s over twenty whole-corpus
#: runs at one-minute loadavg 49 to 83, and 60.3s to 173.3s over twenty-one
#: more at 22 to 114, where a box with four times its cores runnable leaves
#: 1.7 times [measured 2026-09-06: forty-one runs of 253 examples, plus a
#: 506-capture instrumented run at loadavg 23 for the quiet figure;
#: command=extensions/python/tools/example_parity.py].
#:
#: A load that does reach it is no longer a wrong verdict. The run is reported
#: as `no verdict`, with the ceiling and the loadavg, and counted apart from
#: the disagreements, which is why the ceiling can sit where waiting sensibly
#: stops rather than where no load could ever reach it. `main` prints the
#: slowest child each run against this number, because a ceiling derived once
#: from a measurement nothing repeats goes stale silently, and a corpus lane
#: with no per-item wall bound cannot tell "the right answer in seconds" from
#: "the right answer in a different cost class".
TIMEOUT = 300

#: How far ABOVE TIMEOUT the child's own bound sits. The parent must still be
#: the one that gives up first, so `except subprocess.TimeoutExpired` below
#: keeps firing at TIMEOUT exactly as it did; the child's bound is not a
#: second opinion about how long an example may take, it is what remains when
#: nobody is waiting
#: [tested: test_a_process_this_suite_starts_reports_a_wrapper_as_its_parent;
#: commit=88ba8f12b292eece7dc3810942ffce393b34dca4].
CHILD_GRACE = 60

#: The repository's one bound. Every runner in this tree, and a command
#: typed by hand, reach the same file.
BOUNDED = REPO / "bounded.sh"

#: What every child cost, appended as it finishes, so `main` can print the
#: slowest against TIMEOUT. `list.append` is what the threads share; nothing
#: reads it until they have all finished.
COSTS: list[tuple[float, str, str]] = []

#: The examples a configuration had to be run again for. A retry that
#: SUCCEEDED is the same disturbance the bare zero used to be, one attempt
#: earlier, and a lane that swallows it is hiding the same event more quietly.
RETRIED: list[str] = []


def _late(reason: str) -> str:
    """A deadline expiry, with the load it expired under.

    A ceiling reached on a box carrying three times its cores is a different
    fact from one reached on an idle box, and a reader who cannot tell them
    apart treats the first as a defect in the example.
    """
    return f"{reason} under loadavg {os.getloadavg()[0]:.2f}"


def _bounded(command: list[str]) -> list[str]:
    """The same command, bounded by a process that shares its fate rather than the caller's.

    `subprocess.run(timeout=)` is enforced in the PARENT's wait loop. Kill the
    parent and nothing enforces it: the child keeps running with no bound at
    all. Two `swipl` children spawned here survived that way from 2026-09-01
    to 2026-09-03, spinning at 100% for 122 CPU-hours between them.

    `bounded.sh` is the repository's one bound and holds two things: a deadline
    in a process that is the child's own parent, so an orphaned wrapper still
    counts down, and a parent-death signal linking that wrapper to THIS process,
    so a killed runner reaps its children in milliseconds rather than leaving
    them to the deadline.

    `--owner` names this process's pid, read here, in the parent, before the
    fork. A wrapper that reads getppid() after it starts cannot tell its
    original caller from a subreaper that adopted it. The pid is a pool
    worker's PROCESS, not its thread: the signal is armed by `setpriv` after
    the exec rather than by a `preexec_fn`, so no Python runs between fork and
    exec, and the spawning THREAD's exit does not deliver it on this kernel
    [tested: tests/shell/test_bounded_reaping.sh case 6, a GATE lane].
    """
    if not BOUNDED.is_file():
        refusal = (
            f"example_parity bounds the children it spawns through {BOUNDED}, "
            "and that file is not there. Without it a killed runner leaves "
            "them running with no bound at all, which has already cost 122 "
            "CPU-hours. Restore it rather than removing this check."
        )
        raise RuntimeError(refusal)
    return ["sh", str(BOUNDED),
            "--ceiling", str(TIMEOUT + CHILD_GRACE), "--grace", "5",
            "--owner", str(os.getpid()), *command]


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
    #: Which configuration this is, so a run that did not answer can say who
    #: did not answer without the comparator having to remember.
    door: str = "configuration"
    #: What the run cost, and what stopped it early. A run stopped at its
    #: ceiling is a run that did not happen, which is a different sentence
    #: from a disagreement and is counted apart from one.
    seconds: float = 0.0
    stopped: str | None = None


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


#: How much of a child's output is kept before the run is stopped. The bound
#: this sits beside is a DEADLINE, and a deadline does not bound memory: a
#: child printing 256 MiB took this parent to 850 MiB resident, because
#: `capture_output=True` holds the chunk list, the joined bytes and the decoded
#: string at once, and it got there in about two seconds against a 300 second
#: TIMEOUT [measured 2026-09-05; command=python -c "for _ in range(262144):
#: sys.stdout.write('x'*1023+chr(10))" through _run; fixture=resource
#: .getrusage(RUSAGE_SELF).ru_maxrss around the call]. The class is not
#: hypothetical: greedy_chess printed 17,973,938 lines in 120 seconds once its
#: command loop met EOF [source: tests/data/example_skips.txt]. 16 MiB is 33
#: times the largest output a shipped example produces, greedy_chess's own
#: 501,917 bytes when it is given its quit command, and it is the ceiling
#: CeTTa's corpus generator settled on over the same corpus [source:
#: CETTA_PATH/scripts/petta_corpus_manifest.py, MAX_CAPTURE_BYTES and
#: run_bounded_process; CETTA_PATH is the override tests/conformance/cetta.py
#: resolves the fork through].
MAX_CAPTURE_BYTES = 16 * 1024 * 1024


def _capture(
    command: list[str], cwd: Path, env: dict[str, str] | None
) -> tuple[str, int | None, str | None]:
    """One child's output, bounded in BYTES as well as in time.

    `subprocess.run(capture_output=True, timeout=)` buffers whatever the child
    writes with no ceiling at all, so an example that prints without stopping
    exhausts memory long before the deadline is reached. This reads both pipes
    through `selectors` with the same deadline, stops at MAX_CAPTURE_BYTES, and
    signals the process GROUP, which is what reaches the engine's own children.

    `start_new_session=True` puts the `timeout` wrapper in a group of its own
    so a kill reaches everything under it. The DEADLINE still belongs to that
    wrapper, which is the process that shares the child's fate; the loop's own
    deadline is the parent's view of the same bound and not a second opinion
    about it. The shape is the one tests/conformance/petta_capture.py already
    uses for the same corpus [tested:
    test_a_runaway_child_is_stopped_at_the_capture_ceiling,
    test_a_bounded_run_still_reports_a_timeout].

    stdin is left INHERITED, as `subprocess.run` left it, because an example
    that reads it must see what the runner sees. The two streams are kept
    APART and joined stdout-then-stderr at the end, which is the order
    `subprocess.run` produced and which `_read` depends on: interleaving them
    in arrival order put an ANSWER-GROUP line last and the teardown failure
    stopped being the reported error [tested:
    test_the_library_runner_reports_a_teardown_failure].

    Answers the text, the child's exit status, and the reason the run was
    stopped early, or None when the child ended on its own.
    """
    process = subprocess.Popen(  # noqa: S603 -- commands are built by repository runners
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    streams = {process.stdout.fileno(): bytearray(), process.stderr.fileno(): bytearray()}
    captured = 0
    stopped: str | None = None
    deadline = time.monotonic() + TIMEOUT
    selector = selectors.DefaultSelector()
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        selector.register(process.stderr, selectors.EVENT_READ)
        while selector.get_map() and stopped is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stopped = _late(f"timed out after {TIMEOUT}s")
                break
            # A pipe is finished when it reports EOF, never because the process
            # that started it has exited. Asking `process.poll()` here and
            # breaking when it answered was a check-then-act race: `ready` is
            # what epoll saw at one instant and `poll()` is what waitpid saw at
            # a later one, and on a loaded box the gap between them holds a
            # whole child. `epoll_wait` returned nothing at 0.25s because the
            # child had not written yet, this thread was not scheduled again
            # for another 1.6s, and by then the child had printed everything
            # and exited -- so the loop broke on its first iteration and threw
            # away 5,564 bytes that were sitting in the pipes, which `compare`
            # then read as "engine 0 verdicts" [measured 2026-09-06: three
            # reproductions over ten instrumented corpus runs at loadavg
            # 53-108, on both doors, each with the whole of the child's output
            # (5,564, 567 and 358 bytes) recoverable from the pipes after the
            # loop and reproduced byte for byte by re-running the same command;
            # tested: test_a_child_that_writes_late_is_read_in_full].
            for key, _ in selector.select(timeout=min(0.25, remaining)):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                room = MAX_CAPTURE_BYTES - captured
                streams[key.fileobj.fileno()].extend(chunk[:room])
                captured += min(len(chunk), room)
                if len(chunk) > room:
                    stopped = (
                        f"printed more than {MAX_CAPTURE_BYTES} bytes and was stopped"
                    )
                    break
    finally:
        selector.close()
        if stopped is None and process.poll() is None:
            # EOF on both pipes is not exit. A child closes its descriptors
            # when IT exits, and the status then propagates up through
            # bounded.sh's three wrappers, which takes a beat; polling here
            # read None and the kill below shot a process that had already
            # finished its work, so a child exiting 7 after closing its
            # pipes was reported as -9 in 40 of 40 runs, and the runner's
            # last-line-is-the-error fallback then made an error out of its
            # output [measured 2026-09-05: ai-tmp probe over _capture;
            # commit=00df0ebbd0d46a1778be70df020c3512f9e42a16]. Wait for the status, within what is left of
            # the deadline; only a child that is still running after that is
            # a runaway.
            try:
                process.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                stopped = _late(
                    f"closed its output but was still running at {TIMEOUT}s")
        if stopped is not None or process.poll() is None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        out, err = (
            bytes(streams[process.stdout.fileno()]),
            bytes(streams[process.stderr.fileno()]),
        )
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
        process.wait()
    text = out.decode("utf-8", errors="replace") + err.decode("utf-8", errors="replace")
    return text, process.returncode, stopped


def _run(
    command: list[str], cwd: Path, env: dict[str, str] | None = None,
    door: str = "configuration", name: str = "",
) -> tuple[Outcome, str]:
    """One configuration's run, as the outcome the comparator reads and the
    raw text beside it. The text is returned rather than discarded because a
    runner may emit more than answers on its own marker lines: the twin
    coverage lane reads an inference count and the defined heads from the
    same output [tested: test_a_runner_returns_its_raw_text_beside_the_outcome].

    The outcome carries what the run COST and what stopped it, because a run
    the box did not let finish is a different fact from a disagreement and has
    to be reported as itself
    [tested: test_a_stopped_run_is_reported_as_unanswered_with_its_load].
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    started = time.monotonic()
    text, returncode, stopped = _capture(_bounded(command), cwd, env)
    seconds = time.monotonic() - started
    COSTS.append((seconds, door, name))
    if stopped is not None:
        return Outcome([], stopped, returncode=None, door=door,
                       seconds=seconds, stopped=stopped), ""
    outcome = _read(text, returncode)
    error = outcome.error
    if error is None and returncode != 0:
        tail = text.strip().splitlines()
        error = tail[-1][:300] if tail else "no output"
    return Outcome(outcome.groups, error, outcome.verdicts, outcome.returncode,
                   door, seconds), text


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
        door="engine",
        name=str(path.relative_to(root)),
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
    return _run([sys.executable, "-c", source], root, door="library",
                name=str(path.relative_to(root)))[0]


@dataclass(frozen=True, slots=True)
class Difference:
    """One example the two configurations disagree about."""

    path: Path
    reason: str
    detail: str
    #: `disagreement` when the two configurations answered and differed, and
    #: `unanswered` when one of them did not answer at all. They are counted
    #: apart because only the first is a claim about MeTTa: the second is a
    #: claim about the box, and printing it in the same sentence as a
    #: disagreement is how "engine 0 verdicts" read as a defect in the engine.
    kind: str = "disagreement"

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


def _silent(outcome: Outcome) -> bool:
    """Whether this configuration produced nothing a comparator can read."""
    return not outcome.groups and not outcome.verdicts and outcome.error is None


def _unanswered(engine: Outcome, library: Outcome) -> tuple[Outcome, Outcome] | None:
    """The configuration that did not answer and the one that did, or None.

    A run STOPPED at its ceiling did not answer whatever the other one did,
    including when both were stopped: two configurations that were both killed
    agree about nothing, and reading that as agreement is a silent pass.

    Otherwise the signal is the ASYMMETRY. One example in the corpus prints no
    answer group at all on either door
    (ch20-extending-the-engine/20-06-files-and-processes/02-standard-streams.metta,
    which prints verdicts and no groups), and a file that observes nothing
    through both doors is agreement rather than a failure to run. One side
    silent while the other answered is not something an example can be.
    """
    for outcome, other in ((engine, library), (library, engine)):
        if outcome.stopped is not None:
            return outcome, other
    if _silent(engine) != _silent(library):
        return (engine, library) if _silent(engine) else (library, engine)
    return None


def compare(path: Path, root: Path = REPO) -> Difference | None:
    """Run one example both ways and answer what differs.

    A configuration that did not answer is run AGAIN, both doors, before it is
    believed. The lane's verdict must not depend on how loaded the box is, and
    a run the box did not let finish is not reproducible by definition where a
    real failure is. The line a retry must not cross is the one Bazel's
    `--flaky_test_attempts` and pytest-rerunfailures both draw, between an
    environmental failure and an assertion, and it is drawn here as exactly
    that: an answer that never arrived is re-run, an answer that disagreed
    never is [tested: test_an_unanswered_configuration_is_run_again].
    """
    engine, library = run_engine(path, root), run_library(path, root)
    relative = path.relative_to(root)

    if _unanswered(engine, library) is not None:
        RETRIED.append(str(relative))
        engine, library = run_engine(path, root), run_library(path, root)
    missing = _unanswered(engine, library)
    if missing is not None:
        quiet, other = missing
        beside = (
            f"the {other.door} configuration was stopped too: {other.stopped}"
            if other.stopped is not None else
            f"the {other.door} configuration printed {len(other.groups)} "
            f"group(s) and {len(other.verdicts)} verdict(s) in "
            f"{other.seconds:.1f}s"
        )
        return Difference(
            relative,
            f"no verdict: the {quiet.door} configuration answered nothing, twice",
            f"{quiet.stopped or _late('no answer group, no verdict and no error')}; "
            f"it ran {quiet.seconds:.1f}s against a {TIMEOUT}s ceiling; {beside}",
            kind="unanswered",
        )

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
    started = os.getloadavg()[0]
    with ThreadPoolExecutor() as pool:
        found = [d for d in pool.map(compare, paths) if d is not None]

    for difference in found:
        print(difference)
    disagreements = [d for d in found if d.kind == "disagreement"]
    unanswered = [d for d in found if d.kind == "unanswered"]
    print(
        f"{len(paths) - len(found)}/{len(paths)} examples agree "
        f"across both configurations"
    )
    if unanswered:
        # Counted apart from the disagreements, and said out loud even when
        # there are none of those, because "one configuration did not run" is
        # a claim about this box and "the two configurations differ" is a
        # claim about MeTTa. Printing them as one number is what let a child
        # whose output was never read report itself as `engine 0 verdicts`.
        print(f"{len(unanswered)} example(s) made no observation in one "
              f"configuration, counted apart from the {len(disagreements)} "
              f"disagreement(s)")
    if RETRIED:
        shown = ", ".join(sorted(RETRIED)[:5])
        print(f"{len(RETRIED)} example(s) had a configuration answer nothing "
              f"and were run again: {shown}"
              f"{', ...' if len(RETRIED) > 5 else ''}")
    if COSTS:
        seconds, door, name = max(COSTS)
        print(f"slowest child {seconds:.1f}s against a {TIMEOUT}s ceiling "
              f"({door} {name}), loadavg {started:.2f} to "
              f"{os.getloadavg()[0]:.2f}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
