"""Purpose: keep Python twins of compiled equations aligned with stacked clauses.
Guarantees:
  - TwinDispatcher selects the first literal head that admits the arguments
    [tested test_literal_defaults_are_head_patterns_and_clauses_stack]
  - twin views see definitions added after an earlier twin was compiled
    [tested test_existing_twin_sees_later_redefinition]
  - a twin that cannot run names the eager Defined call as the engine door
    [tested: test_twin_refuses_engine_only_bodies; commit=WORKTREE]
Guarded by:
  - _TWIN_LOCK serializes dispatcher creation, view publication, and clause
    replacement [tested test_define_from_two_threads_is_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import inspect
import threading
import types
from collections.abc import Callable
from typing import Any

from .atoms import Atom


class TwinDispatcher:
    """The Python twin of a possibly-stacked definition: clause twins in
    definition order, first whose head admits the arguments answers, the
    engine's own first-match reading that the guards compile. Twins of other
    definitions resolve to dispatchers too, so twins compose: a twin calling
    another defined name runs that name's Python, not a term builder.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("_clauses", "name")

    def __init__(self, name: str) -> None:
        self.name = name
        self._clauses: list[Callable[..., Any]] = []

    def __call__(self, *args: Any):
        with _TWIN_LOCK:
            clauses = tuple(self._clauses)
        for clause in clauses:
            try:
                return clause(*args)
            except _ClauseMiss:
                continue
        msg = f"{self.name}: no clause's head matches {args!r}"
        raise LookupError(msg)

    @property
    def __name__(self) -> str:
        return self.name

    @property
    def __doc__(self) -> str | None:  # type: ignore[override]
        with _TWIN_LOCK:
            return self._clauses[0].__doc__ if self._clauses else None

    @property
    def __signature__(self) -> inspect.Signature:
        """The canonical first clause's parameters, not `__call__`'s `*args`.

        inspect.signature/1 honours this attribute, and everything that asks a
        dispatcher what its parameters are wants the definition's, in source
        order: an Args section becomes one positional (@param ...) per
        parameter, so reading `*args` here published one empty @param for every
        definition however many arguments it took
        [tested: test_a_docstring_emits_the_whole_doc_vocabulary].
        """
        with _TWIN_LOCK:
            first = self._clauses[0] if self._clauses else None
        if first is None:
            return inspect.signature(self.__call__)
        return inspect.signature(first)

    def __repr__(self) -> str:
        with _TWIN_LOCK:
            count = len(self._clauses)
        return f"<python twin of {self.name}, {count} clause(s)>"


class _ClauseMiss(LookupError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """A clause twin refusing arguments its head does not match."""


# (id of a module's globals, name) -> the dispatcher every twin from that
# module resolves the name to; and per module, every twin-globals view built,
# so a later definition becomes visible to earlier twins, Python's own rule
# that a call resolves its callee at call time.
_TWIN_DISPATCHERS: dict[tuple[int, str], TwinDispatcher] = {}
_TWIN_VIEWS: dict[int, list[dict[str, Any]]] = {}
_TWIN_LOCK = threading.RLock()


def hazard_twin(
    name: str,
    hazards: frozenset[str],
    patterns: dict[str, Atom] | None = None,
    params: list[str] | None = None,
) -> Callable[..., Any]:
    """The refusal twin for a clause Python cannot run.

    Calling it names the unsupported engine behavior instead of raising an
    unrelated NameError from inside the original function.
    """

    def unrunnable(*_args, **_kwargs):
        reasons = ", ".join(sorted(hazards))
        msg = (
            f"{name}.py cannot run this clause in Python: its body uses "
            f"{reasons}, which exist only in the engine. Evaluate through "
            "the Defined object instead; calling it evaluates through its space."
        )
        raise RuntimeError(
            msg
        )

    unrunnable.__name__ = name
    return _guard_twin(unrunnable, name, params or [], patterns)


def select_clause_twin(
    name: str,
    twin: Callable[..., Any],
    hazards: frozenset[str],
    patterns: dict[str, Atom],
    params: list[str],
) -> Callable[..., Any]:
    """Choose the runnable twin or a precise engine-only refusal."""
    if hazards:
        return hazard_twin(name, hazards, patterns, params)
    return twin


def twin_dispatcher(fn: types.FunctionType) -> TwinDispatcher:
    """The dispatcher for fn's name in fn's module, created on first use and
    pushed into every twin-globals view of that module.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    mid, name = id(fn.__globals__), fn.__name__
    with _TWIN_LOCK:
        dispatcher = _TWIN_DISPATCHERS.get((mid, name))
        if dispatcher is None:
            dispatcher = _TWIN_DISPATCHERS[(mid, name)] = TwinDispatcher(name)
            for view in _TWIN_VIEWS.get(mid, []):
                view[name] = dispatcher
        return dispatcher


def _python_twin(
    fn: types.FunctionType, patterns: dict[str, Atom] | None = None
) -> Callable[..., Any]:
    """One clause's Python twin, head guard included.

    The twin's globals overlay every dispatcher this module has, its own
    name's first of all, so recursion reaches the dispatcher rather than the
    term builder, across clauses and across definitions. A clause with
    literal head patterns raises a clause miss when an argument misses one,
    and the dispatcher moves on.
    """
    globals_ = dict(fn.__globals__)
    mid = id(fn.__globals__)
    with _TWIN_LOCK:
        for (module_id, other), dispatcher in _TWIN_DISPATCHERS.items():
            if module_id == mid:
                globals_[other] = dispatcher
        _TWIN_VIEWS.setdefault(mid, []).append(globals_)

        name = fn.__name__
        own = twin_dispatcher(fn)
        globals_[name] = own

    closure = fn.__closure__
    freevars = fn.__code__.co_freevars
    if name in freevars and closure is not None:
        cells = list(closure)
        cell = types.CellType()
        cell.cell_contents = own
        cells[freevars.index(name)] = cell
        closure = tuple(cells)

    twin = types.FunctionType(
        fn.__code__, globals_, name=name, argdefs=fn.__defaults__, closure=closure
    )
    twin.__doc__ = fn.__doc__
    order = list(inspect.signature(fn).parameters)
    return _guard_twin(twin, name, order, patterns)


def _guard_twin(
    twin: Callable[..., Any],
    name: str,
    order: list[str],
    patterns: dict[str, Atom] | None,
) -> Callable[..., Any]:
    """Apply one literal-head guard to either kind of clause twin."""
    if not patterns:
        return twin

    def guarded(*args):
        for position, value in zip(order, args, strict=False):
            expected = patterns.get(position)
            if expected is not None and expected != value:
                msg = f"{name}: this clause's head matches {position}={expected}, not {value!r}"
                raise _ClauseMiss(
                    msg
                )
        return twin(*args)

    guarded.__name__ = name
    guarded.__doc__ = twin.__doc__
    return guarded


def append_twin_clause(dispatcher: TwinDispatcher, clause: Callable[..., Any]) -> None:
    """Append one clause under the same lock used by twin dispatch."""
    with _TWIN_LOCK:
        dispatcher._clauses.append(clause)


def replace_twin_clause(
    dispatcher: TwinDispatcher, position: int, clause: Callable[..., Any]
) -> None:
    """Replace one clause atomically for concurrent twin calls."""
    with _TWIN_LOCK:
        dispatcher._clauses[position] = clause
