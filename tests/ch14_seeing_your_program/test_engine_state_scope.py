"""Purpose: engine state stays with its runnable, and an exceeded bound refuses.

Two rules, each because a battery said so: the engine's per-runnable state
belongs to the runnable, and a caller's bound that was exceeded refuses
instead of answering. A runnable's evaluation-fuel scope
was marked open by a write no cleanup put back when an asynchronous limit
landed between `setup_call_cleanup/3`'s setup and its cleanup registration, so
one aborted bounded call left every later runnable in the process taking the
reentrant branch: `!(p122-fact 5)` under `(pragma! max-stack-depth 20)`
answered `120` alone where it answers `[120, (Error -3 StackOverflow)]`, and a
`with-pragma!` overflow in a freshly built space answered nothing at all. And a
0.3-second load answered `[[(Error (spin) StackOverflow)]]` after 66.170
seconds at loadavg 90 to 100, because an alarm that arrives after its goal has
finished cannot refuse anything.
Assumes: the process runtime, and MeTTa objects whose spaces this file drops.
Guarantees:
  - engine state a bounded abort touches does not cross a MeTTa object
    [tested: test_a_bounded_abort_leaves_the_next_contexts_stack_bound_working;
    commit=f6e05ca933f4b79d2e5c148b45780a361d87f586]
  - a caller's wall-clock bound that was exceeded is a refusal, whatever the
    alarm did [tested: test_a_wall_clock_bound_that_is_exceeded_refuses;
    commit=f6e05ca933f4b79d2e5c148b45780a361d87f586]
  - and `(pragma! max-stack-depth N)` stays the answer the corpus pins, which
    is the other half of the same rule [tested:
    test_a_stack_depth_bound_stays_an_answer; commit=f6e05ca933f4b79d2e5c148b45780a361d87f586]
  - a host stack abort inside a caller's bound is raised rather than converted
    into an answer [tested: test_a_host_stack_abort_inside_a_bound_is_raised;
    commit=f6e05ca933f4b79d2e5c148b45780a361d87f586]
Fails when: read as the mechanism's own coverage. The interruption that
  abandons a scope is swept budget by budget in
  tests/prolog/suites/evaluation/fuel.plt, and the missed alarm in
  tests/prolog/suites/evaluation/time_budget.plt; these are the promises those
  mechanisms exist to keep, at the surface a caller sees.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import time

import pytest

from metta import MeTTa
from metta.errors import EngineError, ResourceLimitError, TimeLimitError


def test_a_bounded_abort_leaves_the_next_contexts_stack_bound_working():
    """One context's aborted bounded call cannot disarm another's fuel bound."""
    with MeTTa() as first:
        first.self.run("(= (scope-spin $n) (scope-spin (- $n 1)))")
        with pytest.raises(ResourceLimitError):
            first.self.eval("(scope-spin 5)", inferences=200)

    with MeTTa() as second:
        space = second.self
        space.run("(= (scope-spin-two $n) (scope-spin-two (- $n 1)))")
        (group,) = space.run(
            "!(with-pragma! ((max-stack-depth 20)) (scope-spin-two 5))"
        )
        answers = [str(atom) for atom in group]
    assert len(answers) == 1, answers
    assert answers[0].startswith("(Error ") and answers[0].endswith(" StackOverflow)")


def test_a_wall_clock_bound_that_is_exceeded_refuses(metta):
    """A bound the alarm lost still refuses, and names the seconds it was given.

    `sig_atomic/1` blocks signal delivery, so the alarm the door installed is
    removed before it can be delivered and the goal runs six times its bound
    with nothing raised: `call_with_time_limit(0.05, sig_atomic(sleep(0.3)))`
    answers in plain SWI. That is the shape a starved box produces by itself,
    and the door is what refuses anyway. Driven through the engine door rather
    than through `run(timeout=)` because blocking the alarm is the point and
    MeTTa has no spelling for it.
    """
    started = time.monotonic()
    with pytest.raises(TimeLimitError, match=r"0\.05 second time limit"):
        metta.runtime.once("metta_py_guarded(0.05, -1, sig_atomic(sleep(0.3)))")
    assert time.monotonic() - started > 0.2, "the alarm was not blocked, so this proved nothing"


def test_a_stack_depth_bound_stays_an_answer(metta):
    """The program's own bound answers where a caller's bound refuses.

    `(pragma! max-stack-depth N)` is reduction fuel the program asked for, and
    running out of it is `(Error <culprit> StackOverflow)` beside the answers
    that finished, which is what the corpus pins. The two rules live side by
    side deliberately: a caller's keyword is a refusal and the language's own
    pragma is an answer.
    """
    with metta._new_space() as space:
        space.run("(= (scope-fact 0) 1)")
        space.run("(= (scope-fact $n) (* $n (scope-fact (- $n 1))))")
        (group,) = space.run(
            "!(with-pragma! ((max-stack-depth 20)) (scope-fact 5))"
        )
        answers = [str(atom) for atom in group]
    assert answers == ["120", "(Error -3 StackOverflow)"]


def test_a_host_stack_abort_inside_a_bound_is_raised(metta, tmp_path):
    """SWI's own stack ceiling refuses; it never becomes an answer.

    A caller's bound and the host's stack ceiling are different guards and the
    race between them is real, so the rule has to hold whichever wins: the
    call raises rather than returning the abort as an `(Error ...)` answer the
    caller would read as a result. The class is `EngineError` today because
    the Python seat has no condition for the engine's `stack` refusal kind;
    `tests/data/error-kinds.json` records that gap and its owner.
    """
    source = tmp_path / "deep.metta"
    source.write_text(
        "(= (scope-deep $n) (if (== $n 0) 0 (+ 1 (scope-deep (- $n 1)))))\n"
        "!(with-pragma! ((stack-limit 30000000)) (scope-deep 10000000))\n",
        encoding="utf-8",
    )
    with pytest.raises(EngineError, match=r"[Ss]tack limit"):
        metta.load(source, timeout=30.0)
