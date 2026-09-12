"""Purpose: translate Python annotations into MeTTa type atoms and declarations.
Guarantees:
  - postponed annotations resolve before declaration generation [tested
    test_postponed_annotations_generate_declarations]
  - union expansion is bounded by the configured declaration limit and its
    refusal points to unannotated wrappers plus explicit declaration atoms
    [tested: test_union_expansion_is_bounded; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every host atom class keeps its engine metatype at the annotation boundary
    [tested: test_the_four_metatypes_stay_distinct_across_the_seam;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - full container parameters survive as matchable annotation atoms while
    the runtime type stays MeTTa's Expression
    [tested: test_the_four_containers_share_one_parameterised_treatment;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - advanced typing constructs retain a target type and a full annotation
    claim rather than collapsing to an undefined type
    [tested: test_every_advanced_annotation_reaches_metta_as_a_target_symbol;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - Annotated Atom metadata refines arrow alternatives; all metadata remains
    matchable in annotation claims and the base selects runtime conversion
    [tested: test_atom_metadata_refines_annotation_alternatives,
    test_two_values_of_one_base_type_are_distinguishable_by_their_metadata;
    commit=4eaefdd8d40e53b2613722287302a14b41704662]
  - an annotated_types constraint refines the same way, through its encoded
    atom, when that atom's head is in the catalog's refinement vocabulary;
    ``doc`` and ``Timezone`` stay in the annotation claim alone
    [tested: test_a_refined_signature_declares_the_refined_arrow,
    test_doc_and_timezone_stay_in_the_annotation_claim; commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - the public Space handle annotation denotes the engine's ``SpaceType``
    instead of declaring an unrelated user type [tested:
    test_compiled_removal_statements_preserve_one_many_missing_and_target_scope;
    commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]
  - Literal values refine their runtime base types by exact membership
    [tested: test_literal_signatures_enforce_membership_at_both_crossings;
    commit=WORKTREE]
  - an annotation the runtime cannot name costs only itself: the annotations
    beside it still declare their types, and the refusal fires where the
    unresolvable one is consumed as a type [tested:
    test_one_unresolvable_annotation_costs_only_itself,
    test_an_unresolvable_annotation_an_arity_reaches_still_refuses,
    test_every_resolvable_annotation_kind_survives_the_per_annotation_pass;
    commit=77d3b82aeb856e5d811e83e598138925bfc40e17]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import functools
import inspect
import itertools
import sys
import types
import typing
from collections import abc
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Handle,
    S,
    Symbol,
    Undefined,
    Variable,
    _encode,
    _expr,
)
from metta._atoms.registry import _lookup as _lookup_conversion
from metta._catalog.bounds import config
from metta._catalog.containers import hook_for as _parameterized_hook
from metta._catalog.refinements import refinement_atom
from metta._lazy import lazy

_TYPE_NAMES: tuple[tuple[type, str], ...] = (
    (bool, "Bool"),
    (int, "Number"),
    (float, "Number"),
    (complex, "Number"),
    (str, "String"),
)

_METATYPE_NAMES: dict[type[Atom], str] = {
    Atom: "Atom",
    Symbol: "Symbol",
    Variable: "Variable",
    Expression: "Expression",
    Grounded: "Grounded",
}


def metta_type_for(annotation: Any) -> str:
    """Return the scalar MeTTa type named by a Python annotation."""
    if annotation is inspect.Parameter.empty or annotation is Any:
        return "%Undefined%"
    if annotation in _METATYPE_NAMES:
        return _METATYPE_NAMES[annotation]
    # Native identity belongs to the handle base, including generated and
    # user subclasses. The call-time import keeps the annotation layer below
    # the handle layer [tested: test_native_space_annotations_follow_the_handle_base;
    # commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
    if (isinstance(annotation, type) and issubclass(annotation, Handle)
            and issubclass(annotation, lazy("metta._spaces.handle").SpaceHandle)):
        return "SpaceType"
    for python_type, name in _TYPE_NAMES:
        if annotation is python_type:
            return name
    return "%Undefined%"


def type_atom_for(annotation: Any) -> Atom:
    """Return the first MeTTa type alternative for an annotation."""
    return type_atoms_for(annotation)[0]


def annotation_atom_for(annotation: Any) -> Atom:
    """Project a Python annotation itself, preserving generic parameters.

    An atom is already the projection and travels unchanged.
    """
    if isinstance(annotation, Atom):
        return annotation
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        base, *metadata = typing.get_args(annotation)
        return Expression(
            [
                S.Annotated,
                annotation_atom_for(base),
                *(item if isinstance(item, Atom) else _encode(item) for item in metadata),
            ]
        )
    if isinstance(annotation, typing.TypeVar):
        if annotation.__constraints__:
            return Expression(
                [
                    S.TypeVar,
                    Variable(annotation.__name__.lower()),
                    Expression([S["one_of"], *(annotation_atom_for(item) for item in annotation.__constraints__)]),
                ]
            )
        if annotation.__bound__ is not None:
            return Expression(
                [
                    S.TypeVar,
                    Variable(annotation.__name__.lower()),
                    Expression([S.bound, annotation_atom_for(annotation.__bound__)]),
                ]
            )
        return Variable(annotation.__name__.lower())
    if _is_new_type(annotation):
        return Expression(
            [S.NewType, S[annotation.__name__], annotation_atom_for(annotation.__supertype__)]
        )
    if origin is typing.Literal:
        return Expression([S.Literal, *(_encode(value) for value in typing.get_args(annotation))])
    if origin in _type_predicate_origins():
        return Expression([S[origin.__name__], annotation_atom_for(typing.get_args(annotation)[0])])
    if origin is type:
        arguments = typing.get_args(annotation)
        return Expression([S.type, *(annotation_atom_for(item) for item in arguments)])
    if annotation in (typing.Never, typing.NoReturn):
        return S["Empty"]
    if annotation is typing.Self:
        return Variable("t")
    hook = _parameterized_hook(annotation)
    if hook is not None:
        return hook.annotation_atom(annotation, annotation_atom_for)
    alternatives = type_atoms_for(annotation)
    if len(alternatives) == 1:
        return alternatives[0]
    return Expression([S.Union, *alternatives])


def _direct_type_atoms(annotation: Any, origin: Any) -> list[Atom] | None:
    if annotation is inspect.Parameter.empty or annotation is Any:
        return [S["%Undefined%"]]
    if annotation is Undefined:
        # The canonical table's own row: the class REPRESENTS %Undefined%,
        # and mapping it by class NAME built the ordinary symbol Undefined,
        # which the engine reads as a user type and the metatype declaration
        # silently did nothing [measured 2026-08-24 by the libraries twins
        # agent: arrow(Atom, Atom, metta.Undefined) stored (-> Atom Atom
        # Undefined) and letstarcomputed's first claim answered []].
        return [S["%Undefined%"]]
    if annotation is object:
        return [S["Atom"]]
    if annotation is None or annotation is type(None):
        return [S["NoneType"]]
    if isinstance(annotation, typing.TypeVar):
        if annotation.__constraints__:
            return _typevar_constraints(annotation)
        if annotation.__bound__ is not None:
            return type_atoms_for(annotation.__bound__)
        return [Variable(annotation.__name__.lower())]
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
        _add_unique(arrows, seen, Expression([S["->"], *combination]))
    return arrows


def _tuple_type_atoms(annotation: Any) -> list[Atom]:
    args = typing.get_args(annotation)
    if args and args[-1] is Ellipsis:
        return [S["Expression"]]
    shapes: list[Atom] = []
    seen: set[str] = set()
    for combination in _bounded_product(
        [type_atoms_for(item) for item in args],
        f"the tuple annotation {annotation!r}",
    ):
        _add_unique(shapes, seen, Expression(list(combination)))
    return shapes


def _generic_type_atoms(origin: Any) -> list[Atom]:
    if not isinstance(origin, type):
        return [S["%Undefined%"]]
    if issubclass(origin, abc.Mapping):
        if not inspect.isabstract(origin):
            return [S[_class_type_name(origin)]]
        return [S["%Undefined%"]]
    if origin is list or issubclass(origin, abc.Sequence):
        return [S["Expression"]]
    if not inspect.isabstract(origin):
        return [S[_class_type_name(origin)]]
    return [S["%Undefined%"]]


def type_atoms_for(annotation: Any) -> list[Atom]:
    """Return every MeTTa type alternative named by an annotation.

    An ATOM in annotation position is the type itself, the direction the
    builders already read: ``typed(S.a, S.Number)`` and
    ``arrow(S.Number, S.Bool)`` take an atom or a Python type either way, and a
    signature took only the Python type, so ``def speak(a: S.Animal)`` declared
    ``(-> %Undefined% ...)`` and said nothing. It is the escape hatch the table
    needs, because the table is many-to-one and finite: a MeTTa type with no
    Python class had to be given one, and two shipped twins declare an empty
    class for no reason but to name a type in a signature.
    """
    # The refusal comes first: an annotation the runtime could not name is not
    # a type, and an atom is one already.
    if isinstance(annotation, Unresolved):
        raise annotation.refusal()
    if isinstance(annotation, Atom):
        return [annotation]
    origin = typing.get_origin(annotation)
    if _is_new_type(annotation):
        return [S[annotation.__name__]]
    if origin is typing.Literal:
        return _literal_type_atoms(annotation)
    if origin in _type_predicate_origins():
        return [S["Bool"]]
    if annotation in (typing.Never, typing.NoReturn):
        return [S["Empty"]]
    if annotation is typing.Self:
        return [Variable("t")]
    if annotation is typing.LiteralString:
        return [S["String"]]
    if origin is type:
        return [S["Type"]]
    if origin in (typing.Required, typing.NotRequired):
        return type_atoms_for(typing.get_args(annotation)[0])
    if origin is typing.Annotated:
        base, *metadata = typing.get_args(annotation)
        alternatives = type_atoms_for(base)
        # An Atom already names MeTTa structure at a type boundary, and a
        # metadata object whose atom heads the refinement vocabulary is a
        # constraint the engine decides on the value. Every other item stays
        # in annotation_atom_for's catalog projection.
        refinements = [atom for atom in map(refinement_atom, metadata) if atom is not None]
        if refinements:
            return [Expression([S.Annotated, atom, *refinements]) for atom in alternatives]
        return alternatives
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


def _type_predicate_origins() -> tuple[Any, ...]:
    return tuple(
        predicate
        for predicate in (
            getattr(typing, "TypeIs", None),
            getattr(typing, "TypeGuard", None),
        )
        if predicate is not None
    )


def _is_new_type(annotation: Any) -> bool:
    return callable(annotation) and hasattr(annotation, "__supertype__")


def _literal_type_atoms(annotation: Any) -> list[Atom]:
    members: dict[Atom, list[Atom]] = {}
    for value in typing.get_args(annotation):
        encoded = _encode(value)
        for base in type_atoms_for(type(value)):
            values = members.setdefault(base, [])
            if encoded not in values:
                values.append(encoded)
    return [_expr(S.Annotated, base, _expr(S.Literal, *values))
            for base, values in (members or {S.Atom: []}).items()]


def _typevar_constraints(annotation: typing.TypeVar) -> list[Atom]:
    alternatives: list[Atom] = []
    seen: set[str] = set()
    for constraint in annotation.__constraints__:
        for atom in type_atoms_for(constraint):
            _add_unique(alternatives, seen, atom)
    return alternatives


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
            msg = (
                f"{described} expands to over {limit} superposed combinations; "
                "simplify the Unions, or wrap the callable with an unannotated "
                "signature and supply declaration atoms explicitly"
            )
            raise TypeError(
                msg
            )
    return itertools.product(*alternative_lists)


def declaration_exprs(name: str, arg_annotations: list, ret_annotation: Any) -> list[Expression]:
    """Build every bounded declaration alternative for one signature."""
    arg_lists = [type_atoms_for(annotation) for annotation in arg_annotations]
    return_types = [atom for atom in type_atoms_for(ret_annotation) if atom != S.NoneType] or [
        S["%Undefined%"]
    ]
    declarations: list[Expression] = []
    seen: set[str] = set()
    for combination in _bounded_product(
        [*arg_lists, return_types],
        f"the signature of {name}",
    ):
        declaration = _expr(S[":"], S[name], Expression([S["->"], *combination]))
        _add_unique(declarations, seen, declaration)
    return declarations


def annotation_exprs(
    name: str, arg_annotations: list[Any], ret_annotation: Any
) -> list[Expression]:
    """Represent full Python annotations as ordinary, matchable claims."""
    claims = [
        _expr(
            S.annotation,
            S[name],
            _expr(S.param, index, annotation_atom_for(annotation)),
        )
        for index, annotation in enumerate(arg_annotations, start=1)
    ]
    claims.append(
        _expr(S.annotation, S[name], _expr(S["return"], annotation_atom_for(ret_annotation)))
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
    """Return a stable diagnostic label for a callable.

    A functools.partial carries no __name__, so it would answer "partial" and
    two unnamed partials would collide on that one MeTTa name. The wrapped
    callable is the one the caller meant.
    """
    while isinstance(fn, functools.partial):
        fn = fn.func
    name = getattr(fn, "__name__", None)
    return name if isinstance(name, str) and name else type(fn).__name__


#: The code object every single-annotation probe below borrows. A probe is a
#: function so that typing.get_type_hints resolves it exactly as it resolves
#: the callable it stands in for: same globals, same type parameters, same
#: ForwardRef handling for a postponed string. Nothing ever calls one.
_PROBE_CODE = (lambda: None).__code__


@dataclass(frozen=True)
class Unresolved:
    """One annotation that names something the runtime cannot resolve.

    It stands in the resolved mapping where the type would be, so the
    annotations beside it stay usable and the refusal happens where the
    annotation is CONSUMED as a type rather than where the map is built.
    ``target: Space`` with the import missing must still refuse loudly, and
    it does: type_atoms_for raises this refusal the moment it is asked to
    turn one into a type atom.
    """

    owner: str
    parameter: str
    reason: str

    def refusal(self) -> TypeError:
        """The loud refusal, naming the parameter rather than the callable."""
        where = "return annotation" if self.parameter == "return" else f"parameter {self.parameter!r}"
        return TypeError(
            f"the {where} of {self.owner} does not resolve ({self.reason}); "
            f"a declared type must name something importable"
        )


#The annotations AS WRITTEN, without evaluating any of them.
#
#Reading __annotations__ is the whole story before 3.14. From 3.14 the
#attribute EVALUATES the deferred annotations (PEP 649), so a name that
#resolves nowhere raises out of the read itself, and annotationlib's
#FORWARDREF format is the documented way to get the written form back
#[source: https://docs.python.org/3.14/library/annotationlib.html]. The
#version guard is the definition rather than a branch inside one, because
#annotationlib does not exist to import at all on the versions below it.
if sys.version_info >= (3, 14):
    import annotationlib

    def _written_annotations(fn: Callable) -> dict[str, Any]:
        """Every annotation this callable carries, unevaluated."""
        return dict(
            annotationlib.get_annotations(fn, format=annotationlib.Format.FORWARDREF)
        )

else:

    def _written_annotations(fn: Callable) -> dict[str, Any]:
        """Every annotation this callable carries, unevaluated."""
        return dict(getattr(fn, "__annotations__", None) or {})


def _one_at_a_time(fn: Callable) -> dict[str, Any]:
    """Resolve each annotation on its own, so one bad name costs only itself.

    get_type_hints is all-or-nothing over a whole signature: one parameter
    naming something importable only under TYPE_CHECKING discarded every
    other annotation and refused the registration, including one on a
    parameter no declared arity reaches. Each annotation goes to
    get_type_hints alone, on a probe function carrying the same globals and
    the same type parameters, which is what makes `item: T` and a postponed
    `"list[int]"` resolve here exactly as they resolve in the whole-signature
    pass.
    """
    namespace = fn
    while hasattr(namespace, "__wrapped__"):
        namespace = namespace.__wrapped__
    globalns = getattr(namespace, "__globals__", {})
    type_params = getattr(namespace, "__type_params__", ())
    owner = callable_name(fn)
    resolved: dict[str, Any] = {}
    for parameter, written in _written_annotations(fn).items():
        probe = types.FunctionType(_PROBE_CODE, globalns)
        probe.__annotations__ = {parameter: written}
        probe.__type_params__ = type_params
        try:
            resolved[parameter] = typing.get_type_hints(probe, include_extras=True)[
                parameter
            ]
        except Exception as exc:  # noqa: BLE001  -- any resolution failure is this one annotation's, and the reason travels in the refusal
            resolved[parameter] = Unresolved(owner, parameter, str(exc))
    return resolved


def resolved_annotations(fn: Callable) -> dict[str, Any]:
    """Resolve a callable's postponed annotations.

    The whole-signature pass runs first and answers unchanged whenever it can,
    which is every ordinary callable. Only a signature it refuses is resolved
    one annotation at a time, and each annotation that still cannot resolve
    becomes an Unresolved standing in for it.
    """
    #get_type_hints introspects modules, classes, methods and functions. Two
    #ordinary callables are none of those: a functools.partial, and an instance
    #whose class defines __call__. 3.14 answers {} for both while 3.12 and 3.13
    #raise "is not a module, class, method, or function", which this function
    #then reported as annotations that do not resolve, blaming the annotations
    #for the object's kind. Ask about the thing that carries them: the wrapped
    #callable for a partial, and __call__ for an instance.
    while isinstance(fn, functools.partial):
        fn = fn.func
    if callable(fn) and not (
        inspect.isfunction(fn)
        or inspect.ismethod(fn)
        or inspect.isclass(fn)
        or inspect.ismodule(fn)
        or inspect.isbuiltin(fn)
    ):
        #An instance that names what it wraps, a Defined and its twin
        #dispatcher among them, carries that function's annotations; only an
        #instance that wraps nothing is asked about its __call__.
        fn = inspect.unwrap(fn) if hasattr(fn, "__wrapped__") else type(fn).__call__
    try:
        return typing.get_type_hints(fn, include_extras=True)
    except Exception:  # noqa: BLE001  -- the per-annotation pass reports which annotation failed and why
        return _one_at_a_time(fn)


def for_conversion(annotations: dict[str, Any]) -> dict[str, Any]:
    """The same mapping with each unresolvable annotation read as Any.

    Value conversion at the call boundary asks what a parameter's declared
    type is; "we could not name it" is Any there, the same answer an
    unannotated parameter gives. The arrow declarations refuse first for
    every annotation an arity reaches, so this only ever softens one no
    declared call form uses.
    """
    return {
        name: (Any if isinstance(value, Unresolved) else value)
        for name, value in annotations.items()
    }
