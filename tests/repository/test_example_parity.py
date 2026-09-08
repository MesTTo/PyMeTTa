"""Purpose: prove the parity lane detects a difference, ignores a difference
in spelling that is not one, and preserves the per-form grouping. A lane that
cannot be shown failing is not evidence of anything, so these plant differences
and require the lane to report them.
Guarantees:
  - the library runner enters and exits every engine, so an exception raised
    during teardown is reported rather than hidden behind answers printed
    before close [tested: test_the_library_runner_reports_a_teardown_failure;
    commit=835925ee1c55d2267aa54f0a5ccbdfcdb6fc003c]
  - exit status and verdict lines are compared independently of answer groups
    [tested: test_compare_reports_a_planted_exit_status_difference,
    test_compare_reports_a_planted_verdict_difference,
    test_compare_accepts_equivalent_passing_verdicts; commit=835925ee1c55d2267aa54f0a5ccbdfcdb6fc003c]
  - process termination preserves its status without becoming an answer error
    [tested: test_process_exit_is_not_an_answer_error; commit=bbb512316280110a747e31c26adfc31e8c5104be]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import re
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "extensions" / "python" / "tools"))

import example_parity as parity  # noqa: E402


def test_the_corpus_is_one_definition():
    """Discovery lives here and nowhere else. It used to be duplicated
    across runners, matching on basename rather than path, and the copies
    disagreed [source: ai-audit-md-review.md section 12].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    found = parity.corpus()
    assert found, "the corpus is empty, which means discovery is broken"
    assert all(path.suffix == ".metta" for path in found)
    assert not any(path.is_symlink() for path in found)
    assert not any("_fixtures" in path.parts for path in found)
    declared = set(parity.skips())
    assert not (declared & {str(p.relative_to(REPO)) for p in found})


def test_every_declared_skip_resolves_and_would_otherwise_run():
    """A skip naming a file that does not exist, or one discovery would
    never have yielded anyway, is a line nobody will notice is dead.
    check.sh carried exactly that: it skipped import_error_broken.metta,
    which lives under _fixtures/ and is excluded before any skip is
    consulted [measured 2026-08-18].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    for path, reason in parity.skips().items():
        assert (REPO / path).is_file(), f"{path} does not exist"
        assert reason, f"{path} has no reason"
        assert not (REPO / path).is_symlink(), f"{path} is an alias"
        assert "_fixtures" not in Path(path).parts, f"{path} is excluded anyway"


def test_the_chess_example_is_skipped_for_the_reason_that_is_true():
    """It needs a terminal; it was skipped as long-running and benchmarked.

    The reason read "long-running, covered by benchmarks" until 2026-08-26
    and neither half held: no benchmark in any baseline names it, and given
    its quit command it loads, sets up the board and exits in about a
    quarter second. What it cannot survive is a closed stdin. The file ends
    in ``!(main_loop)``, whose ``(command-loop)`` reads with ``readln!/1``
    and recurses on anything but ``q``, and ``readln!/1`` is
    ``read_line_to_string/2``, which answers ``end_of_file`` for every read
    once stdin is at EOF. Both halves are measured here, because a skip
    reason nothing checks is how the wrong one survived.
    """
    example = "examples/ch22-a-reasoner-you-can-serve/22-03-search/06-greedy_chess.metta"
    assert "interactive terminal" in parity.skips()[example]

    quits = subprocess.run(
        ["sh", "run.sh", example],
        cwd=REPO,
        input="q\n",
        capture_output=True,
        text=True,
        timeout=parity.TIMEOUT,
        check=False,
    )
    assert quits.returncode == 0, quits.stderr[-2000:]
    assert "Quitting MeTTa Greedy Chess." in quits.stdout

    # A whole terminating run is 501,917 bytes and refuses three commands,
    # so a process still producing refusals after four times that many
    # bytes is not a program taking its time.
    looping = subprocess.Popen(
        ["sh", "run.sh", example],
        cwd=REPO,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    try:
        head = looping.stdout.read(2_000_000)
        unfinished = looping.poll() is None
    finally:
        os.killpg(looping.pid, signal.SIGKILL)
        looping.wait(timeout=parity.TIMEOUT)
    assert unfinished, "the command loop ended without a terminal"
    assert head.count("Invalid command") > 1_000, "it blocked rather than looping"


def test_example_parity_reports_a_planted_difference():
    """A real difference in ANSWERS survives the value comparison."""
    engine = parity.Outcome(["((1 2))"], None)
    library = parity.Outcome(["((1 3))"], None)
    assert parity._value(engine.groups[0]) != parity._value(library.groups[0])


def test_the_library_runner_reports_a_teardown_failure(tmp_path):
    """Answers printed before ``MeTTa.__exit__`` cannot hide a broken close."""
    package = tmp_path / "extensions" / "python" / "metta"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        """class _Space:
    def load(self, _path):
        return [[\"answer-before-close\"]]

class MeTTa:
    def __init__(self, **_kwargs):
        self.self = _Space()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        raise RuntimeError(\"PLANTED_CLOSE_FAILURE\")
""",
        encoding="utf-8",
    )
    example = tmp_path / "examples" / "close_probe.metta"
    example.parent.mkdir()
    example.write_text("; the fake loader does not read this fixture\n", encoding="utf-8")

    outcome = parity.run_library(example, tmp_path)

    assert outcome.groups == ["(answer-before-close)"]
    assert outcome.returncode != 0
    assert outcome.error is not None
    assert "PLANTED_CLOSE_FAILURE" in outcome.error


def test_compare_reports_a_planted_exit_status_difference(monkeypatch):
    """Equal answers do not erase a process-status disagreement."""
    path = REPO / "examples" / "ch09-types" / "01-types.metta"
    monkeypatch.setattr(
        parity, "run_engine", lambda *_args: parity.Outcome(["(1)"], None)
    )
    monkeypatch.setattr(
        parity,
        "run_library",
        lambda *_args: parity.Outcome(["(1)"], None, returncode=7),
    )

    difference = parity.compare(path)

    assert difference is not None
    assert difference.reason == "the configurations exited differently"
    assert difference.detail == "engine 0 against library 7"


def test_compare_reports_a_planted_verdict_difference(monkeypatch):
    """Equal answer groups do not erase a failing assertion verdict."""
    path = REPO / "examples" / "ch09-types" / "01-types.metta"
    monkeypatch.setattr(
        parity,
        "run_engine",
        lambda *_args: parity.Outcome(
            ["(1)"], None, ("is 1, should 1. ✅",)
        ),
    )
    monkeypatch.setattr(
        parity,
        "run_library",
        lambda *_args: parity.Outcome(
            ["(1)"], None, ("is 1, should 2. ❌",)
        ),
    )

    difference = parity.compare(path)

    assert difference is not None
    assert difference.reason == "test verdict 1 differs"
    assert "should 1" in difference.detail
    assert "should 2" in difference.detail


def test_compare_accepts_equivalent_passing_verdicts(monkeypatch):
    """A configuration-local home name does not change a passing verdict."""
    path = REPO / "examples" / "ch09-types" / "01-types.metta"
    monkeypatch.setattr(
        parity,
        "run_engine",
        lambda *_args: parity.Outcome(
            ["(true)"], None, ("is &self, should &self. ✅",)
        ),
    )
    monkeypatch.setattr(
        parity,
        "run_library",
        lambda *_args: parity.Outcome(
            ["(true)"], None, ("is &pyspace_1, should &pyspace_1. ✅",)
        ),
    )

    assert parity.compare(path) is None


def test_a_python_tuple_answers_the_same_through_both_doors(metta):
    """The shared Python-surface example exposes pair and empty tuple answers."""
    path = REPO / "examples" / "ch11-python-as-a-notation" / "04-py_surface.metta"
    engine = parity.run_engine(path)
    library = parity.run_library(path)
    assert engine.error is None, engine.error
    assert library.error is None, library.error
    assert engine.groups[-2:] == ["((1 2))", "(())"]
    assert library.groups[-2:] == ["((1 2))", "(())"]
    assert parity.compare(path) is None

    ((grounded,),) = metta.run('!(py-atom "(1, 2)" Grounded)')
    assert grounded.metatype == "Grounded"
    assert type(grounded.value) is tuple
    with metta.bind(held=grounded):
        assert metta.run("!(py-dot (py-dot held __class__) __name__)") == [["tuple"]]
        assert metta.run("!(car-atom held)") == [[1]]

    types = metta.run(
        '!(let $x (py-atom "(1, 2)" Grounded) (collapse (get-type $x)))'
    )
    assert types == [[metta.parse("(tuple Grounded)")]]


def test_spelling_is_not_a_difference():
    """Boolean source aliases parse to the same value even though canonical
    output now uses `True` and `False` from both configurations.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert parity._value("(true)") == parity._value("(True)")
    assert parity._value("(false)") == parity._value("(False)")
    assert parity._value("(1 2)") != parity._value("(- 1 2)")


def test_an_unparseable_group_stays_visible():
    """A group neither side can parse compares as its own text, so a
    malformed answer is not collapsed to equal-by-failure.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert parity._value("(a") == "(a"
    assert parity._value("(a") != parity._value("(b")


def test_the_grouping_is_preserved():
    """`!(superpose (1 2 3))` then `!(+ 1 1)` must not read the same as
    `!(superpose (1 2))` then `!(superpose (3 2))`. Both flatten to the
    answers 1 2 3 2, and the first version of this lane could not tell them
    apart because it printed one line per ANSWER.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    one = parity.Outcome(["(1 2 3)", "(2)"], None)
    two = parity.Outcome(["(1 2)", "(3 2)"], None)
    assert one.groups != two.groups
    flat_one = " ".join(one.groups).replace("(", "").replace(")", "")
    flat_two = " ".join(two.groups).replace("(", "").replace(")", "")
    assert flat_one == flat_two, "the flattened forms really are identical"


def test_an_empty_group_is_an_observation():
    """A form answering nothing prints `()` rather than nothing, because
    dropping it would misalign every group after it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    outcome = parity._read("ANSWER-GROUP ()\nANSWER-GROUP (2)\n")
    assert outcome.groups == ["()", "(2)"]
    assert outcome.error is None


def test_a_verdict_is_read_by_its_shape_and_not_by_a_word_in_it():
    """A doc row that says "should" is not a fifteenth test verdict.

    The engine configuration echoes the source of every library an example
    imports, so a generated `(@doc ...)` row travels through this reader. One
    of lib_torch's says "if autograd should record operations on this tensor",
    and reading a verdict as "the line contains ` should `" counted it,
    reporting `10-torch-library-surface.metta` as engine 15 against library 14
    when both print the same fourteen.
    """
    text = (
        "(@doc torch-requires-grad (@kind function) (@desc \"Change if "
        "autograd should record operations on this tensor.\"))\n"
        "is 1, should 1. \u2705\n"
    )
    assert parity._read(text).verdicts == ("is 1, should 1. \u2705",)


def test_an_error_line_is_not_an_empty_run():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    outcome = parity._read("ANSWER-ERROR something broke\n")
    assert outcome.error == "something broke"
    assert outcome.groups == []


def test_a_runner_returns_its_raw_text_beside_the_outcome():
    """A runner may print more than answers on its own marker lines, and the
    twin coverage lane reads an inference count and the defined heads from
    exactly the same output. Discarding the text would have meant a second
    copy of the subprocess handling, timeout and error tail included.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    outcome, text = parity._run(
        [sys.executable, "-c", "print('ANSWER-GROUP (1)'); print('OTHER 7')"],
        REPO,
    )
    assert outcome.groups == ["(1)"]
    assert outcome.error is None
    assert "OTHER 7" in text


@pytest.mark.parametrize("name", ["ch07-control-flow/07-04-bounded-and-committed-searches/01-forall.metta", "ch09-types/01-types.metta"])
def test_a_known_agreeing_example_agrees(name):
    """Two examples that do agree, so a change breaking the comparison
    itself is caught rather than reading as a corpus finding.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    difference = parity.compare(REPO / "examples" / name)
    assert difference is None, str(difference)


def test_a_runaway_child_is_stopped_at_the_capture_ceiling():
    """A deadline does not bound memory, so the capture carries its own bound.

    Measured on the parent before this existed: a child printing 256 MiB took
    it to 850 MiB resident in about two seconds, against TIMEOUT=300, because
    `capture_output=True` holds the chunk list, the joined bytes and the
    decoded string at once. greedy_chess is the shipped shape of it, printing
    17,973,938 lines in 120 seconds once its command loop meets EOF.
    """
    spew = (
        "import sys\n"
        "line = 'x' * 1023 + chr(10)\n"
        "for _ in range({lines}):\n"
        "    sys.stdout.write(line)\n"
    )
    under = parity.MAX_CAPTURE_BYTES // 4096
    outcome, text = parity._run(
        [sys.executable, "-c", spew.format(lines=under)], REPO
    )
    assert outcome.error is None
    assert len(text) == under * 1024

    over = parity.MAX_CAPTURE_BYTES // 1024 + 4096
    outcome, text = parity._run(
        [sys.executable, "-c", spew.format(lines=over)], REPO
    )
    assert outcome.error == (
        f"printed more than {parity.MAX_CAPTURE_BYTES} bytes and was stopped"
    )
    assert outcome.returncode is None
    assert outcome.groups == []


def test_a_child_that_closes_its_output_before_exiting_keeps_its_status():
    """EOF on both pipes is not exit, and the capture must not shoot the gap.

    A child closes its descriptors when it exits, and under bounded.sh the
    status then climbs through three wrappers before the parent can read it.
    Reading EOF, finding poll() still None and killing the group reported a
    child that exited 7 as -9 in 40 of 40 runs, and the runner's last-line
    fallback then presented a line of its own output as the error; in the
    full suite that read as four parity failures that passed alone. The
    capture now waits for the status, within what is left of the deadline.
    """
    for _ in range(10):
        text, returncode, stopped = parity._capture(
            ["sh", "-c", "echo 'ANSWER-GROUP (1)'; exec >&- 2>&-; sleep 0.05; exit 7"],
            REPO, None,
        )
        assert returncode == 7, (returncode, stopped, text)
        assert stopped is None
        assert "ANSWER-GROUP (1)" in text


def test_a_child_still_running_after_eof_is_named_a_runaway():
    """The wait after EOF is bounded, and a child that outlives it says so."""
    original = parity.TIMEOUT
    parity.TIMEOUT = 3
    try:
        _text, returncode, stopped = parity._capture(
            ["sh", "-c", "echo x; exec >&- 2>&-; sleep 30"], REPO, None
        )
    finally:
        parity.TIMEOUT = original
    assert returncode == -9
    # Two branches can name this stop, the read loop's deadline or the wait
    # after EOF, and which one wins depends on whether EOF was read before the
    # deadline check in the same iteration. Either is the contract: the child
    # was killed at the ceiling and the outcome says it was stopped.
    assert stopped is not None
    assert stopped.startswith((
        "closed its output but was still running at 3s under loadavg ",
        "timed out after 3s under loadavg ",
    ))


def test_a_bounded_run_still_reports_a_timeout():
    """The byte cap is a second bound, not a replacement for the deadline."""
    original = parity.TIMEOUT
    parity.TIMEOUT = 1
    try:
        outcome, _ = parity._run(
            [sys.executable, "-c", "import time; time.sleep(30)"], REPO
        )
    finally:
        parity.TIMEOUT = original
    assert outcome.error is not None
    assert outcome.error.startswith("timed out after 1s under loadavg ")
    assert outcome.returncode is None


#: The real selector, bound at import so the stand-in below can still build
#: one after monkeypatch has replaced the name it would otherwise read.
_REAL_SELECTOR = selectors.DefaultSelector


class _StaleFirstLook:
    """A selector whose FIRST look sees nothing, whatever the pipes hold.

    That is what a descheduled parent's look sees, and reproducing it is the
    only way to plant the race deterministically: the defect needs `select` to
    have looked before the child wrote and `waitpid` to be asked after the
    child exited, and neither the child nor the test can arrange the gap
    between two statements in the parent. Everything but the first look is the
    real selector's.
    """

    def __init__(self):
        self._real = _REAL_SELECTOR()
        self._looked = False

    def select(self, timeout=None):
        if self._looked:
            return self._real.select(timeout)
        self._looked = True
        # Both halves of the race have to be true or the case proves nothing:
        # the pipes must already hold the child's output, and the child must
        # already be gone. Waiting for the real selector to report readiness
        # makes the first certain rather than likely, and the beat after it
        # covers the exit that follows the planted child's last echo. A fixed
        # sleep alone stopped being enough to make either true somewhere above
        # loadavg 100.
        self._real.select(timeout=5)
        time.sleep(0.3)
        return []

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_a_child_that_writes_late_is_read_in_full(monkeypatch):
    """A pipe is finished at EOF, never because the writer's process exited.

    The loop used to break when a `select` had seen nothing and a `poll()`
    then reported the child gone. Those are observations from two different
    instants, and on a loaded box the gap between them holds a whole child:
    `epoll_wait` returned nothing at 0.25s because the child had not written
    yet, the thread was not scheduled again for another 1.6s, and by then the
    child had printed everything and exited. Three reproductions over sixteen
    corpus runs at loadavg 53-108, one on each door, each with the child's
    whole output (5,564, 567 and 358 bytes) still readable from the pipes
    after the loop and reproduced byte for byte by re-running the same
    command; `compare` read each as `engine 0 verdicts` or `library 0
    verdicts` against the door that did answer [measured 2026-09-06].
    """
    monkeypatch.setattr(parity.selectors, "DefaultSelector", _StaleFirstLook)
    text, returncode, stopped = parity._capture(
        ["sh", "-c", "echo 'ANSWER-GROUP (1)'; echo 'is 1, should 1. OK'"],
        REPO, None,
    )
    assert stopped is None, stopped
    assert returncode == 0
    assert "ANSWER-GROUP (1)" in text
    assert "is 1, should 1. OK" in text


def test_a_stopped_run_is_reported_as_unanswered_with_its_load(monkeypatch):
    """A child killed at its ceiling is a run that did not happen.

    It used to reach `compare` as `returncode=None` and be reported as "the
    configurations exited differently", which says the two disagree when what
    happened is that one of them was killed. The load belongs in the sentence
    because a ceiling reached on a box carrying three times its cores is a
    different fact from one reached on an idle box.
    """
    original = parity.TIMEOUT
    parity.TIMEOUT = 1
    try:
        stopped, _ = parity._run(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            REPO, door="engine", name="planted",
        )
    finally:
        parity.TIMEOUT = original
    assert stopped.stopped is not None
    assert stopped.stopped.startswith("timed out after 1s under loadavg ")
    assert stopped.seconds >= 1
    assert stopped.door == "engine"

    answered = parity.Outcome(["(1)"], None, ("is 1, should 1. ✅",), 0,
                              "library", 0.2)
    monkeypatch.setattr(parity, "run_engine", lambda *_args: stopped)
    monkeypatch.setattr(parity, "run_library", lambda *_args: answered)

    difference = parity.compare(REPO / "examples" / "ch09-types" / "01-types.metta")

    assert difference is not None
    assert difference.kind == "unanswered"
    assert difference.reason == (
        "no verdict: the engine configuration answered nothing, twice")
    assert "timed out after 1s under loadavg " in difference.detail
    assert f"against a {parity.TIMEOUT}s ceiling" in difference.detail
    assert "library configuration printed 1 group(s) and 1 verdict(s)" in (
        difference.detail)


def test_two_stopped_configurations_do_not_agree(monkeypatch):
    """Both killed is not both equal, which is how it used to read.

    Two stopped outcomes carry the same `returncode=None`, the same empty
    groups and the same empty verdicts, so every comparison below them passed
    and the example counted as agreeing.
    """
    killed = parity.Outcome([], "timed out after 300s under loadavg 71.00", (),
                            None, "engine", 300.0,
                            "timed out after 300s under loadavg 71.00")
    monkeypatch.setattr(parity, "run_engine", lambda *_args: killed)
    monkeypatch.setattr(
        parity, "run_library",
        lambda *_args: parity.Outcome([], killed.error, (), None, "library",
                                      300.0, killed.stopped))

    difference = parity.compare(REPO / "examples" / "ch09-types" / "01-types.metta")

    assert difference is not None
    assert difference.kind == "unanswered"


def test_an_unanswered_configuration_is_run_again(monkeypatch):
    """A transient is not reproducible and a real one is; the retry separates them.

    The retry is also SAID, because one that succeeded is the same disturbance
    the bare zero used to be, one attempt earlier.
    """
    silent = parity.Outcome([], None, (), 0, "engine", 0.1)
    answering = parity.Outcome(["(1)"], None, (), 0, "engine", 0.1)
    attempts: list[str] = []

    def engine(*_args):
        attempts.append("engine")
        return silent if len(attempts) == 1 else answering

    monkeypatch.setattr(parity, "run_engine", engine)
    monkeypatch.setattr(
        parity, "run_library",
        lambda *_args: parity.Outcome(["(1)"], None, (), 0, "library", 0.1))
    monkeypatch.setattr(parity, "RETRIED", [])

    difference = parity.compare(REPO / "examples" / "ch09-types" / "01-types.metta")

    assert difference is None, str(difference)
    assert len(attempts) == 2, "the configuration that answered nothing was not run again"
    assert parity.RETRIED == ["examples/ch09-types/01-types.metta"]


def test_a_configuration_silent_through_both_doors_is_agreement(monkeypatch):
    """An example can legitimately observe nothing; a SIDE cannot.

    examples/ch20-extending-the-engine/20-06-files-and-processes/02-standard-streams.metta
    prints verdicts and no answer group at all, on either door, so the signal
    has to be the asymmetry rather than the emptiness.
    """
    empty = parity.Outcome([], None, (), 0, "engine", 0.1)
    monkeypatch.setattr(parity, "run_engine", lambda *_args: empty)
    monkeypatch.setattr(
        parity, "run_library",
        lambda *_args: parity.Outcome([], None, (), 0, "library", 0.1))

    assert parity.compare(REPO / "examples" / "ch09-types" / "01-types.metta") is None


def test_the_stated_corpus_size_is_the_real_one():
    """Three places used to state this number and all three were wrong,
    each by a different amount: examples/README.md said 184, llms.txt said
    242 (a glob counting 24 symlink aliases and 12 fixtures), and the
    survey ledger said 169, against 200 that run [measured 2026-08-18]. A
    number nothing derives is a number that drifts.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    size = len(parity.corpus())
    readme = (REPO / "examples" / "README.md").read_text()
    stated = re.search(r"contains (\d+) examples that run", readme)
    assert stated, "examples/README.md no longer states its corpus size"
    assert int(stated.group(1)) == size, (
        f"examples/README.md says {stated.group(1)}, the runners run {size}"
    )


@pytest.mark.parametrize("status", [0, 7])
def test_process_exit_is_not_an_answer_error(tmp_path, status):
    """SWI unwind exceptions carry process control through the answer reporter."""
    example = tmp_path / "exit.metta"
    example.write_text(
        f"!(import! &self (library lib_file))\n!(exit! {status})\n",
        encoding="utf-8",
    )
    outcome, text = parity._run(
        [
            "swipl", "--stack_limit=8g", "-q",
            "-g", 'consult("engine/metta.pl")',
            "-s", "tests/conformance/answer_groups.pl",
            "--", "--file", str(example), "extensions",
        ],
        REPO,
    )
    assert outcome.returncode == status, text
    assert "ANSWER-ERROR " not in text, text
