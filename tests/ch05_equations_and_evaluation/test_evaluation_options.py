"""Purpose: verify the evaluation option product and its cursor ownership.

Guarantees: selecting a consumption shape preserves the engine's ordered bag,
  scoped bindings, annotations, and third truth value [tested:
  test_evaluation_options_compose_without_losing_answers,
  test_evaluation_options_preserve_annotations_and_caller_rows,
  test_evaluation_options_preserve_undefined_truth; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
Owns resources: fixtures close spaces; lazy results are consumed or closed;
  failure and abandonment tests check the source's release explicitly.
"""

from __future__ import annotations

import gc
import time
from dataclasses import dataclass

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import metta._spaces.evaluate as selection
from metta import Expression, G, MeTTa, S, Space, V, equation
from metta._atoms.factories import Undefined
from metta._errors.errors import (
    AssertionFailure,
    EngineError,
    InferenceLimitError,
    MettaResultError,
    TimeLimitError,
)
from metta._spaces.results import Answers, Rows, _AnswerItem


@pytest.fixture
def space():
    """Own the engine context for each evaluation test."""
    with MeTTa() as context:
        yield context.self


def test_evaluation_options_preserve_the_eager_kernel(space, monkeypatch):
    """Evaluation options preserve the eager kernel."""
    def refuse_cursor(*_args, **_kwargs):
        msg = "an eager call opened a replayable cursor"
        raise AssertionError(msg)

    native = selection._spaces_execution_module.evaluate
    eager = []

    def observe(*args, **kwargs):
        eager.append(args[2])
        return native(*args, **kwargs)

    monkeypatch.setattr(Space, "answers", refuse_cursor)
    monkeypatch.setattr(selection._spaces_execution_module, "evaluate", observe)
    assert space.eval("(+ 2 3)") == [G(5)]
    assert space.eval("(+ 2 3)", delivery="values") == [5]
    assert space.eval("(+ 2 3)", answer="one", delivery="values") == 5
    assert len(eager) == 3
    assert space.eval("(superpose (2 2 3))", answer="count") == 3


@settings(max_examples=60, deadline=None)
@given(values=st.lists(st.integers(-1000, 1000), max_size=25), bound=st.integers(0, 30))
def test_evaluation_options_compose_without_losing_answers(values, bound):
    """Evaluation options compose without losing answers."""
    with MeTTa() as context:
        space = context.self
        target = S.superpose(Expression(*values))
        expected = [G(value) for value in values]
        assert space.eval(target) == expected
        assert space.eval(target, delivery="values") == values
        assert space.eval(target, answer="count") == len(values)
        assert space.eval(target, answer="count", limit=bound) == len(values[:bound])
        assert space.eval(target, answer="exists", limit=bound) is bool(values[:bound])
        assert space.eval(target, answer="none", limit=bound) is None
        assert space.eval(target, answer="first", delivery="values") == (values[0] if values else None)
        for shape in ("one", "atom"):
            if len(expected) == 1:
                assert space.eval(target, answer=shape) == expected[0]
            else:
                with pytest.raises(EngineError, match="expected exactly one"):
                    space.eval(target, answer=shape)
        for answer in ("answers", "stream"):
            with space.eval(target, answer=answer, delivery="values", limit=bound) as selected:
                assert list(selected) == values[:bound]
        rows = space.eval(target, answer="rows", limit=bound)
        assert rows.columns == ("value",)
        assert [row.value for row in rows] == expected[:bound]


@pytest.mark.parametrize("answer", ["all", "answers", "stream", "rows"])
@pytest.mark.parametrize("atom_key", [False, True])
def test_evaluation_options_apply_bindings_once(space, answer, atom_key):
    """Evaluation options apply bindings once."""
    bindings = {S.a if atom_key else "a": S.b, S.b if atom_key else "b": S.c}
    with space.bind(bindings):
        result = space.eval(S.a, answer=answer, limit=1)
    if answer in {"answers", "stream"}:
        with result:
            assert list(result) == [S.b]
    elif answer == "rows":
        assert list(result.value) == [S.b]
    else:
        assert result == [S.b]
    assert space.eval(S.a) == [S.a]


def test_evaluation_options_keep_holes_identity_and_batch_groups(space):
    """Evaluation options keep holes identity and batch groups."""
    payload = object()
    assert space.eval("{first}", "{second}", first=2, second=3, delivery="values") == [[2], [3]]
    with space.eval("{held}", held=payload, answer="answers", delivery="values") as answers:
        assert answers.one() is payload
    assert space.eval(G(payload), answer="one", delivery="values", image="opaque") is payload
    assert space.eval(space, answer="one", delivery="values", image="transparent") == space


@pytest.mark.parametrize("answer", ["all", "answers", "stream"])
def test_evaluation_options_compose_theory_and_interpreter(space, answer):
    """Evaluation options compose theory and interpreter."""
    space.add(equation(S.door_choice()).to(S.base))
    laws = (equation(S.door_choice()).to(S.left), equation(S.door_choice()).to(S.right))
    space.run("(: door-eval (-> Atom Atom Atom %Undefined%)) (= (door-eval $t $ty $s) (Seen (metta $t $ty $s)))")
    before = space.space_names()
    result = space.eval(S.door_choice(), theory=laws, interpreter=S.door_eval, answer=answer, limit=1)
    if answer == "all":
        assert result == [S.Seen(S.left)]
    else:
        with result:
            assert list(result) == [S.Seen(S.left)]
    assert space.space_names() == before
    assert space.eval(S.door_choice()) == [S.base]


def test_evaluation_options_preserve_annotations_and_caller_rows(space):
    """Evaluation options preserve annotations and caller rows."""
    space.algebra("door-product", combine="+", extend="*", zero=0, one=1)
    space.add_tagged_fact(7, S.door_tagged(S.yes))
    with space.eval(S.door_tagged(V.value), under="door-product", answer="answers", limit=1) as answers:
        answer = answers.one()
        assert answer.annotation == 7
        assert answer.value == S.door_tagged(S.yes)
        assert answers.rows.one().value == S.yes
    rows = space.eval(S.door_tagged(V.value), under="door-product", answer="rows")
    assert rows.columns == ("value",) and rows.one().value == S.yes
    counted = space.eval(S.door_tagged(V.value), under="counting", answer="one")
    assert counted.annotation == 1


def test_evaluation_options_preserve_undefined_truth(space):
    """Evaluation options preserve undefined truth."""
    space._rt._janus.consult(
        "door_wfs.pl", data=":- table door_wfs/0.\ndoor_wfs :- tnot(door_wfs).\n"
    )
    target = "(translatePredicate (door_wfs))"
    for answer in ("all", "answers", "stream"):
        selected = space.eval(target, answer=answer, limit=1)
        values = list(selected)
        if hasattr(selected, "close"):
            selected.close()
        assert len(values) == 1 and isinstance(values[0], Undefined)
        assert "door_wfs" in values[0].why
    for limit in (None, 1):
        with pytest.raises(EngineError, match="undefined truth"):
            space.eval(target, answer="one", delivery="values", limit=limit)


@dataclass
class DoorPoint:
    """A record whose structural image has a declared constructor."""

    x: int


def test_evaluation_options_select_images_without_losing_values(space):
    """Evaluation options select images without losing values."""
    value = DoorPoint(7)
    assert space.eval(G(value), answer="one", image="opaque", delivery="values") is value
    assert space.eval(G(value), answer="atom", image="transparent") == S.DoorPoint(7)
    assert space.eval(G(value), answer="one", image="auto", delivery="values") is value
    assert space.eval(G([1, 2]), answer="atom", image="auto") == Expression(1, 2)
    assert S[":"](S.DoorPoint, S["->"](S.Number, S.DoorPoint)) in space


@pytest.mark.parametrize("answer", ["all", "answers", "stream"])
def test_evaluation_options_select_error_answers(space, answer):
    """Evaluation options select error answers."""
    target = S.superpose(Expression(G(1), S.Error(S.test, S.reason), G(2)))
    for mode, expected in (("keep", [G(1), S.Error(S.test, S.reason), G(2)]), ("empty", [G(1), G(2)])):
        result = space.eval(target, answer=answer, on_error=mode, limit=3)
        assert list(result) == expected
        if hasattr(result, "close"):
            result.close()
    with pytest.raises(MettaResultError, match="reason"):
        result = space.eval(target, answer=answer, on_error="abort", limit=3)
        list(result)


@pytest.mark.parametrize("limit", [None, 1, 2])
def test_first_selects_the_first_retained_answer(space, limit):
    """First selects the first retained answer."""
    assert space.eval("(superpose ((Error door missing) 7))", answer="first",
                      on_error="empty", delivery="values", limit=limit) == 7
    assert space.eval("(superpose (7 (Error door later)))", answer="first",
                      on_error="abort", delivery="values", limit=limit) == 7
    with pytest.raises(MettaResultError, match="missing"):
        space.eval("(superpose ((Error door missing) 7))", answer="first",
                   on_error="abort", delivery="values", limit=limit)


@pytest.mark.parametrize("answer,limit,expected,seen", [
    ("first", None, 1, [1, 2, 3]),
    ("first", 3, 1, [1]),
    ("exists", None, True, [1]),
    ("all", 1, [1], [1]),
])
def test_evaluation_selection_preserves_eager_effects_and_bounded_demand(space, answer, limit, expected, seen):
    """Evaluation selection preserves eager effects and bounded demand."""
    effects = []

    @space.io(name="door-selection-effect")
    def touch(value: int) -> int:
        effects.append(value)
        return value

    try:
        assert space.eval("(door-selection-effect (superpose (1 2 3)))",
                          answer=answer, delivery="values", limit=limit) == expected
        assert effects == seen
    finally:
        space.unregister_op("door-selection-effect")


@pytest.mark.parametrize("answer", ["all", "answers", "stream", "count"])
@pytest.mark.parametrize("on_error", ["keep", "empty", "abort"])
def test_wall_bounds_propagate_through_every_error_policy(space, answer, on_error):
    """Wall bounds propagate through every error policy."""
    @space.io(name="door-wall-value")
    def slow() -> int:
        time.sleep(0.04)
        return 7

    try:
        with pytest.raises(TimeLimitError):
            result = space.eval("(door-wall-value)", answer=answer,
                                on_error=on_error, timeout=0.02, limit=1)
            if answer in {"answers", "stream"}:
                with result:
                    list(result)
    finally:
        space.unregister_op("door-wall-value")
    assert space.eval("(+ 2 3)") == [G(5)]


@pytest.mark.parametrize("options", [
    {"answer": "invalid"}, {"delivery": "invalid"}, {"on_error": "invalid"},
    {"determinism": "invalid"}, {"image": "invalid"}, {"limit": -1},
    {"limit": True}, {"limit": 1.5}, {"answer": "atom", "delivery": "values"},
])
def test_evaluation_options_refuse_invalid_values(space, options):
    """Evaluation options refuse invalid values."""
    with pytest.raises(ValueError, match="eval"):
        space.eval("(+ 2 3)", **options)


@pytest.mark.parametrize("answer", ["all", "answers", "stream", "count", "exists", "none"])
def test_evaluation_options_check_cardinality_before_truncation(space, answer):
    """Evaluation options check cardinality before truncation."""
    with pytest.raises(AssertionFailure, match="expected at most one"):
        result = space.eval("(superpose (1 2))", answer=answer, determinism="semidet", limit=1)
        if answer in {"answers", "stream"}:
            list(result)
    with pytest.raises(AssertionFailure, match="expected exactly one"):
        result = space.eval("(empty)", answer=answer, determinism="det", limit=1)
        if answer in {"answers", "stream"}:
            list(result)


def test_evaluation_options_preserve_bounds_and_capture(space):
    """Evaluation options preserve bounds and capture."""
    space.run("(= (door-loop) (door-loop))")
    for answer in ("all", "answers", "stream", "count"):
        with pytest.raises(InferenceLimitError):
            result = space.eval("(door-loop)", answer=answer, inferences=200, limit=1)
            if answer in {"answers", "stream"}:
                list(result)
    with space.capture() as captured:
        assert space.eval('(progn (println! "door") 7)', answer="one", delivery="values") == 7
    assert captured.text == '\"door\"\n'


class TrackedSource:
    """Expose demand and cleanup, including deliberately failed operations."""

    def __init__(self, values, *, failure=None, cleanup=None):
        """Hold the finite values and the requested failure witnesses."""
        self.values = iter(values)
        self.failure = failure
        self.cleanup = cleanup
        self.pulls = 0
        self.closes = 0
        self.closed = False
        self.deferred = False

    def __iter__(self):
        """Iterate the single tracked source."""
        return self

    def __next__(self):
        """Count every demand before returning or raising."""
        self.pulls += 1
        if self.failure:
            raise self.failure
        return next(self.values)

    def close(self):
        """Count every close and leave failed cleanup retryable."""
        self.closes += 1
        if self.cleanup:
            raise self.cleanup
        self.closed = True

    def close_deferred(self):
        """Record the abandonment backstop without synchronous engine work."""
        self.deferred = True


def _supply(monkeypatch, source):
    raw = Answers(source)
    monkeypatch.setattr(Space, "answers", lambda *_args, **_kwargs: raw)
    return raw


@pytest.mark.parametrize("answer", ["answers", "stream", "count", "exists", "none"])
def test_evaluation_selections_close_on_every_exit(space, monkeypatch, answer):
    """Evaluation selections close on every exit."""
    source = TrackedSource([G(1), G(2)])
    raw = _supply(monkeypatch, source)
    selected = space.eval(S.x, answer=answer, limit=1)
    if answer in {"answers", "stream"}:
        assert list(selected) == [G(1)]
        selected.close()
    assert source.closed and raw._done and source.pulls == 1
    assert not raw._cache


@pytest.mark.parametrize("answer", ["answers", "stream"])
def test_evaluation_selections_close_on_interrupt_and_abandonment(space, monkeypatch, answer):
    """Evaluation selections close on interrupt and abandonment."""
    source = TrackedSource([], failure=KeyboardInterrupt("door interrupted"))
    _supply(monkeypatch, source)
    selected = space.eval(S.x, answer=answer)
    with pytest.raises(KeyboardInterrupt, match="door interrupted"):
        next(iter(selected))
    assert source.closed
    abandoned = TrackedSource([G(1)])
    raw = _supply(monkeypatch, abandoned)
    selected = space.eval(S.x, answer=answer)
    del selected
    gc.collect()
    # The test's own raw reference holds the backstop until it too is released.
    assert not abandoned.closed
    monkeypatch.undo()
    del raw
    gc.collect()
    assert abandoned.deferred


def test_evaluation_selections_preserve_original_and_cleanup_failures(space, monkeypatch):
    """Evaluation selections preserve original and cleanup failures."""
    source = TrackedSource([], failure=KeyboardInterrupt("door interrupted"), cleanup=OSError("door cleanup"))
    _supply(monkeypatch, source)
    selected = space.eval(S.x, answer="stream")
    with pytest.raises(BaseExceptionGroup) as failure:
        next(selected)
    assert [str(error) for error in failure.value.exceptions] == ["door interrupted", "door cleanup"]
    source.cleanup = None
    selected.close()
    assert source.closed


def test_a_zero_selection_never_pulls_its_source(space, monkeypatch):
    """A zero selection never pulls its source."""
    source = TrackedSource([], failure=AssertionError("zero bound evaluated"))
    _supply(monkeypatch, source)
    with space.eval(S.x, answer="stream", limit=0) as stream:
        assert list(stream) == []
    assert source.closed and source.pulls == 0


def test_selected_answers_replay_bindings_once(space, monkeypatch):
    """Selected answers replay bindings once."""
    row = Rows(("x",), [(G(3),)]).one()
    source = TrackedSource([_AnswerItem(S.row(3), row)])
    raw = Answers(source, columns=("x",))
    monkeypatch.setattr(Space, "answers", lambda *_args, **_kwargs: raw)
    with space.eval(S.row(V.x), answer="answers", limit=1) as answers:
        assert list(answers) == list(answers) == [S.row(3)]
        assert answers.rows.one() == row
        assert len(answers._cache) == 1 and not raw._cache


@pytest.mark.parametrize("answer", ["answers", "stream"])
@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_a_failed_batch_closes_every_acquired_selection(space, monkeypatch, answer, cleanup_fails):
    """A failed batch closes every acquired selection."""
    sources = [TrackedSource([G(index)], cleanup=OSError(f"cleanup {index}") if cleanup_fails else None)
               for index in range(2)]
    acquired = [Answers(source) for source in sources]
    pending = iter(acquired)
    original = EngineError("batch opening failed")

    def open_source(*_args, **_kwargs):
        if len(opened) == 2:
            raise original
        opened.append(1)
        return next(pending)

    opened = []
    monkeypatch.setattr(Space, "answers", open_source)
    try:
        with pytest.raises(BaseExceptionGroup if cleanup_fails else EngineError) as failure:
            space.eval(S.first, S.second, S.third, answer=answer)
        if cleanup_fails:
            assert failure.value.exceptions == (original, sources[0].cleanup, sources[1].cleanup)
        else:
            assert failure.value is original
        assert [source.closes for source in sources] == [1, 1]
        assert [source.pulls for source in sources] == [0, 0]
    finally:
        for source, raw in zip(sources, acquired, strict=True):
            source.cleanup = None
            raw.close()
