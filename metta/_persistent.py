"""Purpose: fixed-schema fact spaces backed by SWI persistency journals.
The provider keeps native MeTTa facts in typed dynamic predicates, writes
every change through library(persistency), and replays the journal when a
new provider attaches to the same path. On attach, an incomplete final
record is copied to ``<journal>.tail`` and removed only when every earlier
newline-terminated record validates. Earlier corruption is refused.
Guarantees:
  - rename= atomically materializes a one-time old-head to new-head journal
    migration before attachment, requires every old head to occur, and leaves
    no replay alias behind [tested:
    test_a_replay_rename_migrates_every_journal_action_once,
    test_a_replay_rename_with_an_absent_old_name_refuses_with_the_remedy,
    test_a_second_replay_does_not_reapply_the_rename,
    test_replay_rename_composes_with_terminal_tail_recovery; commit=ee43d4a0585593b4f40d0c3c0557db8214688829]
  - removal subtracts ONE stored fact and journals one `retract(Fact)` for
    it, the same multiset law a native space obeys, so a provider swap does
    not change what `remove-atom` means
    [tested: test_a_persistent_space_drains_like_a_native_one;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - constructor failure releases its path claim and any unattached reusable
    module [tested: test_constructor_failure_releases_path_and_unattached_module;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - one exclusive interprocess claim on the journal PATHNAME spans tail
    repair, replay migration, attachment and the provider's whole life, so a
    migration cannot replace a journal another process is attached to and
    lose the writes that process acknowledges [tested:
    test_a_journal_migration_cannot_replace_a_journal_another_process_holds,
    test_a_second_provider_in_this_process_is_refused_before_it_touches_the_file;
    commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - terminal-tail recovery syncs the backup file and its directory before
    truncating the journal
    [tested: test_tail_backup_is_durable_before_truncation; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - EVERY proper prefix of a record classifies as an incomplete tail and is
    recovered, and a tail carrying its terminating full stop is refused
    instead of truncated [measured 2026-08-19: 7 of 18 truncation points were refused;
    command=pytest tests/test_persistent.py -q -p no:benchmark;
    fixture=all prefixes of assert(edge(a,b)).; commit=f88aa8be03cb64cb59d3307515ded8701f418321] [tested:
    test_every_truncation_point_of_the_torn_tail_classifies,
    test_a_terminated_record_is_refused_rather_than_truncated;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - snapshot() captures one locked immutable tuple, and add refuses a live
    engine State cell before any persistent updater can append its handle
    [tested: test_a_live_state_cell_never_enters_the_persistent_journal;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - every supported mutation crosses this engine's hooks, so subscriptions
    receive each committed write once in order while rolled-back provider
    transactions remain unjournaled and unannounced
    [tested: test_a_journal_transaction_publishes_only_its_committed_delta,
    test_a_speculative_journal_write_is_neither_persisted_nor_published;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
Owns resources:
  - PersistentFactSpace owns one process path claim, one generated module,
    and one journal attachment until close or constructor rollback
    [tested: test_detached_modules_are_reused_without_weakening_path_claims;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - and one flock(2) descriptor on ``<journal>.lock``, released by close()
    and by every constructor rollback path; the lock file itself is left in
    place, since unlinking it would let a waiter holding the removed inode
    take a claim nobody else can see
    [tested: test_a_second_provider_in_this_process_is_refused_before_it_touches_the_file;
    commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
Guarded by:
  - _STATE_LOCK protects active paths and the module pool; each provider's
    _call_lock serializes journal operations
    [tested: test_detached_modules_are_reused_without_weakening_path_claims;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import hashlib
import importlib
import itertools
import logging
import os
import stat
import tempfile
import threading
from collections import Counter
from collections.abc import Iterator, Mapping
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._engine import Runtime, runtime
from .atoms import Atom, Expression, Grounded, Symbol, _atom_from_wire, _is_ground
from .errors import EngineError, MettaError
from .foreign import SpaceProvider

logger = logging.getLogger(__name__)

__all__ = ["PersistentFactSpace"]


_MODULE_IDS = itertools.count()
_STATE_LOCK = threading.Lock()
_ACTIVE_PATHS: set[Path] = set()
_MODULE_POOL: dict[tuple[tuple[str, int], ...], list[str]] = {}

#: flock(2), where the journal's interprocess claim lives. Imported this way
#: because it does not exist off POSIX, where _claim_journal_lock refuses by
#: name rather than letting an import error stand in for the explanation.
_FCNTL = importlib.import_module("fcntl") if os.name == "posix" else None

_PERSISTENCY_API = {
    ("persistent", 1),
    ("current_persistent_predicate", 1),
    ("db_attach", 2),
    ("db_detach", 0),
    ("db_attached", 1),
    ("db_sync", 1),
    ("db_sync_all", 1),
}

_HELPER_ARITIES = {
    "decode": 2,
    "encode": 2,
    "schema": 2,
    "fact": 2,
    "all": 1,
    "match": 2,
    "add": 2,
    "remove": 3,
    "apply_add": 1,
    "apply_remove": 1,
    "apply_diff": 2,
    "clear_one": 2,
    "clear": 0,
    "validate_native": 1,
    "validate_pattern": 1,
    "validate_fact": 1,
    "validate_pattern_fact": 1,
    "validate_action": 1,
    "validate_stream": 1,
    "validate": 1,
    "validate_text": 1,
    "rename_fact": 4,
    "rename_action": 4,
    "validate_replay_stream": 4,
    "validate_replay": 3,
    "validate_replay_text": 3,
    "write_action": 2,
    "rewrite_replay_stream": 5,
    "rewrite_replay": 4,
    "tail_status": 2,
    "attach": 2,
    "sync": 0,
    "flush": 0,
    "compact": 0,
    "close": 0,
}

_MISSING = object()


def _validate_schema_entry(head: Any, arity: Any) -> tuple[str, int]:
    if not isinstance(head, str):
        msg = f"schema head names must be strings, got {head!r}"
        raise TypeError(msg)
    if "\x00" in head:
        msg = f"schema head {head!r} contains a null byte"
        raise ValueError(msg)
    if isinstance(arity, bool) or not isinstance(arity, int) or arity < 0:
        msg = f"schema arity for {head!r} must be a non-negative integer, got {arity!r}"
        raise ValueError(msg)
    if (head, arity) in _PERSISTENCY_API:
        msg = f"schema head {head!r}/{arity} conflicts with library(persistency)"
        raise ValueError(msg)
    return head, arity


def _validate_generated_updaters(schema: Mapping[str, int]) -> None:
    for head, arity in schema.items():
        for prefix in ("assert_", "asserta_", "retract_", "retractall_"):
            generated = f"{prefix}{head}"
            if schema.get(generated) == arity:
                msg = (
                    f"schema head {generated!r}/{arity} conflicts with the "
                    f"generated updater for {head!r}/{arity}"
                )
                raise ValueError(msg)


def _validated_schema(schema: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(schema, Mapping):
        msg = f"schema must map fact head names to arities, got {type(schema).__name__}"
        raise TypeError(msg)
    copied: dict[str, int] = {}
    for head, arity in schema.items():
        valid_head, valid_arity = _validate_schema_entry(head, arity)
        copied[valid_head] = valid_arity
    if not copied:
        msg = "schema must declare at least one fact head"
        raise ValueError(msg)
    _validate_generated_updaters(copied)
    return copied


def _validated_replay_rename(
    rename: Mapping[str, str] | None,
    schema: Mapping[str, int],
) -> dict[str, str]:
    if rename is None:
        return {}
    if not isinstance(rename, Mapping):
        msg = f"rename must map old journal heads to new schema heads, got {type(rename).__name__}"
        raise TypeError(msg)

    copied: dict[str, str] = {}
    targets: set[str] = set()
    for old, new in rename.items():
        if not isinstance(old, str) or not isinstance(new, str):
            msg = f"rename heads must be strings, got {old!r}: {new!r}"
            raise TypeError(msg)
        if "\x00" in old or "\x00" in new:
            msg = f"rename head contains a null byte: {old!r}: {new!r}"
            raise ValueError(msg)
        if old == new:
            msg = f"rename source and target are both {old!r}; remove that no-op from rename="
            raise ValueError(msg)
        if old in schema:
            msg = (
                f"rename source {old!r} is still declared in schema; remove the old "
                "schema head so replay cannot retain a standing alias"
            )
            raise ValueError(msg)
        if new not in schema:
            msg = (
                f"rename target {new!r} is not declared in schema; declare it with "
                "the old head's arity, then reopen"
            )
            raise ValueError(msg)
        if new in targets:
            msg = f"rename target {new!r} has more than one old head; a rename must be one-to-one"
            raise ValueError(msg)
        copied[old] = new
        targets.add(new)
    return copied


def _journal_path(path: str | os.PathLike[str]) -> Path:
    resolved = Path(path).expanduser().resolve()
    if resolved.exists() and resolved.is_dir():
        msg = f"persistent journal path is a directory: {resolved}"
        raise IsADirectoryError(msg)
    if not resolved.parent.exists():
        msg = f"persistent journal parent does not exist: {resolved.parent}"
        raise FileNotFoundError(msg)
    if not resolved.parent.is_dir():
        msg = f"persistent journal parent is not a directory: {resolved.parent}"
        raise NotADirectoryError(msg)
    return resolved


def _sync_directory(path: Path) -> None:
    if os.name != "posix":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _lock_path(journal: Path) -> Path:
    """The sidecar whose lock claims one journal PATHNAME."""
    return journal.with_name(f"{journal.name}.lock")


def _lock_holder(descriptor: int) -> str:
    """Whatever the standing claim recorded about itself, for the refusal."""
    try:
        recorded = os.pread(descriptor, 64, 0).decode("utf-8", "replace").strip()
    except OSError:
        return "another process"
    return f"process {recorded}" if recorded.isdigit() else "another process"


def _claim_journal_lock(journal: Path) -> int:
    """Take the exclusive interprocess claim on one journal, or refuse.

    library(persistency) already locks, but it locks the wrong thing for this
    provider's purposes: db_open_file/3 opens the append stream with
    lock(write), which is a POSIX record lock on the journal's INODE, and it
    is taken lazily at the first write rather than at attach
    [source: /usr/lib/swi-prolog/library/persistency.pl db_open_file/3;
    measured 2026-08-31: /proc/locks showed `POSIX ADVISORY WRITE <pid>
    103:02:53770050 0 EOF` after one write and no row before it]. An inode
    lock cannot see a PATHNAME being replaced, which is exactly what a
    rename= migration does with tempfile+replace, so a second process
    migrated the journal out from under an attached one and the writes that
    process went on to acknowledge went into the unlinked inode.

    So the claim that spans tail repair, migration, attachment and the whole
    life of the provider is taken here, on a sidecar file that is never
    replaced. flock(2) rather than a POSIX record lock for two reasons the
    kernel documents: a POSIX lock is released when the process closes ANY
    descriptor for that file, and this module opens the journal itself to
    read and to truncate it, while flock treats separate descriptors
    independently and so also refuses a second provider inside this process
    [source: man 2 F_SETLK, Linux man-pages 6.17, "If a process closes any
    file descriptor referring to a file, then all of the process's locks on
    that file are released"; man 2 flock, "these file descriptors are treated
    independently by flock()"]. The kernel drops a flock when the holder
    dies, which is what the SIGKILL survival lane needs: a lock file left
    behind by a killed writer claims nothing.

    The lock file is not removed on release. Unlinking it would let a waiter
    that already holds a descriptor on the removed inode take a lock nobody
    else can see; leaving it costs one empty file beside the journal.
    """
    if _FCNTL is None:
        msg = (
            f"cannot claim persistent journal {journal} exclusively: this "
            f"platform has no flock(2), so nothing stops a second process "
            f"attaching or migrating the same journal and losing writes this "
            f"one acknowledges"
        )
        raise MettaError(msg)
    lock = _lock_path(journal)
    try:
        descriptor = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)
    except OSError as exc:
        msg = f"cannot open the claim file {lock} for persistent journal {journal}: {exc}"
        raise MettaError(msg) from exc
    try:
        _FCNTL.flock(descriptor, _FCNTL.LOCK_EX | _FCNTL.LOCK_NB)
    except OSError as busy:
        holder = _lock_holder(descriptor)
        os.close(descriptor)
        msg = (
            f"persistent journal {journal} is claimed by {holder} through "
            f"{lock}. One attachment owns a journal at a time: a second one "
            f"would replay and append to the same file, and a migration here "
            f"would replace the file the other attachment is still writing "
            f"to. Close the other provider, or point this one at its own path"
        )
        raise MettaError(msg) from busy
    except BaseException:
        os.close(descriptor)
        raise
    try:
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"{os.getpid()}\n".encode())
    except OSError:
        # The claim is the flock, not the text; a pid that could not be
        # recorded costs the next refusal its name and nothing else.
        logger.debug("could not record this process in %s", lock, exc_info=True)
    return descriptor


def _quoted_atom(engine: Runtime, value: str) -> str:
    row = engine.once(
        "term_string(Atom, Text, [quoted(true), ignore_ops(true)])",
        Atom=value,
    )
    if row is None or row.get("truth") is False or not isinstance(row.get("Text"), str):
        msg = f"SWI-Prolog could not quote schema head {value!r}"
        raise MettaError(msg)
    return row["Text"]


def _acquire_module(
    path: Path, schema: Mapping[str, int]
) -> tuple[str, tuple[tuple[str, int], ...], bool]:
    # Clause order controls atoms() order, so preserve the schema mapping's
    # insertion order in the pool key instead of reusing a differently ordered
    # module with the same head/arity pairs.
    key = tuple(schema.items())
    digest = hashlib.blake2s(str(path).encode("utf-8"), digest_size=6).hexdigest()
    with _STATE_LOCK:
        available = _MODULE_POOL.get(key)
        if available:
            module = available.pop()
            logger.debug("reusing persistent module %s", module)
            return module, key, False
        identifier = next(_MODULE_IDS)
    module = f"metta_persistent_{digest}_{identifier}"
    logger.debug("allocating persistent module %s", module)
    return module, key, True


def _return_module(key: tuple[tuple[str, int], ...], module: str) -> None:
    with _STATE_LOCK:
        _MODULE_POOL.setdefault(key, []).append(module)


def _helper_names(module: str, schema: Mapping[str, int]) -> dict[str, str]:
    occupied = set(schema.items())
    occupied.update(
        (f"{prefix}{head}", arity)
        for head, arity in schema.items()
        for prefix in ("assert_", "asserta_", "retract_", "retractall_")
    )

    prefix = f"{module}_private"
    while any((f"{prefix}_{name}", arity) in occupied for name, arity in _HELPER_ARITIES.items()):
        prefix += "_x"
    return {name: f"{prefix}_{name}" for name in _HELPER_ARITIES}


def _module_source(
    module: str,
    mutex: str,
    schema: Mapping[str, int],
    quoted_heads: Mapping[str, str],
    helpers: Mapping[str, str],
) -> str:
    declarations = []
    schema_clauses = []
    for head, arity in schema.items():
        quoted = quoted_heads[head]
        if arity:
            fields = ", ".join(f"arg{index}:any" for index in range(1, arity + 1))
            declarations.append(f":- persistent {quoted}({fields}).")
        else:
            declarations.append(f":- persistent {quoted}.")
        schema_clauses.append(f"{helpers['schema']}({quoted}, {arity}).")

    return f"""
:- module({module}, []).
:- use_module(library(persistency)).

{os.linesep.join(declarations)}

{os.linesep.join(schema_clauses)}

{helpers["decode"]}([Tag, Value], Native) :-
    ( Tag == s ; Tag == "s" ), !,
    ( atom(Value) -> Native = Value
    ; string(Value) -> atom_string(Native, Value)
    ; throw(error(type_error(persistent_symbol, Value), _))
    ).
{helpers["decode"]}([Tag, Value], Native) :-
    ( Tag == g ; Tag == "g" ), !,
    ( string(Value) -> Native = Value
    ; atom(Value) -> atom_string(Value, Native)
    ; throw(error(type_error(persistent_string, Value), _))
    ).
{helpers["decode"]}([Tag, Value], Value) :-
    ( Tag == n ; Tag == "n" ), !,
    ( number(Value) -> true
    ; throw(error(type_error(persistent_number, Value), _))
    ).
{helpers["decode"]}([Tag, Value], Native) :-
    ( Tag == b ; Tag == "b" ), !,
    ( ( Value == true ; Value == "true" ; Value == '@'(true) )
    -> Native = true
    ; ( Value == false ; Value == "false" ; Value == '@'(false) )
    -> Native = false
    ; throw(error(domain_error(boolean, Value), _))
    ).
{helpers["decode"]}(Wire, _) :-
    throw(error(type_error(persistent_native_wire, Wire), _)).

%The boolean atoms encode before the general atom clause, the shim's own
%ordering: on this engine the symbol true IS the boolean atom, every
%crossing canonicalizes, and the journal follows the engine so the
%durable format holds plain terms and no private wrapper.
{helpers["encode"]}(true, ["b", true]) :- !.
{helpers["encode"]}(false, ["b", false]) :- !.
{helpers["encode"]}(Value, ["n", Value]) :- number(Value), !.
{helpers["encode"]}(Value, ["g", Value]) :- string(Value), !.
{helpers["encode"]}(Value, ["s", Text]) :-
    atom(Value), !,
    atom_string(Value, Text).
{helpers["encode"]}(Value, _) :-
    throw(error(type_error(persistent_native, Value), _)).

{helpers["fact"]}(Head, Wire) :-
    {helpers["schema"]}(Head, Arity),
    functor(Fact, Head, Arity),
    call(Fact),
    Fact =.. [_ | Args],
    maplist({helpers["encode"]}, Args, ArgWires),
    atom_string(Head, HeadText),
    Wire = ["e", [["s", HeadText] | ArgWires]].

{helpers["all"]}(Wires) :-
    with_mutex({mutex},
        findall(Wire,
            ( {helpers["schema"]}(Head, _), {helpers["fact"]}(Head, Wire) ),
            Wires)).

{helpers["match"]}(Head, Wires) :-
    {helpers["schema"]}(Head, _),
    with_mutex({mutex},
        findall(Wire, {helpers["fact"]}(Head, Wire), Wires)).

{helpers["add"]}(Head, Wires) :-
    {helpers["schema"]}(Head, Arity),
    length(Wires, Arity),
    maplist({helpers["decode"]}, Wires, Args),
    atom_concat(assert_, Head, AssertHead),
    Goal =.. [AssertHead | Args],
    with_mutex({mutex}, transaction(call(Goal))).

% ONE row, because removal is multiset subtraction and this store is a
% multiset: assert_/N appends, so two identical facts are two rows and two
% removals. library(persistency) generates both updater predicates, and this is the
% retract_/N one: db_retract/1 is retract/1 under the library's own mutex,
% and it journals retract(Fact) rather than retractall(Fact, Count), which
% the journal validator above already accepts. It also answers what it did,
% so the separate presence probe that used to stand in front of the
% retractall goes, and with it a check-then-act window.
{helpers["remove"]}(Head, Wires, Removed) :-
    {helpers["schema"]}(Head, Arity),
    length(Wires, Arity),
    maplist({helpers["decode"]}, Wires, Args),
    atom_concat(retract_, Head, RetractHead),
    Retract =.. [RetractHead | Args],
    with_mutex({mutex},
        ( transaction(call(Retract))
        -> Removed = 1
        ; Removed = 0
        )).

%A world or staged provider transaction has already validated every member
%and computed its exact multiset delta. Apply the whole delta under the same
%module mutex and one SWI transaction, removing before adding just like the
%native world delta. library(persistency) journals each updater as an ordinary
%retract/assert record, so replay sees facts rather than an opaque world blob.
{helpers["apply_remove"]}([Head, Wires]) :-
    {helpers["schema"]}(Head, Arity),
    length(Wires, Arity),
    maplist({helpers["decode"]}, Wires, Args),
    atom_concat(retract_, Head, RetractHead),
    Retract =.. [RetractHead | Args],
    ( call(Retract)
    -> true
    ;  Fact =.. [Head | Args],
       throw(error(existence_error(persistent_fact, Fact), _))
    ).

{helpers["apply_add"]}([Head, Wires]) :-
    {helpers["schema"]}(Head, Arity),
    length(Wires, Arity),
    maplist({helpers["decode"]}, Wires, Args),
    atom_concat(assert_, Head, AssertHead),
    Assert =.. [AssertHead | Args],
    call(Assert).

{helpers["apply_diff"]}(Removed, Added) :-
    with_mutex({mutex},
        transaction(( maplist({helpers["apply_remove"]}, Removed),
                      maplist({helpers["apply_add"]}, Added) ))).

{helpers["clear_one"]}(Head, Arity) :-
    length(Args, Arity),
    atom_concat(retractall_, Head, RetractHead),
    Retract =.. [RetractHead | Args],
    call(Retract).

{helpers["clear"]} :-
    with_mutex({mutex},
        transaction(
            forall({helpers["schema"]}(Head, Arity),
                   {helpers["clear_one"]}(Head, Arity)))).

{helpers["validate_native"]}(Value) :- number(Value), !.
{helpers["validate_native"]}(Value) :- string(Value), !.
{helpers["validate_native"]}(Value) :- atom(Value), !.
{helpers["validate_native"]}(Value) :-
    throw(error(type_error(persistent_native, Value), _)).

{helpers["validate_pattern"]}(Value) :- var(Value), !.
{helpers["validate_pattern"]}(Value) :-
    {helpers["validate_native"]}(Value).

{helpers["validate_fact"]}(Fact) :-
    callable(Fact),
    functor(Fact, Head, Arity),
    ( {helpers["schema"]}(Head, Arity)
    -> Fact =.. [_ | Args], maplist({helpers["validate_native"]}, Args)
    ; throw(error(domain_error(persistent_schema, Fact), _))
    ).

{helpers["validate_pattern_fact"]}(Fact) :-
    callable(Fact),
    functor(Fact, Head, Arity),
    ( {helpers["schema"]}(Head, Arity)
    -> Fact =.. [_ | Args], maplist({helpers["validate_pattern"]}, Args)
    ; throw(error(domain_error(persistent_schema, Fact), _))
    ).

{helpers["validate_action"]}(created(Created)) :- number(Created), !.
{helpers["validate_action"]}(assert(Fact)) :- !,
    {helpers["validate_fact"]}(Fact).
{helpers["validate_action"]}(asserta(Fact)) :- !,
    {helpers["validate_fact"]}(Fact).
{helpers["validate_action"]}(retract(Fact)) :- !,
    {helpers["validate_fact"]}(Fact).
{helpers["validate_action"]}(retractall(Fact, Count)) :- !,
    ( integer(Count), Count >= 0
    -> true
    ; throw(error(type_error(persistent_retract_count, Count), _))
    ),
    {helpers["validate_pattern_fact"]}(Fact).
{helpers["validate_action"]}(Action) :-
    throw(error(domain_error(persistent_journal_action, Action), _)).

%A journal schema name lives only as the top-level functor inside the action's
%fact term. SWI's replay checks that whole term against persistent/3 before it
%asserts or retracts it, so arguments are data and must remain untouched.
%[source: https://github.com/SWI-Prolog/swipl-devel/blob/399af1d254797b944fa9940fb684020288d8b767/library/persistency.pl#L381-L413;
%commit=ee43d4a0585593b4f40d0c3c0557db8214688829]
{helpers["rename_fact"]}(Original, Renames, Renamed, Seen) :-
    Original =.. [Head | Args],
    ( memberchk([Head, NewHead], Renames)
    -> Renamed =.. [NewHead | Args],
       Seen = [Head]
    ;  Renamed = Original,
       Seen = []
    ).

{helpers["rename_action"]}(created(Created), _, created(Created), []) :- !.
{helpers["rename_action"]}(assert(Original), Renames, assert(Renamed), Seen) :- !,
    {helpers["rename_fact"]}(Original, Renames, Renamed, Seen).
{helpers["rename_action"]}(asserta(Original), Renames, asserta(Renamed), Seen) :- !,
    {helpers["rename_fact"]}(Original, Renames, Renamed, Seen).
{helpers["rename_action"]}(retract(Original), Renames, retract(Renamed), Seen) :- !,
    {helpers["rename_fact"]}(Original, Renames, Renamed, Seen).
{helpers["rename_action"]}(retractall(Original, Count), Renames,
                           retractall(Renamed, Count), Seen) :- !,
    {helpers["rename_fact"]}(Original, Renames, Renamed, Seen).
{helpers["rename_action"]}(Action, _, Action, []).

{helpers["validate_replay_stream"]}(Stream, Renames, Seen0, Seen) :-
    read_term(Stream, Action, [module(db)]),
    ( Action == end_of_file
    -> Seen = Seen0
    ;  {helpers["rename_action"]}(Action, Renames, Renamed, ActionSeen),
       {helpers["validate_action"]}(Renamed),
       ( ActionSeen = [Old], memberchk(Old, Seen0)
       -> Seen1 = Seen0
       ;  append(ActionSeen, Seen0, Seen1)
       ),
       {helpers["validate_replay_stream"]}(Stream, Renames, Seen1, Seen)
    ).

{helpers["validate_replay"]}(File, Renames, Seen) :-
    ( exists_file(File)
    -> setup_call_cleanup(
           open(File, read, Stream, [encoding(utf8)]),
           {helpers["validate_replay_stream"]}(Stream, Renames, [], Seen),
           close(Stream))
    ; Seen = []
    ).

{helpers["validate_replay_text"]}(Text, Renames, Seen) :-
    setup_call_cleanup(
        open_string(Text, Stream),
        {helpers["validate_replay_stream"]}(Stream, Renames, [], Seen),
        close(Stream)).

%Use library(persistency)'s own canonical action format so the migrated file
%is another ordinary journal, not a private second format.
%[source: https://github.com/SWI-Prolog/swipl-devel/blob/399af1d254797b944fa9940fb684020288d8b767/library/persistency.pl#L526-L535;
%commit=ee43d4a0585593b4f40d0c3c0557db8214688829]
{helpers["write_action"]}(Stream, Action) :-
    \\+ \\+ ( numbervars(Action, 0, _, [singletons(true)]),
            format(Stream, '~W.~n',
                   [ Action,
                     [ quoted(true),
                       numbervars(true),
                       module(db)
                     ]
                   ])
          ).

{helpers["rewrite_replay_stream"]}(In, Out, Renames, Seen0, Seen) :-
    read_term(In, Action, [module(db)]),
    ( Action == end_of_file
    -> Seen = Seen0
    ;  {helpers["rename_action"]}(Action, Renames, Renamed, ActionSeen),
       {helpers["validate_action"]}(Renamed),
       {helpers["write_action"]}(Out, Renamed),
       ( ActionSeen = [Old], memberchk(Old, Seen0)
       -> Seen1 = Seen0
       ;  append(ActionSeen, Seen0, Seen1)
       ),
       {helpers["rewrite_replay_stream"]}(In, Out, Renames, Seen1, Seen)
    ).

{helpers["rewrite_replay"]}(File, Target, Renames, Seen) :-
    setup_call_cleanup(
        open(File, read, In, [encoding(utf8)]),
        setup_call_cleanup(
            open(Target, write, Out, [encoding(utf8)]),
            {helpers["rewrite_replay_stream"]}(In, Out, Renames, [], Seen),
            close(Out)),
        close(In)).

{helpers["validate_stream"]}(Stream) :-
    read_term(Stream, Action, [module(db)]),
    ( Action == end_of_file
    -> true
    ; {helpers["validate_action"]}(Action),
      {helpers["validate_stream"]}(Stream)
    ).

{helpers["validate"]}(File) :-
    ( exists_file(File)
    -> setup_call_cleanup(
           open(File, read, Stream, [encoding(utf8)]),
           {helpers["validate_stream"]}(Stream),
           close(Stream))
    ; true
    ).

{helpers["validate_text"]}(Text) :-
    setup_call_cleanup(
        open_string(Text, Stream),
        {helpers["validate_stream"]}(Stream),
        close(Stream)).

%A record is complete when it carries its terminating full stop, so the
%reader that DEMANDS one is the one to ask. read_term/2 over a string stream
%raises syntax_error(end_of_file) without it; read_term_from_atom/3 does not,
%and its documentation says so outright: "It is not required for Atom to end
%with a full-stop" [source:
%https://www.swi-prolog.org/pldoc/doc_for?object=read_term_from_atom/3].
%That is why `assert` and `assert(edge(a,b))` used to read as COMPLETE
%records and be refused rather than repaired. A tail of nothing but layout
%reads as end_of_file and is incomplete too: no record was finished in it.
{helpers["tail_status"]}(Text, Status) :-
    catch(
        setup_call_cleanup(
            open_string(Text, Stream),
            read_term(Stream, Term, [module(db)]),
            close(Stream)),
        error(syntax_error(_), _),
        Term = '$metta_torn_record'),
    (   ( Term == '$metta_torn_record' ; Term == end_of_file )
    ->  Status = incomplete
    ;   Status = complete
    ).

{helpers["attach"]}(File, Sync) :- db_attach(File, [sync(Sync)]).
{helpers["sync"]} :- with_mutex({mutex}, db_sync(reload)).
%db_sync(close) flushes and closes the journal stream now; the next write
%reopens it, so this is the on-demand checkpoint under any sync mode.
{helpers["flush"]} :- with_mutex({mutex}, ignore(db_sync(close))).
{helpers["compact"]} :- with_mutex({mutex}, ignore(db_sync(gc))).
{helpers["close"]} :- with_mutex({mutex}, db_detach).
"""


def _validated_fact_head(
    atom: Atom,
    verb: str,
    schema: Mapping[str, int],
) -> tuple[str, tuple[Atom, ...]]:
    if not (isinstance(atom, Expression) and atom.children and isinstance(atom.head, Symbol)):
        msg = f"cannot {verb} {atom}: a persistent fact is a ground (head arguments...) expression"
        raise MettaError(msg)
    head = atom.head.name
    if head not in schema:
        msg = (
            f"cannot {verb} {atom}: unknown persistent head {head!r}; "
            f"declared heads are {list(schema)!r}"
        )
        raise MettaError(msg)
    expected = schema[head]
    if len(atom.args) != expected:
        msg = f"cannot {verb} {atom}: {head!r} has arity {expected}, got {len(atom.args)}"
        raise MettaError(msg)
    return head, atom.args


def _persistent_argument_wire(
    atom: Atom,
    argument: Atom,
    index: int,
    verb: str,
) -> list[Any]:
    if not _is_ground(argument):
        msg = f"cannot {verb} {atom}: argument {index} ({argument}) is not ground"
        raise MettaError(msg)
    if isinstance(argument, Symbol):
        return argument.to_wire()
    if isinstance(argument, Grounded):
        value = argument.value
        if type(value) in (bool, int, float, str):
            return argument.to_wire()
        msg = (
            f"cannot {verb} {atom}: argument {index} is a live Python "
            f"object of type {type(value).__name__}; persistent facts "
            "accept only numbers, symbols, strings, and booleans"
        )
        raise MettaError(msg)
    msg = (
        f"cannot {verb} {atom}: argument {index} ({argument}) is not "
        "a number, symbol, string, or boolean"
    )
    raise MettaError(msg)


@dataclass
class _TransactionState:
    """One thread's optimistic journal transaction."""

    base: tuple[Atom, ...]
    atoms: list[Atom]


def _ordered_surplus(left: list[Atom], right: list[Atom]) -> list[Atom]:
    """Ordered multiset subtraction for hashable persistent facts."""
    remaining = Counter(right)
    surplus = []
    for atom in left:
        if remaining[atom]:
            remaining[atom] -= 1
        else:
            surplus.append(atom)
    return surplus


def _same_multiset(left: tuple[Atom, ...], right: tuple[Atom, ...]) -> bool:
    """Whether two persistent snapshots carry the same facts and counts."""
    return Counter(left) == Counter(right)


class PersistentFactSpace(SpaceProvider):
    """A fixed-schema fact space backed by an append-only text journal.

    Facts are limited to the declared heads and arities. Every argument must
    be a native value carried by MeTTa's wire: a number, symbol, string, or
    boolean. Live Python objects and nested expressions are refused because
    they cannot survive journal replay.

    The journal is schema-bound. Generated memory mutations run inside
    transaction/1, so an append error rolls them back. Journal I/O itself is
    not transactional, so any updater error makes the provider refuse later
    writes until it is closed, checked, and reopened. Compound writes and
    matching reads use a mutex unique to the generated Prolog module. Only one
    process may own a journal path at a time. This class also refuses a second
    live attachment to the same path within the current process.

    ``rename={"old": "new"}`` is a one-open schema migration. Every old head
    must occur in the journal and every new head must be the only declared
    replacement. The constructor validates and atomically rewrites all replay
    actions before attachment, then discards the map. Open the migrated journal
    normally after that; passing the same map again refuses its now-absent old
    name instead of installing an alias.

    `sync` picks the write-sync mode, performance by default: "none" (the
    default) buffers journal writes, the fastest mode; a clean close()
    flushes everything, and only a crash loses the buffered tail. When a
    write matters mid-run, flush() is the on-demand checkpoint: it pushes
    the tail to disk right then, whatever the mode. The standing modes
    are the safety ladder: "flush" flushes the stream after every write,
    so facts survive the death of this process; "close" also closes the
    file after every write, the slowest mode, whose extra promise is a
    journal always consistent for external editing. Measured on this
    machine at 3000 adds: none 169k adds/s, flush 166k, close 86k, so
    per-write crash safety costs about two percent and the always-closed
    journal costs half.
    """

    _SYNC_MODES = ("none", "flush", "close")

    def delivers(self) -> tuple[str, str]:
        """Declare the engine hooks as this exclusively attached store's stream."""
        return ("per-write-exactly", "ordered")

    def __init__(
        self,
        path: str | os.PathLike[str],
        schema: Mapping[str, int],
        sync: str = "none",
        *,
        rename: Mapping[str, str] | None = None,
    ) -> None:
        if sync not in self._SYNC_MODES:
            msg = f"sync must be one of {list(self._SYNC_MODES)}, got {sync!r}"
            raise ValueError(msg)
        self._sync_mode = sync
        self._path = _journal_path(path)
        self._schema = _validated_schema(schema)
        self._replay_rename = _validated_replay_rename(rename, self._schema)
        self._runtime = runtime()
        self._janus = self._runtime._janus
        self._module = ""
        self._module_key: tuple[tuple[str, int], ...] = ()
        self._module_loaded = False
        self._module_released = False
        self._call_lock = threading.RLock()
        self._transaction_local = threading.local()
        self._closed = True
        self._claimed = False
        self._lock_fd: int | None = None
        self._write_failure: str | None = None

        with _STATE_LOCK:
            if self._path in _ACTIVE_PATHS:
                msg = f"persistent journal {self._path} is already attached in this process"
                raise MettaError(msg)
            _ACTIVE_PATHS.add(self._path)
            self._claimed = True

        with ExitStack() as rollback:
            rollback.callback(self._release_path)
            # Before tail repair, before migration, before attach: each of
            # those rewrites or replaces the journal, and the claim has to be
            # older than the first of them.
            self._lock_fd = _claim_journal_lock(self._path)
            rollback.callback(self._release_lock)
            self._module, self._module_key, is_new = _acquire_module(self._path, self._schema)
            self._mutex = f"{self._module}_mutex"
            self._helpers = _helper_names(self._module, self._schema)
            if is_new:
                quoted_heads = {head: _quoted_atom(self._runtime, head) for head in self._schema}
                source = _module_source(
                    self._module,
                    self._mutex,
                    self._schema,
                    quoted_heads,
                    self._helpers,
                )
                self._runtime.consult(f"{self._module}.pl", data=source)
            self._module_loaded = True
            with ExitStack() as unattached:
                unattached.callback(self._release_module)
                self._validate_or_repair_tail()
                self._migrate_replay_rename()
                self._call(
                    "attach",
                    "File, Sync",
                    {"File": str(self._path), "Sync": self._sync_mode},
                    require_open=False,
                )
                unattached.pop_all()
            rollback.callback(self._rollback_attachment)
            self._closed = False
            rollback.pop_all()

    def match(self, pattern: Atom) -> Iterator[Atom]:
        if (
            isinstance(pattern, Expression)
            and isinstance(pattern.head, Symbol)
            and pattern.head.name in self._schema
        ):
            return iter(self._visible_facts(pattern.head.name))
        return self.atoms()

    def atoms(self) -> Iterator[Atom]:
        return iter(self._visible_facts())

    def snapshot(self) -> tuple[Atom, ...]:
        """Capture one immutable journal view under the provider call lock."""
        with self._call_lock:
            return tuple(self._visible_facts())

    def add(self, atom: Atom) -> None:
        head, wires = self._fact_parts(atom, "add", durable=True)
        transaction_state = self._transaction_state()
        if transaction_state is not None:
            transaction_state.atoms.append(atom)
            return
        self._write_call("add", "Head, Wires", {"Head": head, "Wires": wires})

    def remove(self, atom: Atom) -> bool:
        head, wires = self._fact_parts(atom, "remove")
        transaction_state = self._transaction_state()
        if transaction_state is not None:
            try:
                index = transaction_state.atoms.index(atom)
            except ValueError:
                return False
            transaction_state.atoms.pop(index)
            return True
        row = self._write_call(
            "remove",
            "Head, Wires, Removed",
            {"Head": head, "Wires": wires},
        )
        removed = row.get("Removed", _MISSING)
        if removed not in (0, 1):
            msg = f"persistent remove returned an invalid verdict: {removed!r}"
            raise MettaError(msg)
        return removed == 1

    def clear(self) -> None:
        """Remove every stored fact while keeping the declared schema."""
        transaction_state = self._transaction_state()
        if transaction_state is not None:
            transaction_state.atoms.clear()
            return
        self._write_call("clear")

    def begin(self) -> None:
        """Start one optimistic provider transaction for the current thread."""
        with self._call_lock:
            parent = self._transaction_state()
            base = tuple(self._facts()) if parent is None else tuple(parent.atoms)
            self._transaction_stack().append(_TransactionState(base, list(base)))

    def commit(self) -> None:
        """Journal the staged multiset diff, refusing a concurrent stale base."""
        transaction_state = self._require_transaction_state("commit")
        removed = _ordered_surplus(
            list(transaction_state.base), transaction_state.atoms
        )
        added = _ordered_surplus(
            transaction_state.atoms, list(transaction_state.base)
        )
        try:
            stack = self._transaction_stack()
            if len(stack) > 1:
                stack[-2].atoms = list(transaction_state.atoms)
            else:
                self._commit_diff(transaction_state.base, removed, added)
        finally:
            self._transaction_stack().pop()

    def rollback(self) -> None:
        """Discard the current thread's unjournaled staged facts."""
        self._require_transaction_state("rollback")
        self._transaction_stack().pop()

    def commit_world(
        self,
        base: tuple[Atom, ...],
        removed: list[Atom],
        added: list[Atom],
    ) -> None:
        """Journal one immutable world's ordinary fact diff."""
        if self._transaction_state() is not None:
            msg = "cannot commit a reified world inside a provider transaction"
            raise MettaError(msg)
        self._commit_diff(base, removed, added)

    def sync(self) -> None:
        """Reload journal changes that are safe to apply to this attachment."""
        self._write_call("sync")

    def flush(self) -> None:
        """Push buffered journal writes to disk right now, whatever the
        sync mode: the on-demand checkpoint for the fast default.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        self._write_call("flush")

    def compact(self) -> None:
        """Ask library(persistency) to garbage-collect obsolete actions."""
        self._write_call("compact")

    def close(self) -> None:
        """Detach the journal, clear its facts, and return its module for reuse."""
        with self._call_lock:
            if self._closed:
                return
            self._call("close")
            self._closed = True
            self._release_path()
            self._release_module()
            self._release_lock()
            logger.debug("closed persistent journal %s", self._path)

    def _validate_journal(self) -> None:
        if self._replay_rename:
            self._call(
                "validate_replay",
                "File, Renames, _Seen",
                {
                    "File": str(self._path),
                    "Renames": self._replay_rename_pairs(),
                },
                require_open=False,
            )
            return
        self._call(
            "validate",
            "File",
            {"File": str(self._path)},
            require_open=False,
        )

    def _read_invalid_journal(self, validation_error: MettaError) -> bytes:
        try:
            return self._path.read_bytes()
        except OSError as read_error:
            msg = (
                f"cannot inspect persistent journal {self._path} after "
                f"validation failed: {read_error}"
            )
            raise MettaError(msg) from validation_error

    def _terminal_tail(
        self,
        contents: bytes,
        validation_error: MettaError,
    ) -> tuple[int, bytes]:
        boundary = contents.rfind(b"\n") + 1
        tail = contents[boundary:]
        if not tail:
            msg = (
                f"persistent journal {self._path} is corrupt before its "
                f"terminal record. Correct or remove the malformed record "
                f"reported by the engine, then reopen it: {validation_error}"
            )
            raise EngineError(msg) from validation_error
        return boundary, tail

    def _require_incomplete_tail(
        self,
        tail: bytes,
        validation_error: MettaError,
    ) -> None:
        try:
            tail_text = tail.decode("utf-8")
        except UnicodeDecodeError:
            # A process can stop between bytes of one UTF-8 code point. The
            # exact bytes still go to the backup.
            return
        status_row = self._call(
            "tail_status",
            "Text, Status",
            {"Text": tail_text},
            require_open=False,
        )
        status = status_row.get("Status")
        if not isinstance(status, str):
            msg = f"persistent journal tail inspection returned an invalid status: {status!r}"
            raise EngineError(msg) from validation_error
        if status != "incomplete":
            msg = (
                f"persistent journal {self._path} ends with a complete but "
                f"invalid record, not a truncated record. Correct or remove "
                f"the terminal bytes reported by the engine, then reopen it: "
                f"{validation_error}"
            )
            raise EngineError(msg) from validation_error

    def _validated_prefix(
        self,
        contents: bytes,
        boundary: int,
        validation_error: MettaError,
    ) -> None:
        try:
            prefix = contents[:boundary].decode("utf-8")
        except UnicodeDecodeError as prefix_error:
            msg = (
                f"persistent journal {self._path} contains invalid UTF-8 "
                f"before its terminal record. Restore or repair the bytes "
                f"before byte {boundary}, then reopen it."
            )
            raise EngineError(msg) from prefix_error
        try:
            if self._replay_rename:
                self._call(
                    "validate_replay_text",
                    "Text, Renames, _Seen",
                    {
                        "Text": prefix,
                        "Renames": self._replay_rename_pairs(),
                    },
                    require_open=False,
                )
            else:
                self._call(
                    "validate_text",
                    "Text",
                    {"Text": prefix},
                    require_open=False,
                )
        except MettaError as prefix_error:
            msg = (
                f"persistent journal {self._path} is corrupt before its "
                f"incomplete terminal record. Correct or remove the "
                f"malformed newline-terminated record reported by the "
                f"engine, then reopen it: {prefix_error}"
            )
            raise EngineError(msg) from validation_error

    def _save_tail_backup(self, tail: bytes) -> Path:
        backup = Path(f"{self._path}.tail")
        try:
            with backup.open("xb") as stream:
                stream.write(tail)
                stream.flush()
                os.fsync(stream.fileno())
            _sync_directory(backup.parent)
        except FileExistsError as backup_error:
            msg = (
                f"cannot recover persistent journal {self._path}: tail "
                f"backup {backup} already exists. Move that backup aside, "
                f"then reopen the journal."
            )
            raise MettaError(msg) from backup_error
        except OSError as backup_error:
            msg = (
                f"cannot save the incomplete terminal record from "
                f"persistent journal {self._path} to {backup}: "
                f"{backup_error}"
            )
            raise MettaError(msg) from backup_error
        return backup

    def _truncate_journal(self, boundary: int, backup: Path) -> None:
        try:
            with self._path.open("r+b") as stream:
                stream.truncate(boundary)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as truncate_error:
            msg = (
                f"saved the incomplete terminal record from {self._path} "
                f"to {backup}, but could not truncate the journal to byte "
                f"{boundary}: {truncate_error}. Repair the journal before "
                f"reopening it."
            )
            raise MettaError(msg) from truncate_error

    def _validate_or_repair_tail(self) -> None:
        """Validate the journal or remove one incomplete final record.

        library(persistency) writes one complete action and its newline in one
        call. A non-newline suffix is therefore recoverable only when the
        complete prefix validates independently. The removed bytes are kept
        beside the journal so recovery never destroys the only copy.
        """
        try:
            self._validate_journal()
        except MettaError as caught:
            validation_error = caught
            logger.debug(
                "persistent journal validation failed; inspecting its tail",
                exc_info=True,
            )
        else:
            return
        contents = self._read_invalid_journal(validation_error)
        boundary, tail = self._terminal_tail(contents, validation_error)
        self._require_incomplete_tail(tail, validation_error)
        self._validated_prefix(contents, boundary, validation_error)
        backup = self._save_tail_backup(tail)
        self._truncate_journal(boundary, backup)
        self._validate_journal()
        logger.warning(
            "recovered persistent journal %s by saving %d terminal bytes "
            "to %s and truncating at byte %d",
            self._path,
            len(tail),
            backup,
            boundary,
        )

    def _replay_rename_pairs(self) -> list[list[str]]:
        return [[old, new] for old, new in self._replay_rename.items()]

    def _raise_absent_replay_names(self, names: list[str]) -> None:
        rendered = ", ".join(repr(name) for name in names)
        msg = (
            f"replay rename map for {self._path} names absent old "
            f"head(s) {rendered}; remove the absent name(s) from rename= or "
            "correct them, then reopen the journal"
        )
        raise MettaError(msg)

    def _migrate_replay_rename(self) -> None:
        """Materialize one validated name migration before SWI attaches."""
        if not self._replay_rename:
            return
        if not self._path.exists():
            self._raise_absent_replay_names(list(self._replay_rename))

        try:
            descriptor, temp_name = tempfile.mkstemp(
                prefix=f".{self._path.name}.rename-",
                dir=self._path.parent,
            )
        except OSError as exc:
            msg = f"cannot stage replay rename for {self._path}: {exc}"
            raise MettaError(msg) from exc
        os.close(descriptor)
        temporary = Path(temp_name)
        replaced = False
        rename_pairs = self._replay_rename_pairs()
        try:
            row = self._call(
                "rewrite_replay",
                "File, Target, Renames, Seen",
                {
                    "File": str(self._path),
                    "Target": str(temporary),
                    "Renames": rename_pairs,
                },
                require_open=False,
            )
            seen = row.get("Seen", _MISSING)
            if not isinstance(seen, (list, tuple)) or not all(
                isinstance(name, str) for name in seen
            ):
                msg = f"replay rename returned invalid seen heads: {seen!r}"
                raise EngineError(msg)
            missing = [name for name in self._replay_rename if name not in seen]
            if missing:
                self._raise_absent_replay_names(missing)

            temporary.chmod(stat.S_IMODE(self._path.stat().st_mode))
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            temporary.replace(self._path)
            replaced = True
            self._replay_rename = {}
            _sync_directory(self._path.parent)
            self._validate_journal()
        except OSError as exc:
            if replaced:
                msg = (
                    f"replay rename replaced {self._path}, but could not sync "
                    f"its directory: {exc}. Inspect the journal, then reopen "
                    "without rename=."
                )
            else:
                msg = (
                    f"cannot atomically migrate replay names in {self._path}: "
                    f"{exc}. The journal was not replaced; correct the cause "
                    "and retry with rename=."
                )
            raise MettaError(msg) from exc
        finally:
            if not replaced:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    # Keep the migration error; no caller waits on this cleanup.
                    logger.exception(
                        "could not remove failed replay-rename staging file %s",
                        temporary,
                    )

        logger.info(
            "migrated persistent journal %s replay heads: %s",
            self._path,
            rename_pairs,
        )

    def _write_call(
        self,
        helper: str,
        arguments: str = "",
        inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._call_lock:
            if self._closed:
                msg = f"persistent fact space for {self._path} is closed"
                raise MettaError(msg)
            if self._write_failure is not None:
                msg = (
                    f"persistent fact space for {self._path} is unusable for "
                    f"writes because an earlier {self._write_failure}. Close "
                    f"it, repair the journal if needed, and reopen it."
                )
                raise MettaError(msg)
            try:
                return self._call(helper, arguments, inputs)
            except BaseException as exc:
                self._write_failure = (
                    f"{helper} operation failed and journal consistency could "
                    f"not be proved: {type(exc).__name__}: {exc}"
                )
                logger.exception(
                    "persistent %s failed for %s; later writes are refused",
                    helper,
                    self._path,
                )
                raise

    def _facts(self, head: str | None = None) -> list[Atom]:
        if head is None:
            row = self._call("all", "Wires")
        else:
            row = self._call(
                "match",
                "Head, Wires",
                {"Head": head},
            )
        wires = row.get("Wires", _MISSING)
        if not isinstance(wires, (list, tuple)):
            msg = f"persistent enumeration returned invalid wires: {wires!r}"
            raise MettaError(msg)

        facts: list[Atom] = []
        for wire in wires:
            try:
                fact = _atom_from_wire(wire)
            except (TypeError, ValueError) as exc:
                msg = f"persistent journal {self._path} returned malformed fact wire {wire!r}"
                raise MettaError(msg) from exc
            if not isinstance(fact, Expression):
                msg = f"persistent journal {self._path} returned non-fact {fact!r}"
                raise MettaError(msg)
            facts.append(fact)
        return facts

    def _visible_facts(self, head: str | None = None) -> list[Atom]:
        """Return this thread's staged view, or the durable provider view."""
        transaction_state = self._transaction_state()
        if transaction_state is None:
            return self._facts(head)
        facts = list(transaction_state.atoms)
        if head is None:
            return facts
        return [
            atom
            for atom in facts
            if isinstance(atom, Expression)
            and isinstance(atom.head, Symbol)
            and atom.head.name == head
        ]

    def _transaction_state(self) -> _TransactionState | None:
        """Return the current thread's provider transaction, if any."""
        stack = getattr(self._transaction_local, "stack", ())
        return stack[-1] if stack else None

    def _transaction_stack(self) -> list[_TransactionState]:
        """Return this thread's nested provider savepoint stack."""
        stack = getattr(self._transaction_local, "stack", None)
        if stack is None:
            stack = []
            self._transaction_local.stack = stack
        return stack

    def _require_transaction_state(self, operation: str) -> _TransactionState:
        transaction_state = self._transaction_state()
        if transaction_state is None:
            msg = f"cannot {operation} persistent journal {self._path}: no transaction is active"
            raise MettaError(msg)
        return transaction_state

    def _commit_diff(
        self,
        base: tuple[Atom, ...],
        removed: list[Atom],
        added: list[Atom],
    ) -> None:
        """Validate and journal one base-relative multiset delta under one lock."""
        with self._call_lock:
            current = tuple(self._facts())
            if not _same_multiset(current, base):
                msg = (
                    f"persistent journal {self._path} changed after its base was "
                    "captured; refusing a stale diff"
                )
                raise MettaError(msg)
            removed_parts = [
                list(self._fact_parts(atom, "commit world removal"))
                for atom in removed
            ]
            added_parts = [
                list(self._fact_parts(atom, "commit world addition", durable=True))
                for atom in added
            ]
            if removed_parts or added_parts:
                self._write_call(
                    "apply_diff",
                    "Removed, Added",
                    {"Removed": removed_parts, "Added": added_parts},
                )

    def _fact_parts(
        self,
        atom: Atom,
        verb: str,
        *,
        durable: bool = False,
    ) -> tuple[str, list[list[Any]]]:
        head, arguments = _validated_fact_head(atom, verb, self._schema)
        if durable:
            for argument in arguments:
                if isinstance(argument, Symbol) and self._runtime.once(
                    "metta_live_state_cell(Cell)", Cell=argument.name
                ):
                    msg = (
                        f"cannot {verb} {atom}: {argument} is a live State "
                        "cell whose process-local value cannot survive "
                        "journal close and replay"
                    )
                    raise MettaError(msg)
        wires = [
            _persistent_argument_wire(atom, argument, index, verb)
            for index, argument in enumerate(arguments, start=1)
        ]
        return head, wires

    def _call(
        self,
        helper: str,
        arguments: str = "",
        inputs: dict[str, Any] | None = None,
        *,
        require_open: bool = True,
    ) -> dict[str, Any]:
        with self._call_lock:
            if require_open and self._closed:
                msg = f"persistent fact space for {self._path} is closed"
                raise MettaError(msg)
            predicate = self._helpers[helper]
            goal = f"{self._module}:{predicate}"
            if arguments:
                goal += f"({arguments})"
            row = self._runtime.once(goal, **({} if inputs is None else inputs))
            if not row:
                msg = (
                    f"SWI-Prolog refused persistent operation {helper!r} for "
                    f"{self._path}: {goal} failed"
                )
                raise MettaError(msg)
            return row

    def _release_path(self) -> None:
        if not self._claimed:
            return
        with _STATE_LOCK:
            _ACTIVE_PATHS.discard(self._path)
        self._claimed = False

    def _release_lock(self) -> None:
        """Drop this provider's interprocess claim on the journal pathname."""
        descriptor, self._lock_fd = self._lock_fd, None
        if descriptor is None:
            return
        os.close(descriptor)

    def _rollback_attachment(self) -> None:
        self._call("close", require_open=False)
        self._release_module()

    def _release_module(self) -> None:
        if not self._module_loaded or self._module_released:
            return
        _return_module(self._module_key, self._module)
        self._module_released = True
        logger.debug("returned persistent module %s to its schema pool", self._module)
