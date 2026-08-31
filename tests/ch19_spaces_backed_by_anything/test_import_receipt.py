"""Purpose: verify dependency-validated source-import receipts through public doors.

Assumes: ``lib_thread`` supplies the two ``take-atom`` equations and anonymous
space names are recycled after ``drop()``. Guarantees: a receipt is reusable
only while its exact source load, digest, and stored outputs remain live.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

import metta
from metta import MeTTa, S, V
from metta._engine import bridge
from metta.errors import MettaSyntaxError


def quote(value: str) -> str:
    """Quote an atom for a diagnostic Prolog goal."""
    return "'" + value.replace("'", "''") + "'"


def import_thread(space) -> None:
    """Import the shipped Linda library through MeTTa's public import form."""
    answers = space.eval(S["import!"](space, S.library(S["lib_thread"])))
    assert [str(answer) for answer in answers] == ["True"]


def take_call(target):
    """Build the timed call used by both direct and compiled execution doors."""
    return S["take-atom"](target, S.job(V.state), metta.Grounded(2.0))


def thread_state(space) -> dict:
    """Read the receipt, source payload, compiled clauses, and registry together."""
    return bridge().query_once(
        "user:import_receipt(Space, Canon, _, _), "
        "file_base_name(Canon, 'lib_thread.metta'), "
        "findall(_ReceiptLoad, user:import_receipt(Space, Canon, _ReceiptLoad, _Digest), _Receipts), "
        "length(_Receipts, ReceiptCount), "
        "(user:import_receipt(Space, Canon, ReceiptLoadId, _) -> true ; ReceiptLoadId = none), "
        "(user:import_receipt_current(Space, Canon) -> ReceiptCurrent = true ; ReceiptCurrent = false), "
        "aggregate_all(count, filereader:metta_source_load(Canon, Space, _, _), SourceLoads), "
        "(ReceiptLoadId == none -> StoredOutputs = 0 ; "
        " aggregate_all(count, filereader:source_load_assertion(ReceiptLoadId, stored, _), StoredOutputs)), "
        "aggregate_all(count, user:'get-atoms'(Space, [=, ['take-atom'|_], _]), StoredEquations), "
        "user:space_module(Space, _Module), "
        # Deferred translation holds a source's clauses until first use, so
        # the clause counts below are read through the engine's own force
        # door; a removed contribution has no rows to force and stays 0.
        "user:metta_ensure_compiled('take-atom'), "
        "functor(_Binary, 'take-atom', 3), "
        "functor(_Timed, 'take-atom', 4), "
        "aggregate_all(count, (clause(_Module:_Binary, _, _BinaryRef), "
        " clause_property(_BinaryRef, module(_Module))), BinaryClauses), "
        "aggregate_all(count, (clause(_Module:_Timed, _, _TimedRef), "
        " clause_property(_TimedRef, module(_Module))), TimedClauses), "
        "(user:fun_in(_Module, 'take-atom') -> FunctionCurrent = true ; FunctionCurrent = false)",
        {"Space": space.name},
    )


def assert_thread_loaded(state: dict) -> None:
    """Assert every layer agrees that the library contribution is current."""
    assert state["ReceiptCount"] == 1
    assert state["ReceiptCurrent"] == "true"
    assert state["SourceLoads"] == 1
    assert state["StoredOutputs"] >= 2
    assert state["StoredEquations"] == 2
    assert state["BinaryClauses"] == 1
    assert state["TimedClauses"] == 1
    assert state["FunctionCurrent"] == "true"


def remove_exact(space) -> int:
    """Remove the two exact source equations through ``Space.remove``."""
    equations = (
        S["="](
            S["take-atom"](V.space, V.pattern),
            S["space_take"](V.space, V.pattern),
        ),
        S["="](
            S["take-atom"](V.space, V.pattern, V.seconds),
            S["space_take"](V.space, V.pattern, V.seconds),
        ),
    )
    assert [space.remove(equation) for equation in equations] == [True, True]
    return 2


def remove_wildcard(space) -> int:
    """Remove the same equations through bound-head wildcard patterns."""
    patterns = (
        S["="](S["take-atom"](V.space, V.pattern), V.body),
        S["="](S["take-atom"](V.space, V.pattern, V.seconds), V.body),
    )
    assert [space.remove(pattern) for pattern in patterns] == [True, True]
    return 2


def withdraw_source(space) -> int:
    """Withdraw the exact committed load while intentionally retaining its receipt."""
    state = thread_state(space)
    result = bridge().query_once(
        "filereader:withdraw_source_load(Canon, Space, Count)",
        {"Canon": state["Canon"], "Space": space.name},
    )
    assert result["Count"] > 0
    return result["Count"]


REMOVALS = {
    "exact": remove_exact,
    "wildcard": remove_wildcard,
    "withdraw": withdraw_source,
}


@pytest.mark.parametrize("scope", ["own", "self"])
@pytest.mark.parametrize("removal", ["exact", "wildcard", "withdraw"])
def test_public_import_rebuilds_when_a_receipt_dependency_disappears(
    scope: str, removal: str
) -> None:
    """Two scopes crossed with three removals invalidate and rebuild one receipt."""
    context = MeTTa()
    target = context.space()
    owner = target if scope == "own" else context.self
    wrapper = f"c2-receipt-wrapper-{uuid.uuid4().hex}"
    try:
        import_thread(owner)
        assert_thread_loaded(thread_state(owner))

        target.add(S["="](S[wrapper](), take_call(target)))
        direct_before = S.job(S.direct_before)
        target.add(direct_before)
        assert target.eval(take_call(target)) == [direct_before]
        compiled_before = S.job(S.compiled_before)
        target.add(compiled_before)
        assert target.eval(S[wrapper]()) == [compiled_before]

        assert REMOVALS[removal](owner) > 0
        removed = thread_state(owner)
        assert removed["ReceiptCount"] == 1
        assert removed["ReceiptCurrent"] == "false"
        assert removed["SourceLoads"] == (0 if removal == "withdraw" else 1)
        assert removed["StoredEquations"] == 0
        assert removed["BinaryClauses"] == 0
        assert removed["TimedClauses"] == 0
        assert removed["FunctionCurrent"] == "false"

        import_thread(owner)
        assert_thread_loaded(thread_state(owner))
        direct_after = S.job(S.direct_after)
        target.add(direct_after)
        assert target.eval(take_call(target)) == [direct_after]
        compiled_after = S.job(S.compiled_after)
        target.add(compiled_after)
        assert target.eval(S[wrapper]()) == [compiled_after]
    finally:
        try:
            import_thread(owner)
        finally:
            if scope == "self":
                withdraw_source(owner)
            target.drop()


def test_repeat_import_reuses_one_current_receipt_without_duplication() -> None:
    """An unchanged same-life import keeps its load id and every output count."""
    context = MeTTa()
    target = context.space()
    try:
        import_thread(target)
        before = thread_state(target)
        assert_thread_loaded(before)
        import_thread(target)
        after = thread_state(target)
        assert_thread_loaded(after)
        assert after["ReceiptLoadId"] == before["ReceiptLoadId"]
        assert after["StoredOutputs"] == before["StoredOutputs"]
    finally:
        target.drop()


def test_clear_invalidates_the_space_life_and_reimport_builds_a_new_receipt() -> None:
    """A clear leaves the historical receipt unusable until public reimport."""
    context = MeTTa()
    target = context.space()
    try:
        import_thread(target)
        before = thread_state(target)
        target.clear()
        cleared = thread_state(target)
        assert cleared["ReceiptCount"] == 1
        assert cleared["ReceiptCurrent"] == "false"
        assert cleared["SourceLoads"] == 0
        assert cleared["StoredEquations"] == 0

        import_thread(target)
        after = thread_state(target)
        assert_thread_loaded(after)
        assert after["ReceiptLoadId"] != before["ReceiptLoadId"]
    finally:
        target.drop()


def test_failed_reload_restores_the_previous_receipt_and_definitions(
    tmp_path: Path,
) -> None:
    """A failed replacement restores its load id and executable payload."""
    context = MeTTa()
    target = context.space()
    function = f"c2-receipt-reload-{uuid.uuid4().hex}"
    source = tmp_path / "receipt_reload.metta"
    original = f"(= ({function}) 1)\n"
    source.write_text(original)
    try:
        target.load(source)
        canon = str(source.resolve())
        before = bridge().query_once(
            "user:import_receipt(Space, Canon, LoadId, _)",
            {"Space": target.name, "Canon": canon},
        )
        source.write_text(f"(= ({function}) 2)\n(= (broken\n")
        with pytest.raises(MettaSyntaxError):
            target.load(source)
        restored = bridge().query_once(
            "user:import_receipt(Space, Canon, LoadId, _), "
            "filereader:metta_source_load(Canon, Space, LoadId, _)",
            {"Space": target.name, "Canon": canon},
        )
        assert restored["LoadId"] == before["LoadId"]
        assert [str(atom) for atom in target.eval(S[function]())] == ["1"]

        source.write_text(original)
        current = bridge().query_once(
            "(user:import_receipt_current(Space, Canon) -> Current = true ; Current = false)",
            {"Space": target.name, "Canon": canon},
        )
        assert current["Current"] == "true"
    finally:
        target.drop()


def test_remove_and_refill_commit_does_not_late_abolish_the_refill() -> None:
    """A committed remove-plus-refill leaves the replacement callable."""
    context = MeTTa()
    target = context.space()
    function = f"c2-receipt-refill-{uuid.uuid4().hex}"
    space = quote(str(target.name))
    name = quote(function)
    try:
        target.add(S["="](S[function](), S.ready))
        bridge().query_once(
            "transaction((user:metta_remove_atom("
            f"{space}, [=, [{name}], ready], true), "
            f"user:metta_add_atom({space}, [=, [{name}], ready], true))), "
            "user:metta_repair_emptied_shadows, R = committed"
        )
        assert target.eval(S[function]()) == [S.ready]
    finally:
        target.drop()


def acquire_recycled(context, pooled_name):
    """Acquire spaces until the pool hands the dropped name back.

    Sibling tests in one process leave their own dropped names in the shared
    pool, so the next acquisition is not necessarily the one just dropped.
    The pool is finite and the dropped name must resurface, so a bounded
    hunt is deterministic where a single acquisition is order-fragile.
    """
    extras = []
    try:
        for _ in range(64):
            candidate = context.space()
            if candidate.name == pooled_name:
                return candidate, extras
            extras.append(candidate)
    except Exception:
        for extra in extras:
            extra.drop()
        raise
    for extra in extras:
        extra.drop()
    msg = f"pool never recycled {pooled_name}"
    raise AssertionError(msg)


def test_recycled_target_module_contains_no_previous_life_forms() -> None:
    """Dropping and recycling a space name removes its equation and call cache."""
    context = MeTTa()
    function = f"c2-receipt-recycle-{uuid.uuid4().hex}"
    first = context.space()
    pooled_name = first.name
    first.add(S["="](S[function](), S.old_life))
    assert first.eval(S[function]()) == [S.old_life]
    first.drop()

    second, extras = acquire_recycled(context, pooled_name)
    try:
        assert second.name == pooled_name
        module = quote(f"$metta_exec:{second.name}")
        cached = bridge().query_once(
            "aggregate_all(count, "
            f"translator:translated_form_cache({module}, _, _, [{quote(function)}], _, _), "
            "Count)"
        )
        assert cached["Count"] == 0
        assert [str(atom) for atom in second.eval(S[function]())] == [f"({function})"]
    finally:
        second.drop()
        for extra in extras:
            extra.drop()


def test_recycled_module_rearms_a_saved_call_to_an_inherited_definition() -> None:
    """A saved call survives local-shadow removal without a dangling procedure."""
    context = MeTTa()
    function = f"c2-shadow-recycle-{uuid.uuid4().hex}"
    saved = f"c2-saved-shadow-{uuid.uuid4().hex}"
    parent_equation = S["="](S[function](), S.parent)
    child_equation = S["="](S[function](), S.child)
    first = context.space()
    pooled_name = first.name
    context.self.add(parent_equation)
    first.add(child_equation)
    module = quote(f"$metta_exec:{first.name}")
    try:
        asserted = bridge().query_once(
            f"assertz((user:{quote(saved)}(_Answer) :- "
            f"{module}:{quote(function)}(_Answer))), R = asserted"
        )
        assert asserted["R"] == "asserted"
        assert bridge().query_once(
            f"findall(_Value, user:{quote(saved)}(_Value), Rows)"
        )["Rows"] == ["child"]

        first.drop()
        first_dropped = True
        second, extras = acquire_recycled(context, pooled_name)
        try:
            assert second.name == pooled_name
            assert bridge().query_once(
                f"findall(_Value, user:{quote(saved)}(_Value), Rows)"
            )["Rows"] == ["parent"]
            assert second.eval(S[function]()) == [S.parent]
        finally:
            second.drop()
            for extra in extras:
                extra.drop()
    finally:
        bridge().query_once(f"abolish(user:{quote(saved)}/1), R = cleared")
        if not first_dropped:
            first.drop()
        context.self.remove(parent_equation)


def test_saved_goal_runs_after_public_reimport_repairs_its_source() -> None:
    """A goal translated before removal sees reloaded clauses, never Unknown procedure."""
    context = MeTTa()
    target = context.space()
    module = quote(f"$metta_exec:{target.name}")
    binary = S["="](
        S["take-atom"](V.space, V.pattern),
        S["space_take"](V.space, V.pattern),
    )
    timed = S["="](
        S["take-atom"](V.space, V.pattern, V.seconds),
        S["space_take"](V.space, V.pattern, V.seconds),
    )
    try:
        import_thread(target)
        job = S.job(S.ready)
        target.add(job)
        assert target.eval(take_call(target)) == [job]
        # The cached entry is a TEMPLATE, not this call: translation_template/3
        # abstracts a literal argument into a variable so one compiled form
        # serves every literal, and translated_form_hit/5 instantiates it by
        # unifying the stored source with the call. So the source is saved
        # beside the goals and unified here for the same reason, or the goals
        # run with an unbound seconds argument and the engine says so
        # ("Arguments are not sufficiently instantiated") before ever reaching
        # the clauses this test is about.
        saved = target.runtime.once(
            "retractall(user:c2_receipt_saved(_, _, _, _)), "
            f"translator:translated_form_cache({module}, _Key, _Id, _Source, _Goals, _Out), "
            "_Source = ['take-atom'|_Args], "
            f"assertz(user:c2_receipt_saved({module}, _Source, _Goals, _Out)), !, R = saved"
        )
        assert saved["R"] == "saved"
        assert target.remove(binary)
        assert target.remove(timed)
        import_thread(target)
        result = target.runtime.once(
            "user:c2_receipt_saved(_Module, _Source, _Goals, _Out), "
            f"_Source = ['take-atom', {quote(target.name)}, [job, _State], 2.0], "
            "user:metta_py_call_goals(_Module, _Goals), R = _Out"
        )
        assert result is not None
    finally:
        target.runtime.once("retractall(user:c2_receipt_saved(_, _, _, _)), R = cleared")
        try:
            import_thread(target)
        finally:
            target.drop()
