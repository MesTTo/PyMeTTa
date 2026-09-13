"""Purpose: preserve field values and assignment target evaluation order.

Guarantees:
  - Python and compiled writes preserve syntax values and follow changes to
    the native source equation [tested:
    test_field_assignment_keeps_computed_syntax_values; commit=2070690afe0f1e6c580ebdb86e418e5a85bcc02d]
  - assignment evaluates the right side before its target, while augmented
    assignment evaluates its target once before the right side [tested:
    test_field_assignment_evaluates_its_target_once_in_python_order; commit=2070690afe0f1e6c580ebdb86e418e5a85bcc02d]
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any

import annotated_types as at
import pytest

from metta import Atom, Expression, MeTTa, S, Space, convert


@pytest.mark.parametrize("base", (object, Space))
@pytest.mark.parametrize("annotation", (Atom, Expression, Annotated[Atom, at.MinLen(2)]))
@pytest.mark.parametrize("entry", ("python", "compiled"))
def test_field_assignment_keeps_computed_syntax_values(base, annotation, entry):
    """Writing a value preserves it; computing a value reads the live equation."""
    with MeTTa() as context:
        m = context.self

        @dataclass
        class WrittenSyntax(base):
            payload: annotation

        m.define(WrittenSyntax, methods=False)
        instance = WrittenSyntax(S.Data(1, 2))
        value = S["+"](3, 4)
        source = S["="](S["field-source"](), value)
        m.add(S[":"](S["field-source"], S["->"](S.Atom)))
        m.add(source)
        assert m.eval(S["field-source"]()) == [value]
        field_source = convert.build(S["field-source"], Callable[[], Atom], space=m)
        assert field_source() == value

        @m.define
        def write_syntax(target: WrittenSyntax, source: Callable[[], Atom]) -> Any:
            target.payload = source()
            return target.payload

        if entry == "python":
            instance.payload = value
        else:
            assert write_syntax(instance, field_source).one() == value
        assert instance.payload == value

        replacement = S["+"](5, 6)
        m.remove(source)
        m.add(S["="](S["field-source"](), replacement))
        assert m.eval(S["field-source"]()) == [replacement]
        assert field_source() == replacement
        if entry == "python":
            instance.payload = replacement
        else:
            assert write_syntax(instance, field_source).one() == replacement
        assert instance.payload == replacement


@pytest.mark.parametrize("base", (object, Space))
@pytest.mark.parametrize("form", ("assignment", "annotation", "augmentation"))
def test_field_assignment_evaluates_its_target_once_in_python_order(base, form):
    """A constructor target exposes duplicated or reordered target evaluation."""
    events = []

    def initial():
        events.append("receiver")
        return 0

    def supplied():
        events.append("value")
        return 1

    with MeTTa() as context:
        m = context.self

        @dataclass
        class AssignmentTarget(base):
            number: int = field(default_factory=initial)

        m.define(AssignmentTarget, methods=False)
        if form == "augmentation":
            def assign_target():
                AssignmentTarget().number += supplied()
        elif form == "annotation":
            def assign_target():
                AssignmentTarget().number: int = supplied()
        else:
            def assign_target():
                AssignmentTarget().number = supplied()

        assigned = m.define(assign_target)
        assigned().one()
        assert events == (["receiver", "value"] if form == "augmentation" else ["value", "receiver"])
