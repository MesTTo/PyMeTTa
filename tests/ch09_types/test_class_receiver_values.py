"""Purpose: a Python call spells the MeTTa application, so the arrow decides what an argument means.

Guarantees:
  - an Atom argument is syntax written at the call site: a Number or
    %Undefined% position evaluates it, an Atom position or a refinement of
    Atom takes it as written, and an Expression position receives the
    payload-preserving `S.noeval(...)` spelling as the syntax itself, through
    a defined function, a native symbol and a typed lambda [tested:
    test_python_call_arguments_follow_the_arrow; commit=WORKTREE]
  - a Python object argument is a value: a declared class instance reaches
    the callee as the term it is, syntax fields included, across all three
    grains [tested: test_computed_receivers_preserve_their_stored_syntax;
    commit=WORKTREE]
  - a live scalar rule rewrites a written symbol argument exactly as it
    rewrites the same application written in MeTTa, and an Atom position
    keeps the symbol [tested:
    test_written_symbol_arguments_follow_live_scalar_rules; commit=WORKTREE]
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

import annotated_types as at
import pytest

from metta import Atom, Expression, G, MeTTa, S, Space, V, convert

#: An Expression position evaluates written syntax, as `!(f (+ 1 2))` does
#: under `(: f (-> Expression ...))`, so the syntax itself crosses under the
#: payload-preserving form the examples use: `(noeval (+ 1 2))` evaluates to
#: `(+ 1 2)` once and the Expression check then reads that value.
#: The evaluating positions, whose answer is the sum.


def _spelled(annotation: Any, value: Atom) -> Atom:
    return S.noeval(value) if annotation is Expression else value


def _entry(m: Any, name: str, defined: Any, entry: str, annotation: Any) -> Any:
    """The three ways a Python program reaches one engine function."""
    if entry == "defined":
        return lambda *args: list(defined(*args))
    image = (S[name] if entry == "native-symbol" else
             S["|->"](Expression([V.payload]), S[name](V.payload)))
    function = convert.build(image, Callable[[annotation], Any], space=m)
    return lambda *args: [function(*args)]


@pytest.mark.parametrize("grain", ("value", "entity", "prototype"))
@pytest.mark.parametrize("annotation", (Atom, Expression, Annotated[Atom, at.MinLen(2)]))
@pytest.mark.parametrize("entry", ("defined", "native-symbol", "native-lambda"))
def test_computed_receivers_preserve_their_stored_syntax(grain, annotation, entry):
    """A Python instance crosses as the value it is, however its image spells."""
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

        instance = SyntaxReceiver(_spelled(annotation, value))
        assert instance.payload == value
        receiver = convert.project(instance).atom
        # The control: a value bound to a variable is what the engine passes.
        assert m.eval(S.let(V.receiver, S.noeval(receiver),
                            S["observe-receiver"](V.receiver))) == [value]
        call = _entry(m, "observe-receiver", observe_receiver, entry, SyntaxReceiver)
        assert call(instance) == [value]


@pytest.mark.parametrize("annotation", (int, Any, Atom, Annotated[Atom, at.MinLen(2)], Expression))
@pytest.mark.parametrize("entry", ("defined", "native-symbol", "native-lambda"))
def test_python_call_arguments_follow_the_arrow(annotation, entry):
    """`f(S.add(1, 2))` answers what `!(f (+ 1 2))` answers under f's arrow."""
    value = S["+"](1, 2)
    with MeTTa() as context:
        m = context.self

        @m.define
        def observe_argument(payload: annotation) -> Any:
            return payload

        spelled = _spelled(annotation, value)
        written = m.eval(S["observe-argument"](spelled))
        assert written == ([G(3)] if annotation in (int, Any) else [value])
        call = _entry(m, "observe-argument", observe_argument, entry, annotation)
        assert call(spelled) == written


@pytest.mark.parametrize("value", (S.call_value_symbol, G(value=True), G(value=False)))
@pytest.mark.parametrize("entry", ("defined", "native-symbol", "native-lambda"))
def test_written_symbol_arguments_follow_live_scalar_rules(value, entry):
    """A symbol written at the call site is the symbol the engine reads there."""
    with MeTTa() as context:
        m = context.self

        @m.define
        def observe_scalar(payload: Any) -> Any:
            return payload

        @m.define
        def hold_scalar(payload: Atom) -> Any:
            return payload

        observe = _entry(m, "observe-scalar", observe_scalar, entry, Any)
        hold = _entry(m, "hold-scalar", hold_scalar, entry, Atom)
        for replacement in (G(7), G(11)):
            rule = S["="](value, replacement)
            m.add(rule)
            assert m.eval(S["observe-scalar"](value)) == [replacement]
            assert observe(value) == [replacement]
            assert m.eval(S["hold-scalar"](value)) == [value]
            assert hold(value) == [value]
            assert m.remove(rule)
