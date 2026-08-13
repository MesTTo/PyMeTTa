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
from typing import Any, Callable

from .atoms import Atom, Expr, S, Sym, Var, expr
from ._ops import REGISTRY, Operation

__all__ = [
    "register",
    "unregister",
    "metta_type_for",
    "type_atom_for",
    "type_atoms_for",
    "declaration_exprs",
    "referenced_classes",
    "class_declarations",
    "registered",
]

# Python annotation -> MeTTa type name. Everything else is %Undefined%,
# matching what the engine says about an undeclared value.
_TYPE_NAMES: list[tuple[type, str]] = [
    (bool, "Bool"),  # before int: bool is an int in Python, not in MeTTa
    (int, "Number"),
    (float, "Number"),
    (str, "String"),
]


def metta_type_for(annotation: Any) -> str:
    """The MeTTa type a Python annotation names."""
    if annotation is inspect.Parameter.empty or annotation is Any:
        return "%Undefined%"
    if annotation in (Atom, Expr, Sym, Var):
        return "Atom"
    for py, name in _TYPE_NAMES:
        if annotation is py:
            return name
    return "%Undefined%"


def type_atom_for(annotation: Any) -> Atom:
    """The annotation as one atom; the first alternative when several
    superpose. type_atoms_for is the full mapping."""
    return type_atoms_for(annotation)[0]


def type_atoms_for(annotation: Any) -> list[Atom]:
    """Every MeTTa type an annotation names, mapped by the representation
    its values take when they cross. Alternatives superpose the way the
    checker already treats multiple declarations, so a Union contributes
    one atom per member and the checker collects. The cases:

    - a TypeVar becomes the engine's own type VARIABLE, so
      head(items: Sequence[A]) -> A is (-> Expression $a) and the checker
      propagates the binding per call;
    - Union[A, B] and A | B answer both members' atoms;
    - Optional[T] is Union[T, None], and None crosses as a NoneType handle,
      so it answers T's atoms plus NoneType (the declaration builder drops
      NoneType from return position, where returning None answers nothing);
    - Callable[[A, B], R] is the arrow (-> A B R), the type a declared
      function symbol itself answers to get-type;
    - tuple[A, B] is the elementwise (A B), which is get-type's own answer
      for a raw pair; tuple[A, ...] and other Sequences are Expression;
    - a class names its declared type, the name get-type answers for its
      instances, whether they cross as constructor terms or as handles;
    - an abstract origin whose values have no one representation stays
      %Undefined%, the engine's own spelling for uncommitted."""
    import typing

    if annotation is inspect.Parameter.empty or annotation is Any or annotation is object:
        return [S["%Undefined%"]]
    if annotation is None or annotation is type(None):
        return [S.NoneType]
    if isinstance(annotation, typing.TypeVar):
        return [Var(annotation.__name__.lower())]
    origin = typing.get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type) and metta_type_for(annotation) == "%Undefined%":
            return [S[_class_type_name(annotation)]]
        return [S[metta_type_for(annotation)]]

    import types as _types

    if origin in (typing.Union, _types.UnionType):
        alts: list[Atom] = []
        for member in typing.get_args(annotation):
            for atom in type_atoms_for(member):
                if atom not in alts:
                    alts.append(atom)
        return alts

    import collections.abc as abc

    if origin is abc.Callable:
        args = typing.get_args(annotation)
        if not args or args[0] is Ellipsis:
            return [S["%Undefined%"]]
        arg_lists, ret = list(args[0]), args[1]
        arrows: list[Atom] = []
        for combo in _combinations([type_atoms_for(a) for a in arg_lists]
                                   + [type_atoms_for(ret)]):
            arrow = Expr([S["->"], *combo])
            if arrow not in arrows:
                arrows.append(arrow)
        return arrows
    if origin is tuple:
        args = typing.get_args(annotation)
        if args and args[-1] is Ellipsis:
            return [S.Expression]
        shapes: list[Atom] = []
        for combo in _combinations([type_atoms_for(a) for a in args]):
            shape = Expr(list(combo))
            if shape not in shapes:
                shapes.append(shape)
        return shapes
    if isinstance(origin, type):
        if issubclass(origin, abc.Mapping):
            if not inspect.isabstract(origin):
                return [S[_class_type_name(origin)]]
            return [S["%Undefined%"]]
        if origin is list or issubclass(origin, abc.Sequence):
            return [S.Expression]
        if not inspect.isabstract(origin):
            return [S[_class_type_name(origin)]]
    return [S["%Undefined%"]]


def _class_type_name(cls: type) -> str:
    """The MeTTa name a class's instances answer to get-type: the
    registered spelling when the translator knows the class, its own
    name otherwise."""
    from . import convert

    registration = convert._lookup(cls)
    return registration.type_name if registration is not None else cls.__name__


def _combinations(alternative_lists: list[list[Atom]]):
    import itertools

    return itertools.product(*alternative_lists)


def declaration_exprs(name: str, arg_annotations: list, ret_annotation: Any) -> list[Expr]:
    """Every (: name (-> ...)) atom a signature declares: the cross product
    of each argument's alternatives with the return's, one declaration per
    combination, superposing for the checker exactly as a Union reads.
    NoneType leaves the return alternatives, because returning None answers
    nothing rather than a value; a return that was only None declares
    %Undefined%."""
    arg_lists = [type_atoms_for(a) for a in arg_annotations]
    ret_alts = [t for t in type_atoms_for(ret_annotation) if t != S.NoneType]
    if not ret_alts:
        ret_alts = [S["%Undefined%"]]
    out: list[Expr] = []
    for combo in _combinations(arg_lists + [ret_alts]):
        declaration = expr(S[":"], S[name], Expr([S["->"], *combo]))
        if declaration not in out:
            out.append(declaration)
    return out


def referenced_classes(annotations: Iterable[Any]) -> list[type]:
    """Every user class an annotation tree mentions, so registration can
    declare the types it references: a type in MeTTa is a declaration, and
    a signature naming Point should make (: Point ...) exist rather than
    leave the name dangling."""
    import typing

    found: list[type] = []

    def walk(annotation: Any) -> None:
        if annotation is None or annotation is type(None):
            return
        if annotation is inspect.Parameter.empty or annotation is Any or annotation is object:
            return
        if isinstance(annotation, type):
            if (
                metta_type_for(annotation) == "%Undefined%"
                and not inspect.isabstract(annotation)
                and annotation.__module__ not in ("builtins",)
                and annotation not in found
            ):
                found.append(annotation)
            return
        for arg in typing.get_args(annotation):
            if arg is Ellipsis:
                continue
            if isinstance(arg, (list, tuple)):
                for inner in arg:
                    walk(inner)
            else:
                walk(arg)

    for annotation in annotations:
        walk(annotation)
    return found


def class_declarations(cls: type) -> list[Expr]:
    """The (: ...) atoms that make a class a MeTTa type: the translator's
    own declarations for an Enum, dataclass or NamedTuple (constructor
    arrows, member typings), and the plain (: Name Type) for any other
    class, whose instances already answer the name to get-type."""
    from . import convert

    declared = list(convert.declarations(cls))
    if declared:
        return declared
    return [expr(S[":"], S[_class_type_name(cls)], S.Type)]


def resolved_annotations(fn: Callable) -> dict[str, Any]:
    """The function's annotations as real types, never text: under
    `from __future__ import annotations` the raw __annotations__ are
    strings, which would all read as %Undefined% and silently drop the
    declared types. Unresolvable annotations are a hard error naming the
    function."""
    import typing

    try:
        return typing.get_type_hints(fn)
    except Exception as exc:
        raise TypeError(
            f"the annotations of {fn.__name__} do not resolve "
            f"({exc}); a declared type must name something importable"
        ) from exc


def _metta_name(fn: Callable, name: str | None) -> str:
    """The MeTTa spelling: underscores read as hyphens unless overridden."""
    return name if name is not None else fn.__name__.replace("_", "-")


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
                f"cannot register {fn.__name__}: keyword-only parameter "
                f"{p.name!r} is unreachable from a positional MeTTa call site"
            )
        params.append(p)
    if explicit is not None:
        return sorted(set(explicit)), params
    if variadic:
        raise TypeError(
            f"cannot register {fn.__name__}: *args has no single MeTTa call "
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
    # The engine registers every arity in one checked step (a collision with
    # a static procedure throws with nothing touched, and stale arities from
    # an earlier registration of the name are replaced, never left behind);
    # the Python registry commits only after the engine accepted.
    runtime.must(
        "petta_py_register_op_set(Name, Arities, Kind)",
        Name=metta_name,
        Arities=list(arities),
        Kind=kind,
    )
    declarations = (
        tuple(_type_declarations(metta_name, params, fn)) if typed and params else ()
    )
    for declaration in declarations:
        runtime.must("petta_py_add(Space, W)", Space=space, W=declaration.to_wire())
    REGISTRY[metta_name] = Operation(
        name=metta_name,
        fn=fn,
        kind=kind,
        arity=max(arities),
        pass_atoms=pass_atoms,
        space=space,
        declarations=declarations,
    )
    return fn


def unregister(runtime, name: str) -> None:
    """Remove every arity of a registered operation, and every declaration
    registration added, so nothing keeps describing a function that no
    longer exists."""
    op = REGISTRY.get(name)
    for arity_row in list(
        runtime.iter("petta_py_op_spec(Name, Arity, _)", Name=name)
    ):
        runtime.must(
            "petta_py_unregister_op(Name, Arity)", Name=name, Arity=arity_row["Arity"]
        )
    if op is not None:
        for declaration in op.declarations:
            runtime.once(
                "petta_py_remove(Space, W, _)",
                Space=op.space,
                W=declaration.to_wire(),
            )
    REGISTRY.pop(name, None)


def registered() -> dict[str, Operation]:
    """The live registry, name to operation."""
    return dict(REGISTRY)
