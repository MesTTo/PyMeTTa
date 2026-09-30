"""Purpose: install compiled Python functions and class declarations into a space.
Guarantees:
  - equation heads and stacked clause renaming preserve Python underscore
    parameters [tested: test_stacked_underscore_parameters_retain_order_and_binding,
    test_underscore_callable_parameters_keep_python_keyword_labels; commit=69d1511c099eb6aa80c38d898da49487c42470f0]
  - each native definition space and head owns its Python twin family;
    clearing the space retires its reference bindings [tested:
    test_twin_families_follow_their_definition_space,
    test_same_python_name_can_have_distinct_native_twin_heads,
    test_clear_starts_a_new_twin_family; commit=54ca898ed3ce78464a4f2648b1ce92a985ec3db8]
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
  - the space is the authority on a definition: one record per space and
    name remembers what define published, and whether it still stands is
    asked of the space, so a clause is a duplicate only while the space holds
    an equation its head answers through, and a re-define restores whatever
    a removal took, equations, helpers, declarations and doc, and clears what
    a partial removal left behind [tested 2026-09-30T08:34:03+10:00:
    test_redefining_after_an_equation_removal_publishes_again,
    test_a_redefinition_restores_a_removed_declaration_and_doc,
    test_a_redefinition_restores_only_what_a_removal_took]
  - remove_definition, the body of m.remove(<Defined>), takes every atom a
    definition published, every stacked clause, through the ordinary removal
    door in the one transaction define publishes through and retires its
    record, reflection rows, twin family and lint evidence, leaving an older
    atom that merely unifies with one of them; the name-collision refusal
    names that door
    [tested 2026-09-30T08:34:03+10:00: test_removing_a_defined_takes_its_whole_definition,
    test_removing_a_stacked_defined_takes_every_clause,
    test_the_door_leaves_an_older_equation_that_unifies_with_its_own,
    test_the_collision_refusal_names_the_definition_door]
  - every committed change to one of a definition's equations, through any
    door, a program's remove-atom and add-atom as much as a Python one, moves
    its reflection rows, twin family and lint evidence to the clauses the
    space still answers through: the engine tells it through
    seam:equation_changed/2 once the outermost transaction commits, and the
    notice, which can arrive while its writer holds an engine lock, is only
    recorded there and reconciled at the next crossing made with no engine
    callback open; a rolled-back or speculative write is never heard, a
    definition never hears its own writes, and a write to a head no
    definition publishes crosses to no Python [tested 2026-09-30T08:34:03+10:00:
    test_a_program_removing_and_restoring_an_equation_moves_the_definition,
    test_a_rolled_back_program_removal_changes_nothing,
    test_a_program_removal_is_heard_once_its_transaction_commits,
    test_a_speculative_program_removal_commits_nothing,
    test_an_unwatched_equation_write_crosses_to_no_python,
    test_a_notice_neither_locks_nor_crosses,
    test_a_definition_brought_back_is_reflected_again,
    test_definition_caches_follow_atoms_given_back]
  - every engine write of a define, its reflection rows, declarations,
    equations and doc, rides one transaction (metta_py_publish_definition/2),
    so a define failing at any of them leaves the reflection rows, the record,
    the twin family and every space whose storage the transaction reaches as
    they were, an equal equation the space held before included, and tells
    no subscriber of any of them; a provider declaring transactional writes
    is enlisted and rolls back with it; a provider that declares nothing
    about its writes takes a definition and gives it back, as the engine's
    own rule registration does, and one whose storage no transaction reaches
    keeps what it took, which the failure raises as a PartialWriteError
    naming exactly the atoms it kept and lost, from the failure itself;
    a watcher raising on a define's or a removal's
    committed writes leaves them recorded before its SubscriberError reaches
    the caller; its clauses keep the static type shortcuts a define outside
    any transaction compiles with; and a define inside its own space's batch
    is refused
    [tested 2026-09-30T08:34:03+10:00: test_a_define_failing_part_way_leaves_an_equal_equation_standing,
    test_a_define_failing_at_any_write_changes_nothing,
    test_a_definition_publishes_into_and_leaves_a_provider_that_declares_nothing,
    test_a_define_into_a_transactional_provider_rolls_it_back,
    test_a_define_failing_in_a_provider_outside_the_engine_names_what_it_kept,
    test_a_removal_failing_in_a_provider_outside_the_engine_names_what_it_lost,
    test_a_provider_unreadable_after_a_failed_define_is_named_not_hidden,
    test_a_watcher_failing_after_a_definition_commits_leaves_it_recorded,
    test_a_defined_function_keeps_its_static_type_shortcuts,
    test_failed_equation_publication_rolls_back_its_early_declaration,
    test_failed_overload_publication_rolls_back_all_arrows]
  - every registry change enlists its Python preimage, so a transaction's
    rollback restores the record, twin family and reflection counts with the
    atoms, and inside speculative() nothing is committed while the snapshot
    discards the writes; after any interleaving of define, re-define, removal
    and clear in any of those scopes the caches agree with the space, and so
    they do with atoms returned by add and transfer too [tested
    2026-09-30T08:34:03+10:00: test_an_equation_removal_follows_its_transaction,
    test_the_door_follows_its_transaction,
    test_a_rolled_back_redefinition_restores_the_twin,
    test_a_rolled_back_clear_keeps_its_definitions,
    test_a_speculative_define_and_removal_leave_no_trace,
    test_definition_caches_agree_with_the_space,
    test_definition_caches_follow_atoms_given_back]
  - Time: a first define reads nothing and writes everything in one
    crossing; a define of a name this space records, a removal of a Defined,
    and each committed write to a head a definition publishes read the
    definition back in one crossing of W = its physical atoms + declarations
    + doc, so stacking K disjoint two-equation clauses reads K(K-1) atoms
    beside its K writes of 2K atoms; a write to any other head reads nothing
    [source 2026-09-30T03:13:08+10:00: _standing, equation_changed, and metta_py_held/3
    and metta_py_publish_definition/2 in extensions/python/metta/_binding/store.pl]
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
from collections import deque
from collections.abc import Callable, Hashable, MutableMapping, Sequence
from dataclasses import dataclass
from dataclasses import replace as _replace
from functools import partial
from typing import TYPE_CHECKING, Any, dataclass_transform, overload

import metta._declare.define as _declare_define_module
import metta._declare.operations as _declare_operations_module
import metta._declare.rules as _declare_rules_module
import metta._spaces.scope as _spaces_scope_module
import metta.doors as _doors
from metta._atoms.designation import _P, _R, _T
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _alpha_eq,
    _atom_from_wire,
    _map_atoms,
    _to_atom,
)
from metta._atoms.names import attribute_name, binding_name
from metta._binding.dispatch import REGISTRY
from metta._binding.runtime import at_safe_point, runtime
from metta._catalog import call_signatures
from metta._catalog.declarations import inferred
from metta._catalog.documentation import documentation_atom
from metta._compile.twins import (
    TwinNamespace,
    select_clause_twin,
)
from metta._declare import call_syntax, classes
from metta._declare import functions as _space_functions
from metta._errors.errors import (
    CompileError,
    EngineError,
    PartialWriteError,
    Remedy,
    SubscriberError,
)
from metta._lazy import lazy
from metta._spaces.execution import run_void_write, speculative_enabled
from metta._spaces.handle import space_wire
from metta.vocabularies import EffectClass


@dataclass(frozen=True, slots=True)
class _Definition:
    """What define published under one name in one space.

    Whether the space still holds it is the space's answer, read by
    _standing whenever it decides anything, so a removal through any door, a
    rollback and a discarded scope need no entry of their own here.

    ``clauses`` are the clause records the last define published, in
    definition order, each carrying its materialised physical equations,
    helpers, twin and Python owner; a removal leaves them recorded, so the
    atoms a partial removal left behind are still known and the next define
    or removal takes them;
    ``declared`` and ``documented`` the declarations and the doc atom this
    definition added; ``reflected`` the facts it retained in ``&metta``.
    Replaced whole, never mutated, so a preimage is the object itself.
    """

    clauses: tuple[dict[str, Any], ...] = ()
    declared: tuple[Expression, ...] = ()
    documented: Expression | None = None
    reflected: tuple[Expression, ...] = ()


@dataclass(frozen=True, slots=True)
class _Standing:
    """The space's answer about one definition."""

    #: The clause records the space still answers through, in definition
    #: order: it holds one of the equations the clause's head owns, or, for a
    #: member of a merged case component, the owner's case equation.
    live: tuple[dict[str, Any], ...]
    #: Every recorded physical atom the space holds, a partial removal's
    #: debris included, which is the "previous" of a publication's difference.
    held: tuple[Expression, ...]
    #: The recorded or asked-about declarations the space holds.
    declared: tuple[Expression, ...]
    #: Whether the space holds the recorded doc atom.
    documented: bool


_UNRECORDED = _Definition()

_DEFINITIONS: dict[tuple[str, str], _Definition] = {}
_DEFINE_TWINS: dict[str, TwinNamespace] = {}

_DEFINE_FACT_REFS: dict[str, int] = {}

_DEFINED_FUNCTION_NAMES: dict[tuple[str, types.FunctionType], frozenset[str]] = {}

class _DefineLock:
    """A re-entrant lock that can say whether this thread holds it.

    Python's threading.RLock cannot be asked that, and the reconciliation a
    notice asks for (_settle_noticed) must wait while this thread is inside a
    definitions critical section, whose own write is still under way.
    """

    __slots__ = ("_depth", "_lock")

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._depth = threading.local()

    def __enter__(self) -> None:
        self._lock.acquire()
        self._depth.value = getattr(self._depth, "value", 0) + 1

    def __exit__(self, *_exc: object) -> None:
        self._depth.value -= 1
        self._lock.release()

    def held(self) -> bool:
        """Whether this thread is inside a critical section of this lock."""
        return getattr(self._depth, "value", 0) > 0


_DEFINE_LOCK = _DefineLock()

# The definitions engine notices named (equation_changed), waiting for a safe
# point. A notice can reach Python while its writer holds an engine lock, the
# typing policy's around a single equation added outside any transaction, and
# a define waits for engine locks while it holds _DEFINE_LOCK, so the notice
# only appends here and the reconciliation runs where no engine callback is
# open (_binding/runtime.py, at_safe_point).
_NOTICED: deque[tuple[list[Any], str]] = deque()

def _put(mapping: MutableMapping[Any, Any], key: Hashable, value: Any, what: str) -> None:
    """Change one registry entry, None removing it, after enlisting its preimage."""
    _declare_operations_module._replace_entry(mapping, key, value, description=what)

def clear_definitions(space: Any) -> None:
    """Clear one space and the process state describing its definitions.

    Through the execution-policy wrapper, so a clear inside a scope obeys it
    the way every other call in the block does. The process state follows the
    engine rather than accompanying it: inside `with m.speculative():` the
    snapshot discards the clear, and a registry emptied beside it would have
    described a space that still holds its definitions
    [tested: test_every_public_write_door_honours_the_execution_scopes].
    """
    with _DEFINE_LOCK:
        run_void_write(space.runtime, "metta_py_clear", space.name)
    if not speculative_enabled():
        release_definitions(space)
        # The declaration rows the linked operations held here went with the
        # store, and the ownership counts saying they were there must go too,
        # or the next define links an operation that declares nothing
        # [tested: test_clear_starts_a_new_twin_family,
        # test_clearing_a_space_lets_a_later_link_declare_again; commit=e01a1a46a1bcbce16862c3a2cd4175bb9127fd13].
        _declare_operations_module._forget_space(space.name)

def release_definitions(space: Any) -> None:
    """Drop the process state describing a space's definitions, the
    reflection rows included, WITHOUT clearing the space's own store: the
    half a dying space needs, since the engine's release clears the store
    itself under its muting flag and the funnel must not run twice
    [tested 2026-09-30T08:34:03+10:00: test_reflection_facts_follow_a_dropped_space]. Every entry it
    drops enlists its preimage, so a clear a transaction rolls back leaves its
    definitions described [tested 2026-09-30T08:34:03+10:00: test_a_rolled_back_clear_keeps_its_definitions].
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    with _DEFINE_LOCK:
        keys = [key for key in _DEFINITIONS if key[0] == space.name]
        for key in keys:
            _sync_definition_facts(space, _DEFINITIONS[key].reflected, ())
            _put(_DEFINITIONS, key, None, f"definition {key[1]!r} in {key[0]}")
        if keys:
            _watch(space, [(name, ()) for _, name in keys])
        _put(_DEFINE_TWINS, space.name, None, f"twin namespace of {space.name}")
        for defined_key in [key for key in _DEFINED_FUNCTION_NAMES if key[0] == space.name]:
            _put(_DEFINED_FUNCTION_NAMES, defined_key, None, f"installed names in {space.name}")
        classes.home_retired(space.name)

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
    """Whether a registered operation or compiled definition has many answers.

    A generator clause counts only while the space still holds it, so the
    space is asked only when the definition recorded one.
    """
    operation = REGISTRY.get(called)
    if operation is not None and operation.kind in ("many", "raw_many"):
        return True
    with _DEFINE_LOCK:
        definition = _DEFINITIONS.get((space.name, called))
        if definition is None or not any(clause["generator"] for clause in definition.clauses):
            return False
        return any(clause["generator"] for clause in _standing(space, definition).live)

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
    """Return one exact parameter roster, or None when placement is ambiguous.

    A definition's roster counts only while the space still holds its clause,
    so the space is asked only when the definition recorded one at this arity.
    """
    with _DEFINE_LOCK:
        definition = _DEFINITIONS.get((space.name, called), _UNRECORDED)
        clause_names: set[tuple[str, ...]] = set()
        if any(clause["arity"] == arity for clause in definition.clauses):
            clause_names = {
                tuple(clause["params"])
                for clause in _standing(space, definition).live
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
    key = (space.name, fn)
    names = _DEFINED_FUNCTION_NAMES.get(key, frozenset())
    if name not in names:
        _put(_DEFINED_FUNCTION_NAMES, key, names | {name}, f"installed names of {fn.__name__}")

def _installed_callable_name(space: Any, value: object) -> str | None:
    """Resolve the exact live name carried by a bound definition or operation."""
    if callable(value):
        operation = _declare_operations_module._registered_operation(value)
        if operation is not None and space.is_function(operation.name):
            return operation.name
    if not isinstance(value, types.FunctionType):
        return None
    names = _DEFINED_FUNCTION_NAMES.get((space.name, value), frozenset())
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

def _physical_atoms(clauses: Sequence[dict[str, Any]]) -> list[Expression]:
    """Flatten the helper and materialized equations stored for clauses."""
    return [
        atom
        for clause in clauses
        for atom in (*clause.get("aux", ()), *clause["equations"])
    ]

def _standing(
    space: Any, definition: _Definition, asked: Sequence[Expression] = ()
) -> _Standing:
    """Ask the space which of this definition's atoms it still holds.

    One crossing, metta_py_held/3, for every recorded physical atom, recorded
    declaration and the recorded doc, plus ``asked``: the declarations a
    define is about to publish. Each answer is an exact stored occurrence,
    one per atom asked, so a clause published twice needs two copies. A
    clause stands while the space holds one of the equations its head
    answers through, its own or, inside a merged case component, the
    owner's case equation; a helper or a sibling yield it lost is debris the
    next define restores, and a clause whose head the space no longer
    answers through is gone, so its name is free for another function.
    Time: one crossing carrying the definition's recorded atoms and
    ``asked``; none when both are empty.
    """
    physical = _physical_atoms(definition.clauses)
    declarations = tuple(dict.fromkeys((*definition.declared, *asked)))
    documented = () if definition.documented is None else (definition.documented,)
    atoms = (*physical, *declarations, *documented)
    if not atoms:
        return _Standing((), (), (), documented=False)
    flags = [
        bool(flag)
        for flag in space.runtime.apply_must(
            "metta_py_held", space.name, [atom.to_wire() for atom in atoms]
        )
    ]
    answering: list[bool] = []
    position = 0
    for clause in definition.clauses:
        helpers = len(clause.get("aux", ()))
        heads = len(clause["equations"])
        answering.append(any(flags[position + helpers:position + helpers + heads]))
        position += helpers + heads
    owners = _component_owners(definition.clauses)
    live = tuple(
        clause
        for index, clause in enumerate(definition.clauses)
        if answering[owners[index]]
    )
    counted = len(physical)
    return _Standing(
        live,
        tuple(atom for atom, flag in zip(physical, flags, strict=False) if flag),
        tuple(
            declaration
            for declaration, flag in zip(declarations, flags[counted:], strict=False)
            if flag
        ),
        documented=bool(documented) and flags[-1],
    )

def _component_owners(clauses: Sequence[dict[str, Any]]) -> list[int]:
    """The position whose record holds each clause's physical equations.

    _materialize_clause_equations gives a merged component's case equation to
    its first member and nothing to the rest, by the same overlap components.
    """
    owners = list(range(len(clauses)))
    by_arity: dict[int, list[int]] = {}
    for position, clause in enumerate(clauses):
        by_arity.setdefault(clause["arity"], []).append(position)
    for positions in by_arity.values():
        for component in _overlap_components(list(clauses), positions):
            for position in component:
                owners[position] = component[0]
    return owners

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
    fn: types.FunctionType,
    patterns: dict[str, Atom],
    equations: tuple[Expression, ...],
    compiled: _declare_define_module.Compiled,
    twin: Callable[..., Any],
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
        # The Python name that owns the clause, which is what the collision
        # refusal compares, and the clause's twin and its lint owner with the
        # events filed under it, which follow the clause out and back in.
        "owner": fn.__name__,
        "twin": twin,
        "crossings": None,
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
                binding_name(param): f"{name}-clause-{serial}-{binding_name(param)}"
                for param in params
                if param not in clause["patterns"]
            }
        )

        def renamed(atom: Atom, mapping: dict[str, str] = rename) -> Atom:
            if isinstance(atom, Variable) and atom.name in mapping:
                return Variable(mapping[atom.name])
            return atom

        row_parts = [
            clause["patterns"][param] if param in clause["patterns"] else Variable(rename[binding_name(param)])
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

def _reflection_moves(
    previous: tuple[Expression, ...], current: tuple[Expression, ...]
) -> tuple[dict[str, int], list[Expression], list[Expression]]:
    """What moving a definition's reflected facts from ``previous`` to ``current`` changes.

    Answers the reference count the move leaves for each fact it moves, 0
    where one reaches zero; the facts whose count leaves zero, which the
    reflection space gains; and the facts whose count reaches zero, which it
    loses. Definitions share a fact by counting it, so the space holds one
    copy however many reflect it.
    """
    counts: dict[str, int] = {}
    gained: list[Expression] = []
    lost: list[Expression] = []
    for fact in current:
        if fact not in previous:
            key = str(fact)
            count = counts.get(key, _DEFINE_FACT_REFS.get(key, 0))
            if count == 0:
                gained.append(fact)
            counts[key] = count + 1
    for fact in previous:
        if fact not in current:
            key = str(fact)
            count = counts.get(key, _DEFINE_FACT_REFS.get(key, 0))
            if count <= 1:
                lost.append(fact)
            counts[key] = max(count - 1, 0)
    return counts, gained, lost

def _count_reflection(counts: dict[str, int]) -> None:
    """Record the reference counts a reflection move left, each preimage enlisted."""
    for key, count in counts.items():
        _put(_DEFINE_FACT_REFS, key, count or None, f"reflection count of {key}")

def _sync_definition_facts(
    space: Any, previous: tuple[Expression, ...], current: tuple[Expression, ...]
) -> None:
    """Move a definition's reflected facts from ``previous`` to ``current``, all or none.

    One crossing goes per fact the reflection space gains or loses, and when
    a later one fails every earlier one is taken back: each inverse undoes a
    write this move made, so it never touches another owner's copy.
    """
    counts, gained, lost = _reflection_moves(previous, current)
    reflection = _declare_operations_module._REFLECTION_SPACE
    add = partial(space.runtime.must, "metta_py_add(Space, W)", Space=reflection)
    remove = partial(space.runtime.once, "metta_py_remove(Space, W, _)", Space=reflection)
    undo: list[Callable[[], Any]] = []
    try:
        for fact in gained:
            add(W=fact.to_wire())
            undo.append(partial(remove, W=fact.to_wire()))
        for fact in lost:
            remove(W=fact.to_wire())
            undo.append(partial(add, W=fact.to_wire()))
    except BaseException as error:
        _unwind(undo, error)
        raise
    _count_reflection(counts)

def _definition_declarations(
    fn: types.FunctionType, name: str, params: list[str]
) -> tuple[Expression, ...]:
    """The (: ...) declarations one clause's annotations and overloads state."""
    annotated = _declare_operations_module.resolved_annotations(fn)
    overloads = _typing.get_overloads(fn)
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
    return tuple(_declare_operations_module._type_declarations(
        name,
        list(_inspect.signature(fn).parameters.values()),
        None,
        [len(params)],
        fn,
        include_annotation_claims=False,
    ))

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
        known=partial(_space_functions._callable_here, space),
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


def _defined_twin(value: object) -> Callable[..., Any] | None:
    """Resolve a captured definition through its owned Python family."""
    return value.py if isinstance(value, _declare_define_module.Defined) else None


def _publish_define(space: Any, fn: types.FunctionType, name: str, compiled: Any) -> Any:
    """Publish a compiled clause together with any class declarations it uses.

    The space decides what the definition still holds (_standing): a clause
    is a duplicate only while its equations are stored, and the equation
    writes are the difference between what was recorded and is still held
    and what the definition needs now, kubectl apply's three-way reading of
    last-applied, live and desired state [source 2026-09-29T17:39:13+10:00:
    https://kubernetes.io/docs/tasks/manage-kubernetes-objects/declarative-config/#how-apply-calculates-differences-and-merges-changes],
    so a re-define restores what a removal took and clears its debris, and
    its declarations and doc come back the same way. Every engine write, the
    reflection rows, declarations, equations and doc, rides one transaction
    (metta_py_publish_definition/2), so a failure part way leaves the space as
    it was; the twin publishes before it, since the doc reads the family it
    joins, and is taken back when the writes fail. The records change only
    once the writes stand, and never inside ``with m.speculative():``, whose
    snapshot discards the writes; the twin is built in a namespace of its own
    there, so ``.py`` still runs.
    """
    from metta._declare.classes import (  # noqa: PLC0415 -- class declarations share this installer
        owner_of,
    )

    # Every write of a define rides one engine transaction, which the adds a
    # batch holds back cannot join, so a define inside its own space's batch is
    # refused as remove and declare are.
    _spaces_scope_module._refuse_in_batch(space.name, "define")
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
    # Clause stacking is per (space, name), process-wide: equations live in
    # the space, not in whichever MeTTa instance happened to add them. What
    # stacks on is what the space still holds of the recorded clauses.
    key = (space.name, name)
    definition = _DEFINITIONS.get(key, _UNRECORDED)
    declarations = _definition_declarations(fn, name, params)
    standing = _standing(space, definition, () if definition is _UNRECORDED else declarations)
    earlier = list(standing.live)
    _validate_clause_order(space, name, patterns, len(params), earlier)
    _validate_override_declaration(space, fn, name, earlier)
    # The materializer below turns overlapping heads into one ordered case
    # equation. Keeping the authored bodies raw here lets replacement rebuild
    # the whole connected component without accumulating old guards.
    bodies = compiled.equation_bodies
    head = Expression([Symbol(name), *(patterns.get(p, Variable(binding_name(p))) for p in params)])
    equations = tuple(Expression([Symbol("="), head, body]) for body in bodies)
    # Idempotence compares the main equation and all helper equations with
    # auxiliary names canonicalized. A loop-body-only or lifted-body-only
    # change must replace the old clause and its old helpers.
    canonical = _declare_define_module.canonical_aux_set((*equations, *compiled.aux), name)
    duplicate, replaced = _locate_clause(
        earlier, patterns, len(params), canonical, name
    )
    if replaced is not None and earlier[replaced]["owner"] != fn.__name__:
        _refuse_collision(name, earlier[replaced]["owner"])
    stands = not speculative_enabled()
    namespace = _DEFINE_TWINS.get(space.name) or TwinNamespace(_defined_twin)
    home = namespace if stands else TwinNamespace(_defined_twin)
    dispatcher = home.dispatcher(fn, name, [clause["twin"] for clause in earlier])
    twin, bindings = namespace.prepare(fn, dispatcher, patterns)
    clause_twin = select_clause_twin(name, twin, compiled.hazards, patterns, params)
    clause_twin.__doc__ = compiled.facts.doc
    prospective = earlier.copy()
    if duplicate:
        # A re-run cell or module reload must not duplicate answers.
        if replaced is None:
            msg = "a duplicate clause has no replacement index"
            raise RuntimeError(msg)
        prospective[replaced] = earlier[replaced] | {"facts": compiled.facts, "twin": clause_twin}
    else:
        record = _clause_record(fn, patterns, equations, compiled, clause_twin)
        if replaced is None:
            prospective.append(record)
        else:
            prospective[replaced] = record
    prospective = _materialize_clause_equations(name, prospective)
    removed, added = _alpha_multiset_delta(standing.held, _physical_atoms(prospective))
    # What this name has ALREADY declared here, so a second clause adds the
    # arrow its own signature states rather than being suppressed whole, and
    # a clause repeating a signature adds nothing twice; asked of the space,
    # so a declaration a removal took is published again.
    declare = [declaration for declaration in declarations if declaration not in standing.declared]
    facts = _definition_facts(space, name, prospective) if stands else definition.reflected
    counts, gained, lost = _reflection_moves(definition.reflected, facts)
    # The twin publishes first because the doc atom reads the family it joins,
    # and it is the only thing a failed write has to take back: every engine
    # write rides one transaction, so a failure part way leaves the space as it
    # was with no inverse of its own, where removing an added batch by value
    # after a failed add took a user's equal equation with it
    # [tested 2026-09-30T08:34:03+10:00: test_a_define_failing_part_way_leaves_an_equal_equation_standing].
    publication = home.publish(
        fn, name, dispatcher, clause_twin, bindings=bindings, replaced=replaced,
    )
    try:
        documentation = documentation_atom(name, dispatcher, kind="function")
        # The recorded doc atom the space still holds, if it holds it.
        held_doc = definition.documented if standing.documented else None
        reflection = _declare_operations_module._REFLECTION_SPACE
        writes: list[list[Any]] = [["add", reflection, [fact.to_wire()]] for fact in gained]
        writes += [["remove", reflection, [fact.to_wire()]] for fact in lost]
        writes += [["add", space.name, [declaration.to_wire()]] for declaration in declare]
        if removed:
            writes.append(["remove", space.name, [atom.to_wire() for atom in removed]])
        if added:
            writes.append(["add", space.name, [atom.to_wire() for atom in added]])
        if documentation is not None and documentation != held_doc:
            writes.append(["add", space.name, [documentation.to_wire()]])
        if held_doc is not None and documentation != held_doc:
            writes.append(["remove", space.name, [held_doc.to_wire()]])
        # The watch lapses while the writes run and returns with them, so the
        # definition never hears its own writes, whichever transaction they
        # commit in (_binding/store.pl, metta_py_publish_definition/2).
        watches = _watches(space, [(name, _watched_heads(prospective))]) if stands else []
        applied = _publish(space, writes, watches)
    except BaseException:
        publication()
        raise
    if stands:
        _count_reflection(counts)
        _declare_operations_module._record_registry_undo(
            publication, description=f"twin family of {name!r} in {space.name}"
        )
        if space.name not in _DEFINE_TWINS:
            _put(_DEFINE_TWINS, space.name, namespace, f"twin namespace of {space.name}")
        held = tuple(declaration for declaration in definition.declared if declaration in standing.declared)
        recorded = _Definition(tuple(prospective), (*held, *declare), documentation, facts)
        _put(_DEFINITIONS, key, recorded, f"definition {name!r} in {space.name}")
        _remember_defined_callable(space, fn, name)
        crossings = _importlib.import_module('metta._spaces.intents').register_definition_crossings(
            space, fn, equations[0], name
        )
        position = len(prospective) - 1 if replaced is None else replaced
        if crossings is not None and prospective[position]["crossings"] != crossings:
            prospective[position] = prospective[position] | {"crossings": crossings}
            _put(_DEFINITIONS, key, _replace(recorded, clauses=tuple(prospective)),
                 f"definition {name!r} in {space.name}")
    if applied is not None:
        raise applied
    return _defined_result(space, name, compiled, bodies, dispatcher)

def _refuse_collision(name: str, owner: str) -> _typing.NoReturn:
    """Refuse a clause whose head another Python function's definition holds."""
    msg = (
        f"{name!r} is already defined here by a different Python function, "
        f"{owner}; re-run {owner} to change the definition, remove the "
        f"definition first with m.remove({owner}), the Defined @m.define "
        f"bound to that name, or put the extra clauses under the one "
        f"function, where pattern= clauses and generator bodies store one "
        f"equation each"
    )
    raise CompileError(
        msg,
        construct="name collision",
        remedy=Remedy(
            "remove the other function's definition first",
            "quickfix",
            "prose",
            python=f"m.remove({owner})",
        ),
    )

def _unwind(undo: list[Callable[[], Any]], error: BaseException) -> None:
    """Undo a failed publication's engine writes newest first, every one.

    The failure stays the exception; an inverse that fails too is a note on
    it and never stops the rest.
    """
    for inverse in reversed(undo):
        try:
            inverse()
        except BaseException as undo_error:  # noqa: BLE001  -- every remaining inverse must run even when one cleanup fails
            BaseException.add_note(
                error, f"undoing a failed definition write failed: {undo_error!r}"
            )

def remove_definition(space: Any, defined: Any) -> bool:
    """Take one definition back out of the space.

    The body of ``m.remove(<Defined>)`` and ``m -= <Defined>``.

    A Defined names its whole definition: every stacked clause of that name
    in its space. Every atom it published that the space still holds, its
    equations, helper equations, declarations and doc, leaves through the
    ordinary removal door, which reaches subtract-atom and with it the
    engine's one equation funnel, remove_equation/6, all inside the one
    transaction define publishes through (metta_py_publish_definition/2);
    its record, reflection rows, twin family and lint evidence retire with
    them, so a later define of the name starts fresh. Answers whether the
    space held anything of it. A Defined of another space names nothing
    here, and a Prolog-backed one publishes no equations to remove.
    """
    if isinstance(defined, _declare_define_module.PrologBacked):
        msg = (
            f"{defined.name} is registered from {defined.origin}, not published "
            f"as equations, so there is no definition to remove; "
            f"m.unregister_prolog(<extension>) releases the extension that "
            f"file declares, every name it registered with it"
        )
        raise TypeError(msg)
    if defined.space.name != space.name:
        return False
    return _withdraw_definition(space, defined.name)

def _withdraw_definition(space: Any, name: str) -> bool:
    with _DEFINE_LOCK:
        key = (space.name, name)
        definition = _DEFINITIONS.get(key)
        if definition is None:
            return False
        standing = _standing(space, definition)
        held_doc = definition.documented if standing.documented else None
        atoms = [
            *standing.held,
            *standing.declared,
            *((held_doc,) if held_doc is not None else ()),
        ]
        stands = not speculative_enabled()
        counts, _, lost = _reflection_moves(definition.reflected if stands else (), ())
        reflection = _declare_operations_module._REFLECTION_SPACE
        writes: list[list[Any]] = [["remove", reflection, [fact.to_wire()]] for fact in lost]
        if atoms:
            writes.append(["remove", space.name, [atom.to_wire() for atom in atoms]])
        # This door retires the definition itself, so its watch ends with the
        # removals, which raise no notice of their own; inside speculative()
        # the snapshot discards the removals and nothing else moves.
        watches = _watches(space, [(name, ())]) if stands else []
        applied = _publish(space, writes, watches)
        if stands:
            _count_reflection(counts)
            _retire(space, key, definition.clauses)
            _put(_DEFINITIONS, key, None, f"definition {name!r} in {space.name}")
            for defined_key in [k for k in _DEFINED_FUNCTION_NAMES if k[0] == space.name]:
                names = _DEFINED_FUNCTION_NAMES[defined_key]
                if name in names:
                    _put(_DEFINED_FUNCTION_NAMES, defined_key, (names - {name}) or None,
                         f"installed names of {defined_key[1].__name__}")
        if applied is not None:
            raise applied
        return bool(atoms)

def _publish(space: Any, writes: list[list[Any]], watches: list[list[Any]]) -> BaseException | None:
    """Publish a definition's writes and watch in one transaction.

    The transaction is metta_py_publish_definition/2's. Answers the error a
    watcher raised once they committed, which the caller raises after its
    records follow what stands: a SubscriberError, alone or grouped, says its
    write is applied, and a definition that dropped its record then would
    leave the space answering a head no record describes, which a later
    define of the name refuses [tested 2026-09-30T08:34:03+10:00:
    test_a_watcher_failing_after_a_definition_commits_leaves_it_recorded].
    Any other error propagates with the writes rolled back.
    """
    try:
        run_void_write(space.runtime, "metta_py_publish_definition", writes, watches)
    except BaseException as error:
        if not _applied(error):
            _raise_what_providers_kept(space, error)
            raise
        applied: BaseException | None = error
    else:
        applied = None
    _space_functions._invalidate_builtins_cache(space.runtime)
    return applied

def _raise_what_providers_kept(space: Any, error: BaseException) -> None:
    """Raise PartialWriteError when a provider outside the engine kept or lost part of a write.

    The part is what metta_py_publication_residue/1 counted of the failed
    publication, and the error is raised from ``error``; nothing is raised
    when every space the publication wrote rolled back with it. A residue
    that cannot be read leaves a note on ``error`` rather than hiding it.
    """
    try:
        row = space.runtime.once("metta_py_publication_residue(Residue)")
    except Exception as unread:  # noqa: BLE001  -- the failure being raised outranks the residue; the note keeps both
        error.add_note(f"what a provider kept of this write could not be read: {unread}")
        return
    for home_wire, kept_wires, lost_wires in (row or {}).get("Residue") or ():
        name = str(_atom_from_wire(home_wire))
        kept = tuple(_atom_from_wire(wire) for wire in kept_wires)
        lost = tuple(_atom_from_wire(wire) for wire in lost_wires)
        held = []
        if kept:
            held.append(f"still holds the {len(kept)} it received: {', '.join(map(str, kept))}")
        if lost:
            held.append(f"no longer holds the {len(lost)} it gave up: {', '.join(map(str, lost))}")
        repair = "remove what it kept" + (" and add back what it lost" if lost else "")
        msg = (
            f"the write failed after {name}'s provider took part of it, and {name} "
            f"is not transactional: the engine's own state rolled back and the "
            f"provider's did not, so it {' and '.join(held)}. To leave {name} as "
            f"it was, {repair}, which this error's kept and lost carry as atoms; "
            f"the failure is its cause: {error}"
        )
        raise PartialWriteError(msg, space=name, kept=kept, lost=lost) from error

def _applied(error: BaseException) -> bool:
    """Whether an error is a watcher's, raised on a write that committed."""
    if isinstance(error, BaseExceptionGroup):
        return all(_applied(inner) for inner in error.exceptions)
    return isinstance(error, SubscriberError)

def _retire(
    space: Any,
    key: tuple[str, str],
    lost: Sequence[dict[str, Any]],
    *,
    live: Sequence[dict[str, Any]] = (),
) -> None:
    """Retire on the Python side what the space no longer holds of a definition.

    Its reflection rows have moved already, so this hands its twin family to
    the ``live`` clauses and files the lint evidence of the live ones,
    withdrawing the ``lost`` ones'. Every change enlists its Python preimage
    in the caller's transaction frame.
    """
    namespace = _DEFINE_TWINS.get(space.name)
    if namespace is not None:
        _declare_operations_module._record_registry_undo(
            namespace.succeed(key[1], [clause["twin"] for clause in live]),
            description=f"twin family of {key[1]!r} in {space.name}",
        )
    gone = [clause["crossings"] for clause in lost if clause["crossings"] is not None]
    kept = [clause["crossings"] for clause in live if clause["crossings"] is not None]
    _importlib.import_module('metta._spaces.intents').file_definition_crossings(
        space, [*((owner, frozenset()) for owner, _events in gone), *kept]
    )

def equation_changed(space: list[Any], name: str) -> bool:
    """Record the engine's notice that an equation a definition publishes moved.

    The notice says an equation of a head the definition ``name``
    publishes entered or left ``space`` in a committed write, through any door,
    a program's ``remove-atom`` or ``add-atom`` as much as a Python removal
    (engine/ext_points.pl, seam:equation_changed/2, delivered by
    _binding/subscriptions.pl): the definition's reflection rows, twin family
    and lint evidence move to the clauses the space still answers through,
    which brings them back with an equation that returns. ``space`` is the
    space's wire, the name of an atom space or the expression of a parametric
    one. A definition's own writes raise no notice, since define and the
    door that removes a Defined end its watch while they write and record the
    definition themselves, and a rolled-back or speculative write is never
    heard. The notice is only recorded here and reconciled at the next
    crossing made with no engine callback open (_settle_noticed), since it can
    arrive while its writer holds an engine lock a define waits for while it
    holds _DEFINE_LOCK [tested 2026-09-30T08:34:03+10:00:
    test_an_unwatched_equation_write_crosses_to_no_python].
    """
    _NOTICED.append((space, name))
    at_safe_point(_settle_noticed)
    return True

def _settle_noticed() -> bool:
    """Reconcile every definition the recorded notices name, in order.

    Each reconciliation reads the space again, so a name noticed twice
    settles once to what the space holds. Answers False, to run again at a
    later safe point, on a thread inside a definitions critical section.
    """
    if _DEFINE_LOCK.held():
        return False
    with _DEFINE_LOCK:
        while True:
            try:
                space, name = _NOTICED.popleft()
            except IndexError:
                return True
            home = _noticed_space(space)
            if home is not None:
                _reconcile(home, (home.name, name))

@dataclass(frozen=True, slots=True)
class _NoticedSpace:
    """A definition's space as an engine notice names it.

    It holds what _reconcile reads of a handle: the registry's key for it,
    the runtime and its wire. A handle is not made, since inside an engine
    callback each read of a handle's name asks the engine for its scope
    (metta._spaces.lifetime.current).
    """

    name: Any
    runtime: Any

    def to_wire(self) -> list[Any]:
        """The wire the space's handle gives."""
        return space_wire(self.name)

def _noticed_space(wire: list[Any]) -> _NoticedSpace | None:
    """The registry's key for the space a notice's wire names.

    An atom space's key is its name; a parametric space's is the exact
    carrier its handle made, found by its expression, which keeps every
    native field kind apart where a plain list would merge them
    [source 2026-09-30T02:38:50+10:00:
    docs/journal/2026-09-14-parametric-space-transport.md]. None when no
    recorded definition lives there any more.
    """
    engine = runtime()
    if wire[0] in ("p", "s"):
        return _NoticedSpace(wire[1], engine)
    expression = _atom_from_wire(wire)
    for recorded, _name in _DEFINITIONS:
        image = getattr(recorded, "__metta__", None)
        if image is not None and image() == expression:
            return _NoticedSpace(recorded, engine)
    return None

def _watched_heads(clauses: Sequence[dict[str, Any]]) -> tuple[str, ...]:
    """Every head a definition's clauses define, which is what it hears.

    They are the heads of the clauses' physical equations, the definition's
    own name and each helper's, sorted and distinct. A local type alias
    publishes a scalar equation, (= Items (List Number)), whose head is the
    symbol itself.
    """
    names: set[str] = set()
    for atom in _physical_atoms(clauses):
        head = atom.children[1]
        functor = head.children[0] if isinstance(head, Expression) else head
        if not isinstance(functor, Symbol):
            msg = f"a published equation's head names no function: {atom}"
            raise TypeError(msg)
        names.add(functor.name)
    return tuple(sorted(names))

def _watches(space: Any, heads: Sequence[tuple[str, Sequence[str]]]) -> list[list[Any]]:
    """The argument of metta_py_watch/1 for the named definitions.

    Each named definition hears exactly these heads in the space, and no
    heads ends its watch.
    """
    return [[space.name, name, list(watched)] for name, watched in heads]

def _watch(space: Any, heads: Sequence[tuple[str, Sequence[str]]]) -> None:
    """Set which heads the named definitions hear (_binding/subscriptions.pl)."""
    space.runtime.must("metta_py_watch(W)", W=_watches(space, heads))

def _reconcile(space: Any, key: tuple[str, str]) -> None:
    """Move a definition's Python-side state to the clauses the space answers through.

    That state is its reflection rows, twin family and lint evidence. The
    clause records stay as published: what a partial removal left behind is
    still theirs to take.
    """
    definition = _DEFINITIONS.get(key)
    if definition is None:
        return
    standing = _standing(space, definition)
    facts = _definition_facts(space, key[1], list(standing.live))
    if len(standing.live) == len(definition.clauses) and facts == definition.reflected:
        return
    lost = [clause for clause in definition.clauses if not any(clause is kept for kept in standing.live)]
    _sync_definition_facts(space, definition.reflected, facts)
    _retire(space, key, lost, live=standing.live)
    if facts != definition.reflected:
        _put(
            _DEFINITIONS, key, _replace(definition, reflected=facts),
            f"definition {key[1]!r} in {space.name}",
        )

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

    A define is all or nothing wherever a transaction reaches the space's
    storage, a native space's and that of a provider declaring
    transactional writes, which rolls back with it. A provider whose
    storage no transaction reaches keeps what a failed define wrote to it,
    so that failure is raised as metta._errors.errors.PartialWriteError,
    whose kept and lost are the atoms to remove and add back, with the
    failure itself as its cause.
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
