"""Purpose: verify that native write refusals stop compiled continuations.

Guarantees:
  - field write errors stop ordinary, generator and finally continuations
    while preserving storage and already delivered answers [tested:
    test_refused_field_writes_stop_their_compiled_continuation; commit=WORKTREE]
  - native write statuses distinguish Error expressions from false values,
    and ordinary bindings can still carry Error data [tested:
    test_live_writer_errors_stop_the_tail_for_every_error_width,
    test_false_writer_status_and_local_error_data_keep_their_value_semantics;
    commit=WORKTREE]
"""

from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from metta import Expression, MeTTa, S, Space, V
from metta._declare.classes import declaration
from metta.vocabularies import EffectClass


@pytest.mark.parametrize("base", [object, Space])
@pytest.mark.parametrize("form", ["plain", "augmented", "generator", "finally"])
def test_refused_field_writes_stop_their_compiled_continuation(base, form):
    """Refusal leaves storage and subsequent effects untouched."""
    with MeTTa() as context:
        m = context.self
        events = []

        @m.op(effect=EffectClass.oracleIO)
        def after_write() -> int:
            events.append("continued")
            return 1

        @m.define
        @dataclass
        class CheckedWrite(base):
            value: int

        def plain(point: CheckedWrite) -> None:
            point.value = "bad"
            after_write()

        def augmented(point: CheckedWrite) -> None:
            point.value += "bad"
            after_write()

        def generator(point: CheckedWrite) -> Iterator[int]:
            yield 1
            point.value = "bad"
            yield 2

        def cleanup(point: CheckedWrite) -> None:
            try:
                raise ValueError
            finally:
                point.value = "bad"
                after_write()

        functions = {"plain": plain, "augmented": augmented,
                     "generator": generator, "finally": cleanup}
        m.define(functions[form], name="write-probe")
        point = CheckedWrite(5)
        answers = m.eval(S["write-probe"](point))
        if form == "generator":
            assert answers.pop(0) == 1
        assert len(answers) == 1
        assert isinstance(answers[0], Expression) and answers[0].head == S.Error
        assert "BadArgType" in str(answers[0])
        assert point.value == 5
        assert events == []


@pytest.mark.parametrize("width", range(4))
def test_live_writer_errors_stop_the_tail_for_every_error_width(width):
    """Each native Error shape replaces the compiled tail's answer."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class RewrittenWrite:
            value: int

        @m.define
        def update(point: RewrittenWrite) -> int:
            point.value = 9
            return 23

        point = RewrittenWrite(5)
        assert update(point).one() == 23
        assert point.value == 9
        plan = declaration(RewrittenWrite)
        writer = plan.accessor("value", write=True)
        plan.space.remove(S["="](writer(V.point, V.value), V.body))
        error = Expression([S.Error, *(S[f"part{index}"] for index in range(width))])
        plan.space.add(S["="](writer(V.point, V.value), S.noeval(error)))
        assert m.eval(S.update(point)) == [error]
        assert point.value == 9


def test_false_writer_status_and_local_error_data_keep_their_value_semantics():
    """A false writer succeeds and a local still holds its Error value."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class FalseWrite:
            value: int

        @m.define
        def error_source():
            raise ValueError

        error = m.eval(S["error-source"]())[0]

        @m.define
        def update(point: FalseWrite):
            result = error_source()
            point.value = 9
            return result

        point = FalseWrite(5)
        plan = declaration(FalseWrite)
        writer = plan.accessor("value", write=True)
        plan.space.remove(S["="](writer(V.point, V.value), V.body))
        false_status = False
        plan.space.add(S["="](writer(V.point, V.value), false_status))
        assert m.eval(S.update(point)) == [error]
        assert point.value == 5
