"""Purpose: implement the root equation and rules factories without a colliding submodule.

Guarantees:
  - ``Rules.lower`` stores equations, publishes lowering declarations, and
    registers each symbolic head through the engine seam [tested:
    test_rules_lower_emits_queryable_declaration_and_registers_the_head,
    test_rules_lower_refuses_an_empty_rule_set_before_mutating;
    commit=c34c9bf3e55a8425d3f251c3ad06c33bc9755a22]
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
  - construction records variable-staged operation crossings and ground
    effectful calls without changing either result [tested:
    test_a_staged_operation_in_a_law_is_linted_not_refused,
    test_an_effectful_ground_operation_at_rule_construction_is_linted;
    commit=WORKTREE]
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
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._lint_events import LintEvent, event_at_frame
from .atoms import Expression, Symbol, Variable, _encode

__all__ = ["Rules", "equation", "rules"]

_STAGING_DEFINED_CALLS: contextvars.ContextVar[list[LintEvent] | None] = contextvars.ContextVar(
    "petta_staging_defined_calls",
    default=None,
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
    return _STAGING_DEFINED_CALLS.get() is not None


def _record_rule_operation(
    operation: Any, *, staged: bool, frame: types.FrameType
) -> None:
    """Retain one op call in the active rule collector, if there is one."""
    collector = _STAGING_DEFINED_CALLS.get()
    if collector is None:
        return
    if staged:
        kind = "operation-staged-in-law"
    elif operation.effect.value != "pureStructural":
        kind = "effectful-operation-at-construction"
    else:
        return
    collector.append(
        event_at_frame(
            kind,
            str(operation.name),
            frame,
            effect=operation.effect.value,
        )
    )


@contextlib.contextmanager
def _stage_defined_calls() -> Iterator[list[LintEvent]]:
    """Keep eager Defined calls staged for exactly one rules execution."""
    collector: list[LintEvent] = []
    token = _STAGING_DEFINED_CALLS.set(collector)
    try:
        yield collector
    finally:
        _STAGING_DEFINED_CALLS.reset(token)


class Rules(tuple[Expression, ...]):
    """An immutable named equation set recognized by Space's one write door.

    A tuple subtype cannot carry nonempty __slots__, so the name rides the
    instance dict while the equations themselves stay immutable.
    """

    name: str
    lint_events: tuple[LintEvent, ...]
    source_line: int
    source_path: str | None

    def __new__(
        cls,
        name: str,
        equations: Iterator[Expression] | list[Expression],
        *,
        lint_events: Iterable[LintEvent] = (),
        source_path: str | None = None,
        source_line: int = 0,
    ):
        bundle = tuple.__new__(cls, equations)
        bundle.name = name
        bundle.lint_events = tuple(lint_events)
        bundle.source_path = source_path
        bundle.source_line = source_line
        return bundle

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
        from ._lint_events import register_rule_events  # noqa: PLC0415 -- lint is a satellite

        register_rule_events(space, self)
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
    with _stage_defined_calls() as lint_events:
        yielded: list[Any] = list(fn(*positional, **keywords))
    for index, atom in enumerate(yielded, start=1):
        if not (
            isinstance(atom, Expression)
            and len(atom.children) == 3
            and atom.children[0] == Symbol("=")
        ):
            msg = f"rules yield {index} is not equation(lhs).to(rhs): {atom!r}"
            raise TypeError(msg)
    path = inspect.getsourcefile(fn) or inspect.getfile(fn)
    if not (path.startswith("<") and path.endswith(">")):
        path = str(Path(path).resolve())
    return Rules(
        fn.__name__,
        yielded,
        lint_events=lint_events,
        source_path=path,
        source_line=fn.__code__.co_firstlineno,
    )


if TYPE_CHECKING:
    _typed_equation = equation(1)
    _typed_equation.to(2)
    _typed_equation.to("wrong")  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
