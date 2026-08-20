"""Purpose: translate Python annotations into MeTTa type atoms and declarations.
Guarantees:
  - postponed annotations resolve before declaration generation [tested
    test_postponed_annotations_generate_declarations]
  - union expansion is bounded by the configured declaration limit [tested
    test_union_expansion_is_bounded]
  - every host atom class keeps its engine metatype at the annotation seam
    [tested: test_the_four_metatypes_stay_distinct_across_the_seam;
     commit=4b340e87ea282045d5bfa7c00a722353dd69a968]
  - full container parameters survive as matchable annotation atoms while
    the runtime type stays MeTTa's Expression
    [tested: test_the_four_containers_share_one_parameterised_treatment;
     commit=4b340e87ea282045d5bfa7c00a722353dd69a968]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import inspect
import itertools
import types
import typing
from collections import abc
from collections.abc import Callable, Iterable
from typing import Any

from ._config import config
from ._convert_registry import _lookup as _lookup_conversion
from ._parameterized import hook_for as _parameterized_hook
from .atoms import Atom, Expr, Gnd, S, Sym, Var, expr

_TYPE_NAMES: tuple[tuple[type, str], ...] = (
    (bool, "Bool"),
    (int, "Number"),
    (float, "Number"),
    (str, "String"),
)

_METATYPE_NAMES: dict[type[Atom], str] = {
    Atom: "Atom",
    Sym: "Symbol",
    Var: "Variable",
    Expr: "Expression",
    Gnd: "Grounded",
}


def metta_type_for(annotation: Any) -> str:
    """Return the scalar MeTTa type named by a Python annotation."""
    if annotation is inspect.Parameter.empty or annotation is Any:
        return "%Undefined%"
    if annotation in _METATYPE_NAMES:
        return _METATYPE_NAMES[annotation]
    for python_type, name in _TYPE_NAMES:
        if annotation is python_type:
            return name
    return "%Undefined%"


def type_atom_for(annotation: Any) -> Atom:
    """Return the first MeTTa type alternative for an annotation."""
    return type_atoms_for(annotation)[0]


def annotation_atom_for(annotation: Any) -> Atom:
    """Project a Python annotation itself, preserving generic parameters."""
    hook = _parameterized_hook(annotation)
    if hook is not None:
        return hook.annotation_atom(annotation, annotation_atom_for)
    alternatives = type_atoms_for(annotation)
    if len(alternatives) == 1:
        return alternatives[0]
    return Expr([S.Union, *alternatives])


def _direct_type_atoms(annotation: Any, origin: Any) -> list[Atom] | None:
    if annotation is inspect.Parameter.empty or annotation is Any or annotation is object:
        return [S["%Undefined%"]]
    if annotation is None or annotation is type(None):
        return [S.NoneType]
    if isinstance(annotation, typing.TypeVar):
        return [Var(annotation.__name__.lower())]
    if origin is not None:
        return None
    if isinstance(annotation, type) and metta_type_for(annotation) == "%Undefined%":
        return [S[_class_type_name(annotation)]]
    return [S[metta_type_for(annotation)]]


def _union_type_atoms(annotation: Any) -> list[Atom]:
    alternatives: list[Atom] = []
    seen: set[str] = set()
    for member in typing.get_args(annotation):
        for atom in type_atoms_for(member):
            _add_unique(alternatives, seen, atom)
    return alternatives


def _callable_type_atoms(annotation: Any) -> list[Atom]:
    args = typing.get_args(annotation)
    if not args or args[0] is Ellipsis:
        return [S["%Undefined%"]]
    argument_types, return_type = list(args[0]), args[1]
    arrows: list[Atom] = []
    seen: set[str] = set()
    argument_alternatives = [type_atoms_for(item) for item in argument_types]
    argument_alternatives.append(type_atoms_for(return_type))
    for combination in _bounded_product(
        argument_alternatives,
        f"the Callable annotation {annotation!r}",
    ):
        _add_unique(arrows, seen, Expr([S["->"], *combination]))
    return arrows


def _tuple_type_atoms(annotation: Any) -> list[Atom]:
    args = typing.get_args(annotation)
    if args and args[-1] is Ellipsis:
        return [S.Expression]
    shapes: list[Atom] = []
    seen: set[str] = set()
    for combination in _bounded_product(
        [type_atoms_for(item) for item in args],
        f"the tuple annotation {annotation!r}",
    ):
        _add_unique(shapes, seen, Expr(list(combination)))
    return shapes


def _generic_type_atoms(origin: Any) -> list[Atom]:
    if not isinstance(origin, type):
        return [S["%Undefined%"]]
    if issubclass(origin, abc.Mapping):
        if not inspect.isabstract(origin):
            return [S[_class_type_name(origin)]]
        return [S["%Undefined%"]]
    if origin is list or issubclass(origin, abc.Sequence):
        return [S.Expression]
    if not inspect.isabstract(origin):
        return [S[_class_type_name(origin)]]
    return [S["%Undefined%"]]


def type_atoms_for(annotation: Any) -> list[Atom]:
    """Return every MeTTa type alternative named by an annotation."""
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return type_atoms_for(typing.get_args(annotation)[0])
    direct = _direct_type_atoms(annotation, origin)
    if direct is not None:
        return direct
    if origin in (typing.Union, types.UnionType):
        return _union_type_atoms(annotation)
    if origin is abc.Callable:
        return _callable_type_atoms(annotation)
    hook = _parameterized_hook(annotation)
    if hook is not None:
        return [hook.type_atom(annotation, type_atoms_for)]
    if origin is tuple:
        return _tuple_type_atoms(annotation)
    return _generic_type_atoms(origin)


def _class_type_name(cls: type) -> str:
    registration = _lookup_conversion(cls)
    return registration.type_name if registration is not None else cls.__name__


def _add_unique(items: list, seen: set, atom: Atom) -> None:
    key = str(atom)
    if key not in seen:
        seen.add(key)
        items.append(atom)


def _bounded_product(alternative_lists: list[list[Atom]], described: str):
    limit = config.declaration_limit
    total = 1
    for alternatives in alternative_lists:
        total *= max(1, len(alternatives))
        if total > limit:
            raise TypeError(
                f"{described} expands to over {limit} superposed combinations; "
                "simplify the Unions, or register with typed=False and declare by hand"
            )
    return itertools.product(*alternative_lists)


def declaration_exprs(name: str, arg_annotations: list, ret_annotation: Any) -> list[Expr]:
    """Build every bounded declaration alternative for one signature."""
    arg_lists = [type_atoms_for(annotation) for annotation in arg_annotations]
    return_types = [atom for atom in type_atoms_for(ret_annotation) if atom != S.NoneType] or [
        S["%Undefined%"]
    ]
    declarations: list[Expr] = []
    seen: set[str] = set()
    for combination in _bounded_product(
        [*arg_lists, return_types],
        f"the signature of {name}",
    ):
        declaration = expr(S[":"], S[name], Expr([S["->"], *combination]))
        _add_unique(declarations, seen, declaration)
    return declarations


def annotation_exprs(
    name: str, arg_annotations: list[Any], ret_annotation: Any
) -> list[Expr]:
    """Represent full Python annotations as ordinary, matchable claims."""
    claims = [
        expr(
            S.annotation,
            S[name],
            expr(S.param, index, annotation_atom_for(annotation)),
        )
        for index, annotation in enumerate(arg_annotations, start=1)
    ]
    claims.append(
        expr(S.annotation, S[name], expr(S["return"], annotation_atom_for(ret_annotation)))
    )
    return claims


def referenced_classes(annotations: Iterable[Any]) -> list[type]:
    """Return concrete user classes mentioned anywhere in annotations."""
    found: list[type] = []

    def collect(cls: Any) -> None:
        if (
            isinstance(cls, type)
            and metta_type_for(cls) == "%Undefined%"
            and not inspect.isabstract(cls)
            and cls.__module__ != "builtins"
            and cls not in found
        ):
            found.append(cls)

    def walk(annotation: Any) -> None:
        if annotation is None or annotation is type(None):
            return
        if annotation is inspect.Parameter.empty or annotation is Any or annotation is object:
            return
        if isinstance(annotation, type):
            collect(annotation)
            return
        origin = typing.get_origin(annotation)
        if origin is typing.Annotated:
            walk(typing.get_args(annotation)[0])
            return
        collect(origin)
        for argument in typing.get_args(annotation):
            if argument is Ellipsis:
                continue
            if isinstance(argument, (list, tuple)):
                for inner in argument:
                    walk(inner)
            else:
                walk(argument)

    for annotation in annotations:
        walk(annotation)
    return found


def callable_name(fn: Callable) -> str:
    """Return a stable diagnostic label for a callable."""
    name = getattr(fn, "__name__", None)
    return name if isinstance(name, str) and name else type(fn).__name__


def resolved_annotations(fn: Callable) -> dict[str, Any]:
    """Resolve postponed annotations or raise a diagnostic naming the callable."""
    try:
        return typing.get_type_hints(fn)
    except Exception as exc:
        raise TypeError(
            f"the annotations of {callable_name(fn)} do not resolve "
            f"({exc}); a declared type must name something importable"
        ) from exc
