"""Purpose: install compiled Python functions and class declarations into a space.
Guarantees:
  - native call contracts retain each definition's lexical home [tested:
    test_expanded_definition_contracts_keep_distinct_lexical_homes;
    commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
  - class installation imports its peer directly [tested:
    tests/checks/check_layering.py; commit=ab9d3489f87e0d7b7be4b3cd2025494cd62699fe]
  - typing.overload stubs declare every distinct fixed-arity signature before
    their shared equation is published [tested:
    test_define_emits_each_overload_from_one_source,
    test_define_deduplicates_coincident_overload_arrows; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
  - ``install_type`` is the class branch behind ``Space.define`` [tested:
    test_define_absorbs_class_declaration_and_frees_space_type;
    commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - install_define keeps stacked clauses in Python first-match order and
    materializes every overlapping same-arity component as one case equation,
    leaving disjoint heads separate [tested:
    test_literal_defaults_are_head_patterns_and_clauses_stack,
    test_overlapping_clauses_materialize_as_one_case_equation;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - each merged case row reads its OWN clause's parameter names, so stacked
    clauses that spell a parameter differently still bind one variable across
    a row's pattern and its body [tested:
    test_stacked_clauses_may_spell_their_parameters_differently;
    commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - clauses at different arities under one MeTTa name stack instead of
    replacing one another [tested:
    test_define_supports_one_name_at_multiple_arities; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - implicit definition names apply the total underscore-to-hyphen map while
    explicit name= remains exact [tested: test_define_maps_its_implicit_python_name;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - a previously installed Python callable carries its exact MeTTa name into
    later compiled definitions [tested:
    test_compiled_calls_share_the_installed_name_resolver; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - an operation wrapper carries its registered MeTTa name into a definition
    compiled after registration [tested:
    test_module_tier_op_registration_precedes_definition_compilation;
    commit=fc7ec0b08cd8b5876a3f4105211c487185f6a9bf]
  - the compiler sees declared Bool result types, so condition positions do
    not add a redundant host-truthiness operation [tested:
    test_compiled_boolean_call_is_a_direct_condition; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - clear_definitions removes process bookkeeping with the equations it
    describes, and leaves it alone when a speculative scope discards the
    clear [tested: test_reflection_facts_follow_a_dropped_space,
    test_every_public_write_door_honours_the_execution_scopes; commit=9104f9380b32925053ea39c5e8d1d1038c93cdb7]
  - a definition is exposed only after its first twin clause exists, and its
    canonical first-clause documentation follows replacement and clearing
    [tested: test_one_docstring_reaches_help_dot_doc_and_get_doc;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - source spans, AST documentation, free variables, and derived effect joins
    replace atomically across clause replacement and leave reflection on
    clear [tested: test_a_definition_joins_every_called_operations_effect;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - a successful compiled definition publishes advisory operation crossings
    found under its loop bodies [tested:
    test_an_operation_call_inside_a_compiled_loop_is_linted; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - compiled and bound calls share exact parameter names for each unambiguous
    definition or operation arity [tested:
    test_known_call_site_keywords_bind_to_positional_metta_arguments;
    commit=c2ad5892fbfdd690dd7e9b507e76e87d7d1376d1]
  - generated class-method operations declare their Atom delivery policy in
    &metta rather than passing a boolean registration flag [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - an annotation-derived declaration lands before the equation it governs
    and rolls back if equation publication fails [tested:
    test_a_declared_output_type_takes_effect_through_the_decorator_door,
    test_failed_equation_publication_rolls_back_its_early_declaration;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every flat-yield equation is stored and replaced as one atomic clause
    unit [tested: test_same_head_redefinition_replaces_the_whole_yield_unit;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
  - stacking disjoint clauses retains every unchanged physical equation and
    batches only the alpha-equivalence delta, so K two-equation clauses take
    K engine calls and transport 2K atoms rather than 2K squared [tested:
    test_stacked_definition_writes_scale_with_the_new_clause;
    commit=9b6695455c30809c75267c50a5137e38925af386]
  - install_type equips a plain annotated class with data construction,
    __match_args__, and __replace__ before registering its full-arity term
    image [tested: test_define_accepts_a_plain_annotated_data_class;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - ``@typing.override`` under the decorator is read as a declaration: a
    definition carrying it must shadow a head an inherited space defines, and
    one that shadows nothing is refused with both remedies while an undeclared
    shadow is unchanged [tested:
    test_override_declares_a_shadow_of_an_inherited_definition,
    test_override_is_refused_when_nothing_is_shadowed,
    test_a_shadowing_definition_without_the_decorator_is_unchanged;
    commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
Guarded by:
  - _DEFINE_LOCK serializes equation installation, reflection, and process
    bookkeeping for every space [tested test_define_from_two_threads_is_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import builtins as _builtins
import importlib as _importlib
import inspect as _inspect
import os
import threading
import types
import typing as _typing
from collections.abc import Callable, Iterable, Sequence
from functools import partial
from typing import TYPE_CHECKING, Any, dataclass_transform, overload

import metta._declare.define as _declare_define_module
import metta._declare.operations as _declare_operations_module
import metta._declare.rules as _declare_rules_module
import metta.doors as _doors
from metta._atoms.designation import _P, _R, _T
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    S,
    Symbol,
    Variable,
    _alpha_eq,
    _atom_from_wire,
    _encode,
    _expr,
    _map_atoms,
    _to_atom,
)
from metta._atoms.names import attribute_name
from metta._binding.dispatch import REGISTRY
from metta._catalog import call_signatures
from metta._catalog.declarations import inferred
from metta._catalog.documentation import documentation_atom
from metta._compile.twins import (
    append_twin_clause,
    dispatcher_owns_clause,
    replace_twin_clause,
    select_clause_twin,
    twin_dispatcher,
)
from metta._declare import call_syntax, classes
from metta._declare import functions as _space_functions
from metta._errors.errors import CompileError, EngineError, Remedy
from metta._lazy import lazy
from metta._spaces.execution import run_void_write
from metta.vocabularies import EffectClass

_DEFINE_CLAUSES: dict[tuple[str, str], list[dict[str, Any]]] = {}

_DECLARED_DEFINES: dict[tuple[str, str], list[Expression]] = {}



_DEFINED_GENERATORS: set[tuple[str, str]] = set()

_DEFINE_DOCUMENTATION: dict[tuple[str, str], Expression] = {}

_DEFINE_REFLECTION: dict[tuple[str, str], tuple[Expression, ...]] = {}

_DEFINE_FACT_REFS: dict[str, int] = {}

_DEFINED_FUNCTION_NAMES: dict[tuple[str, types.FunctionType], set[str]] = {}

_DEFINE_LOCK = threading.RLock()

def _convert_api():
    """Load structural conversion only for class-backed definitions."""
    return lazy('metta.convert')

def clear_definitions(space: Any) -> None:
    """Clear one space and the process state describing its definitions.

    Through the execution-policy wrapper, so a clear inside a scope obeys it
    the way every other call in the block does. The process state follows the
    engine rather than accompanying it: inside `with m.speculative():` the
    snapshot discards the clear, and a registry emptied beside it would have
    described a space that still holds its definitions
    [tested: test_every_public_write_door_honours_the_execution_scopes].
    """
    # Deferred because _space_execution reaches _space_objects, which imports
    # call_parameter_names from this module; a module-level import closes that
    # cycle. Clearing a space is not a hot door.
    # definition hooks run after execution and library initialization
    from metta._spaces.execution import speculative_enabled  # noqa: PLC0415

    with _DEFINE_LOCK:
        run_void_write(space.runtime, "metta_py_clear", space.name)
    if not speculative_enabled():
        release_definitions(space)

def release_definitions(space: Any) -> None:
    """Drop the process state describing a space's definitions, the
    reflection rows included, WITHOUT clearing the space's own store: the
    half a dying space needs, since the engine's release clears the store
    itself under its muting flag and the funnel must not run twice
    [tested: test_reflection_facts_follow_a_dropped_space].
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    with _DEFINE_LOCK:
        for key in [key for key in _DEFINE_REFLECTION if key[0] == space.name]:
            for fact in _DEFINE_REFLECTION.pop(key):
                _release_definition_fact(space, fact)
        for registry in (_DEFINE_CLAUSES, _DECLARED_DEFINES, _DEFINE_DOCUMENTATION):
            for key in [key for key in registry if key[0] == space.name]:
                del registry[key]
        _DEFINED_GENERATORS.difference_update(
            {key for key in _DEFINED_GENERATORS if key[0] == space.name}
        )
        for defined_key in [
            key for key in _DEFINED_FUNCTION_NAMES if key[0] == space.name
        ]:
            del _DEFINED_FUNCTION_NAMES[defined_key]
        classes.release(space)

def install_define(space: Any, fn: Callable[..., Any], name: str | None = None):
    """Install one compiled function while serializing shared definition state."""
    with _DEFINE_LOCK:
        return _install_define_locked(space, fn, name)

def install_prolog_define(
    space: Any, fn: Callable[..., Any], prolog: Any, name: str | None = None
):
    """Register the Prolog side and keep the Python as the reference twin.

    Nothing of the Python is compiled: the registered predicate IS the
    function, and defining the same name from both would stack a second
    clause the first would keep answering ahead of.
    """
    if not isinstance(fn, types.FunctionType):
        msg = f"define expects a Python function, got {_builtins.type(fn).__name__}"
        raise TypeError(msg)
    name = attribute_name(fn.__name__) if name is None else name
    origin = os.fspath(prolog)
    registered = space.register_prolog(path=origin)
    if name not in registered:
        msg = (
            f"{origin} does not register {name!r}, which is the MeTTa name of "
            f"{fn.__name__}; it registered {', '.join(sorted(registered)) or 'nothing'}. "
            f"A twin has to name the predicate it is the reference for."
        )
        raise CompileError(
            msg,
            construct="prolog twin",
        )
    params = list(_inspect.signature(fn).parameters)
    _refuse_mismatched_twin_arity(space, name, params, origin)
    _remember_defined_callable(space, fn, name)
    return _declare_define_module.PrologBacked(name, params, fn, space, origin)

def _refuse_mismatched_twin_arity(
    space: Any, name: str, params: list[str], origin: str
) -> None:
    """A twin of a different shape is not a twin, and would only ever be
    found by a caller. The predicate takes one argument per parameter plus
    the output, which is the convention every registered predicate follows.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    expected = len(params) + 1
    _, _, shapes, _ = space.runtime.apply_must("metta_py_function_shape", name)
    arities = [int(arity) for arity, _speedup, _indexed in shapes]
    if arities and expected not in arities:
        msg = (
            f"{name} in {origin} takes {' or '.join(str(a) for a in sorted(arities))} "
            f"argument(s), but its Python twin takes {len(params)}, so the "
            f"predicate would need arity {expected}: inputs then one output."
        )
        raise CompileError(
            msg,
            construct="prolog twin",
        )

def _is_nondeterministic(space: Any, called: str) -> bool:
    """Whether a registered operation or compiled definition has many answers."""
    operation = REGISTRY.get(called)
    if operation is not None and operation.kind in ("many", "raw_many"):
        return True
    return (space.name, called) in _DEFINED_GENERATORS

def _operation_effect(space: Any, called: str) -> EffectClass:
    """The callee's declared effect, conservatively top when unclassified."""
    operation = REGISTRY.get(called)
    if operation is not None:
        return operation.effect
    row = space.runtime.once(
        "metta_operation_effect(Name, Effect)",
        Name=called,
    )
    effect = row.get("Effect")
    return EffectClass.oracleIO if effect is None else EffectClass(str(effect))

def _returns_bool(space: Any, called: str) -> bool:
    """Whether get-type declares a named function's result as Bool."""
    declared = space.type(Symbol(called))
    return (
        isinstance(declared, Expression)
        and len(declared.children) >= 2
        and declared.children[0] == Symbol("->")
        and declared.children[-1] == Symbol("Bool")
    )

def call_parameter_names(space: Any, called: str, arity: int) -> tuple[str, ...] | None:
    """Return one exact parameter roster, or None when placement is ambiguous."""
    with _DEFINE_LOCK:
        clause_names = {
            tuple(clause["params"])
            for clause in _DEFINE_CLAUSES.get((space.name, called), ())
            if clause["arity"] == arity
        }
    if len(clause_names) == 1:
        return next(iter(clause_names))
    operation = REGISTRY.get(called)
    if operation is None or arity not in operation.arities:
        return None
    names = tuple(operation.parameter_names[:arity])
    return names if len(names) == len(set(names)) == arity else None

def _remember_defined_callable(space: Any, fn: types.FunctionType, name: str) -> None:
    """Record the exact installed name carried by one source function."""
    _DEFINED_FUNCTION_NAMES.setdefault((space.name, fn), set()).add(name)

def _installed_callable_name(space: Any, value: object) -> str | None:
    """Resolve the exact live name carried by a bound definition or operation."""
    if callable(value):
        operation = _declare_operations_module._registered_operation(value)
        if operation is not None and space.is_function(operation.name):
            return operation.name
    if not isinstance(value, types.FunctionType):
        return None
    names = _DEFINED_FUNCTION_NAMES.get((space.name, value), set())
    live = sorted(name for name in names if space.is_function(name))
    if len(live) <= 1:
        return live[0] if live else None
    msg = (
        f"{value.__name__!r} is installed as {', '.join(map(repr, live))}; "
        "use fn[...] to choose the exact MeTTa name"
    )
    raise CompileError(msg, construct="ambiguous defined call")

def _validate_clause_order(
    space: Any,
    name: str,
    patterns: dict[str, Atom],
    arity: int,
    earlier: list[dict[str, Any]],
) -> None:
    """Refuse collisions and clauses hidden by an earlier Python head."""
    if not earlier and space.is_function_here(name):
        msg = (
            f"{name!r} is already a function this space answers (an "
            f"engine builtin, an operation, or an equation): defining it "
            f"would stack a clause onto it and the existing definition "
            f"would keep answering first. Pick another name, or add the "
            f"equation deliberately with m.run."
        )
        raise CompileError(
            msg,
            construct="name collision",
        )
    same_arity = [clause for clause in earlier if clause["arity"] == arity]
    if patterns and any(not clause["patterns"] for clause in same_arity):
        msg = (
            f"a clause of {name} with a literal head comes after the "
            f"general clause, which already matches everything; define "
            f"the general clause last"
        )
        raise CompileError(
            msg,
            construct="clause order",
        )
    for clause in same_arity:
        earlier_patterns = clause["patterns"]
        if len(earlier_patterns) < len(patterns) and all(
            patterns.get(param) == value for param, value in earlier_patterns.items()
        ):
            msg = (
                f"a clause of {name} fixes every literal from an earlier "
                f"head and adds more literals, so the earlier clause "
                f"already answers every input this clause could match; "
                f"put the more specific clause first"
            )
            raise CompileError(
                msg,
                construct="clause order",
            )

def _validate_override_declaration(
    space: Any, fn: Callable[..., Any], name: str, earlier: list[dict[str, Any]]
) -> None:
    """Read `@typing.override` as the declaration that this definition shadows one.

    Inherited declarations do not shadow by accident here: a space's own
    definition governs as a complete set, C++'s unqualified-lookup rule, and
    the definition that hides an inherited one is deliberate and stays silent
    (2026-08-26, engine/metta/types.pl `governing_type_declaration_in/3`). What
    was missing was the other direction, the developer SAYING so, which is
    exactly `typing.override`'s contract: the decorator is a claim the checker
    refuses when nothing was there to override, and this door refuses it for
    the same reason on the MeTTa side.

    The decorator has to sit BELOW `@m.define`, on the function itself, because
    `typing.override` writes `__override__` on the object it is handed and the
    installer reads it from the function. Applied above, it is handed the
    `Defined`, whose `__slots__` refuse the attribute, and `typing.override`
    swallows that by its own specification, so the claim would be silently
    lost.

    Only the FIRST clause of a name asks: a second clause stacks onto a
    definition this space already owns, so `_is_function_inherited` is false by
    then and re-asking would refuse the continuation of a lawful override.
    """
    if earlier or not getattr(fn, "__override__", False):
        return
    if _space_functions._is_function_inherited(space, name):  # the private sibling of is_function_here, one package
        return
    msg = (
        f"{name!r} is declared @typing.override but overrides nothing: no "
        f"space {space.name} inherits from defines it, so there is no "
        f"definition here to shadow. Drop the decorator, or import the space "
        f"that defines {name!r} -- m.space(name, inherits=other) puts this "
        f"space under it, and (import! ...) into that space or into &self "
        f"puts the definition where this one can hide it."
    )
    raise CompileError(
        msg,
        construct="override declaration",
        remedy=Remedy(
            "drop @typing.override, or inherit from the space that defines "
            "the name",
            "quickfix",
            "prose",
            python="m.space(name, inherits=other)",
        ),
    )

def _same_clause(clause: dict[str, Any], canonical: tuple[Expression, ...], name: str) -> bool:
    old_equations = (*clause.get("raw_equations", clause["equations"]), *clause.get("aux", ()))
    old_canonical = _declare_define_module.canonical_aux_set(old_equations, name)
    return len(old_canonical) == len(canonical) and all(
        _alpha_eq(old, new) for old, new in zip(old_canonical, canonical, strict=True)
    )

def _locate_clause(
    earlier: list[dict[str, Any]],
    patterns: dict[str, Atom],
    arity: int,
    canonical: tuple[Expression, ...],
    name: str,
) -> tuple[bool, int | None]:
    """Return whether the clause is identical and which matching head it replaces."""
    replaced = None
    for position, clause in enumerate(earlier):
        if _same_clause(clause, canonical, name):
            return True, position
        if clause["arity"] == arity and clause["patterns"] == patterns:
            replaced = position
    return False, replaced

def _defined_result(
    space: Any,
    name: str,
    compiled: _declare_define_module.Compiled,
    bodies: tuple[Atom, ...],
    dispatcher: Any,
) -> _root.Defined:
    body = bodies[0] if len(bodies) == 1 else Expression([Symbol("superpose"), Expression(bodies)])
    return _declare_define_module.Defined(
        name,
        compiled.params,
        body,
        dispatcher,
        space,
        patterns=compiled.patterns,
        runtime_ops=compiled.runtime_ops,
        facts=compiled.facts,
        bodies=bodies,
    )

def _store_clause(
    space: Any,
    earlier: list[dict[str, Any]],
    *,
    name: str,
    patterns: dict[str, Atom],
    equations: tuple[Expression, ...],
    compiled: _declare_define_module.Compiled,
    dispatcher: Any,
    clause_twin: Any,
    replaced: int | None,
) -> None:
    record = _clause_record(patterns, equations, compiled)
    prospective = earlier.copy()
    if replaced is None:
        prospective.append(record)
    else:
        prospective[replaced] = record
    prospective = _materialize_clause_equations(name, prospective)

    previous_atoms = _physical_atoms(earlier)
    next_atoms = _physical_atoms(prospective)
    removed, added = _alpha_multiset_delta(previous_atoms, next_atoms)
    if removed:
        space.remove(removed[0], *removed[1:])
    try:
        space.add(*added)
    except BaseException:
        if added:
            space.remove(added[0], *added[1:])
        space.add(*removed)
        raise
    if replaced is None:
        earlier[:] = prospective
        append_twin_clause(dispatcher, clause_twin)
    else:
        earlier[:] = prospective
        replace_twin_clause(dispatcher, replaced, clause_twin)

def _physical_atoms(clauses: Sequence[dict[str, Any]]) -> list[Expression]:
    """Flatten the helper and materialized equations stored for clauses."""
    return [
        atom
        for clause in clauses
        for atom in (*clause.get("aux", ()), *clause["equations"])
    ]

def _alpha_multiset_delta(
    previous: Sequence[Expression], current: Sequence[Expression]
) -> tuple[list[Expression], list[Expression]]:
    """Return removed and added occurrences under alpha equivalence."""
    positions: dict[int, list[int]] = {}
    for index, atom in enumerate(current):
        positions.setdefault(id(atom), []).append(index)
    matched = [False] * len(current)
    removed: list[Expression] = []
    for atom in previous:
        identical = positions.get(id(atom), [])
        if identical:
            matched[identical.pop()] = True
            continue
        for index, candidate in enumerate(current):
            if not matched[index] and _alpha_eq(atom, candidate):
                matched[index] = True
                break
        else:
            removed.append(atom)
    added = [atom for index, atom in enumerate(current) if not matched[index]]
    return removed, added

def _clause_record(
    patterns: dict[str, Atom], equations: tuple[Expression, ...], compiled: _declare_define_module.Compiled
) -> dict[str, Any]:
    return {
        "arity": len(compiled.params),
        "params": tuple(compiled.params),
        "patterns": patterns.copy(),
        "equations": equations,
        "raw_equations": equations,
        "bodies": tuple(compiled.equation_bodies),
        "aux": tuple(compiled.aux),
        "facts": compiled.facts,
        "generator": compiled.generator,
    }

def _materialize_clause_equations(name: str, clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign physical equations, merging only connected overlapping heads."""
    materialized = [clause | {"equations": ()} for clause in clauses]
    by_arity: dict[int, list[int]] = {}
    for position, clause in enumerate(clauses):
        by_arity.setdefault(clause["arity"], []).append(position)

    for positions in by_arity.values():
        for component in _overlap_components(clauses, positions):
            if len(component) == 1:
                position = component[0]
                materialized[position]["equations"] = clauses[position]["raw_equations"]
                continue
            owner = component[0]
            materialized[owner]["equations"] = (
                _case_equation(name, [clauses[position] for position in component]),
            )
    return materialized

def _overlap_components(clauses: list[dict[str, Any]], positions: list[int]) -> list[list[int]]:
    """Connected components under compatible literal-head overlap."""
    remaining = set(positions)
    components: list[list[int]] = []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        component = [seed]
        frontier = [seed]
        while frontier:
            current = frontier.pop()
            neighbours = [
                candidate
                for candidate in sorted(remaining)
                if _heads_overlap(clauses[current]["patterns"], clauses[candidate]["patterns"])
            ]
            for candidate in neighbours:
                remaining.remove(candidate)
                component.append(candidate)
                frontier.append(candidate)
        components.append(sorted(component))
    return components

def _heads_overlap(left: dict[str, Atom], right: dict[str, Atom]) -> bool:
    return all(left[name] == right[name] for name in left.keys() & right.keys())

def _case_equation(name: str, clauses: list[dict[str, Any]]) -> Expression:
    """One general equation whose case rows preserve authored clause order.

    Each row is built from the clause's OWN parameter names. They are the same
    ARITY across a component and nothing more: two Python functions stacked
    under one MeTTa name are two functions, and a position is what they share.
    Reading every row through the first clause's names put a case arm's pattern
    variable and its body's variable at different names whenever the second
    clause spelled a parameter differently, and the call then answered its own
    unreduced body: `def f(a=0)` beside `def f(b)` answered `(+ $_8 1)` for
    `(f 5)` [measured 2026-09-07, and the same shape read a patterned position
    as unpatterned when the pattern was keyed by the other name].
    """
    subject_variables = [
        Variable(f"{name}-argument-{index}") for index in range(len(clauses[0]["params"]))
    ]
    subject: Atom = (
        subject_variables[0] if len(subject_variables) == 1 else Expression(subject_variables)
    )
    rows: list[Expression] = []
    for serial, clause in enumerate(clauses, start=1):
        params = clause["params"]
        rename = {
            variable.name: f"{name}-clause-{serial}-{variable.name}"
            for body in clause["bodies"]
            for variable in _variables_in(body)
        }
        rename.update(
            {
                param: f"{name}-clause-{serial}-{param}"
                for param in params
                if param not in clause["patterns"]
            }
        )

        def renamed(atom: Atom, mapping: dict[str, str] = rename) -> Atom:
            if isinstance(atom, Variable) and atom.name in mapping:
                return Variable(mapping[atom.name])
            return atom

        row_parts = [
            clause["patterns"][param] if param in clause["patterns"] else Variable(rename[param])
            for param in params
        ]
        pattern: Atom = row_parts[0] if len(row_parts) == 1 else Expression(row_parts)
        bodies = tuple(_map_atoms(body, renamed) for body in clause["bodies"])
        body: Atom = (
            bodies[0] if len(bodies) == 1 else Expression([Symbol("superpose"), Expression(bodies)])
        )
        rows.append(Expression([pattern, body]))
    head = Expression([Symbol(name), *subject_variables])
    body = Expression([Symbol("case"), subject, Expression(rows)])
    return Expression([Symbol("="), head, body])

def _variables_in(atom: Atom) -> tuple[Variable, ...]:
    found: list[Variable] = []

    def collect(node: Atom) -> Atom:
        if isinstance(node, Variable):
            found.append(node)
        return node

    _map_atoms(atom, collect)
    return tuple(found)

def _definition_facts(
    space: Any, name: str, clauses: list[dict[str, Any]]
) -> tuple[Expression, ...]:
    """The aggregate reflection of every live clause under one name."""
    if not clauses:
        return ()
    facts: list[Expression] = [Expression([Symbol("defined"), Symbol(space.name), Symbol(name)])]
    home = _atom_from_wire(space.to_wire())
    stream = any(clause["generator"] for clause in clauses)
    rosters: dict[int, set[tuple[str, ...]]] = {}
    for clause in clauses:
        rosters.setdefault(clause["arity"], set()).add(clause["params"])
        derived = clause["facts"]
        span = derived.source_span
        facts.append(
            Expression(
                [
                    Symbol("source-span"),
                    Symbol(space.name),
                    Symbol(name),
                    Grounded(span.path),
                    Grounded(span.start_line),
                    Grounded(span.start_column),
                    Grounded(span.end_line),
                    Grounded(span.end_column),
                ]
            )
        )
    facts.extend(
        call_signatures.native(name, next(iter(names)) if len(names) == 1 else (None,) * arity, home=home, stream=stream)
        for arity, names in rosters.items()
    )
    facts.extend(
        Expression(
            [
                Symbol("free-variable"),
                Symbol(space.name),
                Symbol(name),
                Symbol(free_variable),
            ]
        )
        for free_variable in sorted(
            {variable for clause in clauses for variable in clause["facts"].free_variables}
        )
    )
    effect = EffectClass.compose(clause["facts"].effect for clause in clauses)
    facts.append(Expression([Symbol("effect"), Symbol(name), Symbol(effect.value)]))
    return tuple(dict.fromkeys(facts))

def _retain_definition_fact(space: Any, fact: Expression) -> None:
    key = str(fact)
    count = _DEFINE_FACT_REFS.get(key, 0)
    if count == 0:
        space.runtime.must(
            "metta_py_add(Space, W)",
            Space=_declare_operations_module._REFLECTION_SPACE,
            W=fact.to_wire(),
        )
    _DEFINE_FACT_REFS[key] = count + 1

def _release_definition_fact(space: Any, fact: Expression) -> None:
    key = str(fact)
    count = _DEFINE_FACT_REFS.get(key, 0)
    if count <= 1:
        _DEFINE_FACT_REFS.pop(key, None)
        space.runtime.once(
            "metta_py_remove(Space, W, _)",
            Space=_declare_operations_module._REFLECTION_SPACE,
            W=fact.to_wire(),
        )
    else:
        _DEFINE_FACT_REFS[key] = count - 1

def _sync_definition_facts(space: Any, name: str, clauses: list[dict[str, Any]]) -> None:
    """Replace a definition's reflected facts, restoring the old set on error."""
    key = (space.name, name)
    previous = _DEFINE_REFLECTION.get(key, ())
    current = _definition_facts(space, name, clauses)
    retained: list[Expression] = []
    released: list[Expression] = []
    try:
        for fact in current:
            if fact not in previous:
                _retain_definition_fact(space, fact)
                retained.append(fact)
        for fact in previous:
            if fact not in current:
                _release_definition_fact(space, fact)
                released.append(fact)
    except BaseException:
        for fact in reversed(released):
            _retain_definition_fact(space, fact)
        for fact in reversed(retained):
            _release_definition_fact(space, fact)
        raise
    _DEFINE_REFLECTION[key] = current

def _document_definition(space: Any, name: str, dispatcher: Any) -> None:
    """Publish the dispatcher's canonical first-clause documentation."""
    key = (space.name, name)
    previous = _DEFINE_DOCUMENTATION.get(key)
    current = documentation_atom(name, dispatcher, kind="function")
    if current == previous:
        return
    if current is not None:
        space.add(current)
        _DEFINE_DOCUMENTATION[key] = current
    else:
        _DEFINE_DOCUMENTATION.pop(key, None)
    if previous is not None:
        space.remove(previous)

def _declare_definition(
    space: Any,
    fn: types.FunctionType,
    name: str,
    params: list[str],
) -> tuple[Expression, ...]:
    annotated = _declare_operations_module.resolved_annotations(fn)
    overloads = _typing.get_overloads(fn)
    key = (space.name, name)
    if not overloads and not any(label != "return" for label in annotated):
        return ()
    for signature in overloads:
        signature_params = tuple(_inspect.signature(signature).parameters.values())
        if len(signature_params) != len(params) or any(
            param.kind not in (
                _inspect.Parameter.POSITIONAL_ONLY,
                _inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            for param in signature_params
        ):
            msg = (
                f"an overload of {name} must have the implementation's fixed "
                f"positional arity {len(params)}; use separate @m.define "
                "clauses for different arities"
            )
            raise CompileError(msg, construct="overload signature")
    declarations = _declare_operations_module._type_declarations(
        name,
        list(_inspect.signature(fn).parameters.values()),
        None,
        [len(params)],
        fn,
        include_annotation_claims=False,
    )
    # What this name has ALREADY declared here, so a second clause adds the
    # arrow its own signature states rather than being suppressed whole, and a
    # clause repeating a signature adds nothing twice. One boolean per name
    # recorded only WHETHER it had declared anything, which is a different
    # question: a MeTTa name may carry several declarations, and the second
    # clause of `sized` published none of its own.
    published = _DECLARED_DEFINES.setdefault(key, [])
    added: list[Expression] = []
    try:
        for declaration in declarations:
            if declaration in published:
                continue
            space.add(declaration)
            added.append(declaration)
            published.append(declaration)
    except BaseException:
        _retract_declarations(space, key, added)
        raise
    return tuple(added)

def _retract_declarations(
    space: Any, key: tuple[str, str], declared: Iterable[Expression]
) -> None:
    """Remove exactly the declarations one install added, and forget them."""
    published = _DECLARED_DEFINES.get(key, [])
    for declaration in reversed(list(declared)):
        space.remove(declaration)
        if declaration in published:
            published.remove(declaration)

def _install_define_locked(space: Any, fn: Callable[..., Any], name: str | None = None):
    """Compile a Python function into MeTTa equations, decorator-style.

    Written for whoever is fluent in Python rather than s-expressions:
    the body is read as syntax and lowered deterministically, refusals
    name the construct, the line and what to write instead, and the
    original stays reachable as .py, a twin the equations can be checked
    against on any ground input.

        @m.define
        def add_one(n):
            return n + 1

        m.run("!(add-one 5)")       # [[6]]
        add_one.py(5)               # 6, ordinary Python

    The equation's name is the Python name through the one total map the
    whole surface uses: underscores become hyphens, so ``def add_one``
    installs ``add-one``, exactly as ``fn.add_one`` reaches it (the
    host-convention law, ruled 2026-08-24). A name the map cannot spell
    is asked for exactly: ``@m.define(name="add.one!")`` preserves every
    authored character.

    A generator compiles to nondeterminism (each yield one answer), a
    lambda to the engine's own |->, a comprehension to map-atom and
    filter-atom, and match(Pattern(x, y), template) to a match against
    the running space, lowercase free names in the pattern binding as
    variables.
    """
    if not isinstance(fn, types.FunctionType):
        msg = f"define expects a Python function, got {_builtins.type(fn).__name__}"
        raise TypeError(msg)

    # Implicit names use the same total mechanical map as the factories;
    # explicit names preserve every authored character.
    name = attribute_name(fn.__name__) if name is None else name
    compiled = _declare_define_module.compile_function(
        fn,
        known=space.is_function,
        nondet=partial(_is_nondeterministic, space),
        effect=partial(_operation_effect, space),
        returns_bool=partial(_returns_bool, space),
        metta_name=name,
        defined_name=partial(_installed_callable_name, space),
        call_parameters=partial(call_parameter_names, space),
    )
    dependencies = compiled.class_dependencies | classes.callable_dependencies(fn)
    if dependencies:
        compiled = compiled._replace(class_dependencies=frozenset(dependencies))
        return space.transaction(partial(_publish_define, space, fn, name, compiled))
    return _publish_define(space, fn, name, compiled)


def _publish_define(space: Any, fn: types.FunctionType, name: str, compiled: Any) -> Any:
    """Publish a compiled clause together with any class declarations it uses."""
    from metta._declare.classes import (  # noqa: PLC0415 -- class declarations share this installer
        owner_of,
    )

    for cls in sorted(compiled.class_dependencies, key=lambda cls: cls.__qualname__):
        install_type(space, cls)
    class_owner = owner_of(space)
    call_syntax.link(space, compiled.runtime_ops)
    # The equations lean on these shipped libraries (a dict literal needs
    # lib_dict's vocabulary); import! is idempotent per space, so the
    # dependency lands with the definition rather than ambiently.
    if class_owner is not None:
        class_owner.import_dependencies(compiled.libraries, (*compiled.equation_bodies, *compiled.aux))
    elif compiled.libraries:
        from metta._atoms.library import (  # noqa: PLC0415 -- definition hooks run after execution and library initialization
            import_library,
            lib,
        )

        for library_name in sorted(compiled.libraries):
            import_library(space, getattr(lib, library_name))
    params, patterns = compiled.params, compiled.patterns
    # Clause stacking is per (space, name), process-wide: equations live
    # in the space, not in whichever MeTTa instance happened to add them.
    earlier = _DEFINE_CLAUSES.setdefault((space.name, name), [])
    _validate_clause_order(space, name, patterns, len(params), earlier)
    _validate_override_declaration(space, fn, name, earlier)
    # The materializer below turns overlapping heads into one ordered case
    # equation. Keeping the authored bodies raw here lets replacement rebuild
    # the whole connected component without accumulating old guards.
    bodies = compiled.equation_bodies
    head = Expression([Symbol(name), *(patterns.get(p, Variable(p)) for p in params)])
    equations = tuple(Expression([Symbol("="), head, body]) for body in bodies)
    dispatcher = twin_dispatcher(fn)
    # Idempotence compares the main equation and all helper equations with
    # auxiliary names canonicalized. A loop-body-only or lifted-body-only
    # change must replace the old clause and its old helpers.
    canonical = _declare_define_module.canonical_aux_set((*equations, *compiled.aux), name)
    clause_twin = select_clause_twin(
        name,
        compiled.twin,
        compiled.hazards,
        patterns,
        params,
    )
    clause_twin.__doc__ = compiled.facts.doc
    duplicate, replaced = _locate_clause(
        earlier, patterns, len(params), canonical, name
    )
    if replaced is not None and not dispatcher_owns_clause(dispatcher, replaced):
        msg = (
            f"{name!r} is already defined here by a different Python "
            f"function; re-run that function to change the definition, "
            f"remove it first, or put the extra clauses under the one "
            f"function, where pattern= clauses and generator bodies "
            f"store one equation each"
        )
        raise CompileError(
            msg,
            construct="name collision",
        )
    if duplicate:
        # A re-run cell or module reload must not duplicate answers.
        if replaced is None:
            msg = "a duplicate clause has no replacement index"
            raise RuntimeError(msg)
        prospective = earlier.copy()
        prospective[replaced] = earlier[replaced] | {
            "facts": compiled.facts,
        }
        _sync_definition_facts(space, name, prospective)
        earlier[replaced]["facts"] = compiled.facts
        replace_twin_clause(dispatcher, replaced, clause_twin)
        _document_definition(space, name, dispatcher)
        _remember_defined_callable(space, fn, name)
        _importlib.import_module('metta._spaces.intents').register_definition_crossings(
            space, fn, equations[0], name
        )
        return _defined_result(space, name, compiled, bodies, dispatcher)
    prospective = earlier.copy()
    record = _clause_record(patterns, equations, compiled)
    if replaced is None:
        prospective.append(record)
    else:
        prospective[replaced] = record
    _sync_definition_facts(space, name, prospective)
    declared: tuple[Expression, ...] = ()
    try:
        declared = _declare_definition(space, fn, name, params)
        _store_clause(
            space,
            earlier,
            name=name,
            patterns=patterns,
            equations=equations,
            compiled=compiled,
            dispatcher=dispatcher,
            clause_twin=clause_twin,
            replaced=replaced,
        )
    except BaseException:
        _retract_declarations(space, (space.name, name), declared)
        _sync_definition_facts(space, name, earlier)
        raise
    defined = _defined_result(space, name, compiled, bodies, dispatcher)
    _document_definition(space, name, dispatcher)
    if compiled.generator:
        _DEFINED_GENERATORS.add((space.name, name))
    _remember_defined_callable(space, fn, name)
    _importlib.import_module('metta._spaces.intents').register_definition_crossings(
        space, fn, equations[0], name
    )
    return defined

def install_type(
    space: Any,
    cls: _builtins.type | None = None,
    *,
    accessors: bool = True,
    methods: bool = True,
):
    """Declare a Python class INTO this space, decorator-style: the
    (: ...) declarations land as atoms, an expression-image class
    (a dataclass, a NamedTuple) gains one accessor equation per
    field, and its own METHODS register as MeTTa functions, so the
    class crosses with its behavior, not only its structure.

        @m.define
        @dataclass
        class Point:
            x: float
            y: float
            def norm(self) -> float:
                return (space.x ** 2 + space.y ** 2) ** 0.5

        m.run("!(Point-x (Point 3.0 4.0))")        # [[3.0]]
        m.run("!(Point-norm (Point 3.0 4.0))")     # [[5.0]]

    A method receives the instance whether it arrives as a
    constructor TERM (rebuilt through the translator) or as a live
    handle, and a result the translator knows projects back as a
    term, so a method answering the class answers something MeTTa
    keeps matching and Python builds back. An equation over the
    constructor is then a method written in MeTTa itself, on equal
    footing. An Enum declares its members; get-type sees them all.
    Returns the class, so it stacks under @dataclass.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def apply(target: _builtins.type) -> _builtins.type:
        return classes.install(
            space, target, accessors=accessors, methods=methods
        )

    return apply(cls) if cls is not None else apply

def _register_methods(plan: Any) -> None:
    """Every method the class itself defines, as a MeTTa function
    named {Type}-{method}: the instance argument accepts a
    constructor term (rebuilt through the translator) or a live
    handle, and results the translator knows project back to terms.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    target, type_name = plan.cls, plan.name

    def projectable(value: Any) -> Any:
        try:
            _convert_api().ensure_registered(_builtins.type(value))
        except TypeError:
            return value
        return _convert_api().project(value).atom

    def wrapper_for(fn):
        def call(instance, *args):
            subject = (
                _convert_api().build(instance, target)
                if isinstance(instance, Expression)
                else (instance.value if isinstance(instance, Grounded) else instance)
            )
            values = [a.value if isinstance(a, Grounded) else a for a in args]
            result = fn(subject, *values)
            if result is None:
                return None
            if isinstance(result, Atom):
                return result
            if isinstance(result, (bool, int, float, str)):
                return _encode(result)
            return projectable(result)

        return call

    for method_name, fn in vars(target).items():
        if method_name.startswith("_") or not _inspect.isfunction(fn):
            continue
        parameters = list(_inspect.signature(fn).parameters.values())[1:]
        required = sum(1 for p in parameters if p.default is _inspect.Parameter.empty)
        arities = list(range(1 + required, len(parameters) + 2))
        operation_name = f"{type_name}-{method_name}"
        plan.operation(
            wrapper_for(fn),
            name=operation_name,
            effect=EffectClass.oracleIO,
            declarations=[
                _expr(S.arguments, S[operation_name], S.atoms)
            ],
            arities=arities,
        )

@overload
@dataclass_transform(eq_default=False)
def define(  # type: ignore[overload-overlap]
    space: _root.Space,
    fn: _builtins.type[_T],
    /,
    *,
    accessors: bool = ...,
    methods: bool = ...,
) -> _builtins.type[_T]: ...

@overload
def define(
    space: _root.Space,
    fn: Callable[_P, _R],
    /,
    *,
    name: str | None = ...,
    accessors: bool = ...,
    methods: bool = ...,
) -> _root.Defined[_P, _R]: ...

@overload
def define(
    space: _root.Space, *, name: str
) -> Callable[[Callable[_P, _R]], _root.Defined[_P, _R]]: ...

@overload
def define(
    space: _root.Space, *, prolog: str | os.PathLike[str], name: str | None = None
) -> Callable[[Callable[_P, _R]], _declare_define_module.PrologBacked[_P, _R]]: ...

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch09_types/test_refinements.py::test_a_defined_head_refuses_a_violating_argument_by_name_and_accepts_the_rest', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_define_decorator_declares_field_types', 'extensions/python/tests/ch11_python_as_a_notation/test_authoring_surface.py::test_calling_a_defined_object_evaluates_and_an_unmatched_call_answers_itself'),
    alias='define',
    async_signature=_doors.Signature('self, fn: Callable | None = None, /, *, prolog: Any = None, name: Any = None, accessors: bool = True, methods: bool = True', returns='Any'),
    async_reason="the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the worker would register on the caller's thread rather than the engine's. Only the applied form crosses",
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:define]'),),
)
def define(
    space: _root.Space,
    fn: Callable[..., Any] | None = None,
    *,
    prolog: str | os.PathLike[str] | None = None,
    name: str | None = None,
    accessors: bool = True,
    methods: bool = True,
) -> Any:
    """Compile a Python function into MeTTa equations, decorator-style.

    With `prolog=`, the Prolog file is registered and becomes the
    function, and the Python stays as the reference twin rather than
    being compiled:

        @m.define(prolog=Path(__file__).parent / "fast.pl")
        def vec_dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        m.eval("(vec-dot (1 2) (3 4))")[0] # the Prolog answer
        vec_dot.py((1, 2), (3, 4))          # the reference answers

    Rewriting a defined function in Prolog for speed used to mean
    deleting the Python and the differential oracle with it. Here both
    are declared together and `metta.testing.check_twin` proves they
    agree on ground inputs. The file must register the function's own
    MeTTa name and at the twin's arity, inputs then one output, and
    says so if it does not; its `metta_export` declaration owns the
    types, so annotations on the Python are documentation only.

    Written for whoever is fluent in Python rather than s-expressions:
    the body is read as syntax and lowered deterministically, refusals
    name the construct, the line and what to write instead, and the
    original stays reachable as .py, a twin the equations can be checked
    against on any ground input.

        @m.define
        def add_one(n):
            return n + 1

        add_one(5)                  # [6], evaluated by the engine
        S.add_one(5)                # (add_one 5), staged as data
        add_one.py(5)               # 6, ordinary Python

    The equation's implicit name applies the factories' total mechanical
    map, replacing each underscore with a hyphen. ``name=`` is the exact
    quoted-name escape for punctuation that map cannot preserve:

        @m.define(name="add-one")
        def add_one(n):
            return n + 1

    The same attribute mapping applies to the definition name itself:
    ``def not_provable`` lands as ``not-provable``. An authored
    MeTTa underscore therefore uses explicit ``name="not_provable"``.

    A generator compiles to nondeterminism (each yield one answer), a
    lambda to the engine's own |->, a comprehension to map-atom and
    filter-atom, and match(Pattern(x, y), template) to a match against
    the running space, lowercase free names in the pattern binding as
    variables.
    """
    if isinstance(fn, _builtins.type):
        if prolog is not None or name is not None:
            msg = "define on a class does not take name= or prolog="
            raise TypeError(msg)
        return install_type(space, fn, accessors=accessors, methods=methods)
    if prolog is not None:
        if fn is not None:
            msg = (
                "define(prolog=...) is applied as a decorator, so the "
                "function comes from the definition below it"
            )
            raise TypeError(
                msg
            )
        return lambda function: install_prolog_define(space, function, prolog, name)
    if fn is None:
        if name is None:
            msg = "define takes a function or class, or name= or prolog= and then one"
            raise TypeError(msg)
        return lambda function: install_define(space, function, name)
    # The annotation widened to Callable so the overloads can carry the
    # decorated signature through. install_definition still refuses
    # anything without Python source, which is where the narrowing the
    # annotation used to imply is actually enforced
    # [tested test_define_refuses_callable_objects].
    return install_define(space, fn, name)

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_authoring_surface.py::test_a_rules_generator_scopes_its_variables_to_its_parameters', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_rules_lower_emits_queryable_declaration_and_registers_the_head', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_rules_lower_refuses_an_empty_rule_set_before_mutating'),
)
def rules(space: _root.Space, fn: Callable[..., Any]) -> _declare_rules_module.Rules:
    """Collect and land a non-exclusive equation bundle in this space."""
    bundle = _declare_rules_module.rules(fn)
    space += bundle
    return bundle

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.callable,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_library_surface_wave2.py::test_pre_add_compiles_the_four_verdict_judge', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_aio.py::test_async_rules_and_pre_add_land_as_awaitable_calls'),
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:pre-add]'),),
)
def pre_add(space: _root.Space, fn: _root.Defined[..., Any] | Callable[..., Any]) -> _root.Defined[..., Any]:
    """Compile or accept one unary judge and claim this space's write hook.

    The common decorator stack places ``@pre_add`` above ``@define``, so
    an existing Defined keeps the module that owns its equations. A raw
    function is compiled into this space before claiming the hook.
    """
    handler = fn if isinstance(fn, _declare_define_module.Defined) else space.define(fn)
    if len(handler.params) != 1:
        msg = "a pre-add judge takes exactly one incoming atom"
        raise TypeError(msg)
    handler.space.eval(
        Expression(
            [Symbol("declare-pre-add!"), space, Symbol(handler.name)]
        )
    )
    return handler

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_p5_annotations.py::test_an_atom_in_annotation_position_is_the_type_itself', 'extensions/python/tests/ch09_types/test_inference.py::test_declaring_adds_exactly_the_proposals', 'extensions/python/tests/ch09_types/test_structural_aliases.py::test_a_failed_cycle_and_conflict_leave_previous_behavior_intact'),
    refuses=(_doors.Refusal(_doors.RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_door_refuses_a_missing_engine_answer[type]'),),
)
def type(space: _root.Space, atom: Any) -> Atom:  # noqa: A001 -- the marked body preserves its public door name
    """Return this space's first ``get-type`` answer, including undefined."""
    answers = space.eval(Expression([Symbol("get-type"), _to_atom(atom)]))
    if not answers or not isinstance(answers[0], Atom):
        msg = f"get-type returned no type for {atom!r}"
        raise EngineError(msg)
    return answers[0]

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch09_types/test_inference.py::test_a_catalogue_row_is_not_data_about_a_head', 'extensions/python/tests/ch09_types/test_inference.py::test_a_declared_head_is_skipped', 'extensions/python/tests/ch09_types/test_inference.py::test_a_nested_call_carries_its_heads_declared_result'),
)
def infer_types(space: _root.Space, *, declare: bool = False) -> list[Atom]:
    """Propose a `(: head (-> ...))` for every head here that has none.

        m.infer_types()                 # the proposals, nothing added
        m.infer_types(declare=True)     # add exactly those proposals

    One walk of the stored atoms names the narrowest kind covering the
    children observed at each argument position: all numbers `Number`,
    all strings `String`, all booleans `Bool`, all symbols `Symbol`, all
    expressions sharing one head that head's declared result type when it
    has one and `Expression` otherwise, mixed `Atom`. A variable observed
    at a position stands for anything and constrains nothing, so a
    position with only variables is `%Undefined%`. That is
    `pandas.api.types.infer_dtype` moved from a column's values to an
    argument position's children, its `skipna` included.

    An equation head's RESULT is what its body answers: a literal's own
    type, or the declared result of the head the body calls, which is how
    `(= (double $x) (* $x 2))` proposes `(-> %Undefined% Number)`.
    Anything else, a bare symbol included, is `%Undefined%`, because a
    symbol's own type is `%Undefined%` here too. A head observed at two
    arities gets one proposal per arity, and a head this space already
    declares gets none.

    `declare=True` adds exactly the returned atoms and nothing else, so
    `get-type` then answers them. One thing changes with the program's
    BEHAVIOUR and is worth reading before a proposal is accepted: `Atom`
    in an argument position is a metatype and stops the engine evaluating
    that argument, so a mixed position turns `(f (+ 1 2))` from `3` into
    the term `(+ 1 2)` [measured 2026-09-07]. Proposing and adding are
    two calls for that reason.

    Cost is O(atoms x arity): one pass over the space, plus one type
    lookup per distinct head. `metta.stubs()` and `inspect.signature()`
    show the same arrows, marked inferred, without adding anything.
    """
    lazy('metta.foreign').require_capability(
        space._space, "enumerate", "infer_types"
    )
    proposals: list[Atom] = [row.declaration for row in inferred(space)]
    if declare:
        space.add(*proposals)
    return proposals

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch08_data/test_library_card.py::test_a_card_documents_what_the_library_documents', 'extensions/python/tests/ch09_types/test_refinements.py::test_doc_and_timezone_stay_in_the_annotation_claim', 'extensions/python/tests/ch11_python_as_a_notation/test_define.py::test_one_docstring_reaches_help_dot_doc_and_get_doc'),
    alias='doc',
    refuses=(_doors.Refusal(_doors.RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_door_refuses_a_missing_engine_answer[doc]'),),
)
def doc(space: _root.Space, atom: Any) -> Atom:
    """Return this space's structured ``get-doc`` answer for one subject.

    The answer is the ``(@doc ...)`` atom the engine holds for the
    subject, whether it was documented in MeTTa source or built from a
    Python docstring:

        m.doc(S.area)
        # (@doc-formal (@item area) (@kind function) (@desc "Circle area.") ...)

    A subject with no documentation raises, exactly as ``type`` raises
    for a subject ``get-type`` cannot answer.
    """
    answers = space.eval(
        Expression([Symbol("get-doc"), _to_atom(space), _to_atom(atom)])
    )
    if not answers or not isinstance(answers[0], Atom):
        msg = f"get-doc returned no documentation for {atom!r}"
        raise EngineError(msg)
    return answers[0]

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
