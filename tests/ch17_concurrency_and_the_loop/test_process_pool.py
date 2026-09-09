"""Purpose: metta.parallel.ProcessPool, one booted engine per worker PROCESS.

Guarantees:
  - three programs really run in three worker processes, proved by a
    rendezvous every worker has to reach rather than by a clock [tested:
    test_the_process_pool_runs_three_programs_in_three_workers;
    commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - a worker answers what the same program answers here, which is the
    differential the work unit's double life makes possible: program() is an
    ordinary function in this process too [tested:
    test_a_process_pool_answers_what_the_sequential_run_answers;
    commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - every way of reaching a live engine handle refuses at submit, naming the
    remedy: a closure, a module global, a bound method, and an argument
    [tested: test_a_closure_over_a_space_refuses_at_submit,
    test_a_module_global_space_refuses_at_submit,
    test_a_bound_method_of_a_space_refuses_at_submit,
    test_a_space_argument_refuses_at_submit; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - a handle refuses to cross as an ANSWER too, where no submit-time walk
    could see it [tested: test_a_space_answer_refuses_to_cross; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - a worker whose boot failed says why on its first work unit instead of
    breaking the pool with BrokenProcessPool [tested:
    test_a_worker_that_cannot_boot_says_why; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - fork is refused at construction, and a child that inherited an engine
    anyway refuses at its first crossing with its locks reset [tested:
    test_the_fork_start_method_is_refused_at_construction,
    test_a_forked_child_refuses_the_inherited_engine,
    test_a_fork_resets_the_engine_locks; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import multiprocessing
import os
import subprocess
import sys
import time
from concurrent.futures import Executor
from pathlib import Path

import pytest

from metta import G, S
from metta._errors.errors import MettaError
from metta.parallel import ProcessPool, call, process_pool, program

RULES = "(= (pp-sq $x) (* $x $x))"

#: Every subprocess here is a whole engine boot on a shared box, so the bound
#: is generous; it exists to stop a hung child, not to time anything.
CHILD_SECONDS = 180


def seat_and_run(room: str, seats: int, source: str) -> tuple[int, list]:
    """Take a numbered seat, wait for every seat, then run the program.

    The process-boundary form of test_pool_runs_work_concurrently's barrier.
    A multiprocessing.Barrier cannot travel through a task queue (its
    SemLock refuses to pickle outside process spawning), so the rendezvous
    is a directory every worker can see: this can only answer if `seats`
    workers genuinely run at once, and no amount of background load makes a
    one-worker run pass.
    """
    floor = Path(room)
    (floor / str(os.getpid())).touch()
    limit = time.monotonic() + CHILD_SECONDS
    while len(list(floor.iterdir())) < seats:
        if time.monotonic() > limit:
            msg = f"only {len(list(floor.iterdir()))} of {seats} workers arrived"
            raise TimeoutError(msg)
        time.sleep(0.01)
    return os.getpid(), program(source)


@pytest.fixture(scope="module")
def procs():
    """One three-worker pool for the module: a boot is a whole engine each."""
    pool = process_pool(3, boot=RULES)
    yield pool
    pool.shutdown()


# ------------------------------------------------------------------ structure


def test_the_process_pool_is_an_executor_python_recognises(procs):
    """Not a lookalike: isinstance, the worker count, and the shape it reports."""
    assert isinstance(procs, Executor)
    assert procs.workers == 3
    assert len(procs) == 3
    assert not procs.closed
    assert repr(procs) == "<ProcessPool workers=3 live>"


def test_the_process_pool_runs_three_programs_in_three_workers(procs, tmp_path):
    """The claim the pool exists for, asserted without a clock."""
    room = tmp_path / "seats"
    room.mkdir()
    landed = list(
        procs.starmap(
            seat_and_run,
            [(str(room), 3, f"!(pp-sq {n})") for n in (3, 4, 5)],
        )
    )
    pids = [pid for pid, _ in landed]
    assert len(set(pids)) == 3, f"three programs shared {len(set(pids))} workers"
    assert [answers for _, answers in landed] == [[[G(9)]], [[G(16)]], [[G(25)]]]
    assert os.getpid() not in pids


def test_a_process_pool_answers_what_the_sequential_run_answers(metta, procs):
    """The differential oracle: program() is an ordinary function here too."""
    # One head per text: both sides accumulate equations in whatever space
    # they land in, so a shared head would compare a worker that saw one
    # definition against a parent that saw three.
    texts = [f"(= (pp-oracle{n} $x) (+ $x {n}))\n!(pp-oracle{n} 10)" for n in (1, 2, 3)]
    here = metta._new_space()
    sequential = [here.run(text) for text in texts]
    assert list(procs.map(program, texts)) == sequential


def test_a_call_applies_a_head_the_boot_defined(procs):
    """boot= compiles the head once per worker, not once per task."""
    assert list(procs.starmap(call, [(S.pp_sq, 3), ("pp-sq", 4)])) == [[G(9)], [G(16)]]


def test_imap_unordered_yields_every_program(procs):
    """Completion order across processes still yields every answer."""
    landed = sorted(
        str(groups) for groups in procs.imap_unordered(program, ["!(pp-sq 6)", "!(pp-sq 7)"])
    )
    assert landed == ["[[Grounded(36)]]", "[[Grounded(49)]]"]


def test_boot_seconds_reports_a_started_worker(procs):
    """The cost is data, not a claim in a docstring."""
    list(procs.map(program, ["!(pp-sq 2)"]))
    boots = procs.boot_seconds
    assert boots, "no worker reported its boot"
    assert all(seconds > 0 for seconds in boots.values())
    assert all(pid != os.getpid() for pid in boots)


# ------------------------------------------------------------------- refusals


def test_a_closure_over_a_space_refuses_at_submit(metta, procs):
    """The hazard is not that the handle fails to cross; it is that it does."""
    space = metta._new_space()

    def work(n):
        return space.run(f"!(+ {n} 1)")

    with pytest.raises(MettaError, match=r"worker process has its own engine"):
        procs.submit(work, 1)


def test_a_module_global_space_refuses_at_submit(metta, procs):
    """A module-level handle is a GLOBAL, not a closure cell, and is still seen."""
    namespace = {"kb": metta._new_space()}
    # A def in a namespace rather than at module level: a module-level handle
    # here would boot an engine on import, and the case under test is exactly
    # a function whose __globals__ hold one.
    exec("def work(n):\n    return kb.run(f'!(+ {n} 1)')", namespace)
    with pytest.raises(MettaError, match=r"worker process has its own engine"):
        procs.submit(namespace["work"], 1)


def test_a_bound_method_of_a_space_refuses_at_submit(metta, procs):
    """It pickles, which is exactly why refusing it is the only safe reading."""
    space = metta._new_space()
    with pytest.raises(MettaError, match=r"pickles by NAME"):
        procs.submit(space.run, "!(+ 1 1)")


def test_a_space_argument_refuses_at_submit(metta, procs):
    """An argument reaches the worker as surely as a closure does."""
    space = metta._new_space()
    with pytest.raises(MettaError, match=r"worker process has its own engine"):
        procs.submit(call, S.pp_sq, space)


def test_a_space_answer_refuses_to_cross(procs):
    """No submit-time walk can see an answer, so the work unit checks its own."""
    with pytest.raises(MettaError, match=r"handle on live engine state"):
        list(procs.map(program, ["!(new-space)"]))


def test_a_handle_argument_refuses_before_it_is_evaluated(metta):
    """call() refuses a handle in this process too: one rule, both sides."""
    with pytest.raises(MettaError, match=r"handle on live engine state"):
        call(S.pp_sq, metta._new_space())


def test_a_work_unit_names_its_space_and_never_carries_one(metta):
    """The three shapes a work unit refuses, each naming what it wanted."""
    with pytest.raises(TypeError, match=r"names its space, it does not carry one"):
        program("!(+ 1 1)", space=metta._new_space())
    with pytest.raises(TypeError, match=r"by symbol or by exact string"):
        program("!(+ 1 1)", space=3)
    with pytest.raises(TypeError, match=r"names its head by symbol or by string"):
        call(3)


def test_a_worker_that_cannot_boot_says_why():
    """A failed boot must not read as BrokenProcessPool with no cause."""
    with process_pool(1, boot="(this is not (") as broken:
        with pytest.raises(MettaError, match=r"engine did not boot"):
            list(broken.map(program, ["!(+ 1 1)"]))
        # The worker survived to say it again rather than taking the pool down.
        with pytest.raises(MettaError, match=r"engine did not boot"):
            list(broken.map(program, ["!(+ 2 2)"]))


def test_the_fork_start_method_is_refused_at_construction():
    """Refused before a worker exists, because no worker of one could be sound."""
    with pytest.raises(MettaError, match=r"cannot use the fork start method"):
        ProcessPool(2, mp_context=multiprocessing.get_context("fork"))


def test_the_pool_refuses_a_shape_it_cannot_hold():
    """Worker count and boot text are checked before any process starts."""
    with pytest.raises(TypeError, match=r"workers must be an int"):
        ProcessPool("two")
    with pytest.raises(ValueError, match=r"at least one worker"):
        ProcessPool(0)
    with pytest.raises(TypeError, match=r"boot is MeTTa program text"):
        ProcessPool(1, boot=["(= (f) 1)"])


# ------------------------------------------------------------------- the fork


def _run_child_script(source: str, tmp_path: Path) -> subprocess.CompletedProcess:
    """Run one single-threaded interpreter, from a FILE, that forks on purpose.

    A subprocess rather than a fork of the test session: forking a
    multi-threaded interpreter is what this is ABOUT, and doing it inside
    pytest would fork its reporter, its timeout thread and its captured file
    descriptors along with the engine.

    A file rather than `python -c`, because a `-c` program has no path and
    the fork server preloads `__main__` only when it has one to import
    [measured 2026-09-07: the same script refused under a file and answered
    normally under -c].
    """
    root = Path(__file__).resolve().parents[4]
    script = tmp_path / "ai-forking-child.py"
    script.write_text(source, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        env=os.environ | {"PYTHONPATH": str(root / "extensions" / "python")},
        capture_output=True,
        text=True,
        timeout=CHILD_SECONDS,
        check=False,
    )


FORK_REFUSAL_SCRIPT = """
import os, select, sys
import metta
from metta._binding.runtime import forked
metta.run("!(+ 1 2)")
assert not forked(), "the parent must not think it was forked"
read, write = os.pipe()
if os.fork() == 0:
    os.close(read)
    try:
        answers = metta.run("!(+ 3 4)")
        os.write(write, f"ANSWERED {answers}".encode()[:900])
        os._exit(1)
    except BaseException as exc:
        os.write(write, f"{type(exc).__name__}|{forked()}|{exc}".encode()[:900])
        os._exit(0)
os.close(write)
ready, _, _ = select.select([read], [], [], 60)
said = os.read(read, 8192).decode() if ready else "HUNG"
status = os.waitpid(-1, 0)[1]
print(said)
print("EXIT", os.waitstatus_to_exitcode(status))
print("PARENT STILL WORKS", metta.run("!(+ 5 5)"))
"""


def test_a_forked_child_refuses_the_inherited_engine(tmp_path):
    """The refusal fires in the child, and the parent is untouched by it."""
    done = _run_child_script(FORK_REFUSAL_SCRIPT, tmp_path)
    assert done.returncode == 0, done.stderr
    assert "EngineError|True|" in done.stdout, done.stdout
    assert "inherited a Prolog engine across fork()" in done.stdout
    assert "forkserver" in done.stdout
    assert "EXIT 0" in done.stdout
    assert "PARENT STILL WORKS [[Grounded(10)]]" in done.stdout


LOCK_RESET_SCRIPT = '\nimport os, select, threading\nimport metta\nimport metta._binding.runtime as _engine\nmetta.run("!(+ 1 2)")\nheld = _engine._LOCK\nheld.acquire()                      # the home thread holds it across the fork\n_engine._DEFERRED_WORK.append(("erase", 12345))\nread, write = os.pipe()\n\ndef fork_from_another_thread():\n    if os.fork() == 0:\n        os.close(read)\n        free = _engine._LOCK.acquire(blocking=False)\n        consult = _engine.CONSULT_LOCK.acquire(blocking=False)\n        drained = len(_engine._DEFERRED_WORK)\n        fresh = _engine._LOCK is not held\n        os.write(write, f"{free}|{consult}|{drained}|{fresh}".encode())\n        os._exit(0)\n\nthread = threading.Thread(target=fork_from_another_thread)\nthread.start()\nthread.join(60)\nos.close(write)\nready, _, _ = select.select([read], [], [], 60)\nprint(os.read(read, 256).decode() if ready else "HUNG")\nos.waitpid(-1, 0)\nheld.release()\n'


def test_a_fork_resets_the_engine_locks(tmp_path):
    """Without the reset the child would deadlock before reaching the refusal.

    The parent holds the engine lock on its home thread and forks from a
    SECOND thread, so the child inherits a lock whose holder no longer
    exists. A child that could not take it would never reach the refusal
    above; it would hang on the first crossing.
    """
    done = _run_child_script(LOCK_RESET_SCRIPT, tmp_path)
    assert done.returncode == 0, done.stderr
    assert "True|True|0|True" in done.stdout, done.stdout


IMPORT_TIME_BOOT_SCRIPT = """
import metta
from metta.parallel import process_pool, program

metta.run("!(+ 1 2)")                    # a boot at IMPORT time: the trap

if __name__ == "__main__":
    with process_pool(1) as pool:
        try:
            list(pool.map(program, ["!(+ 1 1)"]))
            print("NO REFUSAL")
        except Exception as exc:
            print("REFUSED", exc)
"""


def test_a_forkserver_worker_that_inherited_an_engine_says_so(tmp_path):
    """The one trap a user meets, named with the edit that fixes it.

    forkserver runs __main__ once in its server and forks workers from it,
    so an engine booted at import time is booted THERE and inherited.
    """
    if "forkserver" not in multiprocessing.get_all_start_methods():
        pytest.skip("this platform has no forkserver start method")
    done = _run_child_script(IMPORT_TIME_BOOT_SCRIPT, tmp_path)
    assert done.returncode == 0, done.stderr
    assert "REFUSED" in done.stdout, done.stdout
    assert "inherited a Prolog engine from the fork server" in done.stdout
    assert '__main__' in done.stdout
    assert "spawn" in done.stdout
