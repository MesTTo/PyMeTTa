"""Purpose: registration of Python callables as MeTTa functions. Reads the
signature for arities (defaults yield several), auto-detects nondeterminism
(a generator function is one), derives a MeTTa type declaration from the
annotations, and registers the whole thing with the engine through shim.pl.
Guarantees:
  - class declaration has no process-global ``record`` registry or second
    decorator spelling [tested:
    test_define_absorbs_class_declaration_and_frees_space_type;
    commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - registration distinguishes a MeTTa function name from its declaration
    space [tested: test_canonical_context_types_replace_public_newtypes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - registration asks the engine grammar whether the requested name reads as
    one symbol and refuses before reflecting or registering anything [tested:
    test_register_op_refuses_a_name_metta_cannot_read;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - implicit operation names apply the total underscore-to-hyphen map while
    explicit name= remains exact [tested: test_op_uses_the_define_name_ladder;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - full annotations become ordinary claims in the declaration space
    [tested: test_the_four_containers_share_one_parameterised_treatment;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - overload stubs each contribute their declared arrow and annotation claims
    [tested: test_every_advanced_annotation_reaches_metta_as_a_target_symbol;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - unreachable **kwargs refuses and a typed zero-parameter operation still
    emits its return arrow
    [tested: test_each_remaining_annotation_shape_refuses_or_carries;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - callable code flags, through partials, wrappers, bound methods, and
    callable objects, classify generators and route coroutine functions to
    future-space dispatch
    before registration changes any engine or registry state [tested:
    test_register_op_reads_co_flags_and_refuses_or_awaits;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - generator signatures supply positional and sparse-dict relation row names
    after injected engine parameters are removed [tested:
    test_sparse_relational_dict_candidates_bind_parameter_names;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - every documented operation owns its portable @doc atom in the
    declaration space, independent of type annotations, under the same transactional
    lifecycle and reference count as type declarations [tested:
    test_every_register_op_writes_its_declaration_and_get_doc_answers;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - each registered arity owns the arrow for exactly the arguments that call
    form accepts, including repeated variadic annotations [tested:
    test_every_array_operation_is_typed_and_a_shape_is_a_constraint;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - Annotated MeTTa parameters retain metadata without losing engine
    injection [tested:
    test_two_values_of_one_base_type_are_distinguishable_by_their_metadata;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - transport, evaluation order, typing, and purity are expressed by op,
    type, and effect atoms rather than boolean decorator flags [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every registration publishes exactly one canonical five-rank effect and
    missing metadata refuses before engine mutation [tested:
    test_unclassified_operation_refuses_with_all_five_effect_remedies,
    test_every_effect_rank_registers_and_reflects; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - the first Python owner refuses to adopt a source-owned declaration, while
    later Python owners share the declaration reference count
    [tested: test_a_duplicate_declaration_names_the_first_one;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the returned staging wrapper carries its registration identity through
    functools.wraps chains, which is how the lint resolves a bare name to the
    operation behind it [tested:
    test_an_effectful_ground_operation_at_rule_construction_is_linted;
    commit=8d6131a9d9902c67ce8cac71e96e8362a8713561]
  - EffectPlan exposes the engine's live named-operation analysis and lattice
    join without executing the target [tested:
    test_effect_plan_reports_nested_calls_without_executing_them,
    test_effect_plan_reads_replaced_operation_classification;
    commit=d06621ddec911922c156c79ce68b2c35318e7fc1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import functools
import importlib as _importlib
import inspect
import typing
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Literal

from ._api_types import _DEFAULT_SPACE, _OperationName, _SpaceId
from ._documentation import documentation_atom
from ._name_mapping import attribute_name
from ._ops import OPERATION_REGISTRATION, REGISTRY, Operation, live_registration
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
from .atoms import Atom, Expression, S, Symbol, _encode, _expr, _to_atom, _variables
from .vocabularies import EffectClass

_CO_GENERATOR = getattr(inspect, "CO_GENERATOR", 0x0020)
_CO_COROUTINE = getattr(inspect, "CO_COROUTINE", 0x0080)
_CO_ITERABLE_COROUTINE = getattr(inspect, "CO_ITERABLE_COROUTINE", 0x0100)
_CO_ASYNC_GENERATOR = getattr(inspect, "CO_ASYNC_GENERATOR", 0x0200)

__all__ = [
    "EffectPlan",
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


@dataclass(frozen=True, slots=True)
class EffectPlan:
    """Named operations reachable from one target and their lattice join."""

    operations: tuple[tuple[str, EffectClass], ...]
    effect: EffectClass

#: The library's own space. Everything Python registers reflects here as
#: ordinary atoms: (op name arity kind) per registered arity,
#: (defined space name) per @define function, (subscription space pattern
#: on) per standing query. It is a space like any other, so MeTTa programs
#: can query the library's surface, and writing to it composes with
#: subscriptions: a Python subscription on &metta reacts to control atoms
#: a MeTTa program adds, which is steering the library from inside MeTTa
#: without forking it.
_REFLECTION_SPACE = "&metta"

_EFFECT_NAMES = tuple(effect.value for effect in EffectClass)
# PostgreSQL's volatility contract makes IMMUTABLE a pure computation,
# STABLE a statement-snapshot read, and VOLATILE unconstrained, including
# writes. The top rank is therefore the only sound single image of volatile.
# https://www.postgresql.org/docs/16/xfunc-volatility.html
_LEGACY_EFFECTS = {
    "immutable": EffectClass.pureStructural,
    "stable": EffectClass.readOnlyLookup,
    "volatile": EffectClass.oracleIO,
}


def _op_facts(op: Operation) -> list[Expression]:
    """The operation's reflected surface: one (op name arity kind) per arity,
    and its mandatory (effect name Class) row. One list, so
    the transaction, rollback, re-registration diff and unregister all treat
    the effect atom exactly as they treat the op atoms.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    facts = [_expr(S.op, S[op.name], arity, S[op.kind]) for arity in op.arities]
    facts.extend(fact for fact in op.catalog if fact not in facts)
    if op.inverse is not None:
        facts.append(_expr(S.inverse, S[op.name]))
    return facts


def _reflect_add(runtime, atom: Expression) -> None:
    runtime.must("metta_py_add(Space, W)", Space=_REFLECTION_SPACE, W=atom.to_wire())


def _reflect_remove(runtime, atom: Expression) -> None:
    runtime.once("metta_py_remove(Space, W, _)", Space=_REFLECTION_SPACE, W=atom.to_wire())


# Declarations are shared: two signatures naming Point both need
# (: Point ...), and removal of every copy on the first unregister would
# leave the second describing an undeclared type. Ownership counts per
# (space, declaration); the atom enters the space with the first owner and
# leaves with the last.
_DECLARATION_REFS: dict[tuple[str, str], int] = {}


def _retain_declaration(runtime, space: str, declaration: Expression) -> None:
    key = (space, str(declaration))
    count = _DECLARATION_REFS.get(key, 0)
    if count == 0:
        runtime.must(
            "metta_py_add_strict_declaration(Space, W)",
            Space=space,
            W=declaration.to_wire(),
        )
    _DECLARATION_REFS[key] = count + 1


def _release_declaration(runtime, space: str, declaration: Expression) -> None:
    key = (space, str(declaration))
    count = _DECLARATION_REFS.get(key, 0)
    if count <= 1:
        _DECLARATION_REFS.pop(key, None)
        runtime.once("metta_py_remove(Space, W, _)", Space=space, W=declaration.to_wire())
    else:
        _DECLARATION_REFS[key] = count - 1


def class_declarations(cls: type) -> list[Expression]:
    """The (: ...) atoms that make a class a MeTTa type: the translator's
    own declarations for an Enum, dataclass or NamedTuple, constructor
    arrows and member typings, derived from the class itself. A plain
    class needs NO declaration: its instances already answer the class
    name to get-type through the engine's MRO typing bridge, so emitting
    one would only restate what the engine figures out on its own.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return list(_importlib.import_module(f"{__package__}.convert").declarations(cls))


def _metta_name(fn: Callable, name: str | None) -> _OperationName:
    """The MeTTa spelling from the shared implicit-or-exact naming ladder.

    Implicit names map every underscore to a hyphen. An explicit name is
    authored MeTTa text and remains exact.
    """
    implicit = attribute_name(_callable_name(fn))
    return _OperationName(implicit if name is None else name)


def _arities(
    fn: Callable,
    explicit: list[int] | None,
) -> tuple[list[int], list[inspect.Parameter], inspect.Parameter | None]:
    """Every arity the defaults allow, smallest first, plus the parameters.

    An explicit arities list overrides the derivation, which is how a
    variadic callable registers: the call sites it serves are named rather
    than inferred, since *args alone says nothing about MeTTa call forms.
    """
    sig = inspect.signature(fn)
    params = []
    variadic = None
    for p in sig.parameters.values():
        if p.kind is inspect.Parameter.VAR_KEYWORD:
            msg = (
                f"cannot register {_callable_name(fn)}: **{p.name} is "
                "unreachable from a positional MeTTa call site"
            )
            raise TypeError(msg)
        if p.kind is inspect.Parameter.VAR_POSITIONAL:
            variadic = p
            continue
        if p.kind is inspect.Parameter.KEYWORD_ONLY:
            msg = (
                f"cannot register {_callable_name(fn)}: keyword-only parameter "
                f"{p.name!r} is unreachable from a positional MeTTa call site"
            )
            raise TypeError(
                msg
            )
        params.append(p)
    if explicit is not None:
        return sorted(set(explicit)), params, variadic
    if variadic is not None:
        msg = (
            f"cannot register {_callable_name(fn)}: *args has no single MeTTa call "
            f"form; pass arities=[...] naming the argument counts to serve"
        )
        raise TypeError(
            msg
        )
    required = sum(1 for p in params if p.default is inspect.Parameter.empty)
    return list(range(required, len(params) + 1)), params, None


def _type_declarations(
    name: str,
    params: list[inspect.Parameter],
    variadic: inspect.Parameter | None,
    arities: list[int],
    fn: Callable,
    *,
    result_type: Atom | None = None,
    include_annotation_claims: bool = True,
) -> list[Expression]:
    """Everything a signature declares: the (-> ...) arrows over the full
    arity, one per Union combination, plus the declarations of every class
    the annotations reference, so a signature naming Point makes Point a
    declared type rather than a dangling name. Annotations resolve through
    typing, so postponed (string) annotations declare the types they name
    rather than %Undefined%, and TypeVars declare type variables, the
    parametric reading.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    declared: list[Expression] = []
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
        ret = hints.get("return", Any)
        if overloads:
            annotation_sets = [
                [
                    hints.get(param.name, inspect.Parameter.empty)
                    for param in signature_params
                ]
            ]
        else:
            fixed = [
                hints.get(param.name, inspect.Parameter.empty)
                for param in signature_params
            ]
            repeated = (
                hints.get(variadic.name, inspect.Parameter.empty)
                if variadic is not None
                else inspect.Parameter.empty
            )
            annotation_sets = [
                [*fixed[:arity], *(repeated for _ in range(max(0, arity - len(fixed))))]
                for arity in arities
            ]
        for argument_annotations in annotation_sets:
            all_annotations.extend((*argument_annotations, ret))
            arrows = declaration_exprs(name, argument_annotations, ret)
            if result_type is not None:
                arrows = [
                    _expr(
                        S[":"],
                        S[name],
                        Expression([*arrow.children[2].children[:-1], result_type]),
                    )
                    for arrow in arrows
                ]
            claims = (
                annotation_exprs(name, argument_annotations, ret)
                if include_annotation_claims
                else []
            )
            if result_type is not None and claims:
                # Annotation reflection describes the public call result, just
                # as the arrow does; the coroutine's eventual Python value is
                # encoded into that FutureSpace [tested:
                # test_async_reflection_has_one_public_return_and_effect;
                # commit=39092863ae34184a9f955f185ff57c1ff177ec40].
                claims[-1] = _expr(
                    S.annotation,
                    S[name],
                    _expr(S["return"], result_type),
                )
            for atom in (*arrows, *claims):
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


# policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the two wire-crossing modes a registration can ask for, and this decoder turns them into the (op ...) kind; evidence=extensions/python/metta/ops.py:register
def _operation_kind(fn: Callable, transport: Literal["encoded", "raw"]) -> str:
    if transport not in ("encoded", "raw"):
        msg = f"transport must be 'encoded' or 'raw', got {transport!r}"
        raise ValueError(msg)
    code = _callable_code(fn)
    flags = code.co_flags if code is not None else 0
    name = _callable_name(fn)
    if flags & _CO_ASYNC_GENERATOR:
        msg = (
            f"cannot register {name}: an async-generator function cannot run "
            "through synchronous op"
        )
        raise TypeError(msg)
    if flags & _CO_COROUTINE:
        if transport == "raw":
            msg = (
                f"cannot register {name}: an async operation answers an "
                "encoded future-space, so transport='raw' cannot carry it"
            )
            raise TypeError(msg)
        return "async"
    if flags & _CO_ITERABLE_COROUTINE:
        msg = (
            f"cannot register {name}: a generator-based coroutine cannot run "
            "through synchronous op"
        )
        raise TypeError(msg)
    many = bool(flags & _CO_GENERATOR)
    return {
        (False, False): "det",
        (False, True): "many",
        (True, False): "raw_det",
        (True, True): "raw_many",
    }[(transport == "raw", many)]


def _effect_class(value: EffectClass | str | Symbol, *, name: str) -> EffectClass:
    """Normalize the five canonical classes and the retired volatility trio."""
    spelling = str(value)
    if spelling in _LEGACY_EFFECTS:
        return _LEGACY_EFFECTS[spelling]
    try:
        return EffectClass(spelling)
    except (TypeError, ValueError) as error:
        choices = ", ".join(_EFFECT_NAMES)
        msg = f"the effect for {name!r} must be one of: {choices}; got {spelling!r}"
        raise ValueError(msg) from error


def _missing_effect(name: str) -> TypeError:
    remedies = ", ".join(f"EffectClass.{effect.value}" for effect in EffectClass)
    return TypeError(
        f"operation {name!r} requires effect= metadata; choose one of: {remedies}"
    )


def _declaration_effect(
    name: str,
    atom: Expression,
    previous: EffectClass | None,
) -> tuple[EffectClass, Expression]:
    """Validate and canonicalize one declaration-route effect."""
    if len(atom.children) != 3 or atom.children[1] != Symbol(name):
        msg = (
            f"an effect declaration for {name!r} must be "
            f"(effect {name} {'|'.join(_EFFECT_NAMES)})"
        )
        raise ValueError(msg)
    declared = atom.children[2]
    if not isinstance(declared, Symbol):
        msg = (
            f"an effect declaration for {name!r} must name its class as a symbol, "
            f"got {declared!s}"
        )
        raise TypeError(msg)
    candidate = _effect_class(declared, name=name)
    if previous is not None and candidate is not previous:
        msg = (
            f"{name!r} has conflicting effect declarations: "
            f"{previous.value} and {candidate.value}"
        )
        raise ValueError(msg)
    return candidate, _expr(S.effect, S[name], S[candidate.value])


def _partition_declarations(
    name: str,
    declarations: Iterable[Atom],
    effect: EffectClass | str | None,
) -> tuple[list[Expression], tuple[Expression, ...], EffectClass]:
    """Split operation-local declarations from &metta policy facts.

    Type and documentation atoms govern compilation in the operation's own
    declaration space. Every other atom is catalog policy and therefore lives
    in &metta. The registration owns both sets for rollback, replacement, and
    unregistration. `(op ...)` is reserved because arity and transport derive
    that fact from the callable and cannot safely disagree with it.
    """
    local: list[Expression] = []
    catalog: list[Expression] = []
    declared_effect: EffectClass | None = None
    for declaration in declarations:
        atom = _to_atom(declaration)
        if not isinstance(atom, Expression) or not atom.children:
            msg = (
                "operation declarations must be expression atoms, "
                f"got {atom!s}"
            )
            raise TypeError(msg)
        head = atom.children[0]
        if head == Symbol("op"):
            msg = (
                "(op ...) is derived from transport=, arities=, and the "
                "callable's generator shape; do not supply it twice"
            )
            raise ValueError(msg)
        if head == Symbol("effect"):
            declared_effect, canonical = _declaration_effect(
                name,
                atom,
                declared_effect,
            )
            if canonical not in catalog:
                catalog.append(canonical)
            continue
        if head == Symbol("arguments"):
            if (
                len(atom.children) != 3
                or atom.children[1] != Symbol(name)
                or atom.children[2] not in (S.atoms, S.values)
            ):
                msg = (
                    f"an argument declaration for {name!r} must be "
                    f"(arguments {name} atoms|values)"
                )
                raise ValueError(msg)
            existing = [fact for fact in catalog if fact.head == S.arguments]
            if existing and atom not in existing:
                msg = (
                    f"{name!r} has conflicting argument declarations: "
                    f"{existing[0]} and {atom}"
                )
                raise ValueError(msg)
            if atom not in catalog:
                catalog.append(atom)
            continue
        target = local if head in (Symbol(":"), Symbol("@doc")) else catalog
        if atom not in target:
            target.append(atom)
    supplied_effect = None if effect is None else _effect_class(effect, name=name)
    if supplied_effect is not None and declared_effect not in (None, supplied_effect):
        msg = (
            f"{name!r} has conflicting effect metadata: effect="
            f"{supplied_effect.value} and declaration {declared_effect.value}"
        )
        raise ValueError(msg)
    resolved = supplied_effect or declared_effect
    if resolved is None:
        raise _missing_effect(name)
    canonical = _expr(S.effect, S[name], S[resolved.value])
    if canonical not in catalog:
        catalog.append(canonical)
    return local, tuple(catalog), resolved


def _passes_atoms(name: str, catalog: tuple[Expression, ...]) -> bool:
    return _expr(S.arguments, S[name], S.atoms) in catalog


def _operation_declarations(
    name: str,
    params: list[inspect.Parameter],
    *,
    variadic: inspect.Parameter | None,
    arities: list[int],
    fn: Callable,
    supplied: list[Expression],
    result_type: Atom | None = None,
) -> tuple[Expression, ...]:
    has_annotations = bool(resolved_annotations(fn) or typing.get_overloads(fn))
    declarations = (
        _type_declarations(
            name,
            params,
            variadic,
            arities,
            fn,
            result_type=result_type,
            include_annotation_claims=has_annotations,
        )
        if has_annotations or result_type is not None
        else []
    )
    for declaration in supplied:
        if declaration not in declarations:
            declarations.append(declaration)
    documentation = documentation_atom(name, fn, kind="operation")
    if documentation is not None:
        declarations.append(documentation)
    return tuple(declarations)


def _require_readable_name(runtime: Any, name: _OperationName) -> None:
    """Refuse a name the engine reader would turn into anything but itself."""
    refusal = runtime.apply("metta_py_symbol_refusal", name)
    if refusal is None:
        return
    kind, *detail = refusal
    if kind == "empty":
        reason = "the name is empty"
    elif kind == "character":
        reason = f"character {detail[0]!r} prevents it being one symbol"
    else:
        reason = f"the token beginning with character {detail[0]!r} is another literal"
    msg = f"cannot register operation {name!r}: {reason} in MeTTa's reader"
    raise ValueError(msg)


def _rollback_registration(
    runtime: Any,
    operation: Operation,
    previous: Operation | None,
    retained: list[Expression],
    added_facts: list[Expression],
) -> None:
    for fact in added_facts:
        _reflect_remove(runtime, fact)
    for declaration in retained:
        _release_declaration(runtime, operation.space or "&self", declaration)
    if previous is not None:
        # The added atoms are gone again, so the previous life's atoms are
        # what &metta holds; recompiling from them IS the restoration, the
        # same route forward registration takes.
        runtime.must("metta_py_compile_op(Name)", Name=previous.name)
        # The purity claim is part of the previous life too. Without this, a
        # failed re-registration of a pure operation left it impure in the
        # engine while the registry still said pure.
        _declare_purity(runtime, previous)
        return
    for arity in operation.arities:
        runtime.must(
            "metta_py_unregister_op(Name, Arity)",
            Name=operation.name,
            Arity=arity,
        )
    _withdraw_purity(runtime, operation)


def _register_transaction(
    runtime: Any,
    operation: Operation,
    previous: Operation | None,
) -> tuple[list[Expression], list[Expression]]:
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
    retained: list[Expression] = []
    added_facts: list[Expression] = []
    try:
        for declaration in operation.declarations:
            _retain_declaration(runtime, operation.space or "&self", declaration)
            retained.append(declaration)
        # The atoms are the registration: reflect them first, then compile
        # the predicate FROM them. The keywords this function received are
        # sugar; metta_py_compile_op reads (op ...) and (inverse ...) back
        # out of &metta, and the cube gate holds the compiled clause
        # identical to the passed-parameter route's.
        for fact in new_facts:
            if fact not in old_facts:
                _reflect_add(runtime, fact)
                added_facts.append(fact)
        runtime.must("metta_py_compile_op(Name)", Name=operation.name)
        _declare_purity(runtime, operation)
    except BaseException:
        _rollback_registration(runtime, operation, previous, retained, added_facts)
        raise
    return new_facts, old_facts


def _retire_previous(
    runtime: Any,
    previous: Operation | None,
    new_facts: list[Expression],
    old_facts: list[Expression],
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
    request. A `m: metta.MeTTa` parameter is the framework's to fill, so it
    never counts toward MeTTa arities or the declared arrow. Detection uses
    resolved annotations only when they resolve: an unresolvable signature
    injects nothing here and keeps failing exactly where it fails today,
    in the typed declaration pass.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    metta_type = _importlib.import_module(f"{__package__}._space").MeTTa
    try:
        hints = resolved_annotations(fn)
    except TypeError:
        return []
    positions = []
    for index, param in enumerate(params):
        annotation = hints.get(param.name)
        while typing.get_origin(annotation) is typing.Annotated:
            annotation = typing.get_args(annotation)[0]
        if annotation is metta_type:
            positions.append(index)
    return positions


def _with_engine(runtime: Any, fn: Callable, positions: list[int]) -> Callable:
    """Wrap fn so the engine weaves itself into the injected slots at each
    call, bound to the CURRENT context's space: an operation called from a
    program running in &kb queries &kb, the &self reading, so the op
    composes across spaces without the space being an argument. Only an
    operation that asked pays the wrapper; every other registration calls
    its function untouched.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    @functools.wraps(fn)
    def woven(*args):
        space_api = _importlib.import_module(f"{__package__}._space")
        # Delayed async injection must not reacquire the process runtime lock;
        # the registration runtime already owns the calling space [tested:
        # test_async_engine_injection_uses_the_registration_runtime;
        # commit=39092863ae34184a9f955f185ff57c1ff177ec40].
        engine = space_api.MeTTa(
            space_api.current_space(),
            _runtime=runtime,
        )
        threaded = list(args)
        for position in positions:
            threaded.insert(position, engine)
        return fn(*threaded)

    return woven


def _effective_declarations(
    metta_name: str,
    catalog: tuple[Expression, ...],
    operation_effect: EffectClass,
    floor: EffectClass,
) -> tuple[tuple[Expression, ...], EffectClass]:
    """Raise a declared effect to a floor the registration itself derived.

    The raised class is carried into the reflected `(effect ...)` row.

    Two registrations derive a floor from the function rather than from what
    the author said, and both must reflect what they derived or a cache reads
    the author's weaker claim:

    - a coroutine body still allocates and settles a distinct public
      FutureSpace, so `writesState` is its floor. Reflect that observable
      write and caches cannot merge two cancellation handles [tested:
      test_async_calls_are_effective_writes_with_independent_handles;
      commit=39092863ae34184a9f955f185ff57c1ff177ec40].
    - a generator IS nondeterministic, so `nondeterministicReadOnly` is its
      floor.

    The join only ever RAISES the rank, so this widens a claim and never
    weakens one.
    """
    effective = operation_effect.join(floor)
    if effective is operation_effect:
        return catalog, operation_effect
    declared_effect = _expr(S.effect, S[metta_name], S[operation_effect.value])
    effective_effect = _expr(S.effect, S[metta_name], S[effective.value])
    return (
        tuple(
            effective_effect if fact == declared_effect else fact
            for fact in catalog
        ),
        effective,
    )


def register[**P, R](
    runtime,
    fn: Callable[P, R],
    *,
    name: str | None = None,
    # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
    transport: Literal["encoded", "raw"] = "encoded",
    effect: EffectClass | str | None = None,
    declarations: Iterable[Atom] = (),
    space: str = _DEFAULT_SPACE,
    arities: list[int] | None = None,
    inverse: Callable | None = None,
) -> Callable[P, R]:
    """Make fn callable from MeTTa. Returns fn unchanged.

    A generator function registers as nondeterministic: each yield is one
    answer, and MeTTa's collapse, superpose and let compose over them. An exact
    tuple yield is a positional relational candidate and an exact dict yield
    is its sparse parameter-name spelling: the engine unifies each row against
    the call, so ground arguments filter and variables bind through the same
    implementation. Use ``Answer(value=...)`` when a generator intentionally
    answers an exact tuple or dict value. Relational rows require encoded
    transport.
    A plain function is deterministic; returning None or raising NotReducible
    answers nothing. Defaults yield one registration per reachable arity; a
    variadic callable names its call forms with arities=[...].

    inverse supplies a distinct result-to-arguments implementation for an
    ordinary result-producing operation. It takes the result and returns the
    arguments, as a tuple, or the bare value at arity one; a generator
    enumerates every preimage, and None or NotReducible means there is none. It
    only ever runs when the arguments are not ground and the result is, so a
    forward call never reaches it. A relational tuple/dict generator needs no
    inverse because its one implementation already binds every direction.

    Python annotations derive type atoms and Atom parameters receive syntax
    before evaluation. `transport="raw"` derives raw_det/raw_many in the
    operation's `(op ...)` fact. Effect metadata is required; ``effect=`` is
    the canonical input and names the strongest observable capability of the
    operation. Existing effect declaration atoms remain a compatibility input.
    Additional declaration atoms are owned for
    the operation's complete lifecycle: type atoms live in its declaration
    space, while its canonical effect row and other policy atoms live in
    &metta and can be matched there. Only ``pureStructural`` enters the
    compatibility allow-list for tabled or memoized bodies.
    """
    metta_name = _metta_name(fn, name)
    kind = _operation_kind(fn, transport)
    supplied, catalog, operation_effect = _partition_declarations(
        metta_name, declarations, effect
    )
    if kind == "async":
        catalog, operation_effect = _effective_declarations(
            metta_name, catalog, operation_effect, EffectClass.writesState
        )
    inverse_kind = _operation_kind(inverse, "encoded") if inverse is not None else "det"
    if kind.endswith("many") or inverse_kind.endswith("many"):
        # A generator IS nondeterministic, and `kind` above is how that was
        # decided from the function itself, so the declaration is LIFTED
        # rather than refused: asking an author to restate what the
        # registration just worked out teaches nothing. The lift only ever
        # RAISES the rank, from a read-only class to the read-only
        # nondeterministic one, so it widens the answer-count claim and never
        # weakens an effect claim. It happens here, before the catalog is
        # built, so the reflected (effect name class) row carries the lifted
        # class; lifting after it would leave a generator reflected as pure
        # and therefore cacheable.
        catalog, operation_effect = _effective_declarations(
            metta_name, catalog, operation_effect,
            EffectClass.nondeterministicReadOnly,
        )
    explicit_arities = arities
    arities, params, variadic = _arities(fn, arities)
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
        msg = f"the inverse of {metta_name} is not callable: {inverse!r}"
        raise TypeError(msg)
    if kind == "async" and inverse is not None:
        msg = (
            f"{metta_name} is async and cannot declare an inverse: its forward "
            "result is a FutureSpace, while an inverse consumes a landed value"
        )
        raise TypeError(msg)
    pass_atoms = _passes_atoms(metta_name, catalog)
    if pass_atoms and kind.startswith("raw_"):
        msg = (
            f"{metta_name} cannot declare atom arguments with raw transport: "
            "raw calls do not cross the atom codec"
        )
        raise ValueError(msg)
    declarations = _operation_declarations(
        metta_name,
        params,
        variadic=variadic,
        arities=arities,
        fn=fn,
        supplied=supplied,
        result_type=S.SpaceType if kind == "async" else None,
    )
    # The grammar check is the last read before the registration transaction:
    # every Python-side refusal above remains free, and an unreadable name has
    # not reflected a contract atom or opened a predicate when it is rejected.
    _require_readable_name(runtime, metta_name)
    conversion_hints = resolved_annotations(fn)
    if kind == "async":
        # Async operation settlement and FutureSpace lifecycle are lib_thread's
        # scheduler surface. Load it into the operation's declaration space
        # before compiling the host clause, so the first call cannot observe a
        # half-installed future path [tested:
        # test_an_async_operation_answers_a_future_space; commit=39092863ae34184a9f955f185ff57c1ff177ec40].
        parallel_api = _importlib.import_module(f"{__package__}.parallel")
        space_api = _importlib.import_module(f"{__package__}._space")
        parallel_api._ensure_thread_library(
            space_api.Space(space, _runtime=runtime)
        )
    previous = REGISTRY.get(metta_name)
    operation = Operation(
        name=metta_name,
        fn=_with_engine(runtime, fn, injected) if injected else fn,
        kind=kind,
        arity=max(arities),
        effect=operation_effect,
        pass_atoms=pass_atoms,
        space=_SpaceId(space),
        declarations=declarations,
        catalog=catalog,
        arities=tuple(arities),
        inverse=inverse,
        parameter_names=tuple(
            [param.name for param in params]
            + (
                [
                    variadic.name
                    for _ in range(max(0, max(arities) - len(params)))
                ]
                if variadic is not None
                else []
            )
        ),
        parameter_annotations=tuple(
            [conversion_hints.get(param.name, Any) for param in params]
            + (
                [
                    conversion_hints.get(variadic.name, Any)
                    for _ in range(max(0, max(arities) - len(params)))
                ]
                if variadic is not None
                else []
            )
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

    # The staging split's op half, the design's own cell: inside a rules
    # body, an op call whose arguments carry RULE VARIABLES stages, storing
    # the op-call term so the law crosses the host per APPLICATION; before
    # this, the host body ran at construction with a Variable atom in hand,
    # firing effects on garbage and inlining whatever the body happened to
    # build. A GROUND op call still runs now, which is the effect-fires-once
    # law the ledger states beside it. The engine's own dispatch reads the
    # bare fn from the registry, so this wrapper prices nothing there; a
    # direct Python call pays one contextvar read.
    # A module-level import would cycle: _rules imports atoms, which
    # this module feeds.
    from ._rules import (  # noqa: PLC0415
        _defined_calls_are_staged,
        _record_rule_operation,
    )

    @functools.wraps(fn)
    def _staging_aware(*args: Any, **kwargs: Any) -> Any:
        staging = _defined_calls_are_staged()
        if staging and not kwargs:
            encoded = [_encode(a) for a in args]
            staged = any(_variables(a) for a in encoded)
            frame = inspect.currentframe()
            if frame is not None and frame.f_back is not None:
                _record_rule_operation(operation, staged=staged, frame=frame.f_back)
            if staged:
                return Expression([Symbol(metta_name), *encoded])
        elif staging:
            frame = inspect.currentframe()
            if frame is not None and frame.f_back is not None:
                _record_rule_operation(operation, staged=False, frame=frame.f_back)
        return fn(*args, **kwargs)

    # Private metadata on the wrapper, so a reader resolves the Python object
    # rather than guessing from its source spelling. It never enters the
    # operation's call path.
    setattr(_staging_aware, OPERATION_REGISTRATION, operation)
    return _staging_aware


def _registered_operation(fn: Callable[..., Any]) -> Operation | None:
    """Return the live registration owned by this callable or wrapper chain.

    Reached as a module attribute by _space_definitions._installed_callable_name,
    which is how a bound definition resolves the exact live name it carries.
    """
    operation = live_registration(fn)
    if operation is not None:
        return operation
    source = inspect.unwrap(fn)
    for candidate in REGISTRY.values():
        behind = candidate.fn
        if fn is behind or source is inspect.unwrap(behind):
            return candidate
    return None



def unregister(runtime, name: str) -> None:
    """Remove every arity of a registered operation, and every declaration
    registration added, so nothing keeps describing a function that no
    longer exists.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    op = REGISTRY.get(name)
    arities = list(runtime.iter("metta_py_op_spec(Name, Arity, _)", Name=name))
    # The registry walk above already knows whether anything is there, so the
    # existence check costs nothing extra. Asking builtins() instead listed
    # every registered function per call, +69.6% on the register-op counter.
    if not arities and op is None:
        msg = f"no operation named {name!r} is registered"
        raise KeyError(msg)
    for arity_row in arities:
        runtime.must("metta_py_unregister_op(Name, Arity)", Name=name, Arity=arity_row["Arity"])
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
    and then re-registered at a stronger rank would otherwise stay cacheable.
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
