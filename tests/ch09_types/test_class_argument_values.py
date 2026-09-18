"""Purpose: preserve constructor values while evaluating default computations.

Guarantees:
  - supplied and default atoms survive Python, compiled and native construction
    under the initializer's arrow, Expression positions through the
    payload-preserving noeval spelling; factories run once before typed
    initialization, including fields excluded from __init__ [tested:
    test_constructor_arguments_preserve_values_and_run_factories;
    commit=WORKTREE]
  - supplied expressions finish before factory defaults and post-init runs
    [tested: test_constructor_sources_finish_before_factories_and_post_init;
    commit=6ff5033a6d52120cb7bce870f4a1fdbed5a0fbd0]
"""

from dataclasses import dataclass, field
from typing import Annotated

import annotated_types as at
import pytest

from metta import Atom, Expression, MeTTa, S, Space, V, convert


@pytest.mark.parametrize("grain", ("value", "entity", "prototype"))
@pytest.mark.parametrize("annotation", (Atom, Expression, Annotated[Atom, at.MinLen(2)]))
@pytest.mark.parametrize("route", (
    "positional", "keyword", "default", "factory", "stored-default", "stored-factory",
))
@pytest.mark.parametrize("entry", ("python", "compiled", "native"))
def test_constructor_arguments_preserve_values_and_run_factories(grain, annotation, route, entry):
    """Initializer input types govern values after source computations finish."""
    value = S["+"](1, 2)
    events = []

    def factory():
        events.append("factory")
        return value

    supplied = route in ("positional", "keyword")
    makes_default = route.endswith("factory")
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @dataclass(frozen=grain == "value")
        class SyntaxArgument(base):
            payload: annotation = (
                field() if supplied else
                field(default_factory=factory, init=not route.startswith("stored-")) if makes_default else
                field(default=value, init=not route.startswith("stored-"))
            )

        m.define(SyntaxArgument, methods=False)
        # A Python call spells the MeTTa application, so the constructor's
        # arrow decides a written atom: Atom and its refinements take it as
        # written, Expression evaluates it, as `!(make-SyntaxArgument (+ 1
        # 2))` does, so the syntax crosses under the payload-preserving
        # spelling `(noeval (+ 1 2))`, which evaluates to the syntax once.
        spelled = S.noeval(value) if annotation is Expression else value
        if entry == "python":
            instance = (
                SyntaxArgument(spelled) if route == "positional" else
                SyntaxArgument(payload=spelled) if route == "keyword" else
                SyntaxArgument()
            )
        elif entry == "compiled":
            if route == "positional":
                def constructed_syntax(payload: Atom) -> SyntaxArgument:
                    return SyntaxArgument(payload)
            elif route == "keyword":
                def constructed_syntax(payload: Atom) -> SyntaxArgument:
                    return SyntaxArgument(payload=payload)
            else:
                def constructed_syntax() -> SyntaxArgument:
                    return SyntaxArgument()
            constructor = m.define(constructed_syntax)
            answer = constructor(value).one() if supplied else constructor().one()
            instance = convert.build(answer, SyntaxArgument)
        else:
            application = (
                S.let(V.payload, S.noeval(value), S["make-SyntaxArgument"](V.payload))
                if supplied else S["make-SyntaxArgument"]()
            )
            answers = m.eval(application)
            assert len(answers) == 1
            instance = convert.build(answers[0], SyntaxArgument)

        assert instance.payload == value
        assert events == (["factory"] if makes_default else [])


@pytest.mark.parametrize("grain", ("value", "entity", "prototype"))
@pytest.mark.parametrize("entry", ("python", "compiled", "native"))
def test_constructor_sources_finish_before_factories_and_post_init(grain, entry):
    """Each entry completes supplied expressions before constructor effects."""
    events = []
    value = S["+"](1, 2)

    def argument():
        events.append("argument")
        return 7

    def factory():
        events.append("factory")
        return value

    def post_init():
        events.append("post-init")

    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @dataclass(frozen=grain == "value")
        class OrderedSyntax(base):
            number: int
            payload: Atom = field(default_factory=factory)

            def __post_init__(self):
                post_init()

        m.define(OrderedSyntax, methods=False)
        m.define(argument, name="class-argument-source")
        if entry == "python":
            instance = OrderedSyntax(argument())
        elif entry == "compiled":
            @m.define
            def ordered_syntax() -> OrderedSyntax:
                return OrderedSyntax(argument())

            instance = convert.build(ordered_syntax().one(), OrderedSyntax)
        else:
            answers = m.eval(S["make-OrderedSyntax"](S["class-argument-source"]()))
            assert len(answers) == 1
            instance = convert.build(answers[0], OrderedSyntax)

        assert (instance.number, instance.payload) == (7, value)
        assert events == ["argument", "factory", "post-init"]
