"""Purpose: pin independent evaluation and dispatch axes at the binding.

Guarantees: batch fuel policy, deferred compilation costs, cumulative tagged
guards, inverse cardinality, context lifetime and wide projection preserve
their boundary contracts; releasing the compilation observer retains every
earlier call-graph listener [tested: this file; commit=WORKTREE].
Owns resources: registered operations, retained contexts and the compilation
observer are released; each changed pragma is restored.
"""

from __future__ import annotations

import contextvars
import importlib

import janus_swi as janus
import pytest

from metta import Expression, MeTTa, S, V
from metta._binding import task_context
from metta._binding.dispatch import dispatch
from metta._binding.options import EVALUATIONS
from metta._errors.errors import InferenceLimitError


@pytest.mark.parametrize("door", tuple(EVALUATIONS))
@pytest.mark.parametrize("target", [["n", 7], "(+ 1 2)", "(superpose (1 1 2))", "(superpose ())"])
def test_evaluation_presets_and_records_share_one_policy(metta, door, target):
    """Every generated preset preserves its record's order, duplicates and emptiness."""
    predicate, record, preset = EVALUATIONS[door]

    def evaluate(options):
        result = metta.runtime.apply_must(predicate, options, metta.name, target)
        if record.answers != "cursor":
            return result
        values = []
        try:
            while rows := metta.runtime.apply_must("metta_py_cursor_chunk", result, 8):
                values.extend(row[:-1] for row in rows)
                if len(rows) < 8:
                    break
            return values
        finally:
            metta.runtime.do_must("metta_py_cursor_close", result)

    assert evaluate(preset) == evaluate(record)


def test_evaluation_compiler_preserves_data_and_never_runs_effects(metta):
    """Control folding cannot interpret a term supplied as program data."""
    assert metta.runtime.must(
        "metta_python_evaluation:evaluation_fold((_X=(true==true)),_Data),"
        "_Data == (_X=(true==true)),"
        "metta_python_evaluation:evaluation_fold("
        "(true->throw(planted_compiler_effect);true),_Effect),"
        "_Effect == throw(planted_compiler_effect),"
        "metta_python_evaluation:evaluation_fold((_A==true->_X=one;_X=two),_Unknown),"
        "var(_A),var(_X),_Unknown == (_A==true->_X=one;_X=two)"
    )["truth"]


def test_evaluation_batch_preserves_its_existing_unmatched_and_fuel_policy(metta):
    """Plain and using batches retain the cut's distinct empty and fuel rules."""
    metta.run("(= (binding-only 0) yes)")
    missing, present = S["binding-only"](1), S["binding-only"](0)
    assert metta.eval(missing) == []
    assert metta.eval(missing, present) == [[], [S.yes]]
    with metta.bind({"binding-arg": 1}):
        assert metta.eval(S["binding-only"](S["binding-arg"]), present) == [[], [S.yes]]
    prior = metta.runtime.must("(metta_pragma('max-stack-depth',Value)->true;Value=0)")["Value"]
    try:
        metta.run("!(pragma! max-stack-depth 20)\n(= (binding-spin $n) (binding-spin (+ $n 1)))")
        # Prepare the function before comparing execution policies: first
        # compilation also reconciles lib_memo's existing recursive graph.
        metta.runtime.must("spaces:metta_ensure_compiled('binding-spin')")
        assert "Error" in str(metta.eval(S["binding-spin"](0), inferences=10000))
        with pytest.raises(InferenceLimitError):
            metta.eval(S["binding-spin"](0), present, inferences=10000)
        with metta.bind({"binding-arg": 0}):
            groups = metta.eval(S["binding-spin"](S["binding-arg"]), present, inferences=10000)
            assert "StackOverflow" in str(groups[0])
            assert groups[1] == [S.yes]
    finally:
        metta.run(f"!(pragma! max-stack-depth {prior})")


def test_evaluation_inference_budget_charges_deferred_compilation():
    """A cold function's compilation observers spend its evaluation quota."""
    with MeTTa() as context:
        metta = context.self
        prior = metta.runtime.must("(metta_pragma('max-stack-depth',Value)->true;Value=0)")["Value"]
        try:
            metta.run(
                "!(pragma! max-stack-depth 20)\n"
                "(= (binding-cold-spin $n) (binding-cold-spin (+ $n 1)))"
            )
            # A declared compile observer gives the cold call more work than
            # its quota, independent of the worker's existing source graph.
            listeners = "findall(_Ref,clause(seam:function_call_graph_changed(_,_),_,_Ref),_Refs)"
            before = metta.runtime.must(f"{listeners},_Refs=[_|_],Refs=prolog(_Refs)")["Refs"]
            observer = metta.runtime.must(
                "assertz((seam:function_call_graph_changed('binding-cold-spin',_) :- "
                "forall(between(1,20000,_),true)),_Ref),Ref=prolog(_Ref)"
            )["Ref"]
            try:
                with pytest.raises(InferenceLimitError, match="10000"):
                    metta.eval(S["binding-cold-spin"](0), inferences=10000)
                assert "StackOverflow" in str(metta.eval(S["binding-cold-spin"](0), inferences=10000))
            finally:
                # A head-pattern retract also matches the generic listeners.
                metta.runtime.must("erase(Ref)", Ref=observer)
                metta.runtime.must(f"{listeners},_Refs==Before", Before=before)
        finally:
            metta.run(f"!(pragma! max-stack-depth {prior})")


def test_tagged_match_guards_share_the_derivations_inference_budget(metta):
    """Individually admitted guards cannot each spend a fresh query quota."""
    algebra = importlib.import_module("metta.algebra")
    algebra.declare(metta, "binding-budget", combine="+", extend="*", zero=0, one=1)
    metta.run("(= (binding-guard 0) True)\n"
              "(= (binding-guard $n) (if (> $n 0) (binding-guard (- $n 1)) True))")
    for index in range(24):
        metta.add_tagged_fact(1, S["binding-row"](index))
    guard = S["binding-guard"](100)
    # Compilation reconciles the worker's existing recursive graph. The
    # preceding cold-call test covers that cost; this quota covers execution.
    metta.runtime.must("spaces:metta_ensure_compiled('binding-guard')")
    assert metta.eval(guard, inferences=20000) == [True, True]
    with pytest.raises(InferenceLimitError, match="20000"):
        list(metta.match(S["binding-row"](V.x), where=guard, under="binding-budget", inferences=20000))
    answers = metta.match(S["binding-row"](V.x), where=guard, under="binding-budget")
    assert len(list(answers)) == 24


@pytest.mark.parametrize("raw", [False, True])
def test_an_inverse_of_a_deterministic_oracle_keeps_every_scheduler_answer(metta, raw):
    """Inverse streams use a stream handoff even when forward kind is det."""
    def roots(_value):
        yield (3,)
        yield (-3,)

    name = "binding-square"
    metta.op(lambda value: value * value, name=name, effect="oracleIO", inverse=roots)
    try:
        janus.consult("binding_inverse_events", data="""
            binding_inverse_events(Engine, Answers, Lanes) :-
                ( engine_next(Engine, Event)
                -> ( Event=answer(Value)
                   -> Answers=[Value|Rest], Lanes=Next
                   ; Event='$metta_scheduler_lane'(Lane),
                     Lanes=[Lane|Next], Answers=Rest ),
                   binding_inverse_events(Engine, Rest, Next)
                ; Answers=[], Lanes=[] ).
        """)
        result = janus.query_once(
            "setup_call_cleanup(engine_create(answer(_X),"
            "(nb_setval('$metta_scheduler_task',binding_test),"
            "metta_py_dispatch([det,Raw,true],Name,[_X],9)),_Engine),"
            "binding_inverse_events(_Engine,Answers,Lanes),engine_destroy(_Engine))",
            {"Raw": "true" if raw else "false", "Name": name},
        )
        assert result["Answers"] == [3, -3]
        assert result["Lanes"] == ["dirty", "normal"] * 3
    finally:
        metta.unregister_op(name)


@pytest.mark.parametrize("raw", [False, True])
def test_dispatch_enters_the_retained_context_for_each_pull_and_close(metta, raw):
    """Generator cleanup observes the same captured context as its yields."""
    selected = contextvars.ContextVar("binding-test-context", default="outside")
    events = []

    def source():
        try:
            events.append(selected.get())
            yield 1
            events.append(selected.get())
            yield 2
        finally:
            events.append(selected.get())

    name = "binding-context-stream"
    metta.op(source, name=name, effect="nondeterministicReadOnly")
    selected.set("captured")
    token = task_context.snapshot()
    selected.set("outside")
    stream = dispatch(["many", "true" if raw else "false", "false"], token, name, [])
    try:
        assert next(stream) == (1 if raw else ["n", 1])
        assert next(stream) == (2 if raw else ["n", 2])
        stream.close()
        assert events == ["captured"] * 3
        assert selected.get() == "outside"
    finally:
        stream.close()
        task_context.release(token)
        metta.unregister_op(name)


@pytest.mark.parametrize("width", [2, 16, 63, 64, 65, 128])
def test_wide_projection_is_a_crossover_and_never_a_variable_limit(metta, width):
    """Plain, guarded and bounded projections return every requested column."""
    head = S[f"binding-columns-{width}"]
    metta.add(Expression(head, *range(width)))
    pattern = Expression(head, *(V[f"x{i}"] for i in range(width)))
    for options in ({}, {"where": True}, {"limit": 1}):
        rows = list(metta.match(pattern, **options).rows)
        assert len(rows) == 1
        assert tuple(rows[0]) == tuple(range(width))


@pytest.mark.parametrize("transport", ["encoded", "raw"])
def test_stream_declines_preserve_answer_multiplicity(metta, transport):
    """Declined yields are absent while duplicate values remain two answers."""
    def source():
        yield from (None, 3, None, 3, None)

    name = "binding-declining-stream"
    metta.op(source, name=name, effect="nondeterministicReadOnly", transport=transport)
    try:
        assert metta.eval(S[name]()) == [3, 3]
    finally:
        metta.unregister_op(name)
