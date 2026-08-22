"""Purpose: implement the root equation and rules factories without a colliding submodule.

Guarantees:
  - each decorated generator parameter becomes a rule-local MeTTa variable,
    and every yielded value is an ordinary binary equation [tested:
    test_a_rules_generator_scopes_its_variables_to_its_parameters;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321].
  - equation halves share one static type parameter [tested:
    sh check.sh mypy ty; commit=f88aa8be03cb64cb59d3307515ded8701f418321].
  - bare rules are immutable bundles accepted by Space.__iadd__, while
    Space.rules lands the same bundle immediately [tested:
    test_a_rules_generator_scopes_its_variables_to_its_parameters;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import contextlib
import contextvars
import inspect
import types
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from .atoms import Expression, Symbol, Variable, _encode

__all__ = ["equation", "rules"]

_STAGING_DEFINED_CALLS: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "petta_staging_defined_calls",
    default=False,
)


class _Equation[T]:
    """One typed left-hand side waiting for its right-hand side."""

    __slots__ = ("_lhs",)

    def __init__(self, lhs: T):
        self._lhs = _encode(lhs)

    def to(self, rhs: T) -> Expression:
        """Complete ``(= lhs rhs)`` as an ordinary matchable atom."""
        return Expression([Symbol("="), self._lhs, _encode(rhs)])


def equation[T](lhs: T) -> _Equation[T]:
    """Start an equation; derives from ``S["="](lhs, rhs)`` in two typed parts."""
    return _Equation(lhs)


def _defined_calls_are_staged() -> bool:
    """Whether calling a Defined object should build rather than evaluate."""
    return _STAGING_DEFINED_CALLS.get()


@contextlib.contextmanager
def _stage_defined_calls() -> Iterator[None]:
    """Keep eager Defined calls staged for exactly one rules execution."""
    token = _STAGING_DEFINED_CALLS.set(True)
    try:
        yield
    finally:
        _STAGING_DEFINED_CALLS.reset(token)


class _RuleBundle(tuple[Expression, ...]):
    """An immutable set of laws recognized by Space's one write door."""

    __slots__ = ()

    def __new__(cls, equations: Iterator[Expression] | list[Expression]):
        return tuple.__new__(cls, equations)


def rules(fn: Callable[..., Iterator[Expression]]) -> _RuleBundle:
    """Collect equations as an immutable bundle accepted by ``space += bundle``.

    A bare decorator builds but does not choose a destination. The receiving
    space lands the complete bundle through its ordinary write operator; the
    bound ``@space.rules`` spelling performs both acts.
    """
    if not isinstance(fn, types.FunctionType) or not inspect.isgeneratorfunction(fn):
        msg = f"rules expects a generator function, got {type(fn).__name__}"
        raise TypeError(msg)
    positional: list[Variable] = []
    keywords: dict[str, Variable] = {}
    for parameter in inspect.signature(fn).parameters.values():
        variable = Variable(parameter.name)
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional.append(variable)
        elif parameter.kind is inspect.Parameter.KEYWORD_ONLY:
            keywords[parameter.name] = variable
        else:
            msg = "rules parameters are named variables; *args and **kwargs have no rule scope"
            raise TypeError(msg)
    with _stage_defined_calls():
        yielded: list[Any] = list(fn(*positional, **keywords))
    for index, atom in enumerate(yielded, start=1):
        if not (
            isinstance(atom, Expression)
            and len(atom.children) == 3
            and atom.children[0] == Symbol("=")
        ):
            msg = f"rules yield {index} is not equation(lhs).to(rhs): {atom!r}"
            raise TypeError(msg)
    return _RuleBundle(yielded)


if TYPE_CHECKING:
    _typed_equation = equation(1)
    _typed_equation.to(2)
    _typed_equation.to("wrong")  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
