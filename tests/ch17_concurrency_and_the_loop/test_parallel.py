"""Purpose: MeTTa.parallel, the Python spelling of the engine's hyperpose.
Guarantees:
  - parallel answers the same set as the sequential superpose twin
    [tested: test_parallel_answers_the_same_set_as_superpose; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - branches really overlap at an in-branch rendezvous
    [tested: test_parallel_runs_branches_concurrently; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the call takes a timeout and does not take an inference bound, because
    the engine's inference limit counts only the calling thread
    [tested: test_parallel_takes_a_timeout_and_has_no_inference_bound;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a dual built for the first time by several threads at once is built ONCE,
    which is the property a check-then-act did not have
    [tested: test_a_dual_is_built_once_under_concurrency; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a blocking relational call on a bare Python thread uses its temporary
    Janus engine without holding the home-engine lock, so unrelated work can
    complete before the blocker is released [tested:
    test_a_bare_thread_blocking_in_the_engine_does_not_freeze_other_calls;
    commit=6ffd7e3bbfc653f10817c48f30cd56572960e43f]
  - an abandoned Channel destroys its SWI message queue from whichever thread
    collects it [tested:
    test_abandoned_channels_destroy_their_swi_queues_from_collector_thread;
    commit=8909645dc7b390e4c6e7af77bfc75791c4f0aea1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import gc
import threading
import time
import weakref

import pytest

from metta import S, channel
from metta._engine import engine_thread, runtime
from metta.atoms import Expression
from metta.errors import EngineError, TimeLimitError

SQUARE = "(= (par-sq $x) (* $x $x))"
SPIN = "(= (par-spin $n) (if (> $n 0) (par-spin (- $n 1)) done))"


def _live_channels() -> int:
    """The engine-side channel table, one row per owned SWI queue."""
    return runtime().once(
        "aggregate_all(count, metta_channel(_Id, _Queue), N)"
    )["N"]


def test_abandoned_channels_destroy_their_swi_queues_from_collector_thread():
    """Collection is the backstop when explicit close was omitted."""
    with channel(max=1):
        pass  # load lib_thread before taking the baseline
    baseline = _live_channels()
    abandoned = [channel(max=8) for _ in range(200)]
    references = [weakref.ref(mailbox) for mailbox in abandoned]
    failures: list[BaseException] = []

    def collect() -> None:
        try:
            abandoned.clear()
            gc.collect()
        except BaseException as failure:
            failures.append(failure)

    collector = threading.Thread(target=collect)
    collector.start()
    collector.join(30)

    assert not collector.is_alive(), "channel collection did not finish"
    assert failures == []
    assert all(reference() is None for reference in references)
    assert _live_channels() == baseline


def test_a_bare_thread_blocking_in_the_engine_does_not_freeze_other_calls(metta):
    """A private temporary engine must not borrow the home engine's lock."""
    mailbox = channel(max=1)
    waiter_observed = threading.Event()
    evaluation_finished = threading.Event()
    received = []
    answers = []
    failures: list[BaseException] = []
    rt = runtime()

    def receive() -> None:
        try:
            received.append(mailbox.recv())
        except BaseException as failure:
            failures.append(failure)

    def observe_waiter() -> None:
        try:
            with engine_thread():
                while not rt.once(
                    "metta_channel(Id, _Queue), "
                    "message_queue_property(_Queue, waiting(_Count)), _Count > 0",
                    Id=mailbox._handle,
                ):
                    time.sleep(0.001)
            waiter_observed.set()
        except BaseException as failure:
            failures.append(failure)
            waiter_observed.set()

    def evaluate() -> None:
        try:
            answers.extend(metta.eval("(+ 1 2)"))
        except BaseException as failure:
            failures.append(failure)
        finally:
            evaluation_finished.set()

    def release() -> None:
        try:
            with engine_thread():
                mailbox.send(S.release)
        except BaseException as failure:
            failures.append(failure)

    consumer = threading.Thread(target=receive, daemon=True)
    observer = threading.Thread(target=observe_waiter, daemon=True)
    evaluator = threading.Thread(target=evaluate, daemon=True)
    consumer.start()
    observer.start()
    observed = waiter_observed.wait(5)
    if observed and not failures:
        evaluator.start()
        completed_before_release = evaluation_finished.wait(5)
    else:
        completed_before_release = False

    releaser = threading.Thread(target=release, daemon=True)
    releaser.start()
    for worker in (releaser, consumer, observer, evaluator):
        if worker.ident is not None:
            worker.join(5)
    mailbox.close()

    assert observed, "the channel receiver never appeared in SWI's waiter count"
    assert not any(
        worker.is_alive() for worker in (releaser, consumer, observer, evaluator)
    )
    assert failures == []
    assert completed_before_release, "the unrelated evaluation waited for the channel"
    assert answers == [3]
    assert received == [S.release]


def test_parallel_answers_the_same_set_as_superpose(metta):
    """Same branches, same answers; hyperpose only changes the order."""
    with metta._new_space() as space:
        space.run(SQUARE)
        branches = [Expression(S["par-sq"], n) for n in (1, 2, 3, 4)]
        parallel = sorted(str(a) for a in space.parallel(*branches))
        sequential = sorted(
            str(a) for a in space.eval(Expression(S.superpose, Expression(*branches)))
        )
        assert parallel == sequential == ["1", "16", "4", "9"]


def test_parallel_accepts_text_and_atoms(metta):
    """A target is a term or its source text, as everywhere else."""
    with metta._new_space() as space:
        space.run(SQUARE)
        answers = space.parallel(Expression(S["par-sq"], 5), "(par-sq 6)")
        assert sorted(str(a) for a in answers) == ["25", "36"]


def test_parallel_without_targets_answers_nothing(metta):
    """No branches is no answers, and no engine call to find that out."""
    with metta._new_space() as space:
        assert space.parallel() == []


def test_parallel_runs_branches_concurrently(metta):
    """Four branches must all enter a rendezvous before any can return."""
    with metta._new_space() as space:
        rendezvous = threading.Barrier(4, timeout=15)
        worker_threads: set[int] = set()
        worker_threads_lock = threading.Lock()

        @space.op(name="parallel-rendezvous", effect="writesState")
        def meet(branch: int) -> int:
            with worker_threads_lock:
                worker_threads.add(threading.get_ident())
            rendezvous.wait()
            return branch

        branches = [Expression(S["parallel-rendezvous"], branch) for branch in range(4)]
        answers = space.parallel(*branches, timeout=20)

        assert sorted(int(answer.value) for answer in answers) == list(range(4))
        assert len(worker_threads) == 4


def test_parallel_takes_a_timeout_and_has_no_inference_bound(metta):
    """Timeout bounds the call; inferences is deliberately not a parameter."""
    with metta._new_space() as space:
        space.run(SPIN)
        forever = Expression(S["par-spin"], 200_000_000)
        with pytest.raises(TimeLimitError):
            space.parallel(forever, forever, timeout=0.1)

        # An inference bound would count only the calling thread, so it is
        # refused rather than accepted and silently not enforced.
        with pytest.raises(TypeError):
            space.parallel(Expression(S["par-spin"], 1), inferences=1000)


def test_parallel_reports_a_failing_branch(metta):
    """A branch that raises is not swallowed by the concurrency. A wrongly
    typed operand and integer division by zero answer `(Error ...)` rather
    than raising now, so the branch uses a HOST instantiation error.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with metta._new_space() as space:
        space.run(SQUARE)
        with pytest.raises(EngineError):
            space.parallel(Expression(S["par-sq"], 2), "(+ $left $right)")


def test_a_dual_is_built_once_under_concurrency(metta):
    """not-provable builds its dual on first use, and it used to build it once
    per racing thread.

    ensure_dual/3 tested two markers and then built, with nothing between the
    test and the act. Thirty-two calls through a pool of eight left five
    clauses of the dual, five dual_ready facts, four dual_hooks_installed and
    seven seam:function_changed handlers, and the answer came back True
    five times instead of once. The count moved between runs, which is what
    said race rather than off-by-one.

    The duplicated handlers were the worse half: seam:function_changed/1
    is an EVENT hook, so each duplicate ran on every compiled equation
    afterwards, and nothing bounded the growth.

    Asserted against the SERIAL answer rather than against a literal, because
    the claim is that concurrency changes nothing.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
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
