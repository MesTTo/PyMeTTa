"""Purpose: build typed equation atoms from parameter-scoped rule generators.

Guarantees:
  - each decorated generator parameter becomes a rule-local MeTTa variable,
    and every yielded value is an ordinary binary equation [tested:
    test_a_rules_generator_scopes_its_variables_to_its_parameters;
    commit=WORKTREE].
  - equation halves share one static type parameter [tested:
    env CHECK_PY=/home/user/Dev/.venv-pypetta/bin/python sh check.sh mypy;
    commit=WORKTREE].
"""

from __future__ import annotations

import contextlib
import contextvars
import inspect
import types
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from .atoms import Expr, Sym, Var, encode

__all__ = ["equation", "rules"]

_T = TypeVar("_T")
_STAGING_DEFINED_CALLS: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "petta_staging_defined_calls",
    default=False,
)


class _Equation(Generic[_T]):
    """One typed left-hand side waiting for its right-hand side."""

    __slots__ = ("_lhs",)

    def __init__(self, lhs: _T):
        self._lhs = encode(lhs)

    def to(self, rhs: _T) -> Expr:
        """Complete ``(= lhs rhs)`` as an ordinary matchable atom."""
        return Expr([Sym("="), self._lhs, encode(rhs)])


def equation(lhs: _T) -> _Equation[_T]:
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


def rules(fn: Callable[..., Iterator[Expr]]) -> list[Expr]:
    """Collect equations; derives from ``V`` parameters plus ``list`` and ``m.add``.

    The decorated generator becomes a list of ordinary equation atoms. Add
    them with ``m.add(*laws)`` or ``m += laws[0]``; the longhand remains
    ``m += S["="](lhs, rhs)``.
    """
    if not isinstance(fn, types.FunctionType) or not inspect.isgeneratorfunction(fn):
        msg = f"rules expects a generator function, got {type(fn).__name__}"
        raise TypeError(msg)
    positional: list[Var] = []
    keywords: dict[str, Var] = {}
    for parameter in inspect.signature(fn).parameters.values():
        variable = Var(parameter.name)
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
            isinstance(atom, Expr)
            and len(atom.children) == 3
            and atom.children[0] == Sym("=")
        ):
            msg = f"rules yield {index} is not equation(lhs).to(rhs): {atom!r}"
            raise TypeError(msg)
    return yielded


if TYPE_CHECKING:
    _typed_equation = equation(1)
    _typed_equation.to(2)
    _typed_equation.to("wrong")  # type: ignore[arg-type]
