"""Purpose: prove the parity lane detects a difference, ignores a difference
in spelling that is not one, and preserves the per-form grouping. A lane that
cannot be shown failing is not evidence of anything, so these plant differences
and require the lane to report them.
Guarantees:
  - the library runner enters and exits every engine, so an exception raised
    during teardown is reported rather than hidden behind answers printed
    before close [tested: test_the_library_runner_reports_a_teardown_failure;
    commit=WORKTREE]
  - exit status and verdict lines are compared independently of answer groups
    [tested: test_compare_reports_a_planted_exit_status_difference,
    test_compare_reports_a_planted_verdict_difference,
    test_compare_accepts_equivalent_passing_verdicts; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
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
