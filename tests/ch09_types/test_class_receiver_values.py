"""Purpose: preserve computed syntax and receivers at Python call boundaries.

Guarantees:
  - defined functions and native callable values receive the existing record
    value across all three grains [tested:
    test_computed_receivers_preserve_their_stored_syntax; commit=WORKTREE]
  - native input annotations inspect supplied syntax values after the Python
    call has computed them [tested:
    test_python_call_values_preserve_expression_arguments; commit=WORKTREE]
  - live scalar rules affect explicit source calls while Python calls carry
    their computed values [tested:
    test_python_call_values_preserve_symbols_with_live_scalar_rules;
    commit=WORKTREE]
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

import annotated_types as at
import pytest

from metta import Atom, Expression, G, MeTTa, S, Space, V, convert


@pytest.mark.parametrize("grain", ("value", "entity", "prototype"))
@pytest.mark.parametrize("annotation", (Atom, Expression, Annotated[Atom, at.MinLen(2)]))
@pytest.mark.parametrize("entry", ("defined", "native-symbol", "native-lambda"))
def test_computed_receivers_preserve_their_stored_syntax(grain, annotation, entry):
    """A quoted native value controls the source/value distinction."""
    value = S["+"](1, 2)
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @dataclass(frozen=grain == "value")
        class SyntaxReceiver(base):
            payload: annotation

        m.define(SyntaxReceiver, methods=False)

        @m.define
        def observe_receiver(instance: SyntaxReceiver) -> Any:
            return instance.payload

        instance = SyntaxReceiver(value)
        assert instance.payload == value
        receiver = convert.project(instance).atom
        assert m.eval(S.let(V.receiver, S.noeval(receiver),
                            S["observe-receiver"](V.receiver))) == [value]
        if entry == "defined":
            answer = observe_receiver(instance).one()
        else:
            image = (S["observe-receiver"] if entry == "native-symbol" else
                     S["|->"](Expression([V.receiver]), S["observe-receiver"](V.receiver)))
            function = convert.build(image, Callable[[SyntaxReceiver], Any], space=m)
            answer = function(instance)
        assert answer == value


@pytest.mark.parametrize("annotation", (Atom, Expression, Annotated[Atom, at.MinLen(2)]))
@pytest.mark.parametrize("entry", ("defined", "native-symbol", "native-lambda"))
def test_python_call_values_preserve_expression_arguments(annotation, entry):
    """A Python argument is data even when its atom head is executable."""
    value = S["+"](1, 2)
    with MeTTa() as context:
        m = context.self

        @m.define
        def retain_syntax_value(payload: annotation) -> Any:
            return payload

        assert m.eval(S.let(V.payload, S.noeval(value),
                            S["retain-syntax-value"](V.payload))) == [value]
        if entry == "defined":
            answer = retain_syntax_value(value).one()
        else:
            image = (S["retain-syntax-value"] if entry == "native-symbol" else
                     S["|->"](Expression([V.payload]), S["retain-syntax-value"](V.payload)))
            function = convert.build(image, Callable[[annotation], Any], space=m)
            answer = function(value)
        assert answer == value


@pytest.mark.parametrize("value", (S.call_value_symbol, G(value=True), G(value=False)))
@pytest.mark.parametrize("entry", ("defined", "native-symbol", "native-lambda"))
def test_python_call_values_preserve_symbols_with_live_scalar_rules(value, entry):
    """Native symbol rewriting does not turn a computed argument into source."""
    with MeTTa() as context:
        m = context.self

        @m.define
        def retain_scalar_value(payload: Any) -> Any:
            return payload

        if entry == "defined":
            function = retain_scalar_value
        else:
            image = (S["retain-scalar-value"] if entry == "native-symbol" else
                     S["|->"](Expression([V.payload]), S["retain-scalar-value"](V.payload)))
            function = convert.build(image, Callable[[Any], Any], space=m)
        for replacement in (G(7), G(11)):
            rule = S["="](value, replacement)
            m.add(rule)
            assert m.eval(S["retain-scalar-value"](value)) == [replacement]
            answer = function(value)
            if entry == "defined":
                answer = answer.one()
            assert answer == value
            assert m.remove(rule)
