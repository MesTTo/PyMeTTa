"""Purpose: implement the root equation and rules factories without a colliding submodule.

Guarantees:
  - ``Rules.lower`` stores equations, publishes lowering declarations, and
    registers each symbolic head through the engine seam [tested:
    test_rules_lower_emits_queryable_declaration_and_registers_the_head,
    test_rules_lower_refuses_an_empty_rule_set_before_mutating;
    commit=WORKTREE]
  - each decorated generator parameter becomes a rule-local MeTTa variable,
    and every yielded value is an ordinary binary equation [tested:
    test_a_rules_generator_scopes_its_variables_to_its_parameters;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321].
  - equation halves share one static type parameter [tested:
    sh check.sh mypy ty; commit=f88aa8be03cb64cb59d3307515ded8701f418321].
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

__all__ = ["Rules", "equation", "rules"]

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


class Rules(list[Expression]):
    """A named equation set that can declare its translator lowering."""

    def __init__(self, name: str, equations: Iterator[Expression] | list[Expression]):
        super().__init__(equations)
        self.name = name

    def lower(self, strategy: Any, *, requires: Any, space: Any = None) -> Any:
        """Store the rules, declare their strategy, and register each head."""
        if not self:
            msg = f"cannot lower empty rule set {self.name!r}"
            raise ValueError(msg)
        if space is None:
            from . import engine  # noqa: PLC0415  -- default context stays lazy

            space = engine().self
        heads: list[Symbol] = []
        for equation_atom in self:
            lhs = equation_atom.children[1]
            if not isinstance(lhs, Expression) or not isinstance(lhs.head, Symbol):
                msg = f"lowering equation has no symbolic function head: {equation_atom}"
                raise TypeError(msg)
            if lhs.head not in heads:
                heads.append(lhs.head)
        space.add(*self)
        declarations = [
            Expression(
                [
                    Symbol("lowering"),
                    head,
                    _encode(strategy),
                    Expression([Symbol("requires"), _encode(requires)]),
                ]
            )
            for head in heads
        ]
        catalog = space._at("&petta")
        catalog.add(*declarations)
        for head in heads:
            answers = space.eval(Expression([Symbol("add-translator-rule!"), head]))
            if answers != [True]:
                msg = f"add-translator-rule! refused {head}, answering {answers!r}"
                raise RuntimeError(msg)
        return declarations[0] if len(declarations) == 1 else tuple(declarations)


def rules(fn: Callable[..., Iterator[Expression]]) -> Rules:
    """Collect equations; derives from ``V`` parameters plus ``list`` and ``m.add``.

    The decorated generator becomes a list of ordinary equation atoms. Add
    them with ``m.add(*laws)`` or ``m += laws[0]``; the longhand remains
    ``m += S["="](lhs, rhs)``.
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
    return Rules(fn.__name__, yielded)


if TYPE_CHECKING:
    _typed_equation = equation(1)
    _typed_equation.to(2)
    _typed_equation.to("wrong")  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
