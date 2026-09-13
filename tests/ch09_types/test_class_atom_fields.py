"""Purpose: verify the evaluation contract of generated syntax-field queries.

Guarantees:
  - field and class-variable queries evaluate their lookup and preserve the
    stored atom, including mutable replacement and native access [tested:
    test_generated_syntax_field_queries_return_the_stored_value,
    test_generated_class_variable_queries_return_the_stored_atom; commit=397a0df18bea23dee8774a721c2bdcd7dfc38c5e]
"""

from dataclasses import FrozenInstanceError, dataclass
from typing import Annotated, Any, ClassVar

import annotated_types as at
import pytest

from metta import Atom, Expression, MeTTa, S, Space, V, convert


@pytest.mark.parametrize("frozen,base", ((True, object), (False, object), (False, Space)))
@pytest.mark.parametrize("annotation,value", (
    (Atom, S["+"](1, 2)),
    (Expression, S["+"](1, 2)),
    (Annotated[Atom, at.MinLen(2)], S["+"](1, 2)),
    (Atom, S.literal),
    (Atom, 12),
    (Atom, None),
))
def test_generated_syntax_field_queries_return_the_stored_value(frozen, base, annotation, value):
    """Generated access executes a query; its stored syntax remains a value."""
    with MeTTa() as context:
        m = context.self

        @dataclass(frozen=frozen)
        class SyntaxField(base):
            payload: annotation

        m.define(SyntaxField, methods=False)

        @m.define
        def syntax_field_observed(instance: SyntaxField) -> Any:
            return instance.payload

        instance = (
            convert.build(S.SyntaxField(value), SyntaxField)
            if frozen else SyntaxField(S.Data(1, 2))
        )
        receiver = convert.project(instance).atom
        if not frozen:
            m.eval(S.let(V.held, S.noeval(value),
                         S["SyntaxField-payload!"](S.noeval(receiver), V.held)))
        assert instance.payload == value
        assert m.eval(S["SyntaxField-payload"](S.noeval(receiver))) == [value]
        assert m.eval(S[syntax_field_observed.name](S.noeval(receiver))) == [value]
        replacement = S.Data(4, 5)
        if frozen:
            with pytest.raises(FrozenInstanceError):
                instance.payload = replacement
        else:
            instance.payload = replacement
            assert instance.payload == replacement
            assert syntax_field_observed(instance).one() == replacement
            m.eval(S.let(V.held, S.noeval(value),
                         S["SyntaxField-payload!"](S.noeval(receiver), V.held)))
            assert instance.payload == value


@pytest.mark.parametrize("frozen,base", ((True, object), (False, object), (False, Space)))
@pytest.mark.parametrize("annotation", (Atom, Expression, Annotated[Atom, at.MinLen(2)]))
def test_generated_class_variable_queries_return_the_stored_atom(frozen, base, annotation):
    """Class-variable access has the same query contract for every grain."""
    value = S["+"](1, 2)
    with MeTTa() as context:
        m = context.self

        @dataclass(frozen=frozen)
        class SyntaxClassVariable(base):
            identity: int
            shared: ClassVar[annotation] = value

        m.define(SyntaxClassVariable, methods=False)

        @m.define
        def syntax_classvar_observed() -> Any:
            return SyntaxClassVariable.shared

        assert SyntaxClassVariable.shared == value
        assert m.eval(S["SyntaxClassVariable-shared"]()) == [value]
        assert syntax_classvar_observed().one() == value
