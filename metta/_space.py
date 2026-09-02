"""Purpose: provide the narrow MeTTa context and context-relative Space handles.

Assumes:
  - the six extracted ``_space_*`` modules own query, definition, execution,
    persistence, eager decoding, and diagnostic implementation [source:
    extensions/python/metta/_space_query.py, _space_definitions.py,
    _space_execution.py, _space_persistence.py, _space_objects.py, and
    _space_diagnostics.py; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Guarantees:
  - solve, Linda verbs, class define, get-type, bang resolution, and both
    transaction laws are observable through one Space handle [tested:
    test_solve_retires_the_five_relational_let_workarounds,
    test_solve_refuses_an_anonymous_only_subject,
    test_take_peek_and_watch_retire_the_thread_linda_fn_strings,
    test_watch_close_before_first_event_cancels_its_eager_subscription,
    test_define_absorbs_class_declaration_and_frees_space_type,
    test_fn_strips_one_bang_only_when_the_exact_name_is_absent, and
    test_transaction_term_uses_empty_answer_rollback_law; commit=c34c9bf3e55a8425d3f251c3ad06c33bc9755a22]
  - relational solve exposes variables from its pattern before variables from
    its subject [tested: test_solve_projects_variables_from_the_winning_pattern;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - ``MeTTa`` carries only context primitives while ``Space`` owns storage,
    query, declaration, and lifecycle verbs [tested:
    test_m7_narrow_core_surface; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``MeTTa.space()`` creates named or anonymous handles through one door
    [tested: test_module_tier_is_sugar_over_one_default_engine;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``Space.reify`` returns an immutable branch value and ``Space.commit``
    applies its base-relative diff through ordinary transaction and event
    doors [tested: test_world_eval_branches_without_touching_parent,
    test_commit_applies_the_world_diff_as_post_commit_events; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - ``Space.covers`` and ``Space.compensates`` publish the two effect-safety
    declarations, while ``Space.saga`` builds recovery on the existing
    transaction and post-commit event doors [tested:
    test_world_coverage_admits_the_joined_plan,
    test_committed_effects_leave_queryable_receipts_and_failed_steps_leave_none;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
  - named space construction accepts a space-name Symbol as well as its text
    spelling [tested: test_space_factory_accepts_a_name_symbol; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - a Symbol or ground Expression names a source-visible atomic or parametric
    space, while a free variable refuses before engine state changes [tested:
    test_python_space_factory_accepts_atom_valued_names; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - a tuple headed by an atom is one subscript pattern, a tuple of complete
    patterns is a join, list writes stream their atoms, and del drains every
    match or raises KeyError [tested:
    test_subscript_one_pattern_and_bulk_delete_laws; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - the ``+=`` write door classifies atoms and scalar conversion kinds before
    iteration, reads dataframe row protocols before generic iteration, and
    sends each fact-stream item through the engine write spine [tested:
    test_adding_an_iterable_of_atoms_writes_one_atom_each,
    test_write_door_scalar_kinds_are_never_mistaken_for_fact_streams,
    test_write_door_uses_the_iteration_protocol_not_only_the_iterable_abc,
    test_the_write_doors_accept_the_same_atoms,
    test_the_write_door_reads_each_dataframe_row_as_one_atom; commit=012413efb73b4dd27c71354c7f654862f349c03f]
  - relative ``(admits Type)`` and ``(capacity n)`` values written through
    ``+=`` invoke the receiver installers, and refuse to overtake a live batch
    [tested: test_relative_capacity_declaration_installs_the_receiver_contract,
    test_relative_admits_declaration_installs_the_receiver_contract,
    test_two_declared_admission_checks_interact_over_one_store,
    test_relative_declarations_refuse_inside_an_active_batch; commit=012413efb73b4dd27c71354c7f654862f349c03f]
  - ``Space.match`` returns a lazy Answers view; truth and single unpack pull
    only their demanded prefix, while len counts inside the engine [tested:
    test_query_answers_complete_the_lazy_projection_protocol,
    test_query_single_unpack_pulls_at_most_two_answers; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - match and call answers accept explicit or scoped algebra carriers;
    counting uses engine aggregates and ordered carriers sort before slicing
    [tested:
    test_counting_counts_match_bag_duplicates_without_opening_a_row_cursor,
    test_counting_counts_duplicate_call_answers_inside_the_engine,
    test_ranked_and_tropical_slices_are_stable_best_prefixes;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - ``Space.pre_add`` declares one compiled unary judge through the engine's
    existing pre-add hook [tested: test_pre_add_compiles_the_four_verdict_judge;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - handle-level Linda waits load their support into the default caller space,
    never into a distinct waited-on space [tested:
    test_peek_does_not_import_linda_into_the_waited_space; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - ``Space.match``, every head-named declaration verb, and the write door
    retain their established semantics after moving off ``MeTTa`` [tested:
    test_query_surfaces_share_column_order,
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms,
    test_the_python_remove_door_subtracts_one_copy; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - all fifteen declaration heads use their settled receiver spellings,
    including ``reacts`` for ``(on ...)``; the former ``reaction`` spelling
    remains as a compatibility alias and no ``declare_*`` alias returns
    [tested: test_declarations_use_their_atom_heads_on_the_receiver and
    test_m7_narrow_core_surface; commit=0cfc68a483d8d64fb499e53bbe9a3cc63f68990f]
  - Expression recognizes Space as the one iterable Handle whose listing is
    collected as an assembly-order snapshot [tested:
    test_expression_of_a_space_is_an_assembly_order_snapshot; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - native iteration snapshots assembly order at iterator creation, handles
    stay truthy independently of contents, and provider length requires its
    Sized declaration [tested:
    test_native_iteration_snapshots_before_mutation,
    test_space_truth_does_not_ask_for_emptiness,
    test_provider_length_requires_and_uses_sized; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - ``Space.limits(stack=bytes)`` scopes a positive stack byte count beside
    time and inference bounds [tested:
    test_stack_limit_is_carried_to_the_limited_six_seam; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - synchronous run, match, eval, and answers calls made directly in an async
    body remain legal and record an AsyncMeTTa lint [tested:
    test_a_sync_engine_call_inside_async_def_is_linted_not_refused;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - ``Space.op`` and ``Space.unregister_op`` are the sole public operation
    lifecycle pair [tested: test_operation_registration_names_are_symmetric;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - encoded generator tuple and sparse-dict yields are relational candidate
    bindings in every call direction [tested:
    test_relational_tuple_candidates_unify_in_all_directions_without_changing_multiplicity,
    test_sparse_relational_dict_candidates_bind_parameter_names;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - ``Space.answers`` and bound ``Space.fn`` expose lazy, replayable
    evaluation, with unknown function attributes rejected at access [tested:
    test_bound_function_namespace_validates_at_access,
    test_function_calls_pull_engine_answers_only_as_demanded;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
  - ``Space.answers`` can evaluate one ask against a theory value or through
    an explicit full-interpreter head without mutating the receiver [tested:
    test_answers_selects_a_theory_or_interpreter_per_ask;
    commit=7c4ddf46d4e23de8390a9f2baddbf96f7575da46]
  - a theory replaces only the receiver's own program for one ask; shared
    session definitions remain visible and are lexically shadowed by theory
    definitions [tested:
    test_an_inherited_arrow_does_not_veto_a_local_definition;
    commit=7b238053d2907cd514e3fd9a29927d43a53c5a3c]
  - ``Space.cast`` preserves the inherited one-argument atom cast while its
    two-argument form keeps explicit context-relative casting [tested:
    test_atom_cast_delegates_to_the_ambient_space;
    commit=162214d7a703e9108dd2422f4f18f3b9c007d367]
  - callable doors cache live deprecation declarations until the next write
    and issue the catalog's since/remedy warning [tested:
    test_deprecation_catalog_rows_drive_warnings_and_explanations;
    commit=d74e2e828cd9272882dcf907cfaf095d2d147ce0]
  - builtin discovery is cached per logical space, with namespace reads
    comparing the engine's function generation and explicit Python mutation
    doors retaining eager invalidation [tested:
    test_cache_reads_compare_the_function_generation,
    test_builtin_discovery_is_cached,
    test_builtin_cache_invalidates_after_a_miss; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - ``Space`` is a grounded ``Handle`` that crosses as a term operand, and
    ``peek`` and ``take`` expose the engine's event-driven Linda operations
    [tested: test_space_handles_are_term_operands_and_round_trip,
    test_space_handle_peek_and_take_are_linda_verbs; commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - dropping a named space clears that life without returning its public name
    to the anonymous allocation pool [tested:
    test_a_named_space_drop_never_enters_the_anonymous_pool;
    commit=d843bb6d17a525c36afd21cab077d63b34447535]
  - compiled ``re.Pattern`` reader classes preserve supported semantic flags,
    reject untranslatable flags, and unregister through the same normalized
    key [tested: test_compiled_reader_patterns_preserve_flags_and_unregister;
    commit=50d1de4d0ead4a0c3997f9b2ef58631bbafaede3]
  - an anonymous space representation records the external file and line that
    created that life, while named-space representations remain stable
    [tested: test_anonymous_space_repr_carries_its_creation_site;
    commit=50d1de4d0ead4a0c3997f9b2ef58631bbafaede3]
Owns resources:
  - ``Space.save`` owns its sibling temporary file and removes it after every
    failed operation [tested: test_save_failure_preserves_existing_file;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import builtins as _builtins
import contextlib
import functools
import hashlib
import importlib as _importlib
import os
import re as _re
import sys
import threading
import warnings
import weakref
from collections import abc as _abc
from collections.abc import Callable, Iterable, Iterator
from contextvars import ContextVar
from pathlib import Path
from typing import (
    Any,
    Literal,
    NamedTuple,
    ParamSpec,
    Self,
    TypeVar,
    cast,
    overload,
)

from . import ops as _ops_module
from ._api_types import _DEFAULT_SPACE, _SpaceId
from ._engine import Runtime, bridge, runtime, started
from ._library import Library, import_library
from ._lint_events import record_sync_engine_call as _record_sync_engine_call
from ._rules import Rules as _Rules
from ._rules import rules as _collect_rules
from ._space_definitions import (
    clear_definitions,
    install_define,
    install_prolog_define,
    install_type,
    release_definitions,
)
from ._space_execution import (
    CapturedOutput,
    ScopedExecution,
    capture_output,
    evaluate,
    evaluate_answers,
    evaluate_count,
    evaluate_many,
    evaluate_status,
    execution_scope,
    profile_extension,
    profile_source,
    run_source,
    run_status,
    value_one,
)
from ._space_objects import (
    _ACTIVE_BATCHES,
    Cursor,
    EngineProfile,
    FunctionCost,
    Prepared,
    ScopedLimits,
    _Assuming,
    _Batch,
    _column_names,
    _FunctionNamespace,
    _refuse_in_batch,
    _require_vocabulary,
    _StatsBlock,
    guard_atom,
    require_deadline,
)
from ._space_persistence import (
    load_space,
    raise_unsafe_text_atom,
    save_space,
)
from ._space_query import _validate_limit, query_count, solve_rows
from ._under import _UNSET
from ._under import selected as _selected_under
from ._version import __version__
from .atoms import (
    Atom,
    Expression,
    Grounded,
    Handle,
    Symbol,
    Undefined,
    Variable,
    _atom_from_wire,
    _decode,
    _to_atom,
    parse,
    unify,
)
from .define import Defined, PrologBacked
from .errors import EngineError, MettaError, SourceNotFound, Timeout
from .results import (
    Answers,
    Rows,
    _AnswerItem,
    _QueryContext,
    _row_class,
    raise_error_answers,
    rows_into,
)
from .vocabularies import (
    AgendaPolicy,
    AnswerPolicy,
    Atomicity,
    Delivery,
    Determinism,
    EffectClass,
    EventOrder,
    Fidelity,
    ImageMode,
    OnError,
    SaveFormat,
    SemiringOrder,
    SourceKind,
    SpaceCapability,
    World,
)

__all__ = ["Cursor", "EngineProfile", "MeTTa", "Prepared", "Space", "current_space"]

_CastT = TypeVar("_CastT")
_R = TypeVar("_R")
_P = ParamSpec("_P")

_BUILTINS_CACHE_LOCK = threading.RLock()
_BUILTINS_CACHE: weakref.WeakKeyDictionary[
    Runtime, tuple[int, int, dict[str, tuple[str, ...]]]
] = weakref.WeakKeyDictionary()
_DEPRECATION_CACHE: weakref.WeakKeyDictionary[
    Runtime, dict[str, tuple[str, str] | None]
] = weakref.WeakKeyDictionary()
#: Whether the runtime holds ANY deprecation declaration at all. The catalog
#: is almost always empty, and without this flag every distinct name's first
#: live call paid one engine crossing to learn nothing: measured 2026-08-26,
#: +1,288 inferences on the parse twin (391 to 1,679) from d74e2e82's
#: per-name reads alone. One process-wide apply-seam emptiness probe
#: amortises them
#: [tested: test_an_empty_deprecation_catalog_costs_one_cheap_probe].
_DEPRECATION_ANY: weakref.WeakKeyDictionary[Runtime, bool] = (
    weakref.WeakKeyDictionary()
)


def _invalidate_builtins_cache(rt: Runtime) -> None:
    """Advance the Python-door epoch and discard every cached space view."""
    with _BUILTINS_CACHE_LOCK:
        epoch, function_generation, _ = _BUILTINS_CACHE.get(rt, (0, -1, {}))
        _BUILTINS_CACHE[rt] = (epoch + 1, function_generation, {})
        _DEPRECATION_CACHE.pop(rt, None)
        _DEPRECATION_ANY.pop(rt, None)


def _catalog_text(value: Any) -> str:
    """Render a catalog term the way its MeTTa source reads."""
    if isinstance(value, list):
        return f"({' '.join(_catalog_text(child) for child in value)})"
    return str(value)


def _deprecation(rt: Runtime, name: str) -> tuple[str, str] | None:
    """Read one live declaration and cache it until the next explicit write."""
    with _BUILTINS_CACHE_LOCK:
        cache = _DEPRECATION_CACHE.setdefault(rt, {})
        if name in cache:
            return cache[name]
        any_declared = _DEPRECATION_ANY.get(rt)
    if any_declared is None:
        any_declared = bool(int(rt.apply_must("metta_py_deprecation_declared")))
        with _BUILTINS_CACHE_LOCK:
            _DEPRECATION_ANY[rt] = any_declared
    if not any_declared:
        with _BUILTINS_CACHE_LOCK:
            _DEPRECATION_CACHE.setdefault(rt, {})[name] = None
        return None
    row = rt.once("metta_deprecation(Name, Since, Remedy)", Name=name)
    declaration = (
        None
        if not row
        else (_catalog_text(row["Since"]), _catalog_text(row["Remedy"]))
    )
    with _BUILTINS_CACHE_LOCK:
        _DEPRECATION_CACHE.setdefault(rt, {})[name] = declaration
    return declaration


def _function_generation(rt: Runtime) -> int:
    """Read the engine's fun/1 generation through its Janus seam.

    The service is SWI's ``last_modified_generation`` for exactly the dynamic
    ``fun/1`` set read by ``metta_py_builtins/1``; translator rules are static
    catalogue-neutral metadata [source:
    engine/metta.pl:metta_host_function_generation/1;
    commit=4c9a794750103e0a3a2e9d883adde337ffb501f0].
    """
    return int(rt.apply_must("metta_py_function_generation"))


def _space_builtins(rt: Runtime, space_name: str) -> list[str]:
    """Read one engine-generation-stamped per-space builtin catalogue."""
    while True:
        observed_generation = _function_generation(rt)
        with _BUILTINS_CACHE_LOCK:
            epoch, cached_generation, catalogues = _BUILTINS_CACHE.setdefault(
                rt, (0, observed_generation, {})
            )
            if cached_generation != observed_generation:
                catalogues = {}
                _BUILTINS_CACHE[rt] = (epoch, observed_generation, catalogues)
            cached = catalogues.get(space_name)
            if cached is not None:
                return list(cached)
        discovered = tuple(rt.builtins())
        confirmed_generation = _function_generation(rt)
        if confirmed_generation != observed_generation:
            continue
        with _BUILTINS_CACHE_LOCK:
            current_epoch, current_generation, current = _BUILTINS_CACHE.get(
                rt, (0, -1, {})
            )
            if current_epoch != epoch or current_generation != confirmed_generation:
                continue
            current[space_name] = discovered
            return list(discovered)

_ACTIVE_SPACE: ContextVar[_SpaceId | None] = ContextVar(
    "metta_active_space", default=None
)
_RUN_BINDINGS: ContextVar[dict[str, Any] | None] = ContextVar(
    "metta_run_bindings", default=None
)


def _satellite(name: str) -> Any:
    """Import one optional surface only when its handle verb is called."""
    return _importlib.import_module(f"{__package__}.{name}")


def _creation_site() -> tuple[str, int]:
    """Return the first caller frame outside the metta package."""
    import inspect  # noqa: PLC0415  -- anonymous construction alone pays

    frame = inspect.currentframe()
    try:
        frame = None if frame is None else frame.f_back
        package_prefix = f"{__package__}."
        while frame is not None:
            module = str(frame.f_globals.get("__name__", ""))
            if module != __package__ and not module.startswith(package_prefix):
                filename = frame.f_code.co_filename
                if not filename.startswith("<"):
                    filename = str(Path(filename).resolve())
                return filename, frame.f_lineno
            frame = frame.f_back
    finally:
        del frame
    return "<unknown>", 0


_READER_PATTERN_FLAGS = (
    (_re.IGNORECASE, "i"),
    (_re.MULTILINE, "m"),
    (_re.DOTALL, "s"),
    (_re.VERBOSE, "x"),
)
_READER_PATTERN_SUPPORTED = _re.NOFLAG
for _reader_flag, _reader_letter in _READER_PATTERN_FLAGS:
    _READER_PATTERN_SUPPORTED |= _reader_flag


def _reader_pattern(pattern: str | _re.Pattern[str]) -> str:
    """Normalize Python's compiled regex contract to the engine's PCRE text."""
    if isinstance(pattern, str):
        return pattern
    if not isinstance(pattern, _re.Pattern):
        msg = f"a reader-token pattern is str or re.Pattern, not {type(pattern).__name__}"
        raise TypeError(msg)
    if not isinstance(pattern.pattern, str):
        msg = "a reader-token re.Pattern must compile text, not bytes"
        raise TypeError(msg)
    flags = _re.RegexFlag(pattern.flags) & ~_re.UNICODE
    unsupported = flags & ~_READER_PATTERN_SUPPORTED
    if unsupported:
        msg = (
            f"reader-token re.Pattern flags {unsupported!s} have no exact PCRE "
            "translation; use IGNORECASE, MULTILINE, DOTALL, VERBOSE, or "
            "write an inline PCRE pattern"
        )
        raise ValueError(msg)
    letters = "".join(
        letter for flag, letter in _READER_PATTERN_FLAGS if flags & flag
    )
    return f"(?{letters}){pattern.pattern}" if letters else pattern.pattern


def current_space(default: str = _DEFAULT_SPACE) -> _SpaceId:
    """The space whose module the ENGINE is evaluating in right now.

    Callable from inside a registered operation, where it answers the space
    of the program that called it: janus re-enters the engine cleanly, so
    an operation can behave per-space without the space being an argument.
    Outside any evaluation it answers the default.
    """
    selected = _ACTIVE_SPACE.get()
    if selected is not None:
        return selected
    if not started():
        return _SpaceId(default)
    row = bridge().query_once("current_metta_space(S)")
    return _SpaceId(str(row["S"])) if row else _SpaceId(default)


class _BoundValues:
    """Named host values visible to source execution inside one block."""

    def __init__(self, values: dict[str, Any]) -> None:
        self._values = values
        self._token: Any = None

    def __enter__(self) -> Self:
        inherited = _RUN_BINDINGS.get() or {}
        self._token = _RUN_BINDINGS.set({**inherited, **self._values})
        return self

    def __exit__(self, *_exception: object) -> None:
        _RUN_BINDINGS.reset(self._token)


def _cancel_abandoned_subscription(subscription: Any) -> None:
    """The finalize backstop: best-effort, late-shutdown-safe."""
    with contextlib.suppress(Exception):
        subscription.cancel()


class _WatchIterator:
    """Own one eager subscription and cancel it whenever the iterator closes.

    close() is the contract; the weakref.finalize backstop only covers an
    ABANDONED iterator, so a dropped handle cannot keep a live subscription
    delivering into nothing [tested: test_an_abandoned_watch_cancels_itself].
    """

    __slots__ = ("__weakref__", "_deadline", "_events", "_finalizer", "_subscription")

    def __init__(self, subscription: Any, deadline: float | None = None) -> None:
        self._subscription = subscription
        self._deadline = deadline
        self._events: Iterator[Any] = subscription.events(deadline)
        self._finalizer = weakref.finalize(
            self, _cancel_abandoned_subscription, subscription
        )

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Any:
        try:
            return next(self._events)
        except StopIteration:
            self.close()
            if self._deadline is not None:
                msg = f"no matching change arrived within {self._deadline} seconds"
                raise Timeout(msg) from None
            raise

    def close(self) -> None:
        """Close the event generator and cancel the eager subscription once."""
        self._finalizer.detach()
        subscription = self._subscription
        if subscription is None:
            return
        self._subscription = None
        close = getattr(self._events, "close", None)
        try:
            if close is not None:
                close()
        finally:
            subscription.cancel()

def _require_source(source: Any, called: str) -> None:
    """Refuse non-text source here rather than at the engine's reader."""
    if not isinstance(source, str):
        msg = f"{called} takes MeTTa source as a string, got {source!r}"
        raise TypeError(msg)


def _require_name(name: Any, called: str) -> None:
    """Refuse a non-string name here, where the caller can still be named.

    The engine reports one as `atom_string/2: Type error`, which names a
    Prolog builtin and the tagged null `@none` instead of the argument.
    """
    if not isinstance(name, str):
        msg = f"{called} takes a name as a string, got {name!r}"
        raise TypeError(msg)


def _substituted(target: Any, using: dict[str, Any]) -> Atom:
    """Apply a bindings mapping to a target in the host, as the engine does.

    ``metta_host_substitute/3`` replaces an ATOM whose name is a binding key,
    recursively [source: engine/filereader.pl:579-584]. Any door that has to
    hold the substituted term rather than hand the pairs to the engine needs
    exactly that, so it is written once.
    """
    atom = _to_atom(target)
    return atom.map(
        lambda item: (
            _to_atom(using[item.name])
            if isinstance(item, Symbol) and item.name in using
            else item
        )
    )


class _SpaceModel(NamedTuple):
    """Which engine declaration a space request needs, and its one argument.

    The mint and the declaration used to be one predicate per model, which is
    why a NAME and a model were exclusive: there was nowhere to put the name.
    Splitting them leaves exactly this to decide, once, for both doors --
    anonymous space() mints a name and declares, named space() declares on the
    name it was given -- and the model crosses as the atom the engine door
    already dispatches on rather than as part of a predicate name.
    """

    model: str
    argument: Any


def _space_model(
    inherits: Space | None,
    *,
    restricted: bool,
    grants: tuple[str, ...],
    equation_home: Space | None,
) -> _SpaceModel | None:
    """The declaration a request needs, or None for a plain space."""
    if restricted:
        return _SpaceModel("restricted", list(grants))
    if equation_home is not None:
        return _SpaceModel("scoped", equation_home._space)
    if inherits is not None:
        return _SpaceModel("inherits", inherits._space)
    return None


def _checked_new_space_request(
    inherits: Space | None,
    *,
    restricted: bool,
    grants: _abc.Iterable[str],
) -> tuple[str, ...]:
    """Refuse a malformed anonymous ``space()`` request at one boundary.

    Validation lives at this public boundary so the engine-side declaration
    transaction only ever sees a live parent, a boolean restriction, and
    known string capability grants.
    """
    if inherits is not None and not isinstance(inherits, Space):
        msg = f"space(inherits=...) takes a live Space handle, got {inherits!r}"
        raise TypeError(msg)
    if inherits is not None and inherits._dropped:
        msg = "space(inherits=...) takes a live Space handle"
        raise MettaError(msg)
    if not isinstance(restricted, bool):
        msg = "space(restricted=...) takes a bool"
        raise TypeError(msg)
    if isinstance(grants, str):
        msg = "space(grants=...) takes an iterable of capability names"
        raise TypeError(msg)
    try:
        requested_grants = tuple(grants)
    except TypeError as exc:
        msg = "space(grants=...) takes an iterable of capability names"
        raise TypeError(msg) from exc
    if any(not isinstance(capability, str) for capability in requested_grants):
        msg = "every space grant must be a string"
        raise TypeError(msg)
    unknown = set(requested_grants) - set(SpaceCapability)
    if unknown:
        msg = f"unknown space capabilities: {sorted(unknown)!r}"
        raise ValueError(msg)
    if requested_grants and not restricted:
        msg = "space grants require restricted=True"
        raise ValueError(msg)
    if inherits is not None and restricted:
        msg = "a space cannot be both inherited and restricted"
        raise ValueError(msg)
    return requested_grants


def _source_identity(source: str | None, path: Any) -> str:
    """What the engine will record this registration's source as.

    The pre-load check needs it, because "a name another Prolog source owns"
    has to distinguish another source from THIS one re-registering. Both
    routes know it before the load: a file is its path, and inline source is
    the module name it loads under, which is what the engine reads back off
    the clauses afterwards.
    """
    if path is not None:
        return os.fspath(path)
    return _inline_module_name(str(source))


def _inline_module_name(source: str) -> str:
    """The name SWI loads inline Prolog source under.

    SWI removes every clause loaded under a name when that name is loaded
    again, so this name decides which library's clauses a later registration
    erases. It was `id(source)`, an address CPython hands to the next object
    of the same size the moment the string is freed, and a library generating
    Prolog therefore lost every predicate but the last: the reuse struck on
    the SECOND registration, not after four hundred, and the failure surfaced
    later as `findall_loop/4: Unknown procedure`.

    A content hash fixes every axis at once. It is deterministic, so two
    different sources cannot collide; it is idempotent, so registering the
    same source twice reloads it rather than accumulating clauses; and it
    means something in a stack trace.

    persistent.py hashes the journal PATH and appends a counter, because two
    providers on one journal need distinct modules. Here the requirement is
    the opposite, that the same source reuse one name, so the two do not
    share a helper.
    """
    digest = hashlib.blake2s(source.encode("utf-8"), digest_size=8).hexdigest()
    return f"metta_inline_{digest}"


def _copies_after_its_base(atom: Any) -> bool:
    """Whether a copied atom is a specializer-generated equation.

    The engine spells every generated head with the `_Spec_` infix, so the
    infix is the marker; a user function that happens to carry it is merely
    ORDERED after the others, never dropped, so the heuristic cannot lose an
    atom.
    """
    try:
        if not isinstance(atom, Expression) or str(atom.head) != "=":
            return False
        lhs = atom.args[0]
        return isinstance(lhs, Expression) and "_Spec_" in str(lhs.head)
    except (AttributeError, IndexError):
        return False


class _HashableSpaceTerm(list[Any]):
    """A Janus list carrier that can also key Python's per-space registries."""

    def __hash__(self) -> int:  # type: ignore[override]  # Janus requires a list carrier while per-space registries require a stable hash
        def frozen(value: Any) -> Any:
            if isinstance(value, list):
                return tuple(frozen(item) for item in value)
            return value

        return hash(frozen(self))


def _fact_stream(value: Any) -> Iterator[Any] | None:
    """Classify one ``+=`` operand without mistaking semantic atoms for rows.

    Precedence is the contract. A constructed Atom, including iterable
    Expression and Space handles, is one atom. Text, bytes, mappings, Paths,
    and values with an explicit ``__metta__`` conversion are scalar too.
    Dataframes expose rows through their row protocol rather than their generic
    iterator. An outer tuple made only of complete tuple/Expression rows is a
    fact stream; any other nonempty tuple is one transparent Expression. Empty
    tuple joins the empty iterable law, while ``Expression()`` remains the
    unambiguous spelling for one empty expression atom.

    The final ``iter(value)`` is deliberate: Python's legacy ``__getitem__``
    protocol is iterable even when ``isinstance(value, Iterable)`` is false.
    """
    if isinstance(value, (Atom, Library)):
        return None
    if isinstance(value, _Rules):
        return iter(value)

    iter_rows = getattr(value, "iter_rows", None)
    if callable(iter_rows):
        return iter(iter_rows())
    itertuples = getattr(value, "itertuples", None)
    if callable(itertuples):
        return iter(itertuples(index=False))

    if isinstance(value, tuple):
        if not value or all(isinstance(item, (Expression, tuple)) for item in value):
            return iter(value)
        return None
    if isinstance(value, (str, bytes, bytearray, _abc.Mapping, Path)):
        return None
    if getattr(type(value), "__metta__", None) is not None:
        return None
    try:
        return iter(value)
    except TypeError:
        return None


class Space(Handle):
    """A space bound to the engine: the way in from Python.

    MeTTa keeps one engine per process; every context shares it. The
    process-default home is &self, the space the CLI itself uses, so source
    pasted from a .metta file behaves identically through ``metta.engine()``.
    ``MeTTa()`` itself is a fresh context over its own anonymous home, so two
    contexts never share stored state; ``Space()`` is still the process
    home, and ``metta.engine()`` the context that borrows it.

    A named space isolates both its atoms and its EQUATIONS, and the rule for
    equations has a third part this docstring used to get wrong by calling
    them process-wide. They are per-space, with a dynamic fallback to &self
    and local shadowing [measured 2026-08-17]:

        equation defined in     &self       s1          s2
        ------------------      ---------   ---------   ---------
        s1                      unreduced   answers     unreduced
        &self                   answers     answers     answers
        both                    &self's     s1's        &self's

    So a helper put in &self is reachable from every space, one put in a named
    space is private to it, and a name defined in both resolves to the local
    one where it exists. Registrations are the thing that really is
    process-wide, which the anonymous ``space()`` factory says.

        from metta import MeTTa, S, V

        m = MeTTa().self
        m.run("(= (foo) boo) !(foo)")     # [[Symbol('boo')]]
        m.add(S.Parent(S.Tom, S.Bob))
        m.match(S.Parent(V.x, S.Bob))
    """

    _expression_listing_snapshot = True

    def __setattr__(self, name: str, value: Any, /) -> None:
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str, /) -> None:
        object.__delattr__(self, name)

    def __init__(
        self,
        name: str | Symbol | Expression | Space = _DEFAULT_SPACE,
        *,
        verbose: bool | None = None,
        metta_path: str | None = None,
        _runtime: Runtime | None = None,
        _created_at: tuple[str, int] | None = None,
    ) -> None:
        super().__init__()
        self._rt = _runtime or runtime(metta_path=metta_path, verbose=verbose)
        self._name_atom: Symbol | Expression | None = None
        if isinstance(name, Space):
            # Opening a space is idempotent, so this door takes back what it
            # answers. A dropped handle still refuses, because _space is what
            # reads the name. It matters now that an engine answer naming a
            # space arrives AS a Space: `metta.space(json_decode(...).one())`
            # used to hand a Symbol here and would otherwise have started
            # raising the moment the codec began classifying that atom
            # correctly.
            self._name_atom = name._name_atom
            engine_name: str | _HashableSpaceTerm = name._space
        elif isinstance(name, Symbol):
            self._name_atom = name
            engine_name = (
                name.name if name.name.startswith("&") else f"&{name.name}"
            )
        elif isinstance(name, Expression):
            if name.vars:
                msg = (
                    f"a parametric space name must be ground; {name!s} leaves "
                    f"free variable(s) {[str(v) for v in name.vars]} open"
                )
                raise ValueError(msg)
            if not name.children:
                msg = "a parametric space name is a nonempty ground expression"
                raise ValueError(msg)
            self._name_atom = name
            engine_name = _HashableSpaceTerm(
                self._rt.apply_must("metta_py_open_atom_space", name.to_wire())
            )
        else:
            engine_name = name
        if not isinstance(engine_name, (str, list)):
            msg = (
                f"a space name is an & string, Symbol, or ground Expression; "
                f"got {engine_name!r}"
            )
            raise TypeError(
                msg
            )
        if isinstance(engine_name, str) and not engine_name.startswith("&"):
            msg = (
                f"a space name starts with &, as in &self or &kb; got {engine_name!r}. "
                f"The prefix is load-bearing: is-space recognises it, and a $ "
                f"name would read back as a variable."
            )
            raise ValueError(
                msg
            )
        # The public parameter takes a plain str so a literal is writable;
        # the NewType is constructed once here and threads through inside.
        self._name = cast(_SpaceId, engine_name)
        self._dropped = False
        self._ephemeral = False
        self._autodrop = False
        self._backing: Any = None
        self._owns_backing = False
        self._created_at = _created_at
        self._context_tokens: list[Any] = []

    @property
    def _space(self) -> _SpaceId:
        """The space name, refused once this handle has been dropped.

        Every engine call reads the name through here, so a dropped handle
        cannot reach the engine at all. That matters because drop() returns
        an anonymous name to the pool: without this, a later ``space()``
        hands the same name to a new handle and writes through the dead one
        land in the new space, silently.
        """
        if self._dropped:
            msg = (
                f"{self._name} was dropped; this handle is dead. Its name may "
                f"already belong to another space, so writes through it would "
                f"land there. Take a new handle from space()."
            )
            raise MettaError(
                msg
            )
        return self._name

    # ------------------------------------------------------------------ naming

    @property
    def name(self) -> _SpaceId:
        """The live engine name represented by this handle."""
        return self._space

    def _at(self, name: str) -> Space:
        """Return another handle in this runtime for internal composition."""
        return Space(name, _runtime=self._rt)

    def _open(
        self,
        name: Any,
        *,
        inherits: Space | None = None,
        restricted: bool = False,
        grants: _abc.Iterable[str] = (),
    ) -> Space:
        """Open a NAMED space, declaring its model on the name given.

        A name and a model are independent: the engine's declarations validate
        with metta_require_space_name/2 and take any space name, and the mint
        below is this door with a fresh name in front of it. Both the
        synchronous space() and the async one come through here, so the two
        cannot drift on which models a named space accepts.
        """
        model = _space_model(
            inherits,
            restricted=restricted,
            grants=_checked_new_space_request(
                inherits, restricted=restricted, grants=grants
            ),
            equation_home=None,
        )
        handle = Space(name, _runtime=self._rt)
        if model is not None:
            # On the handle's own normalized name, so space(S.locked) and
            # space("&locked") declare the same space the same way.
            self._rt.must(
                "metta_py_declare_space(Model, Space, Argument)",
                Model=model.model,
                Space=handle._space,
                Argument=model.argument,
            )
        return handle

    def space_names(self) -> list[str]:
        """Every space name this engine registers, sorted: '&self' and
        '&metta' from boot, every native space something created or wrote to,
        and every foreign space currently bound. (new-space) and (spawn ...)
        create, so their answers are here at once; naming a space never
        registers it, so Space('&kb') is not here until a write, and a bind!
        token's target appears once something is stored under it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        row = self._rt.once("metta_py_space_names(Names)")
        return [str(name) for name in row["Names"]]

    def _new_space(
        self,
        *,
        inherits: Space | None = None,
        restricted: bool = False,
        grants: _abc.Iterable[str] = (),
        _equation_home: Space | None = None,
        _created_at: tuple[str, int] | None = None,
    ) -> Space:
        """An anonymous space with a name nothing else is using.

        Works as a context manager: leaving the block drops the space, so a
        churn of short-lived spaces reuses names instead of growing the
        engine's module table.

            with m._new_space() as scratch:
                scratch.add(...)

        What it isolates is STORED STATE: atoms and equations. Registrations
        are process-wide, so a register_prolog, an op, or a define made on an
        anonymous space is visible from every other one. Reach for this to
        isolate the data a test writes, not the names it registers; to isolate
        a name, unregister it.
        """
        requested_grants = _checked_new_space_request(
            inherits, restricted=restricted, grants=grants
        )
        model = _space_model(
            inherits, restricted=restricted, grants=requested_grants,
            equation_home=_equation_home,
        )
        if model is None:
            row = self._rt.must("metta_py_new_space(Name)")
        else:
            row = self._rt.must(
                "metta_py_new_modelled_space(Model, Argument, Name)",
                Model=model.model,
                Argument=model.argument,
            )
        fresh = Space(
            str(row["Name"]),
            _runtime=self._rt,
            _created_at=_creation_site() if _created_at is None else _created_at,
        )
        fresh._ephemeral = True
        fresh._autodrop = True
        return fresh

    def drop(self) -> None:
        """Clear this space and release an anonymous name for reuse.

        Dropping unregisters a Python provider and closes only backing state
        owned by this handle. A foreign provider with a clear/drop lifecycle,
        such as MORK, releases its provider state.
        A named space's public name is not an anonymous allocation and never
        enters the anonymous pool. &self is cleared but never released.
        Subscriptions on the space cancel with it: a pooled name reused later
        must not deliver to the old life's watchers. The handle itself dies
        here, and dropping twice is a no-op, as closing twice is.
        """
        if self._dropped:
            return
        if self._space != "&self":
            self._rt.must(
                "metta_py_space_releasable(Space)", Space=self._space
            )
        subscriptions = _satellite("subscribe")
        foreign = _satellite("foreign")
        integrate = _satellite("integrate")
        for subscription in subscriptions._subscriptions_for(self._space):
            subscription.cancel()
        if foreign.has_provider(self._space):
            # The owned backing's close is an OBLIGATION, not a courtesy:
            # it runs even when unregistration raises, or a failing
            # provider would leak its connection forever.
            try:
                foreign.unregister_provider(self._rt, self._space)
            finally:
                if self._owns_backing:
                    close = getattr(self._backing, "close", None)
                    if callable(close):
                        close()
        if self._space == "&self":
            self.clear()
        else:
            # The engine's release clears the store itself, under its
            # releasing flag so the removal funnel does not recompile super
            # users of a dying world; only the python-side satellites need
            # clearing here.
            _satellite("_lint_events").clear(self)
            _invalidate_builtins_cache(self._rt)
            release_definitions(self)
            # The store clears in its OWN engine query, before the release:
            # a query cannot reclaim the clauses it erased while it still
            # runs, so clearing inside the release left this space's atoms
            # in the table. The door mutes the removal funnel's super
            # recompilation exactly as the release does, since a dying
            # world's own users die with it
            # [tested: test_dropping_a_space_reclaims_its_atoms].
            self._rt.must("metta_py_clear_for_release(Space)", Space=self._space)
            predicate = (
                "metta_py_release_space" if self._ephemeral else "metta_py_drop_space"
            )
            self._rt.must(f"{predicate}(Space)", Space=self._space)
        integrate._forget_space(self._space)
        self._dropped = True

    @property
    def dropped(self) -> bool:
        """Whether :meth:`drop` has released this handle's space."""
        return self._dropped

    def __enter__(self) -> Self:
        self._context_tokens.append(_ACTIVE_SPACE.set(self._space))
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _ACTIVE_SPACE.reset(self._context_tokens.pop())
        # _autodrop, not _ephemeral: an anonymous name is always pooled at
        # drop (_ephemeral), but only a scratch space whose lifetime IS the
        # with-block dies on exit. A context home minted by MeTTa() is
        # ephemeral yet owned by its context, which drops it at close().
        if self._autodrop and not self._context_tokens:
            self.drop()

    def __repr__(self) -> str:
        state = ", dropped" if self._dropped else ""
        shown = self._name_atom if self._name_atom is not None else self._name
        created = (
            ""
            if self._created_at is None
            else f", created_at={f'{self._created_at[0]}:{self._created_at[1]}'!r}"
        )
        return f"Space({shown!r}{state}{created})"

    def __str__(self) -> str:
        return str(self._name_atom if self._name_atom is not None else self._name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Symbol):
            return self._name_atom == other or self._name == other.name
        if isinstance(other, Expression):
            return self._name_atom == other
        return (
            isinstance(other, Space)
            and self._rt is other._rt
            and self._name == other._name
        )

    def __hash__(self) -> int:
        # The engine has one atom for this reference and the legacy Symbol
        # spelling, so equal Python operands must share its symbol hash.
        if self._name_atom is not None:
            return hash(self._name_atom)
        return hash(("sym", self._name))

    def to_wire(self) -> list:
        """Encode the live engine reference as a portable space operand."""
        if isinstance(self._name_atom, Expression):
            return self._name_atom.to_wire()
        return ["p", str(self._space)]

    @property
    def metatype(self) -> str:
        return "Grounded"

    def __reduce__(self):
        return Space, (
            self._name_atom if self._name_atom is not None else str(self._space),
        )

    def __deepcopy__(self, _memo: dict[int, Any]) -> Space:
        msg = (
            "a space handle owns live engine state and cannot be deep-copied; "
            "use space.copy() to clone its stored atoms"
        )
        raise TypeError(msg)

    def bind(
        self,
        values: _abc.Mapping[str, Any] | None = None,
        /,
        **named: Any,
    ) -> _BoundValues:
        """Scope named host values for :meth:`run` without a call flag."""
        bindings = {} if values is None else dict(values)
        if any(
            not isinstance(name, str | Atom) for name in bindings
        ):
            msg = (
                "a bound host value is named by a string, meaning the SYMBOL "
                "of that name, or by an atom, meaning that atom itself"
            )
            raise TypeError(msg)
        overlap = bindings.keys() & named.keys()
        if overlap:
            msg = f"host values were bound twice: {sorted(overlap)!r}"
            raise TypeError(msg)
        bindings.update(named)
        return _BoundValues(bindings)

    # ----------------------------------------------------------------- running

    def run(
        self,
        source: str,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[list[Atom]]:
        """Run MeTTa source: one list of answers per ! directive.

        The pipeline is the engine's own reader, compiler and evaluator, so
        the answers are exactly what the CLI would print, kept grouped per
        directive instead of flattened. Equations and facts in the source
        land in this space.

        `bind()` names Python values the source refers to by bare symbol,
        the way DuckDB reads a local dataframe by its variable name:

            with m.bind({"graph": my_graph}):
                m.run("!(py-len graph)")

        Each named symbol substitutes to its value (objects by identity),
        after reading, before anything runs. It is a BLOCK rather than a
        keyword because a binding mapping is the kind of value that grows,
        and a block grows down the page where a keyword has to fit beside
        everything else on the call. Every target door reads the same scope,
        so one block covers a run(), an eval() and an answers() together.

        `timeout` (seconds) and `inferences` (engine steps) bound the call
        with the engine's own guards; passing either raises TimeLimitError
        or InferenceLimitError when the bound is hit, and whatever the
        source completed before the stop, writes included, stands.

        `with m.capture() as output` collects printed text in `output.text`
        without changing this method's return shape. `with m.atomic()`
        and `with m.speculative()` scope execution policy without boolean
        combinations on each call. Atomic commits or rolls
        back each complete source; speculative answers and discards its
        writes. Both cover engine state; Python side effects and subscription
        callbacks already fired stay where they happened.

        A term the engine hands back unevaluated is an ordinary MeTTa value,
        not a failure: `!(hello world)` answers `(hello world)` and that is
        the whole of hello world in this language. eval_status() reports
        which answers reduced and which did not, as data, for a caller who
        wants to decide about it.
        """
        _require_source(source, "run")
        _record_sync_engine_call(self, "run", sys._getframe(1))
        try:
            return run_source(
                self._rt,
                self._space,
                source,
                _RUN_BINDINGS.get(),
                timeout=timeout,
                inferences=inferences,
            )
        finally:
            _invalidate_builtins_cache(self._rt)

    def profile(
        self,
        source: str,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> tuple[list[list[Atom]], EngineProfile]:
        """Run source under the engine's statistical profiler, answering
        (groups, profile): the groups exactly as run() answers them, and
        the profile carrying sample counters plus one row per predicate,
        self-ticks first.

            groups, prof = m.profile("!(big-computation)")
            prof.top(5)     # the five predicates the samples landed in

        The sampler is statistical: a program that finishes in
        milliseconds carries few samples, so profile something that runs.
        Profiling changes execution; it is a debugging surface, not a
        mode to leave on.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return profile_source(
            self._rt,
            self._space,
            source,
            _RUN_BINDINGS.get(),
            timeout=timeout,
            inferences=inferences,
        )

    def profile_extension(
        self,
        source: str,
        *,
        extension: str | None = None,
        names: _abc.Sequence[str] | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> tuple[list[list[Atom]], list[FunctionCost]]:
        """Run source under the profiler, reporting only YOUR functions.

        `profile()` answers "which predicate did the samples land in", over
        every predicate in the process. The question a library author has is
        narrower: of the functions my library registered, which one is
        costing me, and is anything wrong with how it was installed.

            groups, costs = m.profile_extension("!(my-workload)",
                                                extension="mylib")
            for cost in costs:
                print(cost)
            # <mylib-join/3 prolog: 40100 calls, 39900 redos, 812 ticks, index 1x>

        Name the `extension` and its registered members are looked up, or
        pass `names` for an explicit list. Each row carries the tier that
        installed the function and where from, its exact call and redo
        counts, the sampler's ticks, and its clause index.

        The two columns worth reading first are `redos` and `speedup`. Redos
        on a function meant to be deterministic are a leftover choice point,
        which costs the caller about twice and is invisible to the inference
        counter. A `speedup` of 1 means no argument discriminates, so every
        call walks the clause list; `indexed` False on a function nothing has
        called much only means SWI has not built one yet.

        The sampler is statistical, so profile something that runs, and
        profiling changes execution: this is a debugging surface.
        """
        if (extension is None) == (names is None):
            msg = (
                "profile_extension takes extension= (its registered members) "
                "or names= (an explicit list), and needs exactly one of them"
            )
            raise ValueError(
                msg
            )
        wanted = (
            [str(name) for name in names]
            if names is not None
            else list(self._extension_members(extension))
        )
        return profile_extension(
            self._rt,
            self._space,
            source,
            _RUN_BINDINGS.get(),
            wanted,
            timeout=timeout,
            inferences=inferences,
        )

    def _extension_members(self, extension: str | None) -> tuple[str, ...]:
        _require_name(extension, "profile_extension")
        return tuple(
            self._rt.must(
                "metta_py_extension_members(Name, Names)", Name=str(extension)
            )["Names"]
        )

    def save(
        self,
        path: str | os.PathLike[str],
        *,
        format: SaveFormat = SaveFormat.metta,  # noqa: A002  -- format is the documented public save keyword
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> int:
        """Write every stored atom of this space, equations included, as
        MeTTa source by default, or as a version-pinned trusted cache with
        format="fast"; answers how many. A path ending .gz writes gzip
        compressed in either format, and load and import! read it back
        under the same name. The completed sibling file is synced and then
        atomically replaces the target, so a failed save leaves the old file
        intact. Atoms carrying live host objects cannot survive either file
        and are refused.

        `timeout` (seconds) and `inferences` (engine steps) bound the save with
        the engine's own guards, exactly as they bound load(). Every part of a
        save is linear in the space -- the enumeration, the unwritable-atom
        scan and the fast writer -- so this is the unbounded engine work those
        guards exist to bound, and the atomic replace above already makes a
        stopped save safe: the sibling is never moved into place.

        There is no `format` on load(), and that is not an omission. When you
        save, the file does not exist and something has to say which of the two
        to write; when you load, load() reads which it is, `.gz` included.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return save_space(
            self._rt,
            self._space,
            path,
            format,
            timeout=timeout,
            inferences=inferences,
        )

    def load(
        self,
        path: str | os.PathLike[str],
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[list[Atom]]:
        """Add a text program or trusted fast cache to this space.

        This is a consult, so it always loads and what it loads REPLACES
        what the same file put in this space before. Edit the file, load it
        again, and the space holds the new definitions and not both; the
        engine says on stderr which file it replaced and how many atoms
        went. Atoms from other sources, and ones you added yourself, stay.
        A load that raises leaves the previous definitions standing, so a
        broken edit costs nothing but the error.

        `!(import! &self path)` is the other door and loads a file that is
        new or edited, skipping one that is neither. The two agree on what
        a reload means and differ only in whether an unchanged file runs
        again, which is SWI's consult/1 against its if(changed).

        A .gz path is detected and read through the decompressed bytes.

        `timeout` (seconds) and `inferences` (engine steps) bound the load
        with the engine's own guards, raising TimeLimitError or
        InferenceLimitError. A load is all or nothing: a stop takes back
        everything the file had put in a space, the same way a load that
        fails on a bad form does, because a file the space holds half of is
        not a file it can replace later. run() is the entry point that
        keeps finished work when a bound stops it. This is the one most
        likely to be handed code the caller did not write, since a file can
        carry `!` directives and an import graph, so it takes the same pair
        its siblings take.
        """
        try:
            return load_space(
                self._rt, self._space, path, timeout=timeout, inferences=inferences
            )
        finally:
            _invalidate_builtins_cache(self._rt)

    def parse(self, source: str) -> Atom:
        """Read one form into an atom without evaluating it."""
        return parse(source)

    def register_token(
        self,
        pattern: str | _re.Pattern[str],
        constructor: Callable[[str], Any],
    ) -> None:
        """Register a full-token regex and its Atom constructor.

        The constructor receives the complete matched lexeme. It may return an
        Atom or any value accepted by :func:`metta.ground`. A later registration
        of the same pattern replaces the constructor. Only future parses read
        the new mapping; atoms already returned are immutable values.
        """
        normalized = _reader_pattern(pattern)
        if not callable(constructor):
            msg = "a reader-token constructor must be callable"
            raise TypeError(msg)
        self._rt.must(
            "metta_py_register_token(Pattern, Constructor)",
            Pattern=normalized,
            Constructor=constructor,
        )

    def unregister_token(self, pattern: str | _re.Pattern[str]) -> None:
        """Remove a reader-token class; an absent pattern is already removed."""
        self._rt.must(
            "metta_py_unregister_token(Pattern)", Pattern=_reader_pattern(pattern)
        )

    # ------------------------------------------------------------- space edits

    def add(self, *atoms: Any) -> None:
        """Add atoms to this space, one engine round-trip for the lot.
        An (= ...) atom compiles as an equation. Every Atom shape the engine's
        add-atom accepts crosses unchanged, including a bare Symbol, Grounded
        value, and empty Expression; a free Variable receives the engine's own
        insufficient-instantiation refusal.

        A variable's NAME is not stored. `(rule $x $y)` reads back as
        `(rule $_17902 $_17904)`, because a variable is an identity and not a
        spelling. That is the right property for a logic engine and it is the
        one thing about storage that surprises everybody once.

        A library IS knowledge, so the same door imports it: ``m += lib.he``
        performs ``!(import! <m> (library lib_he))`` with this space as the
        target. An import is an effect, so it refuses to hide inside an atom
        batch or share a call with stored atoms.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if any(isinstance(atom, Library) for atom in atoms):
            if not all(isinstance(atom, Library) for atom in atoms):
                msg = (
                    "imports and stores cannot share one add: a library "
                    "handle performs an effect while atoms accumulate"
                )
                raise TypeError(msg)
            _refuse_in_batch(self._space, "import")
            for handle in atoms:
                import_library(self, handle)
            return
        pending = _ACTIVE_BATCHES.get().get(self._space)
        if pending is not None:
            # A Rules bundle rides the batch WHOLE, so the flush's re-entry
            # into this door sees its identity and publishes its evidence
            # only when the equations actually land; a discarded batch
            # therefore publishes nothing, which the eager spelling used to
            # get wrong.
            pending.extend(atoms)
            return
        if any(isinstance(atom, _Rules) for atom in atoms):
            # A bundle handed WHOLE keeps its identity: its equations stream
            # in place among the other atoms, and its construction evidence
            # publishes once they land, exactly as `m += bundle` publishes.
            # A SPLATTED bundle (`add(*bundle)`) was erased by the caller
            # before this door ran, which is the one spelling that cannot
            # carry the evidence.
            flattened: list[Any] = []
            for item in atoms:
                if isinstance(item, _Rules):
                    flattened.extend(item)
                else:
                    flattened.append(item)
            self.add(*flattened)
            for bundle in atoms:
                if isinstance(bundle, _Rules):
                    _satellite("_lint_events").register_rule_events(self, bundle)
            return
        wires = [_to_atom(atom).to_wire() for atom in atoms]
        if not wires:
            return
        if len(wires) == 1:
            self._rt.do_must("metta_py_add", self._space, wires[0])
        else:
            self._rt.do_must("metta_py_add_many", self._space, wires)
        _invalidate_builtins_cache(self._rt)

    def remove(self, atom: Any, *more: Any) -> bool | int:
        """Remove ONE unifying occurrence and say whether one was there,
        which is Python's own `list.remove` grain.

        Variadic like `add` and `transfer`: several atoms ride one engine
        crossing inside one transaction, and the answer counts the found,
        so the one-atom call still reads as the truth value it always
        was.

        `space -= atom` is this same grain without the report, the way
        `+=` is `add` without one: Python's in-place difference over a
        MULTISET, whose own Python spelling is `collections.Counter`,
        subtracts the multiplicity given rather than clearing the key.
        That is the only reading under which the operators are inverses,
        so `s += a; s -= a` leaves the space it found. `-=` classifies its
        operand exactly as `+=` does, so the fact stream one door stores
        the other subtracts, one occurrence per element, in one
        transactional crossing.

        The DRAIN is the pattern-shaped door: `del m[pattern]` takes every
        unifying occurrence in one crossing and raises when nothing
        matched, as Python's `del` does, and MeTTa spells it `remove-atom`
        [source: engine/spaces/foreign.pl, remove_matching_atoms/2].
        MeTTa spells this method's grain `subtract-atom`. This is the one
        door that reports absence.

        A bare variable is the remove-everything reading a multiset space
        gives it, each atom leaving through its own proper path, equations
        and their compiled clauses included.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _refuse_in_batch(self._space, "remove")
        if more:
            wires = [_to_atom(each).to_wire() for each in (atom, *more)]
            found = self._rt.apply_must(
                "metta_py_remove_many", self._space, wires
            )
            _invalidate_builtins_cache(self._rt)
            return int(found)
        pattern = _to_atom(atom)
        if isinstance(pattern, Variable):
            # The remove-everything reading, spelled as its own door rather
            # than reached by handing an unbound term to the one-occurrence
            # one. The engine's `subtract-atom` refuses that term precisely
            # because it would otherwise mean two opposite things in one head.
            removed = self._rt.apply_must(
                "metta_py_remove_everything", self._space
            )
        else:
            removed = self._rt.apply_must(
                "metta_py_remove", self._space, pattern.to_wire()
            )
        result = _atom_from_wire(removed)
        _invalidate_builtins_cache(self._rt)
        return bool(getattr(result, "value", True))

    def transfer(self, *atoms: Any, to: Space) -> int:
        """Move ONE unifying occurrence of each atom into another space.

        Variadic and atomic: however many atoms ride the call, one engine
        transaction moves them in one crossing, so a mid-move failure
        rolls every side back and nothing is lost between the spaces. The
        answer counts the moved; an absent atom moves nothing and counts
        nothing, which is ``remove``'s own found-reporting grain, so the
        one-atom call still reads as a truth value. The longhand stays
        reachable: a :meth:`transaction` around ``remove`` and ``add``
        says the same thing one atom at a time. :meth:`take` is the
        WAITING kin for a pattern.
        """
        _refuse_in_batch(self._space, "transfer")
        wires = [_to_atom(atom).to_wire() for atom in atoms]
        moved = self._rt.apply_must(
            "metta_py_transfer", self._space, to._space, wires
        )
        _invalidate_builtins_cache(self._rt)
        return int(moved)

    def atoms(self) -> list[Atom]:
        """Every stored atom in this space."""
        wires = self._rt.apply_must("metta_py_atoms", self._space)
        return [_atom_from_wire(w) for w in wires]

    def peek(
        self, pattern: Any, *, where: Any | None = None, deadline: float | None = None
    ) -> Atom:
        """Wait for one matching atom and leave it in this space.

        A finite deadline raises ``Timeout`` when no match arrives.

        `where` is match()'s guard on a blocking wait: a term over the
        pattern's variables, evaluated once a candidate binds them and
        required true, so "wait for a job whose priority is above five" is one
        call. Without it the guard had to live in the caller, as a wait and a
        re-wait around every candidate the guard rejected, and the deadline
        restarted each time round [measured 2026-08-31].
        """
        return self._wait_for_atom("peek-atom", pattern, where, deadline)

    def take(
        self, pattern: Any, *, where: Any | None = None, deadline: float | None = None
    ) -> Atom:
        """Wait for and remove exactly one matching atom from this space.

        Competing takers cannot receive the same occurrence. A finite
        deadline raises ``TimeoutError`` when no match arrives. `where` is
        peek()'s guard, and it is checked BEFORE the removal, so an atom the
        guard rejects stays where it is for whoever does want it.
        """
        return self._wait_for_atom("take-atom", pattern, where, deadline)

    def _wait_for_atom(
        self,
        operation: str,
        pattern: Any,
        where: Any | None,
        deadline: float | None,
    ) -> Atom:
        require_deadline(deadline)
        caller = (
            self
            if self._space == _DEFAULT_SPACE
            else Space(_DEFAULT_SPACE, _runtime=self._rt)
        )
        caller.eval(
            Expression(
                [
                    Symbol("import!"),
                    caller,
                    Expression([Symbol("library"), Symbol("lib_thread")]),
                ]
            )
        )
        arguments: list[Atom] = [self, _to_atom(pattern)]
        # The guarded pair carries its own NAME rather than another arity: a
        # guard and a timeout would both sit third, and nothing could tell
        # (peek-atom &s (job $x) 5) apart from a guard spelled 5.
        if where is None:
            operation = f"{operation.split('-', maxsplit=1)[0]}-atom"
        else:
            guard = guard_atom(where)
            if guard is None:
                msg = f"where= is a term the engine evaluates per candidate, got {where!r}"
                raise TypeError(msg)
            arguments.append(guard)
            operation = (
                "space_await_where" if operation == "peek-atom" else "space_take_where"
            )
        if deadline is not None:
            arguments.append(Grounded(deadline))
        target = Expression([Symbol(operation), *arguments])
        answers = self.eval(target)
        if not answers:
            if deadline is None:
                msg = f"{operation} ended without an answer"
                raise EngineError(msg)
            msg = (
                f"no atom matching {pattern!r} arrived in {self._name} "
                f"within {deadline} seconds"
            )
            # metta.Timeout, the same class the coordination family raises,
            # so the guide's `except metta.Timeout` catches every deadline
            # miss; it subclasses TimeoutError, so the builtin clause still
            # works (agent A hit the split raising builtin TimeoutError here).
            raise Timeout(msg)
        raise_error_answers(answers, space=self._space, target=target)
        if len(answers) != 1:
            msg = f"{operation} returned {len(answers)} answers, expected one"
            raise EngineError(msg)
        answer = answers[0]
        if not isinstance(answer, Atom):
            msg = f"{operation} returned {answer!r}, not an Atom"
            raise EngineError(msg)
        return answer

    # Space is an Atom subtype, so its overload family retains every base call
    # shape and adds the explicit-context form. An overload implementation must
    # accept every advertised input shape. [source:
    # https://github.com/python/typing/blob/44f42629df028aebb783917a393172e4234ad2e7/docs/spec/overload.rst#L150-L160;
    # commit=162214d7a703e9108dd2422f4f18f3b9c007d367]
    @overload
    def cast(self, type_: _builtins.type[_CastT], /) -> _CastT: ...

    @overload
    def cast(self, type_: Atom | str, /) -> Any: ...

    @overload
    def cast(self, value: Any, type_: _builtins.type[_CastT], /) -> _CastT: ...

    @overload
    def cast(self, value: Any, type_: Atom | str, /) -> Any: ...

    def cast(self, value: Any, type_: Any = ..., /) -> Any:
        """Cast this space atom ambiently with one argument, or answer value
        narrowed by this space's type discipline with two arguments. The
        explicit form has the same acceptance a typed call compiles, ':'
        declarations here and &self in scope, protocol types included. A
        refusal raises metta.CastError naming the value's actual types.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if type_ is ...:
            return super().cast(value)
        return _satellite("casting").cast(self, value, type_)

    def trace(self, source: Atom | str, max_events: int = 1_000_000):
        """Run a TERM, or source, under the engine's reduction trace and
        answer TraceEvent records: what entered reduction at which depth,
        what it answered, and which reductions failed (a call with no
        exit). `m.trace(S.fib(10))` is the ordinary spelling, the same
        argument `answers` and `eval` take; a string is still a string.
        What is traced executes for real, writes included, like run();
        the wrap exists only while tracing, so untraced calls pay
        nothing. max_events bounds the recording, raising past it rather
        than accumulating a long run's trace without limit.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _satellite("_trace").trace(self, source, max_events=max_events)

    def lint(self):
        """Diagnose this space for the silently-wrong class: declared
        types nothing defines, arity mismatches, unbound body variables,
        duplicate equations, and references no function or fact carries.
        Answers metta.lint.Finding records, empty when nothing looks
        wrong.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _satellite("lint").lint(self)

    def copy(self) -> Space:
        """This space's contents in a new anonymous space, cloned through
        the bulk door, so equations copy as equations and keep running:
        "a scratch space set up like production" is one line. The handle
        is ``space()``'s kind, so drop it, or use it as a context
        manager, to return the name. copy.copy(m) answers the same
        through the copy protocol. There is deliberately no __deepcopy__:
        stored Python objects keep their identity across the clone, the
        shallow reading, and a deep clone of a live engine handle has no
        meaning to promise.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _satellite("foreign").require_capability(self._space, "enumerate", "copy")
        # Enumerate the SOURCE before minting: a provider whose enumeration
        # fails then costs nothing, where minting first leaked an anonymous
        # clone on every such failure.
        atoms = list(self.atoms())
        # Specializer-generated equations add LAST, stably. Re-adding a base
        # equation invalidates the clone's specializations of that name, so
        # an enumeration that interleaves a base between two generated
        # clauses dropped the earlier one; with every base in first, each
        # generated equation compiles once and is adopted by the engine.
        atoms.sort(key=_copies_after_its_base)
        clone = self._new_space()
        if atoms:
            try:
                clone.add(*atoms)
            except BaseException:
                clone.drop()
                raise
        return clone

    __copy__ = copy

    def reify(self):
        """Capture this space as an immutable, independently evaluable world."""
        from ._world import reify_space  # noqa: PLC0415 -- avoids the Space type cycle

        return reify_space(self)

    def commit(self, world: Any) -> None:
        """Apply one reified world's diff through this originating space."""
        from ._world import commit_world  # noqa: PLC0415 -- avoids the Space type cycle

        commit_world(self, world)

    def digest(self) -> str:
        """A sha256 hex digest of this space's content: every stored atom,
        equations included, canonicalized (variables numbered, multiset
        sorted) so the same atoms answer the same digest in any insertion
        order and in any process. Two spaces agree on digest() exactly
        when save() would write the same content. Live host objects have
        no cross-process identity and are refused, like save().
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _satellite("foreign").require_capability(self._space, "enumerate", "digest")
        result = self._rt.apply_must("metta_py_digest", self._space)
        if not isinstance(result, list) or len(result) != 2:
            msg = f"metta_py_digest returned an invalid result: {result!r}"
            raise EngineError(msg)
        kind, value = result
        if kind == "object":
            atom = _atom_from_wire(value)
            msg = (
                f"{atom} carries a live Python object; it has no "
                f"cross-process identity to digest. Remove it, or digest "
                f"its data explicitly."
            )
            raise ValueError(
                msg
            )
        if kind == "symbol":
            raise_unsafe_text_atom(_atom_from_wire(value), "digest")
        if kind != "digest":
            msg = f"metta_py_digest returned an unknown result: {result!r}"
            raise EngineError(msg)
        return str(value)

    def __len__(self) -> int:
        provider_length = _satellite("foreign")._provider_length(self._space)
        if provider_length is not None:
            return provider_length
        row = self._rt.once("metta_py_count(Space, N)", Space=self._space)
        return int(row["N"])

    def __bool__(self) -> bool:
        """Always true: a space is a handle to a store, not a value that
        dwindles. Without this, bool() falls through to __len__ and an
        empty space is falsy, so `if space:` skips a perfectly good empty
        space, the bug class that made datetime stop treating midnight as
        false in 3.5. Existence is an ask: use
        ``bool(space.match(V.x))`` rather than ``bool(space)``.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return True

    def __contains__(self, atom: Any) -> bool:
        return self._rt.do("metta_py_contains", self._space, _to_atom(atom).to_wire())

    def clear(self) -> None:
        """Remove everything stored here, compiled equations included."""
        _refuse_in_batch(self._space, "clear")
        clear_definitions(self)
        _satellite("_lint_events").clear(self)
        _invalidate_builtins_cache(self._rt)

    # A handle mutates its store while an atom's + constructs a term.
    def __iadd__(self, atom: Any) -> Self:  # type: ignore[override]
        """add()'s operator spelling for one atom or one fact stream.

        ``m += (S.Edge, a, b)`` adds one fact. ``m += [(S.Edge, a, b),
        (S.Edge, b, c)]`` and a generator yielding those rows add two. A built
        Expression is always one atom even though it implements Sequence.
        Dataframes use ``iter_rows`` or ``itertuples(index=False)``. The
        explicit ``add(list_value)`` door remains available when a list itself
        is intended as one transparent expression.

        Relative ``S.admits(Type)`` and ``S.capacity(n)`` values are declared
        data: they install the same contract as the receiver methods and are
        not stored in this space. Explicit ``add(...)`` remains the raw storage
        door for those shapes.
        """
        if self._install_relative_write_declaration(atom):
            return self
        if isinstance(atom, _Rules):
            # add() owns the bundle law now: equations land, then evidence
            # publishes, and a batch defers both together.
            self.add(atom)
            return self
        stream = _fact_stream(atom)
        if stream is None:
            self.add(atom)
        else:
            self.add(*stream)
        return self

    def _install_relative_write_declaration(self, atom: Any) -> bool:
        """Install the two relative pre-add declarations recognized by ``+=``."""
        if (
            not isinstance(atom, Expression)
            or len(atom) != 2
            or not isinstance(atom.head, Symbol)
        ):
            return False
        argument = atom.children[1]
        if atom.head.name == "admits" and isinstance(argument, Symbol):
            _refuse_in_batch(self._space, "declare")
            self.admits(argument.name)
            return True
        if (
            atom.head.name == "capacity"
            and isinstance(argument, Grounded)
            and isinstance(argument.value, int)
            and not isinstance(argument.value, bool)
        ):
            _refuse_in_batch(self._space, "declare")
            self.capacity(argument.value)
            return True
        return False

    # A handle mutates its store while an atom's - constructs a term.
    def __isub__(self, atom: Any) -> Self:  # type: ignore[override]
        # -= is in-place DIFFERENCE over a MULTISET, and Python's own multiset
        # is collections.Counter, whose -= subtracts the multiplicity given
        # rather than clearing the key: Counter(a=3) -= Counter(a=1) leaves
        # a=2. `set -= {x}` looks total only because a set has no
        # multiplicity to subtract. So this takes ONE occurrence per operand
        # element, which is also the only reading under which += and -= are
        # inverses: `s += a; s -= a` has to leave the space it found, and a
        # drain takes copies the += never added. `del s[pattern]` is the
        # drain door and `remove()` the one that reports absence
        # [user ruling 2026-09-01, "consider python's Counter"].
        #
        # The operand reads by the SAME classification += writes by, so the
        # fact stream one door stores the other subtracts: before that, a
        # tuple of rows quietly became one never-matching pattern and -=
        # "succeeded" over an unchanged space.
        _refuse_in_batch(self._space, "remove")
        stream = _fact_stream(atom)
        if stream is None:
            # One element is already atomic, so it takes the plain door. The
            # batch door opens a transaction for the atomicity a BATCH needs,
            # and a foreign provider that declares nothing about transactional
            # writes refuses one it did not ask for: the C-store example's
            # `store -= atom` failed that way the moment a single removal
            # borrowed the batch path [measured 2026-09-01].
            self._rt.apply_must(
                "metta_py_remove", self._space, _to_atom(atom).to_wire()
            )
        else:
            wires = [_to_atom(row).to_wire() for row in stream]
            self._rt.apply_must("metta_py_remove_many", self._space, wires)
        _invalidate_builtins_cache(self._rt)
        return self

    # A handle merges stores while an atom's | constructs a term.
    def __ior__(self, other: Any) -> Self:  # type: ignore[override]
        """Merge into this space in one bulk crossing: every atom of
        another space, of a registered space name, or of an iterable.

            m |= other_space     # every atom, equations included
            m |= "&kb"           # the space registered under this name
            m |= [a, b, c]       # each element becomes one atom

        Equations in the merge compile on arrival, the same rule add()
        enforces. A space is a multiset, so merging a space into itself
        doubles every atom. A Mapping is refused because add(d) reads the
        same dict as ONE grounded atom and its values would silently
        vanish here; spell the reading you mean. Strings name spaces, so
        an unregistered name is a KeyError rather than a parse.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if isinstance(other, Space):
            merged: list[Any] = other.atoms()
        elif isinstance(other, str):
            if other not in self.space_names():
                msg = (
                    f"{other!r} is not a registered space name; "
                    f"space_names() lists them. To add atoms, pass an "
                    f"iterable: m |= [{other!r}]"
                )
                raise KeyError(
                    msg
                )
            merged = Space(other, _runtime=self._rt).atoms()
        elif isinstance(other, (bytes, bytearray, _abc.Mapping)):
            msg = (
                f"|= does not read a {type(other).__name__}: add() would "
                f"lift it into one atom, and iterating it here would read "
                f"the same operand a second way. Use m.add(x) for one "
                f"atom, or spell the elements: m |= list-of-atoms"
            )
            raise TypeError(
                msg
            )
        elif isinstance(other, _abc.Iterable):
            merged = list(other)
        else:
            msg = (
                f"|= merges a space, a registered space name, or an "
                f"iterable of atoms; {type(other).__name__} is none of "
                f"those"
            )
            raise TypeError(
                msg
            )
        self.add(*merged)
        return self

    def __iter__(self):
        """Iterate one assembly-order snapshot of the stored atoms.

        A native or inherited-native space materializes its readable chain
        when ``iter(space)`` is called, so later additions and removals do not
        alter that iterator. A Python-backed space likewise materializes its
        provider's ``atoms()`` result before returning the iterator; the
        provider owns and must document how concurrent mutation behaves while
        that one enumeration itself is being produced.
        """
        return iter(self.atoms())

    def __getitem__(self, i: Any) -> Rows:
        """Subscription is query. A tuple headed by an atom is one built
        expression pattern; a tuple of complete expression patterns is a join:

            m[(S.Parent, V.x, S.Bob)]
            m[S.edge(V.a, V.b), S.edge(V.b, V.c)]

        Python hands both spellings to ``__getitem__`` as a tuple, so shape is
        the visible classifier. A mixed tuple beginning with a complete
        pattern and followed by a bare atom can only be the tuple mistake; it
        raises and names the one-pattern and join spellings instead of
        silently asking an impossible bare-atom conjunct.

        A str key parses first, matching match()'s tolerance. A slice is
        refused: a slice of a space has no one meaning, and the bounded
        readings have their own doors, match(limit=) for a bounded answer
        set and stream() for rows pulled until you have seen enough.
        """  # noqa: D205, D415  -- the API contract is one continuous invariant, not summary-and-body prose; the first line deliberately introduces the indented example that follows
        pattern = i
        if isinstance(pattern, slice):
            msg = (
                "a space cannot be sliced; match(limit=n) bounds the "
                "answer set, stream() pulls rows until you stop"
            )
            raise TypeError(
                msg
            )
        if isinstance(pattern, tuple):
            complete = (Expression, tuple)
            if not pattern or not isinstance(pattern[0], complete):
                return self.match(pattern)
            if not all(isinstance(part, complete) for part in pattern):
                msg = (
                    "a subscript is one pattern as space[(head, ...)] or a "
                    "join of complete patterns as space[p1, p2] (equivalently "
                    "space.match(p1, p2)); a bare atom cannot be a join conjunct"
                )
                raise TypeError(msg)
            return self.match(*pattern)
        return self.match(pattern)

    def __delitem__(self, pattern: Any) -> None:
        """Del m[pattern] removes every unifying occurrence, the bulk
        spelling of remove()'s multiset subtraction: m[pattern] is a
        query answering many rows, so deleting it deletes them all, the
        way DELETE WHERE does. Nothing unifying raises KeyError, as
        del d[k] does on a missing key; remove() is the door that
        reports absence as False instead.

        It asks the engine's own drain, so the whole pattern costs ONE
        crossing rather than one per removed atom.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _refuse_in_batch(self._space, "remove")
        existed = self._rt.apply_must(
            "metta_py_drain", self._space, _to_atom(pattern).to_wire()
        )
        _invalidate_builtins_cache(self._rt)
        if not bool(getattr(_atom_from_wire(existed), "value", True)):
            raise KeyError(pattern)

    # ----------------------------------------------------------------- queries

    def match(
        self,
        *patterns: Any,
        where: Any | None = None,
        limit: int | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
        into: _builtins.type | None = None,
    ) -> Any:
        """Lazily match patterns against this space as one conjunction.

        Variables shared between patterns join, the engine's own match/4
        doing the joining. Columns are the variable names in first
        appearance order. `where` is a guard term over the same variables,
        evaluated per join and required true, so restrictions a pattern
        cannot spell (an inequality) compose onto the match:

            m.match(S.person(V.name, V.age), where=V.age.ge(18))

        `limit` bounds the answers, the engine stopping at the count
        rather than trimming afterwards. `timeout` (seconds) and
        `inferences` (engine steps) bound the whole call, raising
        TimeLimitError or InferenceLimitError when hit, for joins whose
        size is not known in advance.

        The returned Answers view pulls only what Python observes. ``bool``
        pulls one row, exact-one operations pull at most two, and slicing
        retains an Answers view. ``len`` uses an engine-side aggregate when
        no row has yet been pulled.

        ``under=`` interprets the same ask through an annotation algebra.
        ``under=counting`` answers one integer computed by an engine
        aggregate, including duplicate derivations without crossing their
        rows into Python. Ordered carriers sort in their declared direction
        before slicing, so ``m.match(q, under=ranked)[:3]`` is top-k and
        ``under=tropical`` puts the cheapest annotation first. Other carriers
        answer ``TaggedAnswer`` values with ``annotation``, ``why()`` and
        ``under(other)``; the latter two reuse the retained derivation rather
        than querying the space again. ``with metta.under(carrier)`` supplies
        the carrier when this call has no explicit ``under=``.

        `into=Rows` explicitly chooses the eager Rows face. Other `into=`
        values shape each row into a dataclass, NamedTuple, or
        TypedDict matched by field name, sqlite3's row_factory reading:
        `m.match(S.edge(V.a, V.b), into=Edge)` answers `list[Edge]`,
        and Rows stays the default so nothing is lost. A one-variable query
        whose column holds complete constructor expressions rebuilds those
        expressions instead: `m.match(V.edge, into=Edge)`.

            m.match(S.Edge(V.x, V.y), S.Edge(V.y, V.z))
        """
        _record_sync_engine_call(self, "match", sys._getframe(1))
        _validate_limit(limit)
        carrier = _selected_under(under)
        if carrier is not None:
            return self._match_under(
                patterns,
                where=where,
                limit=limit,
                timeout=timeout,
                inferences=inferences,
                under=carrier,
                into=into,
            )
        cursor = Cursor(self, patterns, where, timeout, inferences, limit=limit)

        def source() -> Iterator[_AnswerItem]:
            pulled = 0
            try:
                while limit is None or pulled < limit:
                    try:
                        row = next(cursor)
                    except StopIteration:
                        return
                    pulled += 1
                    yield _AnswerItem(row, row)
            finally:
                cursor.close()

        query_context = _QueryContext(
            self._space,
            tuple(_to_atom(pattern) for pattern in patterns),
            guard_atom(where),
        )
        answers: Answers[Any] = Answers(
            source(),
            columns=cursor.columns,
            space=self._space,
            target=patterns,
            query=query_context,
            # A pattern query reads and writes nothing, so counting it is
            # always the cheap engine aggregate; the route hints a count
            # source may be given change nothing here.
            count=lambda **_route: query_count(
                self._rt,
                self._space,
                patterns,
                where=where,
                limit=limit,
                timeout=timeout,
                inferences=inferences,
            ),
        )
        if into is None:
            return answers
        eager = Rows(
            cursor.columns,
            answers,
            _query=query_context,
        )
        if into is Rows:
            return eager
        return rows_into(eager, into)

    def _match_under(
        self,
        patterns: tuple[Any, ...],
        *,
        where: Any | None,
        limit: int | None,
        timeout: float | None,
        inferences: int | None,
        under: Any,
        into: _builtins.type | None,
    ) -> Any:
        """Build one lazy carrier view over tagged or ordinary engine rows."""
        algebra_api = _satellite("algebra")
        declaration = algebra_api.resolve(self, under)
        if declaration.name == "counting":
            return self._match_counting_under(
                patterns,
                where=where,
                limit=limit,
                timeout=timeout,
                inferences=inferences,
                algebra_api=algebra_api,
                declaration=declaration,
                into=into,
            )

        atoms = tuple(_to_atom(pattern) for pattern in patterns)
        columns = tuple(_column_names(atoms))
        query_context = _QueryContext(
            self._space,
            atoms,
            guard_atom(where),
        )

        def tagged_source() -> Iterator[_AnswerItem]:
            if len(patterns) != 1:
                msg = "a tagged algebra query takes one proposition pattern"
                raise algebra_api.AlgebraEvaluationError(msg)
            evaluation = algebra_api.evaluate(
                self,
                patterns[0],
                algebra=declaration.name,
            )
            row_cls = _row_class(columns)
            # Built ONCE: the guard term does not depend on the answer, only
            # its substitution does.
            guard_template = None if where is None else guard_atom(where)
            yielded = 0
            for answer in evaluation.answers:
                bindings = unify(atoms[0], answer.value)
                if bindings is None:
                    continue
                if guard_template is not None:
                    guard = guard_template.subs(bindings)
                    guard_answers = self.eval(
                        guard,
                        timeout=timeout,
                        inferences=inferences,
                    )
                    if not any(
                        isinstance(value, Grounded) and _decode(value) is True
                        for value in guard_answers
                    ):
                        continue
                if limit is not None and yielded >= limit:
                    return
                row = row_cls(bindings[Variable(name)] for name in columns)
                yielded += 1
                yield _AnswerItem(answer, row)

        def engine_source() -> Iterator[_AnswerItem]:
            cursor = Cursor(
                self,
                patterns,
                where,
                timeout,
                inferences,
                limit=limit,
                under=declaration.name,
                order=declaration.order,
            )
            try:
                for row in cursor:
                    answer = algebra_api.captured_answer(
                        self,
                        row,
                        cursor.annotation,
                        declaration,
                    )
                    yield _AnswerItem(answer, row)
            finally:
                cursor.close()

        def source() -> Iterator[_AnswerItem]:
            if len(patterns) == 1 and algebra_api.has_tagged_program(
                self, patterns[0]
            ):
                yield from tagged_source()
            else:
                yield from engine_source()

        answers: Answers[Any] = Answers(
            source(),
            columns=columns,
            space=self._space,
            target=patterns,
            query=query_context,
        )
        if into is None:
            return answers
        eager = Rows(columns, answers.rows, _query=query_context)
        if into is Rows:
            return eager
        return rows_into(eager, into)

    def _match_counting_under(
        self,
        patterns: tuple[Any, ...],
        *,
        where: Any | None,
        limit: int | None,
        timeout: float | None,
        inferences: int | None,
        algebra_api: Any,
        declaration: Any,
        into: _builtins.type | None,
    ) -> Answers[int]:
        """Build the scalar engine-side counting view."""
        if into is not None:
            msg = "under=counting answers one scalar and cannot use into="
            raise TypeError(msg)

        def counted() -> Iterator[int]:
            if len(patterns) == 1 and algebra_api.has_tagged_program(
                self, patterns[0]
            ):
                if where is not None:
                    msg = (
                        "tagged under=counting does not accept where=; "
                        "put the restriction in the tagged rule"
                    )
                    raise algebra_api.AlgebraEvaluationError(msg)
                yield algebra_api.count_tagged(
                    self,
                    patterns[0],
                    limit=limit,
                    timeout=timeout,
                    inferences=inferences,
                )
                return
            yield query_count(
                self._rt,
                self._space,
                patterns,
                where=where,
                limit=limit,
                timeout=timeout,
                inferences=inferences,
                under=declaration.name,
            )

        return Answers(
            counted(),
            space=self._space,
            target=patterns,
        )

    def stream(
        self,
        *patterns: Any,
        where: Any | None = None,
        limit: int | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
    ) -> Cursor:
        """match(), pulled: the same conjunction and guard, answered one
        row at a time through a cursor the engine holds open.

            with m.stream(S.edge(V.a, V.b), S.edge(V.b, V.c)) as rows:
                for row in rows:
                    if wanted(row):
                        break            # nothing further is even joined

        The join's state lives inside an SWI engine between pulls, each
        pull is one ordinary call, and unrelated calls interleave freely,
        so a huge join costs one row of work per row actually taken where
        match() computes and decodes every answer up front. `timeout`
        bounds each pull's wall time; `inferences` is one budget for the
        cursor's whole engine work, spent across pulls, and the cursor
        stops on the answer that passes it. Because the budget counts the
        cursor's own engine, it is not the number ``stats()`` reports for
        the same work: ``stats()`` reads the calling thread's counters,
        which see the pull loop rather than the engine. The cursor
        enumerates under the engine's logical update view: writes made
        after the first pull are not seen by this cursor.

        `limit` and `under` mean what they mean on match(), because this is
        match() and the cursor underneath already carried both: a tagging
        algebra (ranked, tropical, prov) answers one TaggedAnswer per pull,
        the same value match() answers. `under='counting'` is refused by
        name, because a counting fold is ONE number over the whole answer
        set and a cursor exists not to have one.

        What this door does NOT take is match()'s `into=`, the same kind of
        difference: `into` builds a container out of every row.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        carrier = _selected_under(under)
        if carrier is None:
            return Cursor(self, patterns, where, timeout, inferences, limit=limit)
        algebra_api = _satellite("algebra")
        declaration = algebra_api.resolve(self, carrier)
        if declaration.name == "counting":
            # A counting fold is ONE value over the whole answer set, which is
            # the thing a cursor exists not to have. Answering per-row would
            # make under= mean a fold through match() and something else here.
            msg = (
                "under='counting' folds every answer into one number, so it "
                "has nothing to stream; use match(under='counting'), which "
                "answers that number, or stream under a tagging algebra "
                "(ranked, tropical, prov) for one tagged answer per pull"
            )
            raise TypeError(msg)
        return Cursor(
            self,
            patterns,
            where,
            timeout,
            inferences,
            limit=limit,
            under=declaration.name,
            order=declaration.order,
            capture=lambda row, annotation: algebra_api.captured_answer(
                self, row, annotation, declaration
            ),
        )

    def assuming(self, *facts: Any) -> _Assuming:
        """Facts held only inside a with-block: the assumptions reading of
        a what-if query, added on entry, removed on exit, exceptions
        included.

            with m.assuming(S.closed(S.bridge)):
                detour = m.match(S.route(V.r), where=...)
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _Assuming(self, [_to_atom(f) for f in facts])

    @overload
    def transaction(self, target: Callable[[], _R], /) -> _R: ...

    @overload
    def transaction(self, target: Atom | str, /) -> list[Atom | Undefined]: ...

    def transaction(self, target: Callable[[], _R] | Any, /) -> Any:
        """Run one callable or term inside a closed engine transaction.

        The two inputs preserve their native failure laws. A zero-argument
        Python callable commits its return value and rolls back on a Python
        exception. A term returns its engine answers and rolls back when that
        answer set is empty, exactly like ``(transaction ...)``.

            m.transaction(lambda: migrate(m))
            m.transaction(S.progn(write, verify))

        Every engine write the callable makes, stored atoms, equations
        and their compiled clauses included, commits or rolls back
        together. An exception is the callable's rollback trigger, because a
        Python callable cannot fail the Prolog way, and it re-raises AS
        ITSELF: your ValueError arrives as ValueError with the engine
        boundary in its chain. Only the engine's dynamic state rolls
        back; what the callable did on the Python side (a list appended,
        a file written) is yours to undo, SWI transactions being
        database-scoped.

        Transactions nest, SWI's own semantics: an inner commit is
        relative to its outer transaction, so an outer rollback discards
        inner work too.

        There is deliberately no `with m.transaction():` form. SWI's
        transaction/1 takes a closed goal; there is no open begin/commit
        to hold across a block, and pretending otherwise would lie about
        the isolation actually provided. transactional() is the
        decorator twin.
        """
        if not callable(target):
            return self.eval(Expression([Symbol("transaction"), _to_atom(target)]))
        #The callback's answer is CAPTURED here rather than carried back
        #through janus. janus converts whatever a callback returns and has no
        #conversion for an atom that is not a sequence: a body ending in
        #`add-atom` used to answer the unit expression, which converted as an
        #empty sequence, and answering `true` raised "Grounded(True) is a leaf
        #atom and has no length" from inside the transaction [measured
        #2026-08-30, examples/gallery/journaled_observed_store.py].
        #
        #Boxing rather than discarding, because the answer IS the result of
        #this call: _replace_catalog_declaration/4 returns the atom it stored
        #through here, so a transaction that answered None stopped every
        #catalog declaration silently, `compensates` included.
        answer: list[Any] = []

        def _capture() -> None:
            answer.append(target())

        try:
            row = self._rt.once("metta_py_transaction(F, R)", F=_capture)
        except MettaError as error:
            term = getattr(error.__cause__, "term", None)
            original = (
                self._rt._original_python_error(term, base=BaseException)
                if term is not None
                else None
            )
            if original is not None and original is not error:
                raise original from error
            raise
        if not row:
            msg = (
                "the transaction goal failed without an exception, which "
                "metta_py_transaction does not do on purpose"
            )
            raise EngineError(
                msg
            )
        return cast("_R", answer[0] if answer else None)

    def saga(self, receipts: Space):
        """Open a committed-receipt saga over this execution space.

        ``receipts`` is an ordinary space that stores ``(did op args result)``
        atoms. Run each forward term with the returned context manager's
        ``run`` method. A normal exit keeps its work and receipts; an
        exceptional exit invokes declared compensations in reverse commit
        order and removes each successfully recovered receipt.

            with orders.saga(receipts) as saga:
                saga.run(S.charge(S.order_7))

        Operations ranked writesState or oracleIO leave receipts. Declare a
        handler with ``compensates`` before recovery. Handlers receive the
        complete receipt, written at the call site as ``(quote <receipt>)`` so
        it is not evaluated on the way in, and must be idempotent, because a
        failed compensation remains queryable and is retried by
        ``rollback()``.
        """
        from ._saga import Saga  # noqa: PLC0415 -- avoids the Space type cycle

        if not isinstance(receipts, Space):
            msg = f"saga receipts must be a Space, got {type(receipts).__name__}"
            raise TypeError(msg)
        return Saga(self, receipts)

    def solve(self, pattern: Any, subject: Any) -> Any:
        """Run relational ``let`` and return bindings keyed by its variables.

        ``solve(4, V.x - 1).x`` places the known value on let's pattern side,
        lets the arithmetic relation solve backwards, and projects ``x``.
        The answer template is derived from the pattern's variables followed
        by any new subject variables, so either relational direction can
        introduce the bindings and the third hand-written ``let`` argument
        disappears.
        """
        pattern_atom = _to_atom(pattern)
        subject_atom = _to_atom(subject)
        columns = tuple(_column_names([pattern_atom, subject_atom]))
        if not columns:
            msg = "solve needs at least one variable in its pattern or subject"
            raise ValueError(msg)
        template: Atom = (
            Variable(columns[0])
            if len(columns) == 1
            else Expression([Variable(name) for name in columns])
        )
        answers = self.eval(
            Expression([Symbol("let"), pattern_atom, subject_atom, template])
        )
        return solve_rows(columns, cast(list[Atom], answers))

    def watch(
        self,
        pattern: Any,
        *,
        on: str = "add",
        where: Any | None = None,
        deadline: float | None = None,
        queue_max: int | None = None,
    ):
        """Yield matching changes, raising Timeout after each quiet deadline.

        `queue_max` bounds the subscription underneath, the same bound
        subscribe() takes; a watch could not name it before, though the
        subscription it builds always had one.
        """
        require_deadline(deadline)
        return _WatchIterator(
            self.subscribe(pattern, on=on, where=where, queue_max=queue_max),
            deadline,
        )

    def limits(
        self,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        stack: int | None = None,
    ) -> ScopedLimits:
        """Scoped default bounds for every call in the with-block:

            with m.limits(inferences=1_000_000, timeout=2.0):
                m.match(...)      # bounded without saying so again

        decimal.localcontext's shape, contextvars underneath, so the
        scope is async-correct and per-task. A per-call timeout= or
        inferences= still overrides, which is the whole ladder: one
        block replaces the parameter forest, and the forest remains
        for whoever wants per-call control.

        stack= is SWI's combined stack ceiling in BYTES, the bound a
        runaway recursion hits as a StackOverflow error atom. It is NOT
        MeTTa's reduction depth: that is the max-stack-depth pragma,
        `(with-pragma! ((max-stack-depth N)) expr)`, which counts
        reduction steps and is scoped in the program text.
        """  # noqa: D415  -- the first line deliberately introduces the indented example that follows
        return ScopedLimits(timeout, inferences, stack)

    def capture(self) -> CapturedOutput:
        r"""Collect printed engine text without changing answer shapes.

        with m.capture() as output:
            groups = m.run("!(println! hello) !(+ 1 2)")
        assert groups == [[3]]
        assert output.text == "hello\n"
        """
        return capture_output()

    def atomic(self) -> ScopedExecution:
        """Make each run in the block one committing engine transaction."""
        return execution_scope("atomic")

    def speculative(self) -> ScopedExecution:
        """Run each source against a snapshot and discard its writes."""
        return execution_scope("speculative")

    def batch(self) -> _Batch:
        """Collect this space's add() calls and cross once at exit:

            with m.batch():
                for edge in edges:
                    m.add(edge)          # collected, no crossing yet
            # one add_many crossing happened here

        The write ladder reads: add one; add(*atoms) several; batch a
        region; transaction all-or-nothing; a provider's own bulk door
        underneath. A batch is a transport economy and must not invent
        semantics, so the sharp edges are stated and enforced: reads
        inside the block see the space WITHOUT the pending adds; a
        remove() or clear() on this space inside the block refuses,
        because it would otherwise silently order around writes the
        program already made; and an exception discards the pending
        batch rather than landing writes the code after the raise never
        saw. Compose with transaction() for atomicity: batch for
        economy, transaction for all-or-nothing, or both.
        """  # noqa: D415  -- the first line deliberately introduces the indented example that follows
        return _Batch(self)

    def transactional(self, fn: Callable[_P, _R], /) -> Callable[_P, _R]:
        """transaction()'s decorator twin, the atomic shape Django made
        familiar: each CALL of the wrapped function runs inside its own
        engine transaction. Decorating runs nothing, exactly as a
        decorator should not; reach for transaction() to run one
        callable now.

            @m.transactional
            def migrate():
                m.add(...)
                m.remove(...)

            migrate()     # one transaction; a raise rolls it all back
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

        @functools.wraps(fn)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            return self.transaction(lambda: fn(*args, **kwargs))

        return wrapper

    def prepare(self, *patterns: Any, where: Any | None = None) -> Prepared:
        """A query whose shape is fixed and whose facts are not: the wire
        form and columns build once, and each solve() may bring per-call
        facts (given=) that leave nothing behind.

            route = m.prepare(S.path(V.a, V.b), where=V.a != ...)
            route.solve()
            route.solve(given=[S.edge(S.x, S.y)])
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return Prepared(
            self,
            [_to_atom(p) for p in patterns],
            guard_atom(where),
        )

    # -------------------------------------------------------------- evaluation

    @overload
    def eval(
        self,
        target: Any,
        *,
        timeout: float | None = ...,
        inferences: int | None = ...,
        under: Any = ...,
        theory: Any | None = ...,
        interpreter: Any | None = ...,
    ) -> list[Atom | Undefined]: ...

    @overload
    def eval(
        self,
        target: Any,
        second: Any,
        /,
        *more: Any,
        timeout: float | None = ...,
        inferences: int | None = ...,
        under: Any = ...,
        theory: Any | None = ...,
        interpreter: Any | None = ...,
    ) -> list[list[Atom | Undefined]]: ...

    def eval(
        self,
        target: Any,
        *more: Any,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
        theory: Any | None = None,
        interpreter: Any | None = None,
    ) -> list[Atom | Undefined] | list[list[Atom | Undefined]]:
        """Evaluate a term, returning every answer.

        This is what !(...) runs, minus the printing: the engine's
        translate_expr over the term, then its goals. Nondeterminism means
        the list can hold any number of answers, including none.

        Variadic, and that is how evaluation BATCHES: several terms ride
        one engine crossing and the answer is one group per term in call
        order, run()'s own grouping carried to the term door. One term
        keeps its flat list, so the scalar reading never changes shape.

        Every answer carries its truth: an answer that is undefined under
        Well Founded Semantics (a tabled loop through tnot, reachable via
        translatePredicate or injected Prolog) arrives as an Undefined
        holding the answer and the delay condition that makes it
        undefined, never as an ordinary-looking value. A term to which no
        rule applies is the ordinary answer itself; `eval_status()` names
        that path `not-reducible`. run() does not carry the third truth
        value; evaluate through eval() when it matters.

        `bind()` binds named host values into the term before it evaluates,
        exactly as it does for run(): inside `with m.bind({"x": tensor})`,
        `m.eval("(decide x)")` hands the tensor itself to the rule, by
        identity, rather than a printed form of it. The name is the SYMBOL x
        and not the variable $x, on this door and the source door alike. The evaluation doors take the same
        vocabulary the source door takes, so reaching for a term instead
        of source text costs no change of spelling.

        A key may be a NAME or an ATOM. A name means the symbol of that name,
        which is what the engine's own substitution matches and what run()
        takes. An atom means exactly that atom, so `bind({V.x: 5})` fills a
        VARIABLE hole -- the one substitution `unify` reports and the one no
        door could apply, because a variable crosses the wire as ['v', 'x']
        where a symbol crosses as ['s', 'x'] and the engine matches names.

        `timeout` (seconds) and `inferences` (engine steps) bound the call,
        raising TimeLimitError or InferenceLimitError when hit. A surrounding
        `capture()` scope collects printed text without changing the list.

        `under`, `theory` and `interpreter` are answers()' three, and mean
        exactly what they mean there; this door is that one materialised. A
        surrounding `with metta.under(carrier)` reaches here too, which it did
        not before: match() and answers() both honoured such a scope while
        eval() ignored it in silence.
        """
        _record_sync_engine_call(self, "eval", sys._getframe(1))
        if more:
            # The batched face: the delegating knobs stay per-term through
            # answers(); the plain lane crosses once for the lot.
            grouped = (target, *more)
            if (
                theory is not None
                or interpreter is not None
                or _selected_under(under) is not None
            ):
                return [
                    list(
                        self.answers(
                            each,
                            timeout=timeout,
                            inferences=inferences,
                            under=under,
                            theory=theory,
                            interpreter=interpreter,
                        )
                    )
                    for each in grouped
                ]
            prepared = [self._prepared_ask(each, None) for each in grouped]
            scope = next((using for _, using in prepared if using), None)
            return evaluate_many(
                self._rt,
                self._space,
                tuple(each for each, _ in prepared),
                timeout,
                inferences,
                using=scope,
            )
        # Atom-keyed bindings are applied here whichever branch runs below, so
        # the eager path and the delegating one agree on what a binding means.
        target, using = self._prepared_ask(target, None)
        # The two doors are NOT one mechanism, which was measured rather than
        # assumed: eval() is one eager engine call (metta_py_eval_all) and
        # answers() opens a cursor, and routing eval() through the cursor
        # unconditionally left a memoized definition's call keys unrecorded
        # where the eager door records them [measured 2026-08-31: a memoized
        # fib(12) reached through the handle then run() stored 13 entries on
        # the eager path and 0 through the cursor]. So the delegation is for
        # what answers() uniquely OWNS -- the carrier, the theory and the
        # interpreter -- and the eager path stays the eager path.
        if theory is not None or interpreter is not None or _selected_under(under) is not None:
            return list(
                self.answers(
                    target,
                    timeout=timeout,
                    inferences=inferences,
                    under=under,
                    theory=theory,
                    interpreter=interpreter,
                )
            )
        return evaluate(
            self._rt, self._space, target, timeout, inferences, using=using
        )

    def answers(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
        theory: Any | None = None,
        interpreter: Any | None = None,
    ) -> Answers[Any]:
        """Evaluate lazily as an immutable, cached and replayable view.

        Creating the view performs no engine work. Existence pulls at most
        one answer, ``one()`` at most two, and ordinary iteration resumes the
        same held evaluation [tested:
        test_function_calls_pull_engine_answers_only_as_demanded;
        commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4].

        ``under=`` has the same carrier semantics as ``match``. In
        particular, ``space.answers(call, under=counting).one()`` counts the
        call's answer derivations inside the engine, and ordered carriers
        order their annotated ``TaggedAnswer`` values before a slice pulls
        its prefix. A surrounding ``metta.under(carrier)`` is used only when
        this call does not pass an explicit carrier.

        ``theory=`` treats an atom or iterable of atoms as the theory value for
        this ask. That value replaces the receiver's own equational program.
        Engine builtins and the shared ``&self`` session space remain in scope
        exactly as they are for every space, and names the theory defines
        shadow inherited ones. It installs the theory in an isolated scratch
        space on the first pull, evaluates there, and drops the space when the
        view is exhausted or abandoned. The receiver is unchanged. This
        mirrors reflective descent functions whose inputs are a reified module
        and term [source:
        https://maude.cs.illinois.edu/maude1/manual/maude-manual-html/maude-manual_24.html;
        commit=0d49980b03d507f9bae0354786ab826a146c20df].

        ``interpreter=`` instead evaluates the explicit full-interpreter
        application ``(interpreter target %Undefined% space)`` for this ask,
        which is the shape MeTTa's own evaluation function has: it says
        "reduce with YOURS rather than the engine's".

        The two COMPOSE, and are the head and the third argument of one
        application rather than rival answers to one question: with both, the
        interpreter is handed the theory's space, so it interprets the theory
        [measured 2026-08-31: an interpreter tracing its delegate answered
        `(Traced base)` alone and `(Traced left), (Traced right)` over a
        two-equation theory]. They used to refuse together.

        The INTERPRETER must declare its first parameter `Atom`, MeTTa's own
        way to receive an argument unevaluated, or the engine reduces the
        target before the interpreter ever sees it; and its RETURN metatype
        `%Undefined%`, or the interpreter's own answer is not reduced either.
        `(: e (-> Atom Atom Atom %Undefined%))` is the declaration.
        """
        _record_sync_engine_call(self, "answers", sys._getframe(1))
        target, using = self._prepared_ask(target, None, theory, interpreter)
        carrier = _selected_under(under)
        if theory is not None:
            return self._answers_with_theory(
                target,
                theory,
                timeout=timeout,
                inferences=inferences,
                carrier=carrier,
                interpreter=interpreter,
            )
        if carrier is None:
            return evaluate_answers(
                self._rt,
                self._space,
                target,
                timeout,
                inferences,
                using=using,
            )
        algebra_api = _satellite("algebra")
        declaration = algebra_api.resolve(self, carrier)
        tagged_target = (
            _substituted(target, using)
            if using
            else (_to_atom(target))
        )
        if declaration.name == "counting":
            def counted() -> Iterator[int]:
                if algebra_api.has_tagged_program(self, tagged_target):
                    yield algebra_api.count_tagged(
                        self,
                        tagged_target,
                        timeout=timeout,
                        inferences=inferences,
                    )
                else:
                    # This scalar IS the whole evaluation: the counting view
                    # holds no answer cursor beside it, so the engine counts
                    # once and one integer crosses. Asking the repeatability
                    # question here instead sent an effect-bearing goal
                    # through a materializing pass that encoded and crossed
                    # every answer to reach a number nobody kept.
                    yield evaluate_count(
                        self._rt,
                        self._space,
                        target,
                        timeout,
                        inferences,
                        using=using,
                        under=declaration.name,
                    )

            return Answers(counted(), space=self._space, target=target)
        columns = tuple(_column_names((tagged_target,)))

        def annotated() -> Iterator[Any]:
            if algebra_api.has_tagged_program(self, tagged_target):
                evaluation = algebra_api.evaluate(
                    self,
                    tagged_target,
                    algebra=declaration.name,
                )
                if not columns:
                    yield from evaluation.answers
                    return
                row_cls = _row_class(columns)
                for answer in evaluation.answers:
                    bindings = unify(tagged_target, answer.value)
                    if bindings is None:
                        continue
                    row = row_cls(bindings[Variable(name)] for name in columns)
                    yield _AnswerItem(answer, row)
                return
            ordinary = evaluate_answers(
                self._rt,
                self._space,
                target,
                timeout,
                inferences,
                using=using,
                under=declaration.name,
                order=declaration.order,
            )
            yield from ordinary._items()

        return Answers(
            annotated(),
            columns=columns,
            space=self._space,
            target=target,
        )

    def _prepared_ask(
        self,
        target: Any,
        using: dict[Any, Any] | None,
        theory: Any = None,
        interpreter: Any = None,
    ) -> tuple[Any, dict[str, Any] | None]:
        """Everything a term ask does to its target before the engine sees it.

        Two things, both of which every door taking a target owes its caller.

        ``interpreter=`` is a TERM rewrite and nothing more, so it costs the
        same three lines wherever it is offered; ``theory=`` needs a scratch
        space and stays with the door that owns its lifetime, which is why the
        rewrite is skipped here when a theory is also present: the application
        has to name the SCRATCH as its space, and the scratch does not exist
        yet.

        And an ATOM-keyed binding from the ``bind()`` scope is applied here
        rather than sent on. The engine's metta_host_substitute/3 matches an
        atom by NAME [source: engine/filereader.pl:579-584], so it can reach a
        symbol and cannot reach a variable at all -- measured 2026-08-31,
        neither ``{"x": 5}`` nor ``{"$x": 5}`` fills the hole in
        ``(dbl $x)``. A variable hole is exactly what ``unify`` reports, so
        the one substitution the library could produce was the one no door
        could apply. An atom key says which atom it means, so it is applied by
        ``Atom.subs`` here and a name key keeps meaning the symbol it always
        meant, to the same engine predicate as before.
        """
        using = {**(_RUN_BINDINGS.get() or {}), **(using or {})} or None
        if using:
            keyed = {key: value for key, value in using.items() if isinstance(key, Atom)}
            if keyed:
                target = (
                    _to_atom(target)
                ).subs(keyed)
                using = {
                    key: value
                    for key, value in using.items()
                    if not isinstance(key, Atom)
                } or None
        if interpreter is not None and theory is None:
            target = self._interpreted(target, interpreter, self)
        return target, using

    def _interpreted(self, target: Any, interpreter: Any, space: Space) -> Expression:
        """The explicit interpreter application, over one space.

        ``(interpreter target %Undefined% space)`` is the shape MeTTa's own
        evaluation function has -- `!(test (metta (+ 1 2) %Undefined% &self) 3)`
        is in the corpus -- so this says "reduce with YOURS instead of the
        engine's". The space argument is what makes it compose with ``theory=``:
        the interpreter reads the space it is handed, and the theory decides
        which space that is.

        The INTERPRETER must declare its first parameter `Atom`, or MeTTa
        reduces the target before it ever arrives and the interpreter sees an
        answer rather than a term
        [measured 2026-08-31: an ordinary define answered `(Saw base)` where
        `(: e (-> Atom Atom Atom %Undefined%))` answered `(Saw (choice))`].
        The return metatype is the other half: `%Undefined%` there so the
        interpreter's own answer reduces, `Atom` so it does not.
        """
        interpreted = _to_atom(target)
        return Expression(
            [_to_atom(interpreter), interpreted, Symbol("%Undefined%"), space]
        )

    def _in_theory(self, theory: Any) -> _abc.Iterator[Space]:
        """A scratch space holding one theory, dropped when the block ends.

        The receiver is unchanged; names the theory defines shadow inherited
        ones, and engine builtins and &self stay in scope as they do for every
        space.
        """
        scratch = self._new_space()
        try:
            atoms = self._theory_atoms(theory)
            if atoms:
                scratch.add(*atoms)
            yield scratch
        finally:
            scratch.drop()

    def _answers_with_theory(
        self,
        target: Any,
        theory: Any,
        *,
        timeout: float | None,
        inferences: int | None,
        carrier: Any | None,
        interpreter: Any | None = None,
    ) -> Answers[Any]:
        """Defer an isolated theory ask and own its scratch-space lifetime."""
        columns = () if isinstance(target, str) else tuple(_column_names((_to_atom(target),)))

        def source() -> Iterator[_AnswerItem]:
            scratch = self._new_space()
            inner: Answers[Any] | None = None
            try:
                atoms = self._theory_atoms(theory)
                if atoms:
                    scratch.add(*atoms)
                # With an interpreter, the application names the SCRATCH and is
                # asked of the RECEIVER: the interpreter's own definition lives
                # here, and the space it reads is the theory's. Asking the
                # scratch instead leaves the interpreter unresolved, and naming
                # the receiver leaves the theory unread
                # [measured 2026-08-31, both ways round].
                asked, ask_of = (
                    (target, scratch)
                    if interpreter is None
                    else (self._interpreted(target, interpreter, scratch), self)
                )
                if carrier is None:
                    inner = ask_of.answers(
                        asked,
                        timeout=timeout,
                        inferences=inferences,
                    )
                else:
                    inner = ask_of.answers(
                        asked,
                        timeout=timeout,
                        inferences=inferences,
                        under=carrier,
                    )
                yield from inner._items()
            finally:
                if inner is not None:
                    close = getattr(inner._source, "close", None)
                    if callable(close):
                        close()
                scratch.drop()

        return Answers(source(), columns=columns, space=self._space, target=target)

    @staticmethod
    def _theory_atoms(theory: Any) -> tuple[Atom, ...]:
        """Normalize one data-valued theory without accepting source text."""
        if isinstance(theory, Space):
            values: Iterable[Any] = theory.atoms()
        elif isinstance(theory, Atom):
            values = (theory,)
        elif isinstance(theory, str) or not isinstance(theory, Iterable):
            msg = (
                "theory= needs an atom, Space, or iterable of atoms as data; "
                "source text belongs at run()"
            )
            raise TypeError(msg)
        else:
            values = theory
        try:
            return tuple(_to_atom(value) for value in values)
        except (TypeError, ValueError) as error:
            msg = f"theory= contains a value that is not an atom: {error}"
            raise TypeError(msg) from error

    def parallel(
        self,
        *targets: Any,
        timeout: float | None = None,
    ) -> list[Atom | Undefined]:
        """Evaluate every target concurrently, answering every branch's answers.

        This is the engine's `hyperpose`, the parallel twin of `superpose`:
        one SWI thread per branch through concurrent_and/2, so independent
        branches cost about one branch's wall clock rather than their sum.

            m.run("(= (sq $x) (* $x $x))")
            m.parallel(S.sq(1), S.sq(2), S.sq(3))    # 1, 4 and 9, in any order

        This is the **in-engine** fan-out: one janus call, the branches split
        below it. The other route is `pool()`, the **Python-side** fan-out
        across several engines. Reach for this one when the fan-out is a MeTTa
        expression, and for `pool()` when it is a Python loop. They compose,
        so a pool worker may itself evaluate a `parallel()`.

        (Before 2026-08-15 this docstring said in-engine fan-out was the only
        route to a second core, because every janus call took one process-wide
        lock. That lock is now per-engine, and Python threads holding their own
        engine measured 1.94x, 3.90x and 7.26x at 2, 4 and 8 threads.)

        **Answers arrive in completion order, not argument order**, because
        the branches race. Compare sets rather than sequences, and evaluate a
        `superpose` instead when order carries meaning.

        Each target is a term or its source text, as everywhere else. No
        targets answers nothing without calling the engine.

        `timeout` bounds the call and is the bound to use here. There is
        deliberately no `inferences=`: the engine's inference limit counts
        the calling thread, and `concurrent_and/2` runs every branch in a
        worker, so a limit of 50,000 does not stop two branches spending six
        million [measured 2026-08-15]. An unenforceable bound is worse than
        an absent one, so eval() over a `superpose` is the way to bound this
        work by inferences, at the cost of running it on one core.
        """
        if not targets:
            return []
        branches = Expression([_to_atom(target) for target in targets])
        return evaluate(
            self._rt,
            self._space,
            Expression([Symbol("hyperpose"), branches]),
            timeout,
            None,
        )

    def pool(self, workers: int | None = None) -> Any:
        """A pool of worker threads that each hold their own Prolog engine.

        The Python-side twin of `parallel()`. Each worker attaches its own
        engine, so the process lock that serialises the home engine does not
        apply to it and the calls genuinely run at once [measured 2026-08-15:
        1.94x, 3.90x and 7.26x at 2, 4 and 8 workers].

            m.run("(= (sq $x) (* $x $x))")
            with m.pool(workers=4) as p:
                p.map(lambda n: m.eval(S.sq(n))[0], range(64))

        Use it as a context manager so every engine is released. `workers`
        defaults to os.cpu_count(). This handle stays usable from the workers:
        a MeTTa is a space name over the process runtime, not thread-owned.

        Reach for `parallel()` instead when the fan-out is a MeTTa expression
        rather than a Python loop; the two compose.
        """
        return _satellite("parallel").EnginePool(workers)

    def reducible(self, target: Any) -> bool:
        """Whether a head reduces here, asked without evaluating anything.

            m.reducible(S.double(4))     # True
            m.reducible(S.Point(1, 2))   # False, nothing applies to that head

        The same head test eval_status() uses, published on its own because a
        caller who wants to DECIDE about an unreduced term should not have to
        run the term to find out. That decision is the caller's: a term
        nothing applies to is its own answer, which is ordinary MeTTa and how
        `!(hello world)` works, so there is no scope here that refuses one.

        The Node surface has had m.reducible() since it existed; Python had
        only eval_status(), which evaluates to tell you [measured 2026-08-31].
        """
        # The seam answers the ATOM true or false, which crosses as the string
        # of that name; bool("false") is True, so the comparison is explicit,
        # the same way algebra.py reads its own boolean seam.
        return (
            self._rt.apply_must(
                "metta_py_reducible", self._space, _to_atom(target).to_wire()
            )
            == "true"
        )

    def eval_status(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        theory: Any | None = None,
        interpreter: Any | None = None,
    ) -> list[tuple[str, Atom | Undefined | None]]:
        """Evaluate a term, pairing each answer with how it was produced.

            m.eval_status(S.double(4))       # [("value", Grounded(8))]
            m.eval_status(S.Point(1, 2))     # [("not-reducible", Expression(...))]
            m.eval_status(S.empty())         # [("empty", None)]

        `value` means an equation, builtin or special form applied.
        `not-reducible` means no rule applied, so the answer is the term
        itself, which is what MeTTa does with any head it cannot call.
        `empty` means the goal produced no answer at all, and its atom is
        None. Reading the last two as the same thing is the mistake this
        exists to prevent: an unevaluated term and a pruned branch look
        alike from the answers alone. An error is not a status here,
        because it arrives as an exception.

        A `bind()` scope binds host values into the term exactly as it
        does for eval(), and it has to: the substitution lands BEFORE the
        reducibility question, so the status of an evaluation that binds
        anything was unaskable without it. Name keys mean symbols and atom
        keys mean themselves, so `bind({V.x: 5})` fills a variable hole.

        `theory` and `interpreter` are eval()'s own, and mean the same here.
        This is the door that says which evaluation path produced an answer, so
        being unable to point it at an alternative evaluation relation was the
        sharpest form of the gap: `m.eval_status(target, interpreter=my_eval)`
        is how you see whether an explicit interpreter reduced a term or handed
        it back. `under=` is deliberately NOT here: a carrier annotates every
        answer with an algebra value, so it would make a status row a triple
        rather than the pair it is, which is a question about what a status IS.
        """
        target, using = self._prepared_ask(target, None, theory, interpreter)
        if theory is None:
            return evaluate_status(
                self._rt, self._space, target, timeout, inferences, using=using
            )
        for scratch in self._in_theory(theory):
            # With an interpreter, the application names the SCRATCH and is
            # asked of the RECEIVER, the same way answers() composes them: the
            # interpreter's definition lives here and the space it reads is
            # the theory's.
            if interpreter is None:
                return scratch.eval_status(
                    target, timeout=timeout, inferences=inferences
                )
            return self.eval_status(
                self._interpreted(target, interpreter, scratch),
                timeout=timeout,
                inferences=inferences,
            )
        raise AssertionError  # pragma: no cover -- _in_theory always yields once

    def run_status(
        self,
        source: str,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[list[tuple[str, Atom | Undefined | None]]]:
        """run(), with each directive's answers paired with how they arose.

        The grouping and the answers are run()'s own; see eval_status() for
        what the three paths mean.
        """
        _require_source(source, "run_status")
        return run_status(self._rt, self._space, source, timeout, inferences)

    def _one(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """Return the sole answer as a plain Python value for internal callers.

            m.eval(S.fact(5))[0]         # Grounded(120)

        Exactly one answer is the contract: none or several raise naming
        the count, because a caller asking for the value has asserted
        there is one. Grounded answers unwrap to their Python values;
        symbols and structure stay atoms.

        This is one point on the answer-cardinality axis, spelled the
        same everywhere it appears: eval() takes every answer (MeTTa's
        collapse), while this private helper demands exactly one. The same
        timeout/inferences bounds apply throughout.

        An `(Error ...)` answer raises MettaResultError carrying the
        atom: an error among the answers is the evaluation reporting
        failure, and failure outranks the count. eval() is the door
        that keeps errors as data.
        """
        answers = self.eval(target, timeout=timeout, inferences=inferences)
        raise_error_answers(answers, space=self._space, target=target)
        return value_one(target, answers)

    def _first(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """The first answer as a plain Python value, or None for no answers.

        The tolerant member of one()'s family: one() asserts exactly
        one, eval() answers all, first() answers the first or nothing,
        decoded by the same rule as one(). An Undefined first answer
        still raises, since None here MEANS no answers. Tolerance is
        about cardinality, not content: a first answer that is an
        `(Error ...)` atom raises MettaResultError exactly as one()
        does, because None must keep meaning "no answers" and an error
        used as a value is the silent kind of wrong.
        """
        answers = self.eval(target, timeout=timeout, inferences=inferences)
        if not answers:
            return None
        raise_error_answers(answers[:1], space=self._space, target=target)
        return value_one(target, answers[:1])

    def stats(self) -> _StatsBlock:
        """The engine's own counters over a with-block, as deltas.

            with m.stats() as s:
                m.match(S.edge(V.x, V.y), S.edge(V.y, V.z))
            s.inferences        # engine steps the block spent
            s.cputime           # engine CPU seconds
            s.walltime          # wall seconds, Python's clock
            s.gc_count, s.gc_freed, s.gc_time
            s.table_bytes       # answer-table bytes grown, tabling's memory

        The counters are SWI's statistics/2 read on the CALLING thread, so
        a block that runs other threads' engine work counts that work too;
        the honest reading is "what this thread saw the engine do while the
        block ran". A lazy cursor is the exception, and a large one: its
        goal runs in an SWI engine, an engine counts its own inferences,
        and this thread cannot see them. Draining 20,000 rows through the
        match cursor reports 40,049 inferences against about 381,000 the
        cursor's engine really spent, 10.5% of the work; the real cost is
        readable off the `inferences` budget, which does count the engine
        [measured 2026-08-27]. The evaluation cursor behind `answers()`
        does report its engine's spend, so that one is whole. The z3py
        Solver.statistics() reading, on the engine this library actually
        has.
        """
        return _StatsBlock(self._rt)

    # -------------------------------------------------------------- operations

    # register returns fn unchanged, so both decorator forms are identities
    # and the two arms have to say so. Without them the bare form collapses
    # into a union that still includes the decorator-factory arm, and a call
    # through the name is checked against the factory: measured as
    # "breed(a, b) takes one argument" in evolutionary_search.py
    # [measured 2026-08-17].
    @overload
    def op(
        self,
        fn: Callable[_P, _R],
        /,
        *,
        name: str | None = ...,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = ...,
        effect: EffectClass | str,
        declarations: Iterable[Atom] = ...,
        arities: list[int] | None = ...,
        inverse: Callable | None = ...,
    ) -> Callable[_P, _R]: ...

    @overload
    def op(
        self,
        *,
        name: str | None = ...,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = ...,
        effect: EffectClass | str,
        declarations: Iterable[Atom] = ...,
        arities: list[int] | None = ...,
        inverse: Callable | None = ...,
    ) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...

    def op(
        self,
        fn: Callable | None = None,
        *,
        name: str | None = None,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = "encoded",
        effect: EffectClass | str | None = None,
        declarations: Iterable[Atom] = (),
        arities: list[int] | None = None,
        inverse: Callable | None = None,
    ) -> Any:
        """Register a Python callable as a MeTTa function, decorator-style.

            @m.op(effect=EffectClass.pureStructural)
            def double(x: int) -> int:
                return 2 * x                    # !(double 21) -> 42

            @m.op(effect=EffectClass.nondeterministicReadOnly)
            def neighbours(n: int):
                yield n - 1                     # a generator is nondeterministic
                yield n + 1

        An implicit Python name maps underscores to MeTTa hyphens. ``name=``
        is exact, for source vocabularies that deliberately use underscores.

        A name must read back as one MeTTa symbol. A space, parenthesis,
        quote, comment opener, variable spelling, number, boolean, or another
        registered reader token is refused before any registry changes, with
        the name and the conflicting character in the error.

        Annotations become ordinary `(: ...)` declarations. An unannotated
        callable makes no type claim. `transport="raw"` skips wire encoding
        both ways and is reflected as raw_det or raw_many in `(op ...)`;
        symbols then reach Python as strings, so encoded transport is the
        fidelity-preserving default. unregister_op(name) removes every
        registered arity and every declaration the registration owns.

        An `Atom` parameter changes evaluation order. The declaration tells
        the compiler to pass the argument as written, before it reduces:

            @m.op(effect=EffectClass.pureStructural)
            def anyatom(term: Atom) -> Atom:
                return term

            # with (= (side) 42), !(anyatom (side)) answers (side)

        An unconstrained parameter receives the evaluated value instead, so
        the otherwise identical `def anyval(term): return term` answers 42.
        Use `Atom` only when the operation deliberately implements syntax or
        a control form; it is not just a static hint.

        An encoded generator may instead yield exact tuples as positional
        relation rows, or exact dicts keyed by parameter name as sparse rows.
        The engine unifies each candidate against the written call, so one
        implementation serves free, partially bound, and ground arguments:

            @m.op
            def route(origin, destination):
                yield (S.paris, S.lyon)
                yield {"destination": S.nice}  # origin is unconstrained

            # route(V.origin, S.lyon).rows[0].origin == S.paris

        Each matching occurrence answers unit and duplicate yields remain
        duplicate answers. Use `Answer(value=...)` when an exact tuple or dict
        is the result value rather than a parameter row. Relational rows
        require encoded transport; raw calls cannot carry unbound argument
        positions.

        When evaluation order stays ordinary but the callable needs the
        resulting Atom wrappers, declare that policy as data:

            m.op(
                inspect_atom,
                name="inspect-atom",
                effect=EffectClass.pureStructural,
                declarations=[parse("(arguments inspect-atom atoms)")],
            )

        The declaration is matchable in &metta and is retired with the
        operation. Raw transport refuses this declaration because it bypasses
        the atom codec entirely.

        The cost ladder, measured on the maintained box in inferences per
        call, explains the transport choice:

            native MeTTa function            9.11   the floor
            transport="raw"                10.11   opaque handles, near-native
            encoded                        17.11   encoded values
            encoded, typed literal         17.11   the check hoists to compile
            py-call, dotted                 22.11   the ad-hoc escape hatch

        The ergonomic default (encoded, typed) costs about 1.7x raw on the
        counter and more on wall clock, since encoding walks the value both
        ways; a registered raw operation measured 0.85us against 2.26us
        encoded. Bulk data should stay opaque: one transparent 64-float
        crossing costs 330 inferences where the handle costs 10.

        `inverse=` remains the distinct-output form. Use it when the forward
        operation returns a result and a separate callable must recover the
        arguments from that result:

            m.op(
                cons,
                name="cons",
                inverse=uncons,
                effect=EffectClass.pureStructural,
            )
            # !(let (cons $h $t) (1 2 3) ($h $t))  ->  (1 (2 3))

        It takes the result and returns the arguments, as a tuple, or the
        bare value at arity one; a generator enumerates every preimage, and
        None or NotReducible means there is none. It runs only when the arguments
        are not ground and the result is, so a forward call never reaches it,
        and an operation without one compiles exactly what it did before.

        A parameter annotated `metta.MeTTa` is the framework's to fill,
        FastAPI's Depends read with the house convention that the
        annotation is the request. The engine injects itself bound to the
        CALLING context's space, so an operation invoked from a program
        running in &kb queries &kb; the slot never counts toward MeTTa
        arities or the declared arrow, and only operations that ask pay
        the weaving:

            @m.op(effect=EffectClass.nondeterministicReadOnly)
            def related(term, engine: metta.MeTTa):
                for row in engine.match(Expression(S.link, term, V.x)):
                    yield row[0]

        Every operation declares its strongest observable effect. The five
        ordered choices are ``pureStructural``, ``readOnlyLookup``,
        ``nondeterministicReadOnly``, ``writesState``, and ``oracleIO``:

            m.op(
                len,
                name="size",
                effect=EffectClass.pureStructural,
            )
            # (= (count-of $x) (size $x))  is cacheable

        It is an allow-list on purpose. An operation that does not say so is
        refused by name in a cached body, loudly, rather than cached and
        quietly wrong.
        """

        def apply(f: Callable) -> Callable:
            registered = _ops_module.register(
                self._rt,
                f,
                name=name,
                transport=transport,
                effect=effect,
                declarations=declarations,
                space=self._space,
                arities=arities,
                inverse=inverse,
            )
            _invalidate_builtins_cache(self._rt)
            return registered

        return apply(fn) if fn is not None else apply

    # The effect classes as four decorators, so the classification is a name
    # rather than a string argument. `op` is the longhand and every one of
    # these is that call with `effect` filled in, so there is one mechanism
    # wearing four faces and `transport=` composes with each.
    #
    # Four rather than five: nondeterministicReadOnly is not here because a
    # generator IS nondeterministic and the registration already decides that
    # from the function itself, lifting a read-only class to it. Declaring it
    # by hand would be restating what the library worked out.

    def _classified(
        self, fn: Callable | None, effect: EffectClass, options: dict[str, Any]
    ) -> Any:
        """`op` with the effect filled in.

        Used bare or called. The branch is here rather than at each of the four: `op` is overloaded
        on whether the callable is present, so handing it an optional one
        satisfies neither overload.
        """
        if fn is None:
            return self.op(effect=effect, **options)
        return self.op(fn, effect=effect, **options)

    def pure(self, fn: Callable | None = None, /, **options: Any) -> Any:
        """An operation whose answer depends only on its arguments.

            @m.pure
            def double(x: int) -> int:
                return 2 * x

        The cache-safe class, and the only one memoization and tabling admit
        without an explicit policy.

        A GENERATOR written this way is lifted to `nondeterministicReadOnly`,
        because a generator is nondeterministic whatever it declares, and the
        registration reads that off the function rather than asking. The lift
        only ever raises the rank, so it widens the answer-count claim and
        never weakens the effect claim -- but it does mean a generator is not
        cache-safe, which is the whole reason it is lifted out of this class
        [tested: test_a_generator_is_lifted_to_the_nondeterministic_rank;
        commit=7e5091540a8dc0903bcee24f3e5b8b85a19f805f].

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        """
        return self._classified(fn, EffectClass.pureStructural, options)

    def reads(self, fn: Callable | None = None, /, **options: Any) -> Any:
        """An operation that reads stable state without changing it.

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        """
        return self._classified(fn, EffectClass.readOnlyLookup, options)

    def writes(self, fn: Callable | None = None, /, **options: Any) -> Any:
        """An operation that changes engine or host state.

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        """
        return self._classified(fn, EffectClass.writesState, options)

    def io(self, fn: Callable | None = None, /, **options: Any) -> Any:
        """An operation that observes an external oracle.

        A clock, randomness, a network, a file, another runtime.

            @m.io
            def now() -> float:
                return time.time()

        The fail-closed top of the lattice. Declare it when what the operation
        reaches is decided at run time or by a library the engine cannot bound.

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        """
        return self._classified(fn, EffectClass.oracleIO, options)

    def unregister_op(self, name: str) -> None:
        """Remove a registered operation, every arity of it.

        An absent name raises KeyError, as convert.unregister_type does:
        removing something that was never there is a mistake worth hearing
        about, not a no-op to absorb.
        """
        _ops_module.unregister(self._rt, name)
        _invalidate_builtins_cache(self._rt)

    # -------------------------------------------------------------- inspection

    def builtins(self) -> list[str]:
        """Every registered function and translator special-form name."""
        return _space_builtins(self._rt, str(self._space))

    def _invalidate_builtins(self) -> None:
        """Discard cached catalogues after an engine-side mutation."""
        _invalidate_builtins_cache(self._rt)

    def _warn_deprecated(self, name: str, *, stacklevel: int) -> None:
        """Warn from the caller's frame when the catalog retires ``name``."""
        declaration = _deprecation(self._rt, name)
        if declaration is None:
            return
        since, remedy = declaration
        warnings.warn(
            f"{name} is deprecated since {since}; {remedy}",
            DeprecationWarning,
            stacklevel=stacklevel,
        )

    def is_function(self, name: str) -> bool:
        """Report whether a function is visible from this space."""
        _require_name(name, "is_function")
        return bool(self._rt.once("metta_py_is_function(Name)", Name=name))

    def _is_catalogued(self, name: str) -> bool:
        """Point membership in the builtins catalogue, no list build."""
        return bool(self._rt.once("metta_py_catalogue_member(Name)", Name=name))

    def is_function_here(self, name: str) -> bool:
        """Whether a function would answer from THIS space: it has clauses
        this space's module sees, its own or the shared ones in user.
        Another space's equations are invisible here and do not count.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _require_name(name, "is_function_here")
        return bool(
            self._rt.once(
                "metta_py_function_visible(Space, Name)", Space=self._space, Name=name
            )
        )

    def arities(self, name: str) -> list[int]:
        """Compiled predicate arities for a name: MeTTa arity plus one each."""
        row = self._rt.once("metta_py_arities(Name, As)", Name=name)
        return list(row.get("As", []))

    def _disassemble(self, name: str) -> str:
        """The Prolog clauses a function name compiled to, dis for the
        translator: one listing per registered arity, resolved in this
        space's module. What the engine RUNS for a call, which is the
        debuggability bytecode has and homoiconicity alone does not
        give, since (= ...) atoms are the source, not the compilation.
        Also reachable as m.fn[name].compiled.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _require_name(name, "disassemble")
        row = self._rt.once(
            "metta_py_disassemble(Space, Name, Text)", Space=self._space, Name=name
        )
        if not row:
            msg = (
                f"{name!r} has no compiled clauses here; is_function() "
                f"tells whether the engine knows the name at all"
            )
            raise MettaError(
                msg
            )
        return str(row["Text"])

    def register_prolog(
        self,
        source: str | None = None,
        *,
        path: str | os.PathLike[str] | None = None,
        names: _abc.Sequence[str] | _abc.Mapping[str, str] = (),
    ) -> tuple[str, ...]:
        """Register Prolog predicates as MeTTa functions, at native speed.

        This is the extension point for a library that wants to run fast.
        op() is the one most people find first, and every call it
        serves crosses the janus boundary: 25.16 inferences and 2.34us per
        call, against 7.16 inferences and 0.13us for the same operation
        written in Prolog [measured 2026-08-15, 3000 calls in one harness].

        Read the microseconds, not the inferences. The crossing counts as ONE
        inference and costs real time, so inferences say a Python operation is
        3.1x a Prolog one while wall clock says 18x. That is a fine price for
        reaching NumPy or an LLM and a bad one for arithmetic in a loop.

        A registered predicate keeps its nondeterminism: one that offers three
        solutions gives the MeTTa function three answers.

        A predicate follows the compiled calling convention, inputs first and
        one output last:

            m.register_prolog(
                "'vec-dot'(A, B, Out) :- ... .",
                names=["vec-dot"],
            )
            m.eval("(vec-dot (1 2) (3 4))")[0]

        or, for a library shipping a file beside its Python:

            m.register_prolog(path=Path(__file__).parent / "fast.pl",
                              names=["vec-dot", "vec-norm"])

        Every name is registered explicitly rather than discovered, because
        registering a name whose predicate is absent records no arity and then
        compiles every call to it into a partial application instead of
        failing, which is a silent wrong answer rather than an error. This
        raises instead: a name with no predicate behind it is refused before
        it can do that.

        The refusals are the engine's, through check_prolog_function_names/3
        and import_prolog_functions/2, so this and the MeTTa spelling enforce
        one rule rather than two copies of it. Three names are refused: one
        with no predicate behind it, a builtin, and a special form.

        Nothing is registered unless every name can be, so a typo in the list
        changes nothing. The consulted SOURCE does stay loaded on failure,
        which is deliberate rather than overlooked: loading it again is the
        retry, and it is idempotent, since the source is identified by a hash
        of its own content.

        **This is a method on a space and it registers PROCESS-WIDE.** So do
        op and define. Only equations are space-scoped, so an anonymous
        space() isolates one of the three things you can register and
        shares the other two. That is deliberate rather than overlooked: a
        Prolog predicate lives in `user`, every space has to be able to call
        it, and a library loaded inside a named space would define itself
        where the registration could not see it. The method sits on the space
        because that is where the rest of the surface is, not because the
        registration is scoped to it.

        The name is owned by one tier. A second registration of the same name
        from another tier is refused, in both directions, naming the owner, so
        two libraries cannot silently take the same name from each other.

        A parameter a MeTTa caller should reach unevaluated needs a type
        declaration, which this call does not take yet:

            m.register_prolog("'shape-of'(A, Out) :- Out = [shape, A].",
                              names=["shape-of"])
            m.run("(: shape-of (-> Atom Atom))")
            m.eval("(shape-of (+ 1 2))")[0] # (shape (+ 1 2)), not (shape 3)

        Declare it BEFORE anything calls the function. A call site compiled
        while the declaration is absent keeps evaluating the argument even
        after it lands.
        """
        if (source is None) == (path is None):
            msg = "register_prolog takes exactly one of source or path"
            raise ValueError(
                msg
            )
        if isinstance(names, _abc.Mapping):
            registered = self._register_renamed(path, names)
            _invalidate_builtins_cache(self._rt)
            return registered
        for name in names:
            _require_name(name, "register_prolog")
        wanted = [str(name) for name in names]

        # Before the source loads, not after. Consulting a file that defines a
        # builtin's name has already replaced the engine's static predicate by
        # the time a per-name refusal could fire, so refusing afterwards left
        # (+ 1 2) answering the library's answer while this call reported the
        # registration as refused.
        if wanted:
            self._rt.must(
                "check_prolog_function_names(Names, Source, _)",
                Names=wanted,
                Source=_source_identity(source, path),
            )

        declares = "exports" if wanted else self._require_a_declaration(source, path)

        origin = self._load_prolog_source(source, path)

        # A source carrying its own :- metta_export/1 has already registered
        # by now, through the load, so a caller who declared in the file
        # passes no names at all.
        if not wanted:
            # An extension that exports nothing registers nothing, and that is
            # the shape of a provider: it contributes clauses to a seam.
            if declares == "extension":
                _invalidate_builtins_cache(self._rt)
                return ()
            registered = self._declared_exports(origin)
            _invalidate_builtins_cache(self._rt)
            return registered

        # One goal, so the engine validates every name before it registers any:
        # a typo in the third name used to leave the first two registered and
        # callable, with the list of what had taken dying inside the exception.
        # The rule lives there rather than here, so this and the MeTTa spelling
        # cannot drift apart.
        self._rt.must("import_prolog_functions(Names, _)", Names=wanted)
        _invalidate_builtins_cache(self._rt)
        return tuple(wanted)

    def _require_a_declaration(self, source: str | None, path: Any) -> str:
        """What this source declares, read BEFORE it loads.

        It used to be consulted first and checked after, so a provider file
        with no declaration raised and installed the provider anyway: catching
        the error made everything work, which is the one outcome that teaches
        an author to ignore an error.

        All three routes are named, because pointing only at `metta_export` is
        a dead end for a provider author, who has no functions to export.
        """
        goal, inputs = (
            ("metta_py_source_declares(Source, Declares)", {"Source": os.fspath(path)})
            if path is not None
            else ("metta_py_string_declares(Text, Declares)", {"Text": str(source)})
        )
        declares = str(self._rt.must(goal, **inputs)["Declares"])
        if declares == "nothing":
            msg = (
                "register_prolog needs one of three things: the names to "
                'register, a :- metta_export("...") declaration for a '
                "source that defines functions, or a "
                ":- metta_extension(name, []) declaration for one that "
                "contributes clauses to a seam and exports nothing, such "
                "as a space provider. Discovering the names would "
                "silently register whatever else the source defines"
            )
            raise ValueError(
                msg
            )
        return declares

    def _register_renamed(
        self, path: Any, renames: _abc.Mapping[Any, Any]
    ) -> tuple[str, ...]:
        """Import a Prolog module's exports under names of your choosing.

        The one collision a name refusal cannot fix is two libraries that both
        export `norm/2`: neither is wrong and neither can be asked to change.
        SWI has resolved it for thirty years with a renaming import list, and
        this is that, so the second library arrives as `libb-norm` and neither
        is rebound. Without it SWI refuses the second import, prints "No
        permission to import ... (already imported from ...)" and continues,
        leaving the newcomer silently bound to the incumbent's code.

        The arity comes from the module's own export list, so a rename names
        only the two names, and a name the module does not export is refused
        with the list of what it does export.
        """
        if path is None:
            msg = (
                "renaming imports a Prolog MODULE, which SWI's import list "
                "names as a file, so it needs path= rather than source="
            )
            raise ValueError(
                msg
            )
        pairs = []
        for exported, metta_name in renames.items():
            _require_name(exported, "register_prolog")
            _require_name(metta_name, "register_prolog")
            pairs.append([str(exported), str(metta_name)])
        wanted = [pair[1] for pair in pairs]
        # Before the load, for the reason the unrenamed path documents.
        self._rt.must(
            "check_prolog_function_names(Names, Source, _)",
            Names=wanted,
            Source=os.fspath(path),
        )
        self._rt.must(
            "use_module_global(File, Renames)",
            File=os.fspath(path),
            Renames=pairs,
        )
        self._rt.must("import_prolog_functions(Names, _)", Names=wanted)
        return tuple(wanted)

    def _load_prolog_source(self, source: str | None, path: Any) -> str:
        """Load the source and answer the name the engine knows it by."""
        if path is not None:
            source_path = os.fspath(path)
            if not Path(source_path).is_file():
                msg = f"no Prolog source at {source_path!r}"
                raise SourceNotFound(msg)
            self._rt.consult(source_path)
            return source_path
        # The name the load runs under, not a constant. A declaration inside
        # the source records itself under prolog_load_context/2's answer, which
        # for a stream load is this module name, so asking under any other name
        # found nothing and a source declaring its own exports inline was told
        # it had declared none.
        module = _inline_module_name(str(source))
        self._rt.consult(module, data=str(source))
        return module

    def _declared_exports(self, origin: str) -> tuple[str, ...]:
        row = self._rt.must("metta_py_declared_exports(Source, Names)", Source=origin)
        declared = tuple(str(name) for name in row.get("Names", []))
        if not declared:
            msg = (
                "register_prolog needs the names to register, or a "
                ':- metta_export("...") declaration in the source. '
                "Discovering them would silently register whatever else "
                "the source defines"
            )
            raise ValueError(
                msg
            )
        return declared

    def register_foreign_library(
        self,
        path: str | os.PathLike[str],
        *,
        entry: str | None = None,
        names: _abc.Sequence[str] = (),
    ) -> tuple[str, ...]:
        """Load a compiled `.so` and register its predicates as MeTTa functions.

        The C tier is the cheapest one on this page's cost table, one
        inference per call, and reaching it used to mean hand-writing two
        Prolog directives into `register_prolog`:

            m.register_foreign_library(Path(__file__).parent / "cbump.so",
                                       entry="install_cbump", names=["c-bump"])

        `entry` is the C initialiser, `install_cbump` in
        `install_t install_cbump(void)`; leave it out for a library whose
        entry is plain `install`.

        The path is resolved to an ABSOLUTE one here, which is the trap this
        exists to close: `use_foreign_library/2` accepts a path relative to
        the working directory, resolves it, and SWI deprecates that and warns
        on every load, so a library that shipped one worked from the repo root
        and warned or failed anywhere else. A file that is not there is
        refused here rather than inside the engine's loader.

        Everything after the load is `register_prolog`, so the same refusals
        apply: a name with no predicate behind it, a builtin, a special form,
        and a name another tier owns.
        """
        # resolve() rather than abspath(), which is the ruff-suggested spelling
        # and the better one here: the path is embedded in the use_foreign_library
        # goal below, so following a symlink to the real object is what the
        # loader wanted anyway.
        resolved = str(Path(os.fspath(path)).resolve())
        if not Path(resolved).is_file():
            msg = f"no compiled library at {resolved!r}"
            raise SourceNotFound(msg)
        load = (
            f"use_foreign_library('{resolved}')"
            if entry is None
            else f"use_foreign_library('{resolved}', {entry})"
        )
        return self.register_prolog(
            f":- use_module(library(shlib)).\n:- {load}.\n", names=names
        )

    def register_library_path(self, directory: Any, name: str) -> None:
        """Point MeTTa at a directory of files your package ships.

            # in your package's __init__
            m.register_library_path(Path(__file__).parent / "prolog", "pettorch")

        Subject first, as every register_* call: the directory being
        registered, then the library name it serves.

        `(library pettorch fast.pl)` then resolves, from MeTTa and from
        `register_prolog(path=...)`. Without it a pip-installed library is
        under neither `<engine>/../lib` nor a git checkout, so it has to pass
        absolute paths and compute them from `__file__` by hand.

        This is SWI's own `file_search_path/2`, so an alias registered here is
        one every SWI tool already understands, and aliases compose: the
        second argument of one may be another alias. Registering the same
        directory twice is a no-op; a directory that is not there is refused
        here rather than at the first import that needs it.
        """
        _require_name(name, "register_library_path")
        self._rt.must(
            "register_metta_library_path(Alias, Directory, _)",
            Alias=str(name),
            Directory=os.fspath(directory),
        )

    def unregister_prolog(self, extension: str) -> tuple[str, ...]:
        """Release everything one extension registered, and its clauses.

        The unit is the extension, not the name. `register_prolog` used to
        load a bunch of loose predicates: the engine recorded that each name
        was a function and nothing at all about the library it came from, so
        there was no uninstall to write and a partly-failed registration left
        debris nobody could enumerate.

            :- metta_extension(pettorch, [version('0.3.1')]).
            :- metta_export("(: vec-dot (-> Number Number Number))").

            m.register_prolog(path="fast.pl")     # names come from the file
            m.unregister_prolog("pettorch")       # everything it installed

        PostgreSQL's rule, and its reason: an individual member cannot be
        dropped on its own, only the whole extension, which is what stops one
        registry keeping a claim on a name another route already replaced.
        The clauses go too, through SWI's own `unload_file/1`, so a name is
        not left callable through a predicate nothing records.

        Answers the names it released. Raises when no extension of that name
        is loaded, rather than reporting success for a no-op.
        """
        _require_name(extension, "unregister_prolog")
        released = self._rt.must(
            "metta_py_extension_members(Name, Names)", Name=str(extension)
        )
        names = tuple(str(name) for name in released.get("Names", []))
        self._rt.must("metta_py_unregister_extension(Name)", Name=str(extension))
        _invalidate_builtins_cache(self._rt)
        return names

    # ----------------------------------------------------------- subscriptions

    def subscribe(
        self,
        pattern: Any,
        callback: Callable | None = None,
        *,
        on: str = "add",
        where: Any | None = None,
        queue_max: int | None = None,
    ):
        """A standing query on this space: every added (or removed, or
        both) atom unifying with the pattern becomes an Event.

            seen = []
            sub = m.subscribe(S.order(V.id), lambda e: seen.append(e))
            m.add(S.order(1))          # seen[0].bindings["id"] == 1
            sub.cancel()

        With a callback, delivery is synchronous. An unscoped write delivers
        before it returns; a transaction delivers its ordered segment only
        after the complete commit, while rollback and speculation deliver
        nothing. The callback may write back; the engine re-enters cleanly,
        and an infinite add-triggers-add loop is the author's own.
        Without one, events queue on the subscription and drain() empties
        them: the mailbox reading. That queue is bounded by `queue_max`,
        and a write arriving at a full queue raises SubscriberError rather
        than discarding the oldest event: nobody draining is a bug in the
        consumer, and a silently shortened history is how it stays hidden.
        A removal event fires only when something was removed, and carries
        the pattern that was asked for rather than the occurrence that
        left. The two are the same atom for a ground removal and differ
        for a pattern one: removal is multiset subtraction, so
        `remove(S.alert(V.q))` takes one of the alerts and the event
        cannot say which. Re-read the space when you need to know;
        `metta.structures.LiveView` is the worked instance.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        subscriptions = _satellite("subscribe")
        guard = None if where is None else guard_atom(where)
        if where is not None and guard is None:
            msg = f"where= is a term the engine evaluates per event, got {where!r}"
            raise TypeError(msg)
        return subscriptions.subscribe(
            self._rt,
            self._space,
            _to_atom(pattern),
            callback,
            on,
            queue_max=(
                subscriptions.SUBSCRIPTION_QUEUE_MAX
                if queue_max is None
                else queue_max
            ),
            # The guard becomes ONE admission test over the event, built by
            # the module that owns the instantiation and given this space's
            # own evaluation door, so a guard means on an event exactly what
            # it means on a match.
            admits=(
                None
                if guard is None
                else subscriptions.guard_admits(guard, self.eval)
            ),
        )

    def _event_stream(self) -> Any:
        """This engine's stream of `(action, space, atom)` changes.

            seen = m.events().fold(
                lambda held, event: [*held, event.atom],
                space=m.name, pattern=S.order(V.id), state=[],
            )
            m.add(S.order(1))
            seen.take()          # [(order 1)], and the fold starts again

        The stream is the primitive and a FOLD over it is how anything
        consumes it: a step `(state, event) -> state` run immediately for an
        unscoped write or after the whole transaction commits. subscribe() is
        the fold whose step delivers, bridge() the fold whose step writes, and
        a declared `(on ...)` reaction the fold whose step evaluates, so a
        consumer you write and one this library ships are the same kind of
        thing.
        """
        return _satellite("events").stream(self._rt)

    def prolog(self) -> None:
        """Drop into the engine's own interactive Prolog toplevel, the
        deepest debugging lever there is: listing/1 shows compiled
        equations, trace/0 steps through them, and quitting the toplevel
        returns here with the session intact. janus's own janus.prolog(),
        surfaced where the debugging happens.

        This is the only Prolog-facing surface here besides register_prolog,
        and that is a decision rather than a gap. There is no public
        "call any Prolog goal" method: the supported way to reach your own
        Prolog from Python is to register it and call it as a MeTTa function,
        which keeps one set of conversion rules, one error taxonomy and one
        lock. A raw goal is janus's job and janus is importable directly.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self._rt._janus.prolog()

    # ------------------------------------------------------------- diagnostics

    def derivation(
        self,
        target: Any,
        depth: int | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[Any]:
        """Every proof of an answer, as trees in MeTTa terms.

        Each tree names the equations that fired and the stored atoms at the
        leaves, read from the translated_from links the engine keeps for
        every compiled clause. Meta-interpreted, so slower than evaluation;
        a diagnostic, not an evaluation path. The default walks each proof
        without a depth cutoff. A positive depth returns a partial tree with
        Truncated nodes when its budget ends, so an empty list means no proof.
        `timeout` and `inferences` guard the whole search. An evaluation error
        inside a proof surfaces as itself rather than as an empty proof list.

        A `bind()` scope binds host values into the term, for the reason
        eval_status needs it: the substitution lands BEFORE the search, so the
        proof of an evaluation that binds anything was unaskable. Name keys
        mean symbols and atom keys mean themselves, so `bind({V.x: 5})` fills
        a variable hole. It takes no `theory` or
        `interpreter`, because a meta-interpreted diagnostic does not select an
        evaluation relation.
        """
        target, using = self._prepared_ask(target, None)
        diagnostics = _importlib.import_module(f"{__package__}._space_diagnostics")
        return diagnostics.derivations(
            self._rt,
            self._space,
            _substituted(target, using) if using else target,
            depth,
            timeout=timeout,
            inferences=inferences,
        )

    def why(self, pattern: Any, *, where: Any | None = None) -> str:
        """Why a pattern matches nothing here, in words.

        Checks the cheap explanations in order: unknown function, wrong
        arity, no stored atoms with that head. Honest when it cannot tell,
        and honest about the PREMISE too: a pattern that does match is a
        question with a false premise, and this refuses it the way
        Answers.why() always did rather than answering it. Asking why
        `(job $id $pri)` matched nothing, when it matches two atoms, used to
        answer "2 job atom(s) exist here but none unifies with it"
        [measured 2026-08-31].

        `where` is match()'s guard, and asking with one is where the answer
        gets interesting: a query can be empty because the pattern found
        nothing OR because the guard rejected everything it found, and only
        the guarded question can tell you which.

        One implementation, because there were two and they agreed word for
        word on every genuine miss while disagreeing about the premise.
        """
        return self.match(pattern, where=where).why()

    # ------------------------------------------------------------ definitions

    @overload
    def define(  # type: ignore[overload-overlap]
        self,
        fn: _builtins.type,
        /,
        *,
        accessors: bool = ...,
        methods: bool = ...,
    ) -> _builtins.type: ...

    @overload
    def define(
        self,
        fn: Callable[_P, _R],
        /,
        *,
        name: str | None = ...,
        accessors: bool = ...,
        methods: bool = ...,
    ) -> Defined[_P, _R]: ...

    @overload
    def define(
        self, *, name: str
    ) -> Callable[[Callable[_P, _R]], Defined[_P, _R]]: ...

    @overload
    def define(
        self, *, prolog: str | os.PathLike[str], name: str | None = None
    ) -> Callable[[Callable[_P, _R]], PrologBacked[_P, _R]]: ...

    def define(
        self,
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

        This is rung 4 of the naming ladder applied to the definition door
        itself: ``def not_provable`` lands as ``not-provable``. An authored
        MeTTa underscore therefore uses explicit ``name="not_provable"``.

        A generator compiles to nondeterminism (each yield one answer), a
        lambda to the engine's own |->, a comprehension to map-atom and
        filter-atom, and match(Pattern(x, y), template) to a match against
        the running space, lowercase free names in the pattern binding as
        variables.
        """
        if isinstance(fn, type):
            if prolog is not None or name is not None:
                msg = "define on a class does not take name= or prolog="
                raise TypeError(msg)
            return install_type(self, fn, accessors=accessors, methods=methods)
        if prolog is not None:
            if fn is not None:
                msg = (
                    "define(prolog=...) is applied as a decorator, so the "
                    "function comes from the definition below it"
                )
                raise TypeError(
                    msg
                )
            return lambda function: install_prolog_define(self, function, prolog, name)
        if fn is None:
            if name is None:
                msg = "define takes a function or class, or name= or prolog= and then one"
                raise TypeError(msg)
            return lambda function: install_define(self, function, name)
        # The annotation widened to Callable so the overloads can carry the
        # decorated signature through. install_definition still refuses
        # anything without Python source, which is where the narrowing the
        # annotation used to imply is actually enforced
        # [tested test_define_refuses_callable_objects].
        return install_define(self, fn, name)

    def rules(self, fn: Callable[..., Any]) -> _Rules:
        """Collect and land a non-exclusive equation bundle in this space."""
        bundle = _collect_rules(fn)
        self += bundle
        return bundle

    def pre_add(self, fn: Defined[..., Any] | Callable[..., Any]) -> Defined[..., Any]:
        """Compile or accept one unary judge and claim this space's write door.

        The common decorator stack places ``@pre_add`` above ``@define``, so
        an existing Defined keeps the module that owns its equations. A raw
        function is compiled into this space before claiming the hook.
        """
        handler = fn if isinstance(fn, Defined) else self.define(fn)
        if len(handler.params) != 1:
            msg = "a pre-add judge takes exactly one incoming atom"
            raise TypeError(msg)
        handler.space.eval(
            Expression(
                [Symbol("declare-pre-add!"), self, Symbol(handler.name)]
            )
        )
        return handler

    def type(self, atom: Any) -> Atom:
        """Return this space's first ``get-type`` answer, including undefined."""
        answers = self.eval(Expression([Symbol("get-type"), _to_atom(atom)]))
        if not answers or not isinstance(answers[0], Atom):
            msg = f"get-type returned no type for {atom!r}"
            raise EngineError(msg)
        return answers[0]

    def doc(self, atom: Any) -> Atom:
        """Return this space's structured ``get-doc`` answer for one subject.

        The answer is the ``(@doc ...)`` atom the engine holds for the
        subject, whether it was documented in MeTTa source or built from a
        Python docstring:

            m.doc(S.area)
            # (@doc-formal (@item area) (@kind function) (@desc "Circle area.") ...)

        A subject with no documentation raises, exactly as ``type`` raises
        for a subject ``get-type`` cannot answer.
        """
        answers = self.eval(
            Expression([Symbol("get-doc"), _to_atom(self), _to_atom(atom)])
        )
        if not answers or not isinstance(answers[0], Atom):
            msg = f"get-doc returned no documentation for {atom!r}"
            raise EngineError(msg)
        return answers[0]

    @property
    def fn(self) -> _FunctionNamespace:
        """Functions visible here, as bound attribute or exact-name handles.

            car = m.fn.car_atom
            car(m.parse("(1 2 3)"))     # [1]
            m.fn["=="](1, 1).one()      # True

        Underscores transliterate to hyphens. Brackets preserve exact
        punctuation, and an unknown name raises at access rather than
        becoming a later empty evaluation.
        """
        return _FunctionNamespace(self)

    # ---------------------------------------------------------- integrations

    def integrate(self, target: Any) -> str:
        """Install a library integration; see metta.integrate."""
        return _satellite("integrate").integrate(self, target)

    def _register_space(self, provider: Any, name: str) -> Any:
        """A space answered by Python: matches, adds and removals route to
        the provider, so a table, a dataframe or a service is matchable the
        way stored atoms are. See metta.foreign.SpaceProvider.

        Subject first, as every register_* call: the thing being
        registered, then where it lives. The two calls that named the
        name first were the surface's own inconsistency, and learning
        the order from op raised TypeError here.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _satellite("foreign").register_provider(self._rt, name, provider)
        return provider

    def _unregister_space(self, name: str) -> None:
        """Remove a registered Python-backed space."""
        _satellite("foreign").unregister_provider(self._rt, name)

    def handles(
        self,
        pattern: str | Atom,
        fidelity: Fidelity,
        *,
        det: Determinism | None = None,
    ) -> Atom:
        """Declare how faithfully a space answers queries of one shape.

        The declaration is one (handles ...) atom in &metta, and queries
        are routed by the most specific declared shape that matches:
        Exact licenses pushing the caller's bound to the provider, Partial
        and Sound stay candidates the engine re-unifies, and Refuse makes
        the query a loud error instead of a silent partial answer. Write
        (in $x) at a position to match only queries arriving with it
        bound, so a scan-only source is three words:

            rows.handles("(edge (in $a) $b)", "Refuse")

        Coherence is checked eagerly in the same transaction as the
        write: a new entry that can disagree with an existing one on some
        query fails here, naming both, rather than on the first query
        that falls into their overlap. The atom is returned; removing it
        from &metta withdraws the declaration.
        """
        _require_vocabulary(
            fidelity, Fidelity, "fidelity",
            because="it is the declared claim the router acts on, so an "
            "unknown word would silently declare nothing",
        )
        if det is not None:
            _require_vocabulary(
                det, Determinism, "det",
                because="the same vocabulary declare_function_determinism uses everywhere else",
            )
        shape = _to_atom(pattern)
        children = [Symbol("handles"), Symbol(str(self.name)), shape, Symbol(fidelity)]
        if det is not None:
            children.append(Symbol(det))
        atom = Expression(children)
        self._rt.must(
            "metta_py_declare_handles(Space, W, Ctx)",
            Space="&metta",
            W=atom.to_wire(),
            Ctx=str(self.name),
        )
        return atom

    def annotations(
        self,
        subject_or_algebra: str,
        algebra: str | None = None,
        *,
        capabilities: _abc.Iterable[str] = (),
    ) -> Atom:
        """Declare the algebra a context's answer annotations live in.

        A context is a space name or an operation name. bool is the
        default at which everything vanishes; ranked admits ordered
        annotations, which is what (top k ...) consumes. A custom name must
        first be introduced with :meth:`algebra`. A one-argument call uses
        this space as the context; the two-argument form keeps an operation
        context as the explicit first subject. Capabilities are
        checked against the algebra's requirements before the catalog write;
        amplitude programs, for example, must explicitly declare ``finite``,
        ``contractive`` and ``staged`` [tested:
        test_amplitudes_interfere_inside_the_fragment_and_are_refused_outside;
        commit=f88aa8be03cb64cb59d3307515ded8701f418321]. Declaring replaces any earlier row for the
        context, so the reader never meets two disagreeing atoms.
        """
        name = self.name if algebra is None else subject_or_algebra
        algebra = subject_or_algebra if algebra is None else algebra
        algebra_api = _satellite("algebra")
        declaration = algebra_api.require(self, algebra)
        declared_capabilities = frozenset(capabilities)
        missing = declaration.requires - declared_capabilities
        if missing:
            refusal = (
                "amplitude_fragment_refused"
                if algebra == "amplitude"
                else "algebra_requirements_missing"
            )
            msg = f"{refusal}({name}, {algebra}, missing={sorted(missing)!r})"
            raise algebra_api.AlgebraRequirementError(msg)
        catalog = Space("&metta", _runtime=self._rt)
        for previous in catalog.atoms():
            if (
                isinstance(previous, Expression)
                and len(previous.children) >= 3
                and previous.children[0] == Symbol("annotations")
                and previous.children[1] == Symbol(str(name))
            ):
                catalog.remove(previous)
        children: list[Atom] = [
            Symbol("annotations"),
            Symbol(str(name)),
            Symbol(algebra),
        ]
        if declared_capabilities:
            children.append(
                Expression(
                    [
                        Symbol("capabilities"),
                        *(Symbol(capability) for capability in sorted(declared_capabilities)),
                    ]
                )
            )
        atom = Expression(children)
        catalog.add(atom)
        return atom

    def algebra(
        self,
        name: str,
        *,
        combine: str,
        extend: str,
        zero: Any,
        one: Any,
        laws: _abc.Iterable[str] = (),
        carrier: _abc.Iterable[Any] = (),
        requires: _abc.Iterable[str] = (),
        order: SemiringOrder | None = None,
    ) -> Atom:
        """Declare operations and checked laws for an arbitrary atom carrier.

        Public laws are certificates, not wishes. When an equational law is
        named, ``carrier`` must be finite and the operation tables are checked
        exhaustively before the catalog atom lands. ``contraction`` is the
        explicit resource-reuse capability and has no equation to sample.
        """
        return _satellite("algebra").declare(
            self,
            name,
            combine=combine,
            extend=extend,
            zero=zero,
            one=one,
            laws=laws,
            carrier=carrier,
            requires=requires,
            order=order,
        )

    def _replace_catalog_declaration(
        self,
        head: str,
        keys: tuple[Atom, ...],
        values: tuple[Atom, ...],
        *,
        supersedes: tuple[int, ...] = (),
    ) -> Atom:
        """Replace every catalog row this declaration supersedes, atomically.

        A row is `(<head> <key>... <value>...)`. The keys say WHICH row this
        is and the values say what it declares, both are passed, and the
        stored atom is built HERE, so the retract pattern and the atom that
        replaces it cannot disagree about the head or the key. They could
        before: a caller passed the head, the key and the whole atom
        separately and nothing checked the first two occurred in the third.
        `image` did disagree, passing its two key atoms as one nested pair,
        which built `(image (<space> <type>) $previous)` against a flat row,
        matched nothing, and left every previous row standing.

        Both halves of the replacement are load-bearing and both were got
        wrong by the doors that wrote this longhand instead of calling here.
        The removal LOOPS, because `metta_py_remove` takes one occurrence and
        a catalog that somehow holds two rows for one subject would keep the
        stale one: measured 2026-08-31, a second `(emits &s fair)` row
        survived a redeclaration and left the engine reading two policies for
        one space. And it runs in a TRANSACTION, because a failure between the
        remove and the add leaves the declaration missing rather than
        unchanged.

        How many trailing slots a superseded row has is `len(values)`, so no
        caller states it. ``supersedes`` names EXTRA counts, for a declaration
        whose own shape grew: `agenda` supersedes both the three-element form
        and the four-element one that names a function, whichever it writes.
        """
        atom = Expression([Symbol(head), *keys, *values])
        shapes = [
            Expression(
                [Symbol(head), *keys,
                 *(Variable(f"previous{slot}") for slot in range(count))]
            )
            for count in {len(values), *supersedes}
        ]

        def replace() -> Atom:
            for previous in shapes:
                while True:
                    removed = self._rt.apply_must(
                        "metta_py_remove",
                        "&metta",
                        previous.to_wire(),
                    )
                    result = _atom_from_wire(removed)
                    if not bool(getattr(result, "value", True)):
                        break
            self._rt.must(
                "metta_py_add(Space, W)",
                Space="&metta",
                W=atom.to_wire(),
            )
            return atom

        return self._at("&metta").transaction(replace)

    def covers(self, effect: EffectClass | str) -> Atom:
        """Declare the strongest effect this reified world can handle.

        Coverage is a catalog fact ``(covers <space> <effect>)``. World
        evaluation always admits pureStructural plans. A stronger joined plan
        runs only when this declaration is at least as strong; redeclaring
        replaces the previous row atomically.

            orders.covers("writesState")
            world = orders.reify()
        """
        declared = EffectClass(_require_vocabulary(effect, EffectClass, "effect"))
        subject = (
            self._name_atom
            if self._name_atom is not None
            else Symbol(str(self._space))
        )
        return self._replace_catalog_declaration(
            "covers", (subject,), (Symbol(str(declared)),)
        )

    def compensates(self, operation: str, compensation: str) -> Atom:
        """Declare one recovery operation for an effectful operation.

        The catalog row is ``(compensates operation compensation)``. The
        source operation must already be registered at writesState or
        oracleIO, because weaker operations leave no saga receipt. The
        recovery name must already be a host operation or compiled MeTTa
        function. It receives the complete ``(did ...)`` receipt. The runner writes
        the call as ``(quote <receipt>)`` so the receipt is not evaluated
        on the way in; the quote is a barrier and does not survive, so the
        handler is handed the receipt itself.
        Redeclaring replaces the old row atomically.
        """
        operation_name = str(operation)
        compensation_name = str(compensation)
        return self._replace_catalog_declaration(
            "compensates", (Symbol(operation_name),), (Symbol(compensation_name),)
        )

    def add_tagged_fact(self, tag: Any, proposition: Any) -> Atom:
        """Store ``(fact tag proposition)``, the normative annotation form."""
        atom = _satellite("algebra").tagged_fact(tag, proposition)
        self.add(atom)
        return atom

    def add_tagged_rule(self, tag: Any, head: Any, *premises: Any) -> Atom:
        """Store one rule generated by the algebra-agnostic tag threader."""
        atom = _satellite("algebra").tagged_rule(tag, head, *premises)
        self.add(atom)
        return atom

    def image(
        self,
        type_name: str,
        setting: ImageMode,
    ) -> Atom:
        """Choose how one Python type crosses one context boundary.

        opaque carries the live object by identity; transparent projects its
        structural MeTTa image; auto makes that choice from the value's size
        and replayability. A later declaration for the same context and type
        replaces the earlier one, so an attached provider reads one policy.
        Use ``_`` as the type name for a context-wide fallback.
        """
        _require_vocabulary(setting, ImageMode, "image setting")
        # Keyed on the TYPE as well as the space: one space declares an image
        # per type, so there are two key atoms.
        return self._replace_catalog_declaration(
            "image", (Symbol(str(self.name)), Symbol(type_name)),
            (Symbol(setting),)
        )

    def sample(
        self,
        query: str | Atom,
        *,
        k: int = 10,
        seed: int = 7,
    ) -> list[Atom]:
        """Choose ``k`` tagged alternatives with replacement by ``(rate n)``.

        The argument names and list result follow ``random.choices``. A local
        seeded generator makes repeated calls reproducible without changing
        Python's process-global random state.
        """
        return list(
            _satellite("algebra").sample(
                self,
                query,
                algebra="prob",
                draws=k,
                seed=seed,
            )
        )

    def source(
        self,
        kind: SourceKind,
    ) -> Atom:
        """Declare a space's consumption discipline.

        repeated is the default: the source re-enumerates. linear is a
        one-shot source, a cursor or a feed: its SECOND consumption is a
        loud error naming the space, where the undeclared floor answers a
        silently empty set from the drained object; re-registering the
        provider resets the mark, because a fresh provider is a fresh
        source. peek promises reads do not consume, which the conformance
        kit checks by enumerating twice.
        """
        _require_vocabulary(kind, SourceKind, "kind")
        return self._replace_catalog_declaration(
            "source", (Symbol(str(self.name)),), (Symbol(kind),)
        )

    def on_error(
        self,
        subject_or_pattern: str | Atom,
        pattern_or_mode: str | Atom,
        mode: OnError | None = None,
    ) -> Atom:
        """Declare what a context's failure becomes, per query shape.

        abort is the undeclared floor: the provider's error propagates.
        keep delivers the failure as one (Error <query> <reason>) answer
        beside the answers that already streamed, the language's own
        error-as-alternative reading. empty ends the stream silently, BY
        declaration, which is what separates it from a swallowed error.
        Shapes route most-specific-first exactly as (handles ...) entries
        do. Control signals and transport failures are never kept or
        emptied: an interrupt is the caller's, and an absent backend has
        said nothing about the data.
        """
        name = self.name if mode is None else subject_or_pattern
        pattern = subject_or_pattern if mode is None else pattern_or_mode
        chosen = str(pattern_or_mode) if mode is None else str(mode)
        _require_vocabulary(chosen, OnError, "mode")
        shape = _to_atom(pattern)
        atom = Expression([Symbol("on-error"), Symbol(str(name)), shape, Symbol(chosen)])
        self._rt.must(
            "metta_py_add(Space, W)", Space="&metta", W=atom.to_wire()
        )
        return atom

    def merge(
        self,
        pattern: str | Atom,
        policy: AnswerPolicy,
    ) -> Atom:
        """Declare how the engine merges one query shape's answers
        ACROSS contexts, for the multi-context idiom
        (match (superpose (&a &b)) ...).

        depth is today's space-after-space order and the undeclared
        floor. fair interleaves the streams round-robin. best-first is a
        k-way ordered merge by annotation, sound only when every merged
        context declares (emits <ctx> best-first), and loudly refused
        without. Shapes route most-specific-first as everywhere.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _require_vocabulary(policy, AnswerPolicy, "policy")
        shape = _to_atom(pattern)
        atom = Expression([Symbol("merge"), shape, Symbol(policy)])
        self._rt.must(
            "metta_py_add(Space, W)", Space="&metta", W=atom.to_wire()
        )
        return atom

    def context(
        self,
        world: World,
    ) -> Atom:
        """Record what a space's absence means.

        Negation as failure reads absence as falsity, which is only
        sound over a world the answerer holds whole, so a negated goal
        may consult a foreign space only when it declares closed-world;
        an undeclared one refuses under negation loudly. Native spaces
        are the engine's own database and closed by construction.
        """
        _require_vocabulary(world, World, "world")
        return self._replace_catalog_declaration(
            "context", (Symbol(str(self.name)),), (Symbol(world),)
        )

    def agenda(
        self,
        policy: AgendaPolicy,
        function: str | None = None,
    ) -> Atom:
        """Declare which reaction fires first when several match one write.

        declaration is the default and the order they were declared, which is
        what the engine produced by accident before this was a policy;
        recency is the most recently declared first; specificity is the most
        tests in the pattern first; priority reads each reaction's own
        declared number, highest first; and user names a MeTTa function that
        SCORES a reaction, highest first. Every policy breaks ties on
        declaration order.

            alarms.reacts("(alert $w)", "(insert &log (all $w))")
            alarms.reacts("(alert fire)", "(insert &log (fire))", priority=9)
            alarms.agenda("priority")
        """
        _require_vocabulary(policy, AgendaPolicy, "policy")
        if (policy == "user") != (function is not None):
            msg = (
                "the user policy names the MeTTa function that scores a "
                "reaction, and no other policy takes one"
            )
            raise ValueError(msg)
        values = [Symbol(policy)]
        if function is not None:
            values.append(Symbol(str(function)))
        return self._replace_catalog_declaration(
            "agenda", (Symbol(str(self.name)),), tuple(values), supersedes=(1, 2)
        )

    def reacts(
        self,
        pattern: str | Atom,
        operation: str | Atom,
        priority: int | None = None,
    ) -> Atom:
        """Declare a reaction, stored as an (on ...) atom: when an atom
        matching PATTERN lands in the space, OPERATION runs under the
        match's bindings.

        The managed heads are (insert <ctx> <atom>), (retract <ctx>
        <atom>) and (revise <ctx> <old> <new>), engine-routed rules
        going through the same write paths as direct writes. Declaring
        installs the engine's write hook, which is why reactions go
        through here or metta_install_bridges rather than a bare
        add-atom.

        A subscription bridge is the NEIGHBOUR, not a special case of this:
        a reaction's operation runs engine-side, so it reaches registered
        spaces, while the bridge rule delivers Python-side to anything
        with add and remove, an unregistered or remote target included.
        Same multi-context-systems idea, two delivery tiers.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        shape = _to_atom(pattern)
        op = _to_atom(operation)
        parts = [Symbol("on"), Symbol(str(self.name)), shape, op]
        if priority is not None:
            if not isinstance(priority, int) or isinstance(priority, bool):
                msg = f"priority is an integer, not {priority!r}"
                raise TypeError(msg)
            parts.append(Grounded(priority))
        atom = Expression(parts)
        self._rt.must(
            "metta_py_add(Space, W)", Space="&metta", W=atom.to_wire()
        )
        self._rt.must("metta_install_bridges")
        return atom

    def admits(self, type_name: str) -> Atom:
        """Type a pool's membership: only TYPE-carrying atoms enter.

        A thread pool is a space whose atoms are spaces, and this is its
        door: (admits &pool Space) plus per-atom (: <space> Space)
        declarations make membership a type judgement the ontology
        already knows how to make.
        """
        atom = self._replace_catalog_declaration(
            "admits", (Symbol(str(self.name)),), (Symbol(type_name),)
        )
        self._rt.must(
            "metta_admission_claim(Pool, Declarer)",
            Pool=str(self.name),
            Declarer=current_space(),
        )
        return atom

    def capacity(self, limit: int) -> Atom:
        """Bound a pool: an add beyond LIMIT atoms is refused loudly."""
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            msg = f"capacity is a positive integer, not {limit!r}"
            raise ValueError(msg)
        atom = self._replace_catalog_declaration(
            "capacity", (Symbol(str(self.name)),), (Grounded(limit),)
        )
        self._rt.must(
            "metta_admission_claim(Pool, Declarer)",
            Pool=str(self.name),
            Declarer=current_space(),
        )
        return atom

    def atomicity(
        self,
        atomicity: Atomicity,
    ) -> Atom:
        """Declare what a space's writes promise inside a transaction.

        Named for what it declares rather than for the atom it stores, which
        stays `(writes <ctx> ...)`: `writes` on a Space is the effect
        decorator for an OPERATION, and one object cannot spell two concepts
        one way.

        transactional providers implement metta.foreign.Transactional and
        are committed or rolled back WITH the engine's transaction;
        best-effort is the author's declared acceptance of a write that
        survives a rollback; atomic-single refuses transactional writes.
        Undeclared spaces refuse them loudly too, because a foreign write
        silently surviving a rolled-back transaction is the wrong answer
        the declaration exists to replace.
        """
        _require_vocabulary(atomicity, Atomicity, "atomicity")
        return self._replace_catalog_declaration(
            "writes", (Symbol(str(self.name)),), (Symbol(atomicity),)
        )

    def emits(
        self,
        policy: AnswerPolicy,
    ) -> Atom:
        """Declare the order a context emits its own answers in.

        best-first is the promise (top k ...) needs before its bound may
        reach the provider: the first k of a best-first emission ARE the
        k best. Distinct from the (merge <pattern> <policy>) strategy,
        which is how the ENGINE merges answers across several contexts.
        """
        _require_vocabulary(policy, AnswerPolicy, "policy")
        return self._replace_catalog_declaration(
            "emits", (Symbol(str(self.name)),), (Symbol(policy),)
        )

    def events(
        self,
        delivery: Delivery | None = None,
        order: EventOrder = EventOrder.unordered,
    ) -> Atom | Any:
        """Return the event stream, or declare what this context promises.

        Subscribability is a promise about the context, not something the
        seam reads off its methods. A native space needs no declaration:
        every write into it runs the engine's own hooks, so it delivers
        per-write-exactly and ordered by construction. A FOREIGN context
        declares, and one that declares nothing refuses a subscription
        instead of serving one that silently misses writes.

            shared.events("at-most-once")   # redis pub/sub
            mirror.events("per-write-exactly", "ordered")

        delivery is at-most-once, at-least-once or per-write-exactly, and
        order is ordered or unordered, defaulting to unordered because an
        omitted promise is the weaker one. A Python provider says the same
        thing by overriding delivers(), which registration writes here.
        """
        if delivery is None:
            return self._event_stream()
        _require_vocabulary(delivery, Delivery, "delivery")
        _require_vocabulary(order, EventOrder, "order")
        return self._replace_catalog_declaration(
            "events", (Symbol(str(self.name)),), (Symbol(delivery), Symbol(order))
        )

    # ------------------------------------------------------------ interop

    @property
    def runtime(self) -> Runtime:
        """The engine bridge itself, for callers going under the surface."""
        return self._rt

    @property
    def metta(self) -> MeTTa:
        """The owning evaluation context, so a handle can reach every
        context-level door: ``m.metta.space(S.kb)`` creates a sibling space
        in THIS handle's own context rather than the process default, which
        is the creation door the twins' known-issue asked for. The context
        BORROWS this handle's space as its home, so answering it mints
        nothing, and two answers compare equal because they share the
        runtime and the home.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return MeTTa(self)


def _release_abandoned_world(rt: Runtime, home: str) -> None:
    """The finalize backstop: best-effort, late-shutdown-safe."""
    with contextlib.suppress(Exception):
        rt.must("metta_py_release_space(Space)", Space=home)


class MeTTa:
    """One MeTTa evaluation context; context-relative operations use Space.

    ``MeTTa()`` is a fresh context, the way ``dict()`` is a fresh dict: it
    mints an anonymous space of its own as its home, so two contexts never
    see each other's atoms or equations, and it owns that space, releasing
    it on :meth:`close` or when a ``with`` block leaves. Passing a space
    (a ``Space``, an ``&name`` string, a ``Symbol``, or a parametric ground
    ``Expression``) makes the context a BORROWER of that space instead:
    ``MeTTa(Space())`` is the process-default context ``metta.engine()``
    answers, and closing a borrower never drops what the caller supplied,
    the way a file object built on someone else's descriptor leaves it open.
    ``&self`` is just the default home's name; within any context its own
    home plays that role.
    """

    __slots__ = ("__weakref__", "_finalizer", "_minted", "_owns_self", "_rt", "_self")

    def __init__(
        self,
        space: Space | Symbol | Expression | str | None = None,
        *,
        verbose: bool | None = None,
        metta_path: str | None = None,
        _runtime: Runtime | None = None,
    ) -> None:
        self._minted: list = []
        self._finalizer = None
        if isinstance(space, Space):
            # A borrowed home carries its runtime, and explicit options
            # still mean what they say: routing them through runtime()
            # applies verbose and raises on a conflicting metta_path,
            # exactly the one-engine contract that door documents. Silently
            # ignoring them was measured as accepting a conflicting engine
            # path and a dead verbose=True
            # [tested: test_a_borrowing_context_still_honors_its_options].
            if metta_path is not None or verbose is not None:
                runtime(metta_path=metta_path, verbose=verbose)
            self._rt = space.runtime
            self._self = space
            self._owns_self = False
            return
        self._rt = (
            runtime(metta_path=metta_path, verbose=verbose)
            if _runtime is None
            else _runtime
        )
        if space is None:
            home = Space(_DEFAULT_SPACE, _runtime=self._rt)
            # Minted as a WORLD: the home declares itself onto &self, so
            # spaces the program mints inside it (new-space included) read
            # its equations the way every default-world space reads &self's,
            # and close() can tear the whole world down as one unit.
            self._self = home._new_space(_equation_home=home)
            # Ownership transfer: the home's lifetime is this context's
            # close(), not any with-block entered on the space itself.
            self._self._autodrop = False
            self._owns_self = True
            # close() is the contract; the finalize backstop only covers an
            # ABANDONED context. It watches the HOME HANDLE, not this
            # context object, because the handle is what a caller keeps:
            # `MeTTa().self` leaves the context unreferenced while its home
            # is very much in use, and a backstop on the context released
            # that home into the free-name pool, where the next mint drew
            # the same name and tried to make it inherit from itself. A
            # resource may not die while a reference handed out of it lives
            # [tested: test_a_home_handle_outliving_its_context_keeps_the_world].
            self._finalizer = weakref.finalize(
                self._self, _release_abandoned_world, self._rt, self._self._space
            )
        else:
            self._self = Space(space, _runtime=self._rt)
            self._owns_self = False

    def close(self) -> None:
        """Release the context's own home space; closing twice is a no-op.

        A borrowed home, the process default included, is the caller's
        and survives; only a home this context minted is dropped, and the
        drop takes the whole world with it: every space minted inside the
        context, by this object or by the program's own new-space, is
        released first, since it read the home's equations and cannot
        outlive it. A space the program declared with (inherits ...) still
        refuses, naming the heir, because that relationship is the
        program's own.
        """
        if self._owns_self:
            if self._finalizer is not None:
                self._finalizer.detach()
            # Handles this context minted tear down python-side first, so
            # their subscriptions and provider state cannot follow a pooled
            # name into another life; the engine's own cascade then covers
            # the program's handle-less mints.
            for ref in self._minted:
                handle = ref()
                if handle is not None and not handle.dropped:
                    handle.drop()
            self._self.drop()

    @property
    def closed(self) -> bool:
        """Whether :meth:`close` has released this context's own home."""
        return self._owns_self and self._self._dropped

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def __eq__(self, other: object) -> bool:
        """Two contexts are equal when they share a runtime and a home."""
        if not isinstance(other, MeTTa):
            return NotImplemented
        return self._rt is other._rt and self._self == other._self

    def __hash__(self) -> int:
        return hash((id(self._rt), self._self))

    def __repr__(self) -> str:
        # The identity face beside __eq__: the home space names the context,
        # the way Space's own repr names the handle, and a closed context
        # says so instead of hiding behind the object default.
        state = ", closed" if self.closed else ""
        return f"MeTTa(self={str(self._self)!r}{state})"

    @property
    def self(self) -> Space:
        """The context's home space handle, its own ``&self``."""
        return self._self

    @property
    def runtime(self) -> Runtime:
        """The engine bridge itself, for callers going under the surface."""
        return self._rt

    def info(self) -> dict[str, str | None]:
        """Return backend versions and the consulted MeTTa runtime tree."""
        janus_bridge = bridge()
        version_row = janus_bridge.query_once(
            "current_prolog_flag(version, SwiVersion)"
        )
        if version_row is None or not isinstance(version_row.get("SwiVersion"), int):
            msg = "janus did not report the running SWI-Prolog version"
            raise EngineError(msg)
        swi_version_num = version_row["SwiVersion"]
        return {
            "metta": __version__,
            "janus": janus_bridge.version_str(),
            "swi_prolog": janus_bridge.version_str(swi_version_num),
            "python": (
                f"{sys.version_info.major}.{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            ),
            "metta_path": self._rt.metta_path,
        }

    def space(
        self,
        name: str | Symbol | Expression | Space | None = None,
        backing: Any = None,
        *,
        inherits: Space | None = None,
        restricted: bool = False,
        grants: _abc.Iterable[str] = (),
        journal: str | os.PathLike[str] | None = None,
        schema: _abc.Mapping[str, Any] | None = None,
        sync: str = "none",
    ) -> Space:
        """Create one native, provider-backed, remote, or journaled space.

        The BACKING value derives the implementation, so the common calls
        carry no options at all: with no name the engine mints an anonymous
        handle; a ``Space`` reopens that same space, which is what an engine
        answer naming one arrives as; a ``SpaceProvider`` backing is
        attached directly; an HTTP(S) URL becomes a remote provider (build
        the transport with ``metta.remote.connect`` when it needs a token,
        headers, or its own timeout, and hand THAT in as the backing); and
        ``journal=`` constructs ``PersistentFactSpace`` from ``schema=`` or
        a schema mapping supplied as the backing. ``sync`` paces the
        journal and means nothing without one, so it refuses alone.

        ``inherits``, ``restricted`` and ``grants`` choose the space MODEL and
        are independent of whether the space is named. MeTTa's own
        ``!(new-space &locked (restricted))`` names a restricted space, and
        ``metta.space(S.locked, restricted=True)`` is that call. Declaring a
        model on a name that already carries the same one is a no-op; a
        different one raises, because a space cannot have two models.
        """
        if sync != "none" and journal is None:
            msg = "space(sync=...) paces a journal; pass journal= as well"
            raise TypeError(msg)
        # VALIDATE first, so a refusal costs nothing: no space is minted
        # for a request that cannot be built
        # [tested: test_a_failed_space_construction_leaks_nothing].
        if journal is not None:
            if schema is None and isinstance(backing, _abc.Mapping):
                schema = backing
            if schema is None:
                msg = "space(journal=...) needs schema= or a schema mapping as backing"
                raise TypeError(msg)
            if backing is not None and not isinstance(backing, _abc.Mapping):
                msg = "journaled space backing is its schema mapping"
                raise TypeError(msg)
        elif isinstance(backing, str):
            #A bare URL takes the transport's own defaults; a transport that
            #needs a token, headers, an ssl context, a timeout, another
            #remote space, or batching is BUILT with metta.remote and handed
            #in as a RemoteSpace backing, so those knobs live where the
            #protocol does.
            _satellite("remote")._refuse_this_process(
                backing, "&anonymous" if name is None else str(name)
            )
        elif callable(backing) and not isinstance(
            backing, _satellite("foreign").SpaceProvider
        ):
            #A bare transport callable is a PROTOCOL, not a space. Refusing
            #with the composition beats the provider checker's can_run
            #message, which would send its author down the wrong path.
            msg = (
                "a transport callable is not a space; wrap it as the space "
                "it serves: metta.remote.RemoteSpace(transport)"
            )
            raise TypeError(msg)
        if name is None:
            # The context's home plays the &self role for the context's own
            # spaces: an anonymous space minted here resolves EQUATIONS
            # through the home, by the narrow equation-home relation, so its
            # atoms stay its own and conjunctive matching keeps the direct
            # native path (a space_parent row would also union reads and
            # route joins per conjunct, both measured as defects). When the
            # home IS &self that resolution already holds, so the default
            # world needs no row at all.
            equation_home = (
                self._self
                if inherits is None
                and not restricted
                and self._self._space != _DEFAULT_SPACE
                else None
            )
            handle = self._self._new_space(
                inherits=inherits,
                restricted=restricted,
                grants=grants,
                _equation_home=equation_home,
            )
        else:
            handle = self._self._open(
                name, inherits=inherits, restricted=restricted, grants=grants
            )

        # Everything below can refuse, and a refusal must not leak what was
        # just acquired: the anonymous mint unwinds by dropping (it is
        # fresh by construction), while a NAMED open never drops on unwind,
        # because the name may be a pre-existing space whose destruction
        # would be data loss, and an auto-created empty name is the benign
        # residue. An owned provider constructed before the failure closes
        # first, so a journal cannot stay attached past its failed space
        # [tested: test_a_failed_space_construction_leaks_nothing].
        # ACQUIRE under one unwind. The anonymous mint unwinds by dropping
        # (fresh by construction); a NAMED open never drops on unwind,
        # because the name may be a pre-existing space whose destruction
        # would be data loss. An owned provider constructed before the
        # failure closes first, so a journal cannot stay attached past its
        # failed space [tested: test_a_failed_space_construction_leaks_nothing].
        minted_fresh = name is None
        owns_backing = False
        provider = backing
        try:
            if journal is not None:
                provider = _satellite("_persistent").PersistentFactSpace(
                    journal,
                    schema,
                    sync=sync,
                )
                owns_backing = True
            elif isinstance(backing, str):
                remote = _satellite("remote")
                provider = remote.RemoteSpace(remote.connect(backing))
                owns_backing = True
            if provider is not None:
                _satellite("foreign").register_provider(
                    self._rt, handle._space, provider
                )
                handle._backing = provider
                handle._owns_backing = owns_backing
                if journal is not None:
                    # An owned journal stages user-transaction writes and
                    # journals only the committed delta. The declaration is
                    # what makes the existing coordinator enlist that
                    # protocol; the enclosing unwind owns the failure path.
                    handle.atomicity(Atomicity.transactional)
        except BaseException:
            if owns_backing and provider is not backing:
                close = getattr(provider, "close", None)
                if callable(close):
                    close()
            if minted_fresh:
                handle.drop()
            raise
        self._minted.append(weakref.ref(handle))
        return handle

    @property
    def fn(self) -> _FunctionNamespace:
        """The bound function namespace of this context's self space."""
        return self._self.fn

    def unregister_op(self, name: str) -> None:
        """Release an operation installed through :meth:`op`."""
        self._self.unregister_op(name)

    def capture(self) -> CapturedOutput:
        """Capture printed engine text across this context."""
        return self._self.capture()

    def atomic(self) -> ScopedExecution:
        """Scope source execution to committing transactions."""
        return self._self.atomic()

    @overload
    def transaction(self, target: Callable[[], _R], /) -> _R: ...

    @overload
    def transaction(self, target: Atom | str, /) -> list[Atom | Undefined]: ...

    def transaction(self, target: Any, /) -> Any:
        """Run one callable or term in an engine transaction."""
        return self._self.transaction(target)

    # ---------------------------------------------- generated context tier
    # Every door below is GENERATED by tools/aiogen.py from the synchronous
    # Space method it delegates to, whose signature, return annotation and
    # docstring it carries, each with the tier note appended. MeTTa held a
    # hand-written subset of these once, typed (*args: Any) -> Any, which
    # erased every overload a checker could use and silently missed doors
    # (a context that could define but not eval). Do not edit them here:
    # change Space, or remove the door's row from MODULE_DOORS in
    # tools/aio_divergences.py.

    def run(
        self,
        source: str,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[list[Atom]]:
        """Run MeTTa source: one list of answers per ! directive.

        The pipeline is the engine's own reader, compiler and evaluator, so
        the answers are exactly what the CLI would print, kept grouped per
        directive instead of flattened. Equations and facts in the source
        land in this space.

        `bind()` names Python values the source refers to by bare symbol,
        the way DuckDB reads a local dataframe by its variable name:

            with m.bind({"graph": my_graph}):
                m.run("!(py-len graph)")

        Each named symbol substitutes to its value (objects by identity),
        after reading, before anything runs. It is a BLOCK rather than a
        keyword because a binding mapping is the kind of value that grows,
        and a block grows down the page where a keyword has to fit beside
        everything else on the call. Every target door reads the same scope,
        so one block covers a run(), an eval() and an answers() together.

        `timeout` (seconds) and `inferences` (engine steps) bound the call
        with the engine's own guards; passing either raises TimeLimitError
        or InferenceLimitError when the bound is hit, and whatever the
        source completed before the stop, writes included, stands.

        `with m.capture() as output` collects printed text in `output.text`
        without changing this method's return shape. `with m.atomic()`
        and `with m.speculative()` scope execution policy without boolean
        combinations on each call. Atomic commits or rolls
        back each complete source; speculative answers and discards its
        writes. Both cover engine state; Python side effects and subscription
        callbacks already fired stay where they happened.

        A term the engine hands back unevaluated is an ordinary MeTTa value,
        not a failure: `!(hello world)` answers `(hello world)` and that is
        the whole of hello world in this language. eval_status() reports
        which answers reduced and which did not, as data, for a caller who
        wants to decide about it.
        Runs against this context's self space.
        """
        return self._self.run(source, timeout=timeout, inferences=inferences)

    def load(
        self,
        path: str | os.PathLike[str],
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[list[Atom]]:
        """Add a text program or trusted fast cache to this space.

        This is a consult, so it always loads and what it loads REPLACES
        what the same file put in this space before. Edit the file, load it
        again, and the space holds the new definitions and not both; the
        engine says on stderr which file it replaced and how many atoms
        went. Atoms from other sources, and ones you added yourself, stay.
        A load that raises leaves the previous definitions standing, so a
        broken edit costs nothing but the error.

        `!(import! &self path)` is the other door and loads a file that is
        new or edited, skipping one that is neither. The two agree on what
        a reload means and differ only in whether an unchanged file runs
        again, which is SWI's consult/1 against its if(changed).

        A .gz path is detected and read through the decompressed bytes.

        `timeout` (seconds) and `inferences` (engine steps) bound the load
        with the engine's own guards, raising TimeLimitError or
        InferenceLimitError. A load is all or nothing: a stop takes back
        everything the file had put in a space, the same way a load that
        fails on a bad form does, because a file the space holds half of is
        not a file it can replace later. run() is the entry point that
        keeps finished work when a bound stops it. This is the one most
        likely to be handed code the caller did not write, since a file can
        carry `!` directives and an import graph, so it takes the same pair
        its siblings take.
        Runs against this context's self space.
        """
        return self._self.load(path, timeout=timeout, inferences=inferences)

    def match(
        self,
        *patterns: Any,
        where: Any | None = None,
        limit: int | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
        into: _builtins.type | None = None,
    ) -> Any:
        """Lazily match patterns against this space as one conjunction.

        Variables shared between patterns join, the engine's own match/4
        doing the joining. Columns are the variable names in first
        appearance order. `where` is a guard term over the same variables,
        evaluated per join and required true, so restrictions a pattern
        cannot spell (an inequality) compose onto the match:

            m.match(S.person(V.name, V.age), where=V.age.ge(18))

        `limit` bounds the answers, the engine stopping at the count
        rather than trimming afterwards. `timeout` (seconds) and
        `inferences` (engine steps) bound the whole call, raising
        TimeLimitError or InferenceLimitError when hit, for joins whose
        size is not known in advance.

        The returned Answers view pulls only what Python observes. ``bool``
        pulls one row, exact-one operations pull at most two, and slicing
        retains an Answers view. ``len`` uses an engine-side aggregate when
        no row has yet been pulled.

        ``under=`` interprets the same ask through an annotation algebra.
        ``under=counting`` answers one integer computed by an engine
        aggregate, including duplicate derivations without crossing their
        rows into Python. Ordered carriers sort in their declared direction
        before slicing, so ``m.match(q, under=ranked)[:3]`` is top-k and
        ``under=tropical`` puts the cheapest annotation first. Other carriers
        answer ``TaggedAnswer`` values with ``annotation``, ``why()`` and
        ``under(other)``; the latter two reuse the retained derivation rather
        than querying the space again. ``with metta.under(carrier)`` supplies
        the carrier when this call has no explicit ``under=``.

        `into=Rows` explicitly chooses the eager Rows face. Other `into=`
        values shape each row into a dataclass, NamedTuple, or
        TypedDict matched by field name, sqlite3's row_factory reading:
        `m.match(S.edge(V.a, V.b), into=Edge)` answers `list[Edge]`,
        and Rows stays the default so nothing is lost. A one-variable query
        whose column holds complete constructor expressions rebuilds those
        expressions instead: `m.match(V.edge, into=Edge)`.

            m.match(S.Edge(V.x, V.y), S.Edge(V.y, V.z))
        Runs against this context's self space.
        """
        return self._self.match(
            *patterns, where=where, limit=limit, timeout=timeout, inferences=inferences, under=under, into=into
        )

    def add(self, *atoms: Any) -> None:
        """Add atoms to this space, one engine round-trip for the lot.
        An (= ...) atom compiles as an equation. Every Atom shape the engine's
        add-atom accepts crosses unchanged, including a bare Symbol, Grounded
        value, and empty Expression; a free Variable receives the engine's own
        insufficient-instantiation refusal.

        A variable's NAME is not stored. `(rule $x $y)` reads back as
        `(rule $_17902 $_17904)`, because a variable is an identity and not a
        spelling. That is the right property for a logic engine and it is the
        one thing about storage that surprises everybody once.

        A library IS knowledge, so the same door imports it: ``m += lib.he``
        performs ``!(import! <m> (library lib_he))`` with this space as the
        target. An import is an effect, so it refuses to hide inside an atom
        batch or share a call with stored atoms.
        Runs against this context's self space.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._self.add(*atoms)

    def remove(self, atom: Any, *more: Any) -> bool | int:
        """Remove ONE unifying occurrence and say whether one was there,
        which is Python's own `list.remove` grain.

        Variadic like `add` and `transfer`: several atoms ride one engine
        crossing inside one transaction, and the answer counts the found,
        so the one-atom call still reads as the truth value it always
        was.

        `space -= atom` is this same grain without the report, the way
        `+=` is `add` without one: Python's in-place difference over a
        MULTISET, whose own Python spelling is `collections.Counter`,
        subtracts the multiplicity given rather than clearing the key.
        That is the only reading under which the operators are inverses,
        so `s += a; s -= a` leaves the space it found. `-=` classifies its
        operand exactly as `+=` does, so the fact stream one door stores
        the other subtracts, one occurrence per element, in one
        transactional crossing.

        The DRAIN is the pattern-shaped door: `del m[pattern]` takes every
        unifying occurrence in one crossing and raises when nothing
        matched, as Python's `del` does, and MeTTa spells it `remove-atom`
        [source: engine/spaces/foreign.pl, remove_matching_atoms/2].
        MeTTa spells this method's grain `subtract-atom`. This is the one
        door that reports absence.

        A bare variable is the remove-everything reading a multiset space
        gives it, each atom leaving through its own proper path, equations
        and their compiled clauses included.
        Runs against this context's self space.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._self.remove(atom, *more)

    @overload
    def eval(
        self,
        target: Any,
        *,
        timeout: float | None = ...,
        inferences: int | None = ...,
        under: Any = ...,
        theory: Any | None = ...,
        interpreter: Any | None = ...,
    ) -> list[Atom | Undefined]: ...
    @overload
    def eval(
        self,
        target: Any,
        second: Any,
        /,
        *more: Any,
        timeout: float | None = ...,
        inferences: int | None = ...,
        under: Any = ...,
        theory: Any | None = ...,
        interpreter: Any | None = ...,
    ) -> list[list[Atom | Undefined]]: ...
    def eval(
        self,
        target: Any,
        *more: Any,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
        theory: Any | None = None,
        interpreter: Any | None = None,
    ) -> list[Atom | Undefined] | list[list[Atom | Undefined]]:
        """Evaluate a term, returning every answer.

        This is what !(...) runs, minus the printing: the engine's
        translate_expr over the term, then its goals. Nondeterminism means
        the list can hold any number of answers, including none.

        Variadic, and that is how evaluation BATCHES: several terms ride
        one engine crossing and the answer is one group per term in call
        order, run()'s own grouping carried to the term door. One term
        keeps its flat list, so the scalar reading never changes shape.

        Every answer carries its truth: an answer that is undefined under
        Well Founded Semantics (a tabled loop through tnot, reachable via
        translatePredicate or injected Prolog) arrives as an Undefined
        holding the answer and the delay condition that makes it
        undefined, never as an ordinary-looking value. A term to which no
        rule applies is the ordinary answer itself; `eval_status()` names
        that path `not-reducible`. run() does not carry the third truth
        value; evaluate through eval() when it matters.

        `bind()` binds named host values into the term before it evaluates,
        exactly as it does for run(): inside `with m.bind({"x": tensor})`,
        `m.eval("(decide x)")` hands the tensor itself to the rule, by
        identity, rather than a printed form of it. The name is the SYMBOL x
        and not the variable $x, on this door and the source door alike. The evaluation doors take the same
        vocabulary the source door takes, so reaching for a term instead
        of source text costs no change of spelling.

        A key may be a NAME or an ATOM. A name means the symbol of that name,
        which is what the engine's own substitution matches and what run()
        takes. An atom means exactly that atom, so `bind({V.x: 5})` fills a
        VARIABLE hole -- the one substitution `unify` reports and the one no
        door could apply, because a variable crosses the wire as ['v', 'x']
        where a symbol crosses as ['s', 'x'] and the engine matches names.

        `timeout` (seconds) and `inferences` (engine steps) bound the call,
        raising TimeLimitError or InferenceLimitError when hit. A surrounding
        `capture()` scope collects printed text without changing the list.

        `under`, `theory` and `interpreter` are answers()' three, and mean
        exactly what they mean there; this door is that one materialised. A
        surrounding `with metta.under(carrier)` reaches here too, which it did
        not before: match() and answers() both honoured such a scope while
        eval() ignored it in silence.
        Runs against this context's self space.
        """
        return cast("Any", self._self).eval(target, *more, timeout=timeout, inferences=inferences, under=under, theory=theory, interpreter=interpreter)

    def solve(self, pattern: Any, subject: Any) -> Any:
        """Run relational ``let`` and return bindings keyed by its variables.

        ``solve(4, V.x - 1).x`` places the known value on let's pattern side,
        lets the arithmetic relation solve backwards, and projects ``x``.
        The answer template is derived from the pattern's variables followed
        by any new subject variables, so either relational direction can
        introduce the bindings and the third hand-written ``let`` argument
        disappears.
        Runs against this context's self space.
        """
        return self._self.solve(pattern, subject)

    def doc(self, atom: Any) -> Atom:
        """Return this space's structured ``get-doc`` answer for one subject.

        The answer is the ``(@doc ...)`` atom the engine holds for the
        subject, whether it was documented in MeTTa source or built from a
        Python docstring:

            m.doc(S.area)
            # (@doc-formal (@item area) (@kind function) (@desc "Circle area.") ...)

        A subject with no documentation raises, exactly as ``type`` raises
        for a subject ``get-type`` cannot answer.
        Runs against this context's self space.
        """
        return self._self.doc(atom)

    @overload
    def define(  # type: ignore[overload-overlap]
        self,
        fn: _builtins.type,
        /,
        *,
        accessors: bool = ...,
        methods: bool = ...,
    ) -> _builtins.type: ...
    @overload
    def define(
        self,
        fn: Callable[_P, _R],
        /,
        *,
        name: str | None = ...,
        accessors: bool = ...,
        methods: bool = ...,
    ) -> Defined[_P, _R]: ...
    @overload
    def define(
        self, *, name: str
    ) -> Callable[[Callable[_P, _R]], Defined[_P, _R]]: ...
    @overload
    def define(
        self, *, prolog: str | os.PathLike[str], name: str | None = None
    ) -> Callable[[Callable[_P, _R]], PrologBacked[_P, _R]]: ...
    def define(
        self,
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

        This is rung 4 of the naming ladder applied to the definition door
        itself: ``def not_provable`` lands as ``not-provable``. An authored
        MeTTa underscore therefore uses explicit ``name="not_provable"``.

        A generator compiles to nondeterminism (each yield one answer), a
        lambda to the engine's own |->, a comprehension to map-atom and
        filter-atom, and match(Pattern(x, y), template) to a match against
        the running space, lowercase free names in the pattern binding as
        variables.
        Runs against this context's self space.
        """
        return cast("Any", self._self).define(fn, prolog=prolog, name=name, accessors=accessors, methods=methods)

    @overload
    def op(
        self,
        fn: Callable[_P, _R],
        /,
        *,
        name: str | None = ...,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = ...,
        effect: EffectClass | str,
        declarations: Iterable[Atom] = ...,
        arities: list[int] | None = ...,
        inverse: Callable | None = ...,
    ) -> Callable[_P, _R]: ...
    @overload
    def op(
        self,
        *,
        name: str | None = ...,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = ...,
        effect: EffectClass | str,
        declarations: Iterable[Atom] = ...,
        arities: list[int] | None = ...,
        inverse: Callable | None = ...,
    ) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...
    def op(
        self,
        fn: Callable | None = None,
        *,
        name: str | None = None,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = "encoded",
        effect: EffectClass | str | None = None,
        declarations: Iterable[Atom] = (),
        arities: list[int] | None = None,
        inverse: Callable | None = None,
    ) -> Any:
        """Register a Python callable as a MeTTa function, decorator-style.

            @m.op(effect=EffectClass.pureStructural)
            def double(x: int) -> int:
                return 2 * x                    # !(double 21) -> 42

            @m.op(effect=EffectClass.nondeterministicReadOnly)
            def neighbours(n: int):
                yield n - 1                     # a generator is nondeterministic
                yield n + 1

        An implicit Python name maps underscores to MeTTa hyphens. ``name=``
        is exact, for source vocabularies that deliberately use underscores.

        A name must read back as one MeTTa symbol. A space, parenthesis,
        quote, comment opener, variable spelling, number, boolean, or another
        registered reader token is refused before any registry changes, with
        the name and the conflicting character in the error.

        Annotations become ordinary `(: ...)` declarations. An unannotated
        callable makes no type claim. `transport="raw"` skips wire encoding
        both ways and is reflected as raw_det or raw_many in `(op ...)`;
        symbols then reach Python as strings, so encoded transport is the
        fidelity-preserving default. unregister_op(name) removes every
        registered arity and every declaration the registration owns.

        An `Atom` parameter changes evaluation order. The declaration tells
        the compiler to pass the argument as written, before it reduces:

            @m.op(effect=EffectClass.pureStructural)
            def anyatom(term: Atom) -> Atom:
                return term

            # with (= (side) 42), !(anyatom (side)) answers (side)

        An unconstrained parameter receives the evaluated value instead, so
        the otherwise identical `def anyval(term): return term` answers 42.
        Use `Atom` only when the operation deliberately implements syntax or
        a control form; it is not just a static hint.

        An encoded generator may instead yield exact tuples as positional
        relation rows, or exact dicts keyed by parameter name as sparse rows.
        The engine unifies each candidate against the written call, so one
        implementation serves free, partially bound, and ground arguments:

            @m.op
            def route(origin, destination):
                yield (S.paris, S.lyon)
                yield {"destination": S.nice}  # origin is unconstrained

            # route(V.origin, S.lyon).rows[0].origin == S.paris

        Each matching occurrence answers unit and duplicate yields remain
        duplicate answers. Use `Answer(value=...)` when an exact tuple or dict
        is the result value rather than a parameter row. Relational rows
        require encoded transport; raw calls cannot carry unbound argument
        positions.

        When evaluation order stays ordinary but the callable needs the
        resulting Atom wrappers, declare that policy as data:

            m.op(
                inspect_atom,
                name="inspect-atom",
                effect=EffectClass.pureStructural,
                declarations=[parse("(arguments inspect-atom atoms)")],
            )

        The declaration is matchable in &metta and is retired with the
        operation. Raw transport refuses this declaration because it bypasses
        the atom codec entirely.

        The cost ladder, measured on the maintained box in inferences per
        call, explains the transport choice:

            native MeTTa function            9.11   the floor
            transport="raw"                10.11   opaque handles, near-native
            encoded                        17.11   encoded values
            encoded, typed literal         17.11   the check hoists to compile
            py-call, dotted                 22.11   the ad-hoc escape hatch

        The ergonomic default (encoded, typed) costs about 1.7x raw on the
        counter and more on wall clock, since encoding walks the value both
        ways; a registered raw operation measured 0.85us against 2.26us
        encoded. Bulk data should stay opaque: one transparent 64-float
        crossing costs 330 inferences where the handle costs 10.

        `inverse=` remains the distinct-output form. Use it when the forward
        operation returns a result and a separate callable must recover the
        arguments from that result:

            m.op(
                cons,
                name="cons",
                inverse=uncons,
                effect=EffectClass.pureStructural,
            )
            # !(let (cons $h $t) (1 2 3) ($h $t))  ->  (1 (2 3))

        It takes the result and returns the arguments, as a tuple, or the
        bare value at arity one; a generator enumerates every preimage, and
        None or NotReducible means there is none. It runs only when the arguments
        are not ground and the result is, so a forward call never reaches it,
        and an operation without one compiles exactly what it did before.

        A parameter annotated `metta.MeTTa` is the framework's to fill,
        FastAPI's Depends read with the house convention that the
        annotation is the request. The engine injects itself bound to the
        CALLING context's space, so an operation invoked from a program
        running in &kb queries &kb; the slot never counts toward MeTTa
        arities or the declared arrow, and only operations that ask pay
        the weaving:

            @m.op(effect=EffectClass.nondeterministicReadOnly)
            def related(term, engine: metta.MeTTa):
                for row in engine.match(Expression(S.link, term, V.x)):
                    yield row[0]

        Every operation declares its strongest observable effect. The five
        ordered choices are ``pureStructural``, ``readOnlyLookup``,
        ``nondeterministicReadOnly``, ``writesState``, and ``oracleIO``:

            m.op(
                len,
                name="size",
                effect=EffectClass.pureStructural,
            )
            # (= (count-of $x) (size $x))  is cacheable

        It is an allow-list on purpose. An operation that does not say so is
        refused by name in a cached body, loudly, rather than cached and
        quietly wrong.
        Runs against this context's self space.
        """
        return cast("Any", self._self).op(fn, name=name, transport=transport, effect=effect, declarations=declarations, arities=arities, inverse=inverse)

    def pure(self, fn: Callable | None = None, /, **options: Any) -> Any:
        """An operation whose answer depends only on its arguments.

            @m.pure
            def double(x: int) -> int:
                return 2 * x

        The cache-safe class, and the only one memoization and tabling admit
        without an explicit policy.

        A GENERATOR written this way is lifted to `nondeterministicReadOnly`,
        because a generator is nondeterministic whatever it declares, and the
        registration reads that off the function rather than asking. The lift
        only ever raises the rank, so it widens the answer-count claim and
        never weakens the effect claim -- but it does mean a generator is not
        cache-safe, which is the whole reason it is lifted out of this class
        [tested: test_a_generator_is_lifted_to_the_nondeterministic_rank;
        commit=7e5091540a8dc0903bcee24f3e5b8b85a19f805f].

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        Runs against this context's self space.
        """
        return self._self.pure(fn, **options)

    def reads(self, fn: Callable | None = None, /, **options: Any) -> Any:
        """An operation that reads stable state without changing it.

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        Runs against this context's self space.
        """
        return self._self.reads(fn, **options)

    def writes(self, fn: Callable | None = None, /, **options: Any) -> Any:
        """An operation that changes engine or host state.

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        Runs against this context's self space.
        """
        return self._self.writes(fn, **options)

    def io(self, fn: Callable | None = None, /, **options: Any) -> Any:
        """An operation that observes an external oracle.

        A clock, randomness, a network, a file, another runtime.

            @m.io
            def now() -> float:
                return time.time()

        The fail-closed top of the lattice. Declare it when what the operation
        reaches is decided at run time or by a library the engine cannot bound.

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        Runs against this context's self space.
        """
        return self._self.io(fn, **options)

    def stats(self) -> _StatsBlock:
        """The engine's own counters over a with-block, as deltas.

            with m.stats() as s:
                m.match(S.edge(V.x, V.y), S.edge(V.y, V.z))
            s.inferences        # engine steps the block spent
            s.cputime           # engine CPU seconds
            s.walltime          # wall seconds, Python's clock
            s.gc_count, s.gc_freed, s.gc_time
            s.table_bytes       # answer-table bytes grown, tabling's memory

        The counters are SWI's statistics/2 read on the CALLING thread, so
        a block that runs other threads' engine work counts that work too;
        the honest reading is "what this thread saw the engine do while the
        block ran". A lazy cursor is the exception, and a large one: its
        goal runs in an SWI engine, an engine counts its own inferences,
        and this thread cannot see them. Draining 20,000 rows through the
        match cursor reports 40,049 inferences against about 381,000 the
        cursor's engine really spent, 10.5% of the work; the real cost is
        readable off the `inferences` budget, which does count the engine
        [measured 2026-08-27]. The evaluation cursor behind `answers()`
        does report its engine's spend, so that one is whole. The z3py
        Solver.statistics() reading, on the engine this library actually
        has.
        Runs against this context's self space.
        """
        return self._self.stats()

    def limits(
        self,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        stack: int | None = None,
    ) -> ScopedLimits:
        """Scoped default bounds for every call in the with-block:

            with m.limits(inferences=1_000_000, timeout=2.0):
                m.match(...)      # bounded without saying so again

        decimal.localcontext's shape, contextvars underneath, so the
        scope is async-correct and per-task. A per-call timeout= or
        inferences= still overrides, which is the whole ladder: one
        block replaces the parameter forest, and the forest remains
        for whoever wants per-call control.

        stack= is SWI's combined stack ceiling in BYTES, the bound a
        runaway recursion hits as a StackOverflow error atom. It is NOT
        MeTTa's reduction depth: that is the max-stack-depth pragma,
        `(with-pragma! ((max-stack-depth N)) expr)`, which counts
        reduction steps and is scoped in the program text.
        Runs against this context's self space.
        """  # noqa: D415  -- the first line deliberately introduces the indented example that follows
        return self._self.limits(timeout=timeout, inferences=inferences, stack=stack)

    def speculate(self) -> ScopedExecution:
        """Run each source against a snapshot and discard its writes.

        Runs against this context's self space.
        """
        return self._self.speculative()

    def trace(self, source: Atom | str, max_events: int = 1_000_000):
        """Run a TERM, or source, under the engine's reduction trace and
        answer TraceEvent records: what entered reduction at which depth,
        what it answered, and which reductions failed (a call with no
        exit). `m.trace(S.fib(10))` is the ordinary spelling, the same
        argument `answers` and `eval` take; a string is still a string.
        What is traced executes for real, writes included, like run();
        the wrap exists only while tracing, so untraced calls pay
        nothing. max_events bounds the recording, raising past it rather
        than accumulating a long run's trace without limit.
        Runs against this context's self space.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._self.trace(source, max_events)

    def __bool__(self) -> bool:
        """Always true: a space is a handle to a store, not a value that
        dwindles. Without this, bool() falls through to __len__ and an
        empty space is falsy, so `if space:` skips a perfectly good empty
        space, the bug class that made datetime stop treating midnight as
        false in 3.5. Existence is an ask: use
        ``bool(space.match(V.x))`` rather than ``bool(space)``.
        Runs against this context's self space.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._self.__bool__()

    def __iadd__(self, atom: Any) -> Self:
        """add()'s operator spelling for one atom or one fact stream.

        ``m += (S.Edge, a, b)`` adds one fact. ``m += [(S.Edge, a, b),
        (S.Edge, b, c)]`` and a generator yielding those rows add two. A built
        Expression is always one atom even though it implements Sequence.
        Dataframes use ``iter_rows`` or ``itertuples(index=False)``. The
        explicit ``add(list_value)`` door remains available when a list itself
        is intended as one transparent expression.

        Relative ``S.admits(Type)`` and ``S.capacity(n)`` values are declared
        data: they install the same contract as the receiver methods and are
        not stored in this space. Explicit ``add(...)`` remains the raw storage
        door for those shapes.
        Runs against this context's self space.
        """
        self._self.__iadd__(atom)
        return self

    def __isub__(self, atom: Any) -> Self:
        """Runs against this context's self space."""
        self._self.__isub__(atom)
        return self

    def __ior__(self, other: Any) -> Self:
        """Merge into this space in one bulk crossing: every atom of
        another space, of a registered space name, or of an iterable.

            m |= other_space     # every atom, equations included
            m |= "&kb"           # the space registered under this name
            m |= [a, b, c]       # each element becomes one atom

        Equations in the merge compile on arrival, the same rule add()
        enforces. A space is a multiset, so merging a space into itself
        doubles every atom. A Mapping is refused because add(d) reads the
        same dict as ONE grounded atom and its values would silently
        vanish here; spell the reading you mean. Strings name spaces, so
        an unregistered name is a KeyError rather than a parse.
        Runs against this context's self space.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self._self.__ior__(other)
        return self

    def __contains__(self, atom: Any) -> bool:
        """Runs against this context's self space."""
        return self._self.__contains__(atom)

    def __iter__(self):
        """Iterate one assembly-order snapshot of the stored atoms.

        A native or inherited-native space materializes its readable chain
        when ``iter(space)`` is called, so later additions and removals do not
        alter that iterator. A Python-backed space likewise materializes its
        provider's ``atoms()`` result before returning the iterator; the
        provider owns and must document how concurrent mutation behaves while
        that one enumeration itself is being produced.
        Runs against this context's self space.
        """
        return self._self.__iter__()

    def __len__(self) -> int:
        """Runs against this context's self space."""
        return self._self.__len__()

    def __getitem__(self, i: Any) -> Rows:
        """Subscription is query. A tuple headed by an atom is one built
        expression pattern; a tuple of complete expression patterns is a join:

            m[(S.Parent, V.x, S.Bob)]
            m[S.edge(V.a, V.b), S.edge(V.b, V.c)]

        Python hands both spellings to ``__getitem__`` as a tuple, so shape is
        the visible classifier. A mixed tuple beginning with a complete
        pattern and followed by a bare atom can only be the tuple mistake; it
        raises and names the one-pattern and join spellings instead of
        silently asking an impossible bare-atom conjunct.

        A str key parses first, matching match()'s tolerance. A slice is
        refused: a slice of a space has no one meaning, and the bounded
        readings have their own doors, match(limit=) for a bounded answer
        set and stream() for rows pulled until you have seen enough.
        Runs against this context's self space.
        """  # noqa: D205, D415  -- the API contract is one continuous invariant, not summary-and-body prose; the first line deliberately introduces the indented example that follows
        return self._self.__getitem__(i)

    def __delitem__(self, pattern: Any) -> None:
        """Del m[pattern] removes every unifying occurrence, the bulk
        spelling of remove()'s multiset subtraction: m[pattern] is a
        query answering many rows, so deleting it deletes them all, the
        way DELETE WHERE does. Nothing unifying raises KeyError, as
        del d[k] does on a missing key; remove() is the door that
        reports absence as False instead.

        It asks the engine's own drain, so the whole pattern costs ONE
        crossing rather than one per removed atom.
        Runs against this context's self space.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._self.__delitem__(pattern)

    # ------------------------------------------ end of generated context tier

    def register_prolog(self, *args: Any, **kwargs: Any) -> tuple[str, ...]:
        """Install a declared Prolog extension."""
        return self._self.register_prolog(*args, **kwargs)

    def register_foreign_library(self, *args: Any, **kwargs: Any) -> tuple[str, ...]:
        """Install a compiled SWI foreign library."""
        return self._self.register_foreign_library(*args, **kwargs)

    def register_library_path(self, directory: Any, name: str) -> None:
        """Register one named Prolog library directory."""
        self._self.register_library_path(directory, name)

    def unregister_prolog(self, extension: str) -> tuple[str, ...]:
        """Release one declared Prolog extension."""
        return self._self.unregister_prolog(extension)

    def prolog(self) -> None:
        """Enter SWI-Prolog's interactive toplevel."""
        self._self.prolog()
