"""Purpose: registration of Python callables as MeTTa functions. Reads the
signature for arities (defaults yield several), auto-detects nondeterminism
(a generator function is one), derives a MeTTa type declaration from the
annotations, and registers the whole thing with the engine through shim.pl.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: keyword-argument call forms once PeTTa itself grows a
    spelling for them; today MeTTa call sites are positional.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from . import convert
from ._ops import REGISTRY, Operation
from ._type_annotations import (
    callable_name as _callable_name,
)
from ._type_annotations import (
    declaration_exprs,
    metta_type_for,
    referenced_classes,
    resolved_annotations,
    type_atom_for,
    type_atoms_for,
)
from .atoms import Expr, S, expr

__all__ = [
    "REFLECTION_SPACE",
    "class_declarations",
    "declaration_exprs",
    "metta_type_for",
    "referenced_classes",
    "register",
    "registered",
    "type_atom_for",
    "type_atoms_for",
    "unregister",
]

#: The library's own space. Everything Python registers reflects here as
#: ordinary atoms: (op name arity kind) per registered arity,
#: (defined space name) per @define function, (subscription space pattern
#: on) per standing query. It is a space like any other, so MeTTa programs
#: can query the library's surface, and writing to it composes with
#: subscriptions: a Python subscription on &petta reacts to control atoms
#: a MeTTa program adds, which is steering the library from inside MeTTa
#: without forking it.
REFLECTION_SPACE = "&petta"


def _op_facts(op: Operation) -> list[Expr]:
    return [expr(S.op, S[op.name], arity, S[op.kind]) for arity in op.arities]


def _reflect_add(runtime, atom: Expr) -> None:
    runtime.must("petta_py_add(Space, W)", Space=REFLECTION_SPACE, W=atom.to_wire())


def _reflect_remove(runtime, atom: Expr) -> None:
    runtime.once("petta_py_remove(Space, W, _)", Space=REFLECTION_SPACE, W=atom.to_wire())


# Declarations are shared: two signatures naming Point both need
# (: Point ...), and removal of every copy on the first unregister would
# leave the second describing an undeclared type. Ownership counts per
# (space, declaration); the atom enters the space with the first owner and
# leaves with the last.
_DECLARATION_REFS: dict[tuple[str, str], int] = {}


def _retain_declaration(runtime, space: str, declaration: Expr) -> None:
    key = (space, str(declaration))
    count = _DECLARATION_REFS.get(key, 0)
    if count == 0:
        runtime.must("petta_py_add(Space, W)", Space=space, W=declaration.to_wire())
    _DECLARATION_REFS[key] = count + 1


def _release_declaration(runtime, space: str, declaration: Expr) -> None:
    key = (space, str(declaration))
    count = _DECLARATION_REFS.get(key, 0)
    if count <= 1:
        _DECLARATION_REFS.pop(key, None)
        runtime.once("petta_py_remove(Space, W, _)", Space=space, W=declaration.to_wire())
    else:
        _DECLARATION_REFS[key] = count - 1


def class_declarations(cls: type) -> list[Expr]:
    """The (: ...) atoms that make a class a MeTTa type: the translator's
    own declarations for an Enum, dataclass or NamedTuple, constructor
    arrows and member typings, derived from the class itself. A plain
    class needs NO declaration: its instances already answer the class
    name to get-type through the engine's MRO typing bridge, so emitting
    one would only restate what the engine figures out on its own."""
    return list(convert.declarations(cls))


def _metta_name(fn: Callable, name: str | None) -> str:
    """The MeTTa spelling: underscores read as hyphens unless overridden."""
    return name if name is not None else _callable_name(fn).replace("_", "-")


def _arities(fn: Callable, explicit: list[int] | None) -> tuple[list[int], list[inspect.Parameter]]:
    """Every arity the defaults allow, smallest first, plus the parameters.

    An explicit arities list overrides the derivation, which is how a
    variadic callable registers: the call sites it serves are named rather
    than inferred, since *args alone says nothing about MeTTa call forms.
    """
    sig = inspect.signature(fn)
    params = []
    variadic = False
    for p in sig.parameters.values():
        if p.kind is inspect.Parameter.VAR_KEYWORD:
            continue  # unreachable from MeTTa, harmless to ignore
        if p.kind is inspect.Parameter.VAR_POSITIONAL:
            variadic = True
            continue
        if p.kind is inspect.Parameter.KEYWORD_ONLY:
            raise TypeError(
                f"cannot register {_callable_name(fn)}: keyword-only parameter "
                f"{p.name!r} is unreachable from a positional MeTTa call site"
            )
        params.append(p)
    if explicit is not None:
        return sorted(set(explicit)), params
    if variadic:
        raise TypeError(
            f"cannot register {_callable_name(fn)}: *args has no single MeTTa call "
            f"form; pass arities=[...] naming the argument counts to serve"
        )
    required = sum(1 for p in params if p.default is inspect.Parameter.empty)
    return list(range(required, len(params) + 1)), params


def _type_declarations(name: str, params: list[inspect.Parameter], fn: Callable) -> list[Expr]:
    """Everything a signature declares: the (-> ...) arrows over the full
    arity, one per Union combination, plus the declarations of every class
    the annotations reference, so a signature naming Point makes Point a
    declared type rather than a dangling name. Annotations resolve through
    typing, so postponed (string) annotations declare the types they name
    rather than %Undefined%, and TypeVars declare type variables, the
    parametric reading."""
    hints = resolved_annotations(fn)
    annotations = [hints.get(p.name, inspect.Parameter.empty) for p in params]
    ret = hints.get("return", Any)
    declared = declaration_exprs(name, annotations, ret)
    for cls in referenced_classes([*annotations, ret]):
        for extra in class_declarations(cls):
            if extra not in declared:
                declared.append(extra)
    return declared


def register(
    runtime,
    fn: Callable,
    *,
    name: str | None = None,
    typed: bool = True,
    raw: bool = False,
    pass_atoms: bool = False,
    space: str = "&self",
    arities: list[int] | None = None,
) -> Callable:
    """Make fn callable from MeTTa. Returns fn unchanged.

    A generator function registers as nondeterministic: each yield is one
    answer, and MeTTa's collapse, superpose and let compose over them. A
    plain function is deterministic; returning None or raising Decline
    answers nothing. Defaults yield one registration per reachable arity;
    a variadic callable names its call forms with arities=[...].
    """
    metta_name = _metta_name(fn, name)
    arities, params = _arities(fn, arities)
    many = inspect.isgeneratorfunction(fn)
    kind = ("raw_many" if many else "raw_det") if raw else ("many" if many else "det")
    # Everything computable is computed BEFORE the engine changes: a
    # refusing annotation or an over-expanded Union leaves nothing half
    # registered. Then the engine registers every arity in one checked
    # step (a collision with a static procedure throws with nothing
    # touched); declaration and reflection writes follow with a rollback
    # that restores the previous registration whole, and the Python
    # registry commits last.
    declarations = tuple(_type_declarations(metta_name, params, fn)) if typed and params else ()
    previous = REGISTRY.get(metta_name)
    operation = Operation(
        name=metta_name,
        fn=fn,
        kind=kind,
        arity=max(arities),
        pass_atoms=pass_atoms,
        space=space,
        declarations=declarations,
        arities=tuple(arities),
    )
    new_facts = _op_facts(operation)
    old_facts = _op_facts(previous) if previous is not None else []
    runtime.must(
        "petta_py_register_op_set(Name, Arities, Kind)",
        Name=metta_name,
        Arities=list(arities),
        Kind=kind,
    )
    retained: list[Expr] = []
    added_facts: list[Expr] = []
    try:
        for declaration in declarations:
            _retain_declaration(runtime, space, declaration)
            retained.append(declaration)
        for fact in new_facts:
            if fact not in old_facts:
                _reflect_add(runtime, fact)
                added_facts.append(fact)
    except BaseException:
        for fact in added_facts:
            _reflect_remove(runtime, fact)
        for declaration in retained:
            _release_declaration(runtime, space, declaration)
        if previous is not None:
            runtime.must(
                "petta_py_register_op_set(Name, Arities, Kind)",
                Name=previous.name,
                Arities=list(previous.arities or (previous.arity,)),
                Kind=previous.kind,
            )
        else:
            for arity in arities:
                runtime.must(
                    "petta_py_unregister_op(Name, Arity)",
                    Name=metta_name,
                    Arity=arity,
                )
        raise
    # Committed: the previous life retires, shared pieces surviving. Facts
    # equal in both lives were never re-added, so they are not removed;
    # declarations release through the refcount, staying while any other
    # owner still declares them.
    if previous is not None:
        for fact in old_facts:
            if fact not in new_facts:
                _reflect_remove(runtime, fact)
        for declaration in previous.declarations:
            _release_declaration(runtime, previous.space or space, declaration)
    REGISTRY[metta_name] = operation
    return fn


def unregister(runtime, name: str) -> None:
    """Remove every arity of a registered operation, and every declaration
    registration added, so nothing keeps describing a function that no
    longer exists."""
    op = REGISTRY.get(name)
    for arity_row in list(runtime.iter("petta_py_op_spec(Name, Arity, _)", Name=name)):
        runtime.must("petta_py_unregister_op(Name, Arity)", Name=name, Arity=arity_row["Arity"])
    if op is not None:
        for declaration in op.declarations:
            _release_declaration(runtime, op.space or "&self", declaration)
        for fact in _op_facts(op):
            _reflect_remove(runtime, fact)
    REGISTRY.pop(name, None)


def registered() -> dict[str, Operation]:
    """The live registry, name to operation."""
    return dict(REGISTRY)
