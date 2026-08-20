"""Purpose: registration of Python callables as MeTTa functions. Reads the
signature for arities (defaults yield several), auto-detects nondeterminism
(a generator function is one), derives a MeTTa type declaration from the
annotations, and registers the whole thing with the engine through shim.pl.
Guarantees:
  - registration distinguishes a MeTTa function name from its declaration
    space [tested test_public_context_types_are_distinct]
  - full annotations become ordinary claims in the declaration space
    [tested: test_the_four_containers_share_one_parameterised_treatment;
     commit=4224c26819d90b9e03efdaef78cb573b91729295]
  - overload stubs each contribute their declared arrow and annotation claims
    [tested: test_every_advanced_annotation_reaches_metta_as_a_target_symbol;
     commit=4224c26819d90b9e03efdaef78cb573b91729295]
  - unreachable **kwargs refuses and a typed zero-parameter operation still
    emits its return arrow
    [tested: test_each_remaining_annotation_shape_refuses_or_carries;
     commit=ff4ac16f07a6e373e79ed0eae0a4c2d64cb92550]
  - callable code flags, through partials, wrappers, bound methods, and
    callable objects, classify generators and refuse coroutine functions
    before registration changes any engine or registry state [tested:
    test_register_op_reads_co_flags_and_refuses_or_awaits;
    commit=9b1b808f6b8d8aa6a8080c13092fa73ce7893aaa]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: keyword-argument call forms once PeTTa itself grows a
    spelling for them; today MeTTa call sites are positional.
"""

from __future__ import annotations

import functools
import inspect
import threading
import typing
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from . import _engine, convert
from ._api_types import _DEFAULT_SPACE, MettaName, SpaceName
from ._ops import REGISTRY, Operation
from ._type_annotations import (
    annotation_atom_for,
    annotation_exprs,
    declaration_exprs,
    metta_type_for,
    referenced_classes,
    resolved_annotations,
    type_atom_for,
    type_atoms_for,
)
from ._type_annotations import (
    callable_name as _callable_name,
)
from .atoms import Expr, S, expr

__all__ = [
    "REFLECTION_SPACE",
    "annotation_atom_for",
    "annotation_exprs",
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

_P = ParamSpec("_P")
_R = TypeVar("_R")

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
    """The operation's reflected surface: one (op name arity kind) per arity,
    and (effect name immutable) when it declared itself pure. One list, so
    the transaction, rollback, re-registration diff and unregister all treat
    the effect atom exactly as they treat the op atoms."""
    facts = [expr(S.op, S[op.name], arity, S[op.kind]) for arity in op.arities]
    if op.pure:
        facts.append(expr(S.effect, S[op.name], S.immutable))
    if op.inverse is not None:
        facts.append(expr(S.inverse, S[op.name]))
    return facts


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


_RECORDED: list[type] = []
_RECORDED_LOCK = threading.Lock()


def record(cls: type) -> type:
    """The declarative-record wiring, attrs' and pydantic's shape: one
    decorator over a dataclass, NamedTuple, or Enum and the class
    converts both ways, its `(: ...)` declarations land in &self, and it
    serves as a cast and query(into=) target.

        @petta.record
        @dataclass
        class Edge:
            a: str
            b: str

    Conversion registers immediately (an unregistrable class fails at
    the decorator, not at first use). The declarations are engine-side
    atoms, so they land the moment an engine exists: immediately when
    one is already booted, or on the first MeTTa construction otherwise,
    which is what lets the decorator run at import time without booting
    anything. Every underlying registration call stays public for the
    classes that need custom shapes."""
    convert.ensure_registered(cls)
    with _RECORDED_LOCK:
        _RECORDED.append(cls)
    if _engine.booted():
        declare_recorded()
    return cls


def declare_recorded() -> None:
    """Land every pending recorded class's declarations in &self; a
    no-op when nothing is pending, called by MeTTa construction so a
    decorator that ran before any engine existed still declares."""
    with _RECORDED_LOCK:
        if not _RECORDED:
            return
        pending = list(_RECORDED)
        _RECORDED.clear()
    declarations = [atom for cls in pending for atom in class_declarations(cls)]
    if not declarations:
        return
    runtime = _engine.runtime()
    runtime.do_must(
        "petta_py_add_many",
        _DEFAULT_SPACE,
        [declaration.to_wire() for declaration in declarations],
    )


def class_declarations(cls: type) -> list[Expr]:
    """The (: ...) atoms that make a class a MeTTa type: the translator's
    own declarations for an Enum, dataclass or NamedTuple, constructor
    arrows and member typings, derived from the class itself. A plain
    class needs NO declaration: its instances already answer the class
    name to get-type through the engine's MRO typing bridge, so emitting
    one would only restate what the engine figures out on its own."""
    return list(convert.declarations(cls))


def _metta_name(fn: Callable, name: str | None) -> MettaName:
    """The MeTTa spelling: the Python name verbatim unless overridden.

    Nothing is rewritten. A hyphenated MeTTa name is one Python cannot
    spell, so it is asked for with name=, where it is visible at the
    registration rather than inferred from the identifier."""
    return MettaName(name if name is not None else _callable_name(fn))


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
            raise TypeError(
                f"cannot register {_callable_name(fn)}: **{p.name} is "
                "unreachable from a positional MeTTa call site"
            )
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
    declared: list[Expr] = []
    overloads = typing.get_overloads(fn)
    signatures = overloads or (fn,)
    all_annotations: list[Any] = []
    for signature in signatures:
        signature_params = (
            list(inspect.signature(signature).parameters.values())
            if overloads
            else params
        )
        hints = resolved_annotations(signature)
        annotations = [
            hints.get(param.name, inspect.Parameter.empty)
            for param in signature_params
        ]
        ret = hints.get("return", Any)
        all_annotations.extend((*annotations, ret))
        for atom in (
            *declaration_exprs(name, annotations, ret),
            *annotation_exprs(name, annotations, ret),
        ):
            if atom not in declared:
                declared.append(atom)
    for cls in referenced_classes(all_annotations):
        for extra in class_declarations(cls):
            if extra not in declared:
                declared.append(extra)
    return declared


def _callable_code(fn: Callable) -> Any:
    """The Python code object governing one callable, if it has one."""
    current: Any = fn
    seen: set[int] = set()
    while id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, functools.partial):
            current = current.func
            continue
        current = inspect.unwrap(current)
        if inspect.ismethod(current):
            current = current.__func__
            continue
        code = getattr(current, "__code__", None)
        if code is not None:
            return code
        call = inspect.getattr_static(type(current), "__call__", None)
        if call is None:
            break
        current = call
    return None


def _operation_kind(fn: Callable, raw: bool) -> str:
    code = _callable_code(fn)
    flags = code.co_flags if code is not None else 0
    name = _callable_name(fn)
    if flags & inspect.CO_ASYNC_GENERATOR:
        raise TypeError(
            f"cannot register {name}: an async-generator function cannot run "
            "through synchronous register_op"
        )
    if flags & inspect.CO_COROUTINE:
        raise TypeError(
            f"cannot register {name}: a coroutine function cannot run through "
            "synchronous register_op"
        )
    if flags & inspect.CO_ITERABLE_COROUTINE:
        raise TypeError(
            f"cannot register {name}: a generator-based coroutine cannot run "
            "through synchronous register_op"
        )
    many = bool(flags & inspect.CO_GENERATOR)
    return {
        (False, False): "det",
        (False, True): "many",
        (True, False): "raw_det",
        (True, True): "raw_many",
    }[(raw, many)]


def _operation_declarations(
    name: str,
    params: list[inspect.Parameter],
    fn: Callable,
    typed: bool,
) -> tuple[Expr, ...]:
    if not typed:
        return ()
    return tuple(_type_declarations(name, params, fn))


def _rollback_registration(
    runtime: Any,
    operation: Operation,
    previous: Operation | None,
    retained: list[Expr],
    added_facts: list[Expr],
) -> None:
    for fact in added_facts:
        _reflect_remove(runtime, fact)
    for declaration in retained:
        _release_declaration(runtime, operation.space or "&self", declaration)
    if previous is not None:
        # The added atoms are gone again, so the previous life's atoms are
        # what &petta holds; recompiling from them IS the restoration, the
        # same route forward registration takes.
        runtime.must("petta_py_compile_op(Name)", Name=previous.name)
        # The purity claim is part of the previous life too. Without this, a
        # failed re-registration of a pure operation left it impure in the
        # engine while the registry still said pure.
        _declare_purity(runtime, previous)
        return
    for arity in operation.arities:
        runtime.must(
            "petta_py_unregister_op(Name, Arity)",
            Name=operation.name,
            Arity=arity,
        )
    _withdraw_purity(runtime, operation)


def _register_transaction(
    runtime: Any,
    operation: Operation,
    previous: Operation | None,
) -> tuple[list[Expr], list[Expr]]:
    """Publish one complete operation surface or restore its previous life.

    Declarations go in BEFORE the registration, which is the order that
    matters rather than a detail. A declaration decides how a call site
    compiles, and the engine recompiles what a late one made stale, so
    registering first meant every typed registration triggered that recompile
    over its own fresh function, scanning for stale call sites that could not
    exist yet [measured 2026-08-16: +48 inferences per register-and-unregister
    cycle on the register-op benchmark, gone with this order]. It is also the
    order that closes the ordering trap here: the first call site ever
    compiled against this name already sees its type.
    """
    new_facts = _op_facts(operation)
    old_facts = _op_facts(previous) if previous is not None else []
    retained: list[Expr] = []
    added_facts: list[Expr] = []
    try:
        for declaration in operation.declarations:
            _retain_declaration(runtime, operation.space or "&self", declaration)
            retained.append(declaration)
        # The atoms are the registration: reflect them first, then compile
        # the predicate FROM them. The keywords this function received are
        # sugar; petta_py_compile_op reads (op ...) and (inverse ...) back
        # out of &petta, and the cube gate holds the compiled clause
        # identical to the passed-parameter route's.
        for fact in new_facts:
            if fact not in old_facts:
                _reflect_add(runtime, fact)
                added_facts.append(fact)
        runtime.must("petta_py_compile_op(Name)", Name=operation.name)
        _declare_purity(runtime, operation)
    except BaseException:
        _rollback_registration(runtime, operation, previous, retained, added_facts)
        raise
    return new_facts, old_facts


def _retire_previous(
    runtime: Any,
    previous: Operation | None,
    new_facts: list[Expr],
    old_facts: list[Expr],
    fallback_space: str,
) -> None:
    if previous is None:
        return
    for fact in old_facts:
        if fact not in new_facts:
            _reflect_remove(runtime, fact)
    for declaration in previous.declarations:
        _release_declaration(runtime, previous.space or fallback_space, declaration)


def _engine_positions(params: list[inspect.Parameter], fn: Callable) -> list[int]:
    """The positions whose annotation asks for the engine itself: FastAPI's
    Depends read with the house convention that the annotation IS the
    request. A `m: petta.MeTTa` parameter is the framework's to fill, so it
    never counts toward MeTTa arities or the declared arrow. Detection uses
    resolved annotations only when they resolve: an unresolvable signature
    injects nothing here and keeps failing exactly where it fails today,
    in the typed declaration pass."""
    from .space import MeTTa  # noqa: PLC0415  space imports ops at top; the cycle breaks here

    try:
        hints = resolved_annotations(fn)
    except TypeError:
        return []
    return [i for i, p in enumerate(params) if hints.get(p.name) is MeTTa]


def _with_engine(fn: Callable, positions: list[int]) -> Callable:
    """Wrap fn so the engine weaves itself into the injected slots at each
    call, bound to the CURRENT context's space: an operation called from a
    program running in &kb queries &kb, the &self reading, so the op
    composes across spaces without the space being an argument. Only an
    operation that asked pays the wrapper; every other registration calls
    its function untouched."""

    @functools.wraps(fn)
    def woven(*args):
        from .space import MeTTa, current_space  # noqa: PLC0415  the same deliberate cycle break

        engine = MeTTa(current_space())
        threaded = list(args)
        for position in positions:
            threaded.insert(position, engine)
        return fn(*threaded)

    return woven


def register(
    runtime,
    fn: Callable[_P, _R],
    *,
    name: str | None = None,
    typed: bool = True,
    raw: bool = False,
    pass_atoms: bool = False,
    space: str = _DEFAULT_SPACE,
    arities: list[int] | None = None,
    inverse: Callable | None = None,
    pure: bool = False,
) -> Callable[_P, _R]:
    """Make fn callable from MeTTa. Returns fn unchanged.

    A generator function registers as nondeterministic: each yield is one
    answer, and MeTTa's collapse, superpose and let compose over them. A
    plain function is deterministic; returning None or raising Decline
    answers nothing. Defaults yield one registration per reachable arity;
    a variadic callable names its call forms with arities=[...].

    inverse supplies the BACKWARDS direction, so the operation can stand in a
    pattern position the way a MeTTa equation does. It takes the result and
    returns the arguments, as a tuple, or the bare value at arity one; a
    generator enumerates every preimage, and None or Decline means there is
    none. It only ever runs when the arguments are not ground and the result
    is, so a forward call never reaches it and an operation without one
    compiles exactly what it compiled before.

    pure declares that the operation has no effect a cache could hide, which
    is what lets it appear in a `(tabled ...)` or memoized body. It is an
    allow-list on purpose: an operation that does not say so is refused there
    by name, loudly, rather than cached and quietly wrong.
    """
    metta_name = _metta_name(fn, name)
    kind = _operation_kind(fn, raw)
    explicit_arities = arities
    arities, params = _arities(fn, arities)
    injected = _engine_positions(params, fn)
    if injected:
        params = [p for i, p in enumerate(params) if i not in injected]
        if explicit_arities is None:
            # The derivation in _arities counted the engine slots; the MeTTa
            # call site never fills them, so the range re-derives without.
            required = sum(1 for p in params if p.default is inspect.Parameter.empty)
            arities = list(range(required, len(params) + 1))
    # Everything computable is computed BEFORE the engine changes: a
    # refusing annotation or an over-expanded Union leaves nothing half
    # registered. Then the engine registers every arity in one checked
    # step (a collision with a static procedure throws with nothing
    # touched); declaration and reflection writes follow with a rollback
    # that restores the previous registration whole, and the Python
    # registry commits last.
    if inverse is not None and not callable(inverse):
        raise TypeError(f"the inverse of {metta_name} is not callable: {inverse!r}")
    if pure and kind == "raw_many":
        # A raw generator is the one shape whose answers the engine never
        # sees whole, so "no effect a cache could hide" is not checkable even
        # in principle. Refusing here beats a caller finding out later.
        raise ValueError(
            f"{metta_name} cannot be declared pure: a raw generator's answers "
            f"cross one at a time and are never seen whole"
        )
    declarations = _operation_declarations(metta_name, params, fn, typed)
    conversion_hints = resolved_annotations(fn) if typed else {}
    previous = REGISTRY.get(metta_name)
    operation = Operation(
        name=metta_name,
        fn=_with_engine(fn, injected) if injected else fn,
        kind=kind,
        arity=max(arities),
        pass_atoms=pass_atoms,
        space=SpaceName(space),
        declarations=declarations,
        arities=tuple(arities),
        inverse=inverse,
        pure=pure,
        parameter_annotations=tuple(
            conversion_hints.get(param.name, Any) for param in params
        ),
        return_annotation=conversion_hints.get("return", Any),
    )
    new_facts, old_facts = _register_transaction(runtime, operation, previous)
    # Committed: the previous life retires, shared pieces surviving. Facts
    # equal in both lives were never re-added, so they are not removed;
    # declarations release through the refcount, staying while any other
    # owner still declares them.
    _retire_previous(runtime, previous, new_facts, old_facts, space)
    REGISTRY[metta_name] = operation
    return fn


def unregister(runtime, name: str) -> None:
    """Remove every arity of a registered operation, and every declaration
    registration added, so nothing keeps describing a function that no
    longer exists."""
    op = REGISTRY.get(name)
    arities = list(runtime.iter("petta_py_op_spec(Name, Arity, _)", Name=name))
    # The registry walk above already knows whether anything is there, so the
    # existence check costs nothing extra. Asking builtins() instead listed
    # every registered function per call, +69.6% on the register-op counter.
    if not arities and op is None:
        raise KeyError(f"no operation named {name!r} is registered")
    for arity_row in arities:
        runtime.must("petta_py_unregister_op(Name, Arity)", Name=name, Arity=arity_row["Arity"])
    if op is not None:
        for declaration in op.declarations:
            _release_declaration(runtime, op.space or "&self", declaration)
        for fact in _op_facts(op):
            _reflect_remove(runtime, fact)
        _withdraw_purity(runtime, op)
    REGISTRY.pop(name, None)


def _declare_purity(runtime: Any, operation: Operation) -> None:
    """Say the operation has no effect a cache could hide, or take it back.

    Retract first either way, because a re-registration of the same name must
    not leave the previous life's claim standing: an operation declared pure
    and then re-registered without the flag would otherwise stay cacheable.
    """
    runtime.must("retractall(metta_host_pure_operation(Name))", Name=operation.name)
    if operation.pure:
        runtime.must("assertz(metta_host_pure_operation(Name))", Name=operation.name)


def _withdraw_purity(runtime: Any, operation: Operation) -> None:
    if operation.pure:
        runtime.must("retractall(metta_host_pure_operation(Name))", Name=operation.name)


def registered() -> dict[str, Operation]:
    """The live registry, name to operation."""
    return REGISTRY.copy()
