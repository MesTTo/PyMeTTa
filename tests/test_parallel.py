"""Purpose: MeTTa.parallel, the Python spelling of the engine's hyperpose.
Guarantees:
  - parallel answers the same set as the sequential superpose twin
    [tested test_parallel_answers_the_same_set_as_superpose]
  - branches really run concurrently, so N of them cost about one
    [tested test_parallel_runs_branches_concurrently]
  - the call takes a timeout and does not take an inference bound, because
    the engine's inference limit counts only the calling thread
    [tested test_parallel_takes_a_timeout_and_has_no_inference_bound]
  - a dual built for the first time by several threads at once is built ONCE,
    which is the property a check-then-act did not have
    [tested test_a_dual_is_built_once_under_concurrency]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import time

import pytest

from petta import S
from petta.atoms import expr

SQUARE = "(= (par-sq $x) (* $x $x))"
SPIN = "(= (par-spin $n) (if (> $n 0) (par-spin (- $n 1)) done))"


def test_parallel_answers_the_same_set_as_superpose(metta):
    """Same branches, same answers; hyperpose only changes the order."""
    with metta.new_space() as space:
        space.run(SQUARE)
        branches = [expr(S["par-sq"], n) for n in (1, 2, 3, 4)]
        parallel = sorted(str(a) for a in space.parallel(*branches))
        sequential = sorted(
            str(a) for a in space.eval(expr(S.superpose, expr(*branches)))
        )
        assert parallel == sequential == ["1", "16", "4", "9"]


def test_parallel_accepts_text_and_atoms(metta):
    """A target is a term or its source text, as everywhere else."""
    with metta.new_space() as space:
        space.run(SQUARE)
        answers = space.parallel(expr(S["par-sq"], 5), "(par-sq 6)")
        assert sorted(str(a) for a in answers) == ["25", "36"]


def test_parallel_without_targets_answers_nothing(metta):
    """No branches is no answers, and no engine call to find that out."""
    with metta.new_space() as space:
        assert space.parallel() == []


def test_parallel_runs_branches_concurrently(metta):
    """The point of the method: four branches cost about one branch.

    Wall clock is the only signal for parallelism, so the workload is sized
    well above this box's timing noise and the margin is generous.
    """
    with metta.new_space() as space:
        space.run(SPIN)
        branch = expr(S["par-spin"], 3_000_000)

        start = time.perf_counter()
        space.eval(branch)
        one = time.perf_counter() - start
        if one < 0.05:
            pytest.skip(f"one branch took {one:.3f}s, too fast to time reliably")

        start = time.perf_counter()
        answers = space.parallel(branch, branch, branch, branch)
        concurrent = time.perf_counter() - start

        assert len(answers) == 4
        assert concurrent < one * 2.5, (
            f"four branches took {concurrent:.3f}s against {one:.3f}s for one, "
            "which is sequential rather than concurrent"
        )


def test_parallel_takes_a_timeout_and_has_no_inference_bound(metta):
    """timeout bounds the call; inferences is deliberately not a parameter."""
    from petta.errors import TimeLimitError

    with metta.new_space() as space:
        space.run(SPIN)
        forever = expr(S["par-spin"], 200_000_000)
        with pytest.raises(TimeLimitError):
            space.parallel(forever, forever, timeout=0.1)

        # An inference bound would count only the calling thread, so it is
        # refused rather than accepted and silently not enforced.
        with pytest.raises(TypeError):
            space.parallel(expr(S["par-spin"], 1), inferences=1000)


def test_parallel_reports_a_failing_branch(metta):
    """A branch that raises is not swallowed by the concurrency. A wrongly
    typed operand answers `(Error ...)` rather than raising now, so the branch
    that has to raise is a HOST error, division by zero."""
    from petta.errors import EngineError

    with metta.new_space() as space:
        space.run(SQUARE)
        with pytest.raises(EngineError):
            space.parallel(expr(S["par-sq"], 2), "(/ 1 0)")


def test_a_dual_is_built_once_under_concurrency(metta):
    """not-provable builds its dual on first use, and it used to build it once
    per racing thread.

    ensure_dual/3 tested two markers and then built, with nothing between the
    test and the act. Thirty-two calls through a pool of eight left five
    clauses of the dual, five dual_ready facts, four dual_hooks_installed and
    seven metta_on_function_changed handlers, and the answer came back True
    five times instead of once. The count moved between runs, which is what
    said race rather than off-by-one.

    The duplicated handlers were the worse half: metta_on_function_changed/1
    is an EVENT hook, so each duplicate ran on every compiled equation
    afterwards, and nothing bounded the growth.

    Asserted against the SERIAL answer rather than against a literal, because
    the claim is that concurrency changes nothing.
    """
    metta.run("(= (conc-p $x) (> $x 1))")
    calls = " ".join(["(not-provable (conc-p 0))"] * 16)
    concurrent = metta.run(f"!(collapse (hyperpose ({calls})))")[-1]
    assert len(concurrent[0]) == 16, concurrent

    serial = metta.run("!(collapse (not-provable (conc-p 0)))")[-1]
    assert len(serial[0]) == 1, f"the dual answers {len(serial[0])} times, not once"

    # The dual compiles into the module of the space that defined the function
    # it negates, which for &self is not `user` any more.
    clauses = next(
        iter(metta.runtime.iter(
            "space_module('&self', M), "
            "aggregate_all(count, clause(M:'not-conc-p'(_, _), _), N)"
        ))
    )["N"]
    assert clauses == 1, f"{clauses} clauses of the dual were built, not one"
