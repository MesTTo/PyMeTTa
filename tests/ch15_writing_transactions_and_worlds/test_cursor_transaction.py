"""Purpose: keep cursor and function work inside its creating transaction.

Guarantees:
  - installer imports are visible at once and disappear on rollback
    [tested: test_installer_imports_into_home_and_staging_are_visible,
    test_failed_installer_imports_leave_no_equations; commit=WORKTREE].
  - every read door sees earlier writes and cursor writes in the same unit
    [tested: test_answers_and_fn_see_the_transactions_writes,
    test_cursor_transactions_preserve_the_bag; commit=WORKTREE].
  - held cursors refuse another thread and outside cursors remain lazy
    [tested: test_held_cursor_refuses_a_pull_from_another_thread,
    test_outside_cursor_is_lazy_and_keeps_its_logical_update_view;
    commit=WORKTREE].
  - capture, nested policies and both bounds retain their contracts
    [tested: test_held_capture_delivers_all_output_on_the_first_pull,
    test_held_atomic_work_dies_with_outer_rollback,
    test_held_speculation_returns_all_answers_without_writes,
    test_cursor_inference_budget_refuses_inside_and_outside,
    test_cursor_time_budget_refuses_inside_and_outside; commit=WORKTREE].
Owns resources: tests close spaces and views, unregister their library aliases
  and operations, and join the one worker used to test thread ownership.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from types import SimpleNamespace

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import metta as metta_package
from metta import S, V, lib, testing
from metta._engine import engine_thread
from metta.atoms import TRUE
from metta.errors import EngineError, InferenceLimitError, TimeLimitError
from metta.integrate import installed, integrate


@pytest.fixture
def cursor_library(tmp_path):
    """One immutable source directory, shared by the reads in a test."""
    (tmp_path / "hello.metta").write_text(
        "(= (txcursor-hello) 42)\n", encoding="utf-8"
    )
    yield tmp_path
    metta_package.engine().runtime.must(
        "retractall(user:file_search_path(Alias, Directory))",
        Alias="txcursor-fixture",
        Directory=str(tmp_path),
    )


def import_fixture(space, directory):
    """Import through the function cursor used by the library descriptor."""
    space.register_library_path(directory, "txcursor-fixture")
    space.add(lib(S.library(S.txcursor_fixture, S["hello.metta"])))


def assert_library_visible(space):
    """Equation storage, matching and all evaluation doors agree."""
    equation = S["="](S["txcursor-hello"](), 42)
    assert equation in space.atoms()
    testing.assert_answers(
        space.match(S["="](S["txcursor-hello"](), V.value)).value, [42]
    )
    testing.assert_answers(space.eval(S["txcursor-hello"]()), [42])
    with space.answers(S["txcursor-hello"]()) as answers:
        testing.assert_answers(answers, [42])
    with space.fn["txcursor-hello"]() as answers:
        testing.assert_answers(answers, [42])


def assert_reads(space, expected):
    """Compare answer bags through three independent public doors."""
    pattern = S["txcursor-item"](V.value)
    target = S.match(space, pattern, V.value)
    testing.assert_answers(space.eval(target), expected)
    with space.answers(target) as answers:
        testing.assert_answers(answers, expected)
    with space.fn.match(space, pattern, V.value) as answers:
        testing.assert_answers(answers, expected)


def test_installer_imports_into_home_and_staging_are_visible(metta, cursor_library):
    """An installer reads its home and a space it creates before commit."""
    with ExitStack() as spaces:
        home = spaces.enter_context(metta._new_space())
        staging_spaces = []

        def install(space):
            import_fixture(space, cursor_library)
            staging = spaces.enter_context(metta_package.space())
            staging_spaces.append(staging)
            staging.register_library_path(cursor_library, "txcursor-fixture")
            staging += lib(S.library(S.txcursor_fixture, S["hello.metta"]))
            assert_library_visible(space)
            assert_library_visible(staging)

        integration = SimpleNamespace(
            __name__="txcursor_success", install_metta=install
        )
        assert integrate(home, integration) == "txcursor_success"
        assert_library_visible(home)
        assert_library_visible(staging_spaces[0])
        assert (home.name, "txcursor_success") in installed()


def test_failed_installer_imports_leave_no_equations(metta, cursor_library):
    """Both imported programs and the installation receipt roll back."""
    with metta._new_space() as home, metta_package.space() as staging:
        before = home.atoms(), staging.atoms()

        def install(space):
            import_fixture(space, cursor_library)
            import_fixture(staging, cursor_library)
            assert_library_visible(space)
            assert_library_visible(staging)
            message = "discard cursor imports"
            raise RuntimeError(message)

        integration = SimpleNamespace(
            __name__="txcursor_failure", install_metta=install
        )
        with pytest.raises(RuntimeError, match="discard cursor imports"):
            integrate(home, integration)
        assert (home.atoms(), staging.atoms()) == before
        for space in (home, staging):
            assert not space.is_function("txcursor-hello")
            testing.assert_answers(
                space.eval(S["txcursor-hello"]()), [S["txcursor-hello"]()]
            )
            assert not space.match(S["="](S["txcursor-hello"](), V.value))
        assert (home.name, "txcursor_failure") not in installed()


def test_answers_and_fn_see_the_transactions_writes(metta):
    """Cursor writes are immediately visible through every read door."""
    with metta._new_space() as space:
        def write():
            space.add(S["txcursor-item"](1))
            assert_reads(space, [1])
            with space.answers(S["add-atom"](space, S["txcursor-item"](2))) as answers:
                assert answers.one() is True
            assert_reads(space, [1, 2])
            assert space.fn["add-atom"](space, S["txcursor-item"](3)).one() is True
            assert_reads(space, [1, 2, 3])

        space.transaction(write)
        assert_reads(space, [1, 2, 3])


@pytest.mark.parametrize("rollback", [False, True])
def test_held_cursor_refuses_a_pull_from_another_thread(metta, rollback):
    """Refusal releases rows even when the caller catches it and commits."""
    with metta._new_space() as space:
        counts = (
            "aggregate_all(count, metta_host_held_position(_,_,_), Positions), "
            "aggregate_all(count, metta_host_held_row(_,_,_,_), Rows)"
        )
        before = metta.runtime.must(counts)
        remedy = (
            "step it from the transaction's thread, or open it outside the transaction"
        )

        def read_elsewhere(iterator):
            with engine_thread():
                return next(iterator)

        def work():
            with space.answers("(superpose (1 2 3))") as answers:
                iterator = iter(answers)
                assert next(iterator) == 1
                with ThreadPoolExecutor(max_workers=1) as worker:
                    try:
                        worker.submit(read_elsewhere, iterator).result()
                    except EngineError as error:
                        assert remedy in str(error)
                        if rollback:
                            raise
                    else:
                        pytest.fail("a held cursor was stepped by another thread")

        if rollback:
            with pytest.raises(EngineError, match=remedy):
                space.transaction(work)
        else:
            space.transaction(work)
        assert metta.runtime.must(counts) == before


def test_outside_cursor_is_lazy_and_keeps_its_logical_update_view(metta):
    """A read starts on demand, then retains the active clause enumeration."""
    with metta._new_space() as space:
        space.add(S["txcursor-item"](1), S["txcursor-item"](2))
        target = S.match(space, S["txcursor-item"](V.value), V.value)
        with space.answers(target) as answers:
            space.add(S["txcursor-item"](3))
            iterator = iter(answers)
            assert next(iterator) == 1
            space.add(S["txcursor-item"](4))
            testing.assert_answers(iterator, [2, 3])
        assert_reads(space, [1, 2, 3, 4])


def test_held_capture_delivers_all_output_on_the_first_pull(metta, capsys):
    """Opening eagerly captures the entire enumeration exactly once."""
    with metta._new_space() as space:
        def work():
            with space.capture() as output:
                with space.answers(
                    "(superpose ((println! txcursor-one) (println! txcursor-two)))"
                ) as answers:
                    iterator = iter(answers)
                    assert next(iterator) == TRUE
                    assert output.text == "txcursor-one\ntxcursor-two\n"
                    assert next(iterator) == TRUE
                    assert list(iterator) == []
                    assert output.text == "txcursor-one\ntxcursor-two\n"

        space.transaction(work)
    assert capsys.readouterr().out == ""


def test_held_atomic_work_dies_with_outer_rollback(metta):
    """A nested atomic cursor commits only relative to its outer transaction."""
    with metta._new_space() as space:
        def work():
            with space.atomic():
                assert space.answers(
                    S["add-atom"](space, S["txcursor-item"](1))
                ).one() is True
            assert_reads(space, [1])
            message = "discard nested cursor"
            raise RuntimeError(message)

        with pytest.raises(RuntimeError, match="discard nested cursor"):
            space.transaction(work)
        assert_reads(space, [])


def test_held_speculation_returns_all_answers_without_writes(metta):
    """A speculative cursor retains both answers and discards both writes."""
    with metta._new_space() as space:
        def work():
            with space.speculative():
                with space.answers(
                    "(superpose ((add-atom &self (txcursor-item 1)) "
                    "(add-atom &self (txcursor-item 2))))"
                ) as answers:
                    testing.assert_answers(answers, [True, True])
            assert_reads(space, [])

        space.transaction(work)
        assert_reads(space, [])


@pytest.mark.parametrize("inside", [False, True])
def test_cursor_inference_budget_refuses_inside_and_outside(metta, inside):
    """The same reserved inference refusal bounds either cursor shape."""
    with metta._new_space() as space:
        space.run(
            "(= (txcursor-burn $n) "
            "(if (== $n 0) 0 (txcursor-burn (- $n 1))))"
        )

        def work():
            with space.answers(S["txcursor-burn"](10000), inferences=500) as answers:
                next(iter(answers))

        with pytest.raises(InferenceLimitError):
            space.transaction(work) if inside else work()


@pytest.mark.parametrize("inside", [False, True])
def test_cursor_time_budget_refuses_inside_and_outside(metta, inside):
    """An answer arriving after its deadline refuses in either shape."""
    with metta._new_space() as space:
        @space.op(name="txcursor-pause", effect="oracleIO")
        def pause() -> int:
            time.sleep(0.02)
            return 1

        def work():
            with space.answers(S["txcursor-pause"](), timeout=0.001) as answers:
                next(iter(answers))

        try:
            with pytest.raises(TimeLimitError):
                space.transaction(work) if inside else work()
        finally:
            space.unregister_op("txcursor-pause")


@settings(
    max_examples=40,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    history=st.lists(
        st.tuples(st.sampled_from(["add", "remove"]), st.integers(0, 4),
                  st.sampled_from(["storage", "answers", "fn"])),
        max_size=12,
    ),
    import_at=st.integers(0, 12),
    rollback=st.booleans(),
)
def test_cursor_transactions_preserve_the_bag(cursor_library, history, import_at, rollback):
    """Generated histories preserve bags, read agreement and rollback.

    The source fixture is immutable. Every generated case owns a fresh space,
    so no fixture state is carried from one history to the next.
    """
    with metta_package.space() as space:
        space.add(S["txcursor-item"](0), S["txcursor-item"](0))
        before = space.atoms()
        expected = [0, 0]
        operations = list(history)
        operations.insert(import_at % (len(operations) + 1), ("import", 0, "fn"))

        def work():
            imported = False
            for action, value, door in operations:
                if action == "import":
                    import_fixture(space, cursor_library)
                    imported = True
                else:
                    atom = S["txcursor-item"](value)
                    if door == "storage":
                        space.add(atom) if action == "add" else space.remove(atom)
                    else:
                        head = "add-atom" if action == "add" else "subtract-atom"
                        answers = (
                            space.answers(S[head](space, atom))
                            if door == "answers" else space.fn[head](space, atom)
                        )
                        with answers:
                            answers.one()
                    if action == "add":
                        expected.append(value)
                    elif value in expected:
                        expected.remove(value)
                assert_reads(space, expected)
                if imported:
                    assert_library_visible(space)
            if rollback:
                message = "discard generated history"
                raise RuntimeError(message)

        if rollback:
            with pytest.raises(RuntimeError, match="discard generated history"):
                space.transaction(work)
            testing.assert_answers(space.atoms(), before)
            assert_reads(space, [0, 0])
            assert not space.is_function("txcursor-hello")
        else:
            space.transaction(work)
            assert_reads(space, expected)
            assert_library_visible(space)
