"""Purpose: fixed-schema fact spaces backed by SWI persistency journals.
The provider keeps native MeTTa facts in typed dynamic predicates, writes
every change through library(persistency), and replays the journal when a
new provider attaches to the same path.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import hashlib
import itertools
import os
import threading
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import petta as pkg

from .atoms import Atom, Expr, Gnd, Sym, from_wire, is_ground
from .errors import PettaError
from .foreign import SpaceProvider

__all__ = ["PersistentFactSpace"]


_MODULE_IDS = itertools.count()
_STATE_LOCK = threading.Lock()
_ACTIVE_PATHS: set[Path] = set()

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
    "clear_one": 2,
    "clear": 0,
    "validate_native": 1,
    "validate_fact": 1,
    "validate_action": 1,
    "validate_stream": 1,
    "validate": 1,
    "attach": 2,
    "sync": 0,
    "flush": 0,
    "compact": 0,
    "close": 0,
}

_MISSING = object()


def _validated_schema(schema: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(schema, Mapping):
        raise TypeError(
            f"schema must map fact head names to arities, got {type(schema).__name__}"
        )
    copied: dict[str, int] = {}
    for head, arity in schema.items():
        if not isinstance(head, str):
            raise TypeError(f"schema head names must be strings, got {head!r}")
        if "\x00" in head:
            raise ValueError(f"schema head {head!r} contains a null byte")
        if isinstance(arity, bool) or not isinstance(arity, int) or arity < 0:
            raise ValueError(
                f"schema arity for {head!r} must be a non-negative integer, "
                f"got {arity!r}"
            )
        if (head, arity) in _PERSISTENCY_API:
            raise ValueError(
                f"schema head {head!r}/{arity} conflicts with library(persistency)"
            )
        copied[head] = arity
    if not copied:
        raise ValueError("schema must declare at least one fact head")

    for head, arity in copied.items():
        for prefix in ("assert_", "asserta_", "retract_", "retractall_"):
            generated = f"{prefix}{head}"
            if copied.get(generated) == arity:
                raise ValueError(
                    f"schema head {generated!r}/{arity} conflicts with the "
                    f"generated updater for {head!r}/{arity}"
                )
    return copied


def _journal_path(path: str | os.PathLike[str]) -> Path:
    resolved = Path(path).expanduser().resolve()
    if resolved.exists() and resolved.is_dir():
        raise IsADirectoryError(f"persistent journal path is a directory: {resolved}")
    if not resolved.parent.exists():
        raise FileNotFoundError(
            f"persistent journal parent does not exist: {resolved.parent}"
        )
    if not resolved.parent.is_dir():
        raise NotADirectoryError(
            f"persistent journal parent is not a directory: {resolved.parent}"
        )
    return resolved


def _janus_module() -> Any:
    if pkg.janus is None:
        pkg.MeTTa()
    if pkg.janus is None:
        raise RuntimeError("PeTTa started without a Janus module")
    return pkg.janus


def _quoted_atom(janus: Any, value: str) -> str:
    row = janus.query_once(
        "term_string(Atom, Text, [quoted(true), ignore_ops(true)])",
        {"Atom": value},
    )
    if row is None or row.get("truth") is False or not isinstance(row.get("Text"), str):
        raise PettaError(f"SWI-Prolog could not quote schema head {value!r}")
    return row["Text"]


def _new_module(path: Path) -> str:
    digest = hashlib.blake2s(str(path).encode("utf-8"), digest_size=6).hexdigest()
    with _STATE_LOCK:
        identifier = next(_MODULE_IDS)
    return f"petta_persistent_{digest}_{identifier}"


def _helper_names(module: str, schema: Mapping[str, int]) -> dict[str, str]:
    occupied = {(head, arity) for head, arity in schema.items()}
    for head, arity in schema.items():
        for prefix in ("assert_", "asserta_", "retract_", "retractall_"):
            occupied.add((f"{prefix}{head}", arity))

    prefix = f"{module}_private"
    while any(
        (f"{prefix}_{name}", arity) in occupied
        for name, arity in _HELPER_ARITIES.items()
    ):
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
    with_mutex({mutex}, call(Goal)).

{helpers["remove"]}(Head, Wires, Removed) :-
    {helpers["schema"]}(Head, Arity),
    length(Wires, Arity),
    maplist({helpers["decode"]}, Wires, Args),
    Fact =.. [Head | Args],
    atom_concat(retractall_, Head, RetractHead),
    Retract =.. [RetractHead | Args],
    with_mutex({mutex},
        ( once(call(Fact))
        -> call(Retract), Removed = 1
        ; Removed = 0
        )).

{helpers["clear_one"]}(Head, Arity) :-
    length(Args, Arity),
    atom_concat(retractall_, Head, RetractHead),
    Retract =.. [RetractHead | Args],
    call(Retract).

{helpers["clear"]} :-
    with_mutex({mutex},
        forall({helpers["schema"]}(Head, Arity),
               {helpers["clear_one"]}(Head, Arity))).

{helpers["validate_native"]}(Value) :- number(Value), !.
{helpers["validate_native"]}(Value) :- string(Value), !.
{helpers["validate_native"]}(Value) :- atom(Value), !.
{helpers["validate_native"]}(Value) :-
    throw(error(type_error(persistent_native, Value), _)).

{helpers["validate_fact"]}(Fact) :-
    callable(Fact),
    functor(Fact, Head, Arity),
    ( {helpers["schema"]}(Head, Arity)
    -> Fact =.. [_ | Args], maplist({helpers["validate_native"]}, Args)
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
    integer(Count),
    {helpers["validate_fact"]}(Fact).
{helpers["validate_action"]}(Action) :-
    throw(error(domain_error(persistent_journal_action, Action), _)).

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

{helpers["attach"]}(File, Sync) :- db_attach(File, [sync(Sync)]).
{helpers["sync"]} :- with_mutex({mutex}, db_sync(reload)).
%db_sync(close) flushes and closes the journal stream now; the next write
%reopens it, so this is the on-demand checkpoint under any sync mode.
{helpers["flush"]} :- with_mutex({mutex}, ignore(db_sync(close))).
{helpers["compact"]} :- with_mutex({mutex}, ignore(db_sync(gc))).
{helpers["close"]} :- with_mutex({mutex}, db_detach).
"""


class PersistentFactSpace(SpaceProvider):
    """A fixed-schema fact space backed by an append-only text journal.

    Facts are limited to the declared heads and arities. Every argument must
    be a native value carried by PeTTa's wire: a number, symbol, string, or
    boolean. Live Python objects and nested expressions are refused because
    they cannot survive journal replay.

    The journal is schema-bound. Its writes sit outside transaction/1, so a
    compound update is not a transactional file operation. Compound writes
    and matching reads use a mutex unique to the generated Prolog module.
    Only one process may own a journal path at a time. This class also refuses
    a second live attachment to the same path within the current process.

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

    def __init__(
        self,
        path: str | os.PathLike[str],
        schema: Mapping[str, int],
        sync: str = "none",
    ) -> None:
        if sync not in self._SYNC_MODES:
            raise ValueError(
                f"sync must be one of {list(self._SYNC_MODES)}, got {sync!r}"
            )
        self._sync_mode = sync
        self._path = _journal_path(path)
        self._schema = _validated_schema(schema)
        self._janus = _janus_module()
        self._module = _new_module(self._path)
        self._mutex = f"{self._module}_mutex"
        self._helpers = _helper_names(self._module, self._schema)
        self._call_lock = threading.RLock()
        self._closed = True
        self._claimed = False

        quoted_heads = {head: _quoted_atom(self._janus, head) for head in self._schema}
        source = _module_source(
            self._module,
            self._mutex,
            self._schema,
            quoted_heads,
            self._helpers,
        )

        with _STATE_LOCK:
            if self._path in _ACTIVE_PATHS:
                raise PettaError(
                    f"persistent journal {self._path} is already attached in "
                    "this process"
                )
            _ACTIVE_PATHS.add(self._path)
            self._claimed = True

        try:
            self._janus.consult(f"{self._module}.pl", data=source)
            self._call(
                "validate",
                "File",
                {"File": str(self._path)},
                require_open=False,
            )
            self._call(
                "attach",
                "File, Sync",
                {"File": str(self._path), "Sync": self._sync_mode},
                require_open=False,
            )
        except BaseException:
            self._release_path()
            raise
        self._closed = False

    def match(self, pattern: Atom) -> Iterator[Atom]:
        if (
            isinstance(pattern, Expr)
            and isinstance(pattern.head, Sym)
            and pattern.head.name in self._schema
        ):
            return iter(self._facts(pattern.head.name))
        return self.atoms()

    def atoms(self) -> Iterator[Atom]:
        return iter(self._facts())

    def add(self, atom: Atom) -> None:
        head, wires = self._fact_parts(atom, "add")
        self._call("add", "Head, Wires", {"Head": head, "Wires": wires})

    def remove(self, atom: Atom) -> bool:
        head, wires = self._fact_parts(atom, "remove")
        row = self._call(
            "remove",
            "Head, Wires, Removed",
            {"Head": head, "Wires": wires},
        )
        removed = row.get("Removed", _MISSING)
        if removed not in (0, 1):
            raise PettaError(
                f"persistent remove returned an invalid verdict: {removed!r}"
            )
        return removed == 1

    def clear(self) -> None:
        """Remove every stored fact while keeping the declared schema."""
        self._call("clear")

    def sync(self) -> None:
        """Reload journal changes that are safe to apply to this attachment."""
        self._call("sync")

    def flush(self) -> None:
        """Push buffered journal writes to disk right now, whatever the
        sync mode: the on-demand checkpoint for the fast default."""
        self._call("flush")

    def compact(self) -> None:
        """Ask library(persistency) to garbage-collect obsolete actions."""
        self._call("compact")

    def close(self) -> None:
        """Detach the journal and remove its facts from the generated module."""
        with self._call_lock:
            if self._closed:
                return
            self._call("close")
            self._closed = True
            self._release_path()

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
            raise PettaError(
                f"persistent enumeration returned invalid wires: {wires!r}"
            )

        facts = []
        for wire in wires:
            try:
                fact = from_wire(wire)
            except (TypeError, ValueError) as exc:
                raise PettaError(
                    f"persistent journal {self._path} returned malformed fact "
                    f"wire {wire!r}"
                ) from exc
            if not isinstance(fact, Expr):
                raise PettaError(
                    f"persistent journal {self._path} returned non-fact {fact!r}"
                )
            facts.append(fact)
        return facts

    def _fact_parts(self, atom: Atom, verb: str) -> tuple[str, list[list[Any]]]:
        if not (
            isinstance(atom, Expr) and atom.children and isinstance(atom.head, Sym)
        ):
            raise PettaError(
                f"cannot {verb} {atom}: a persistent fact is a ground "
                "(head arguments...) expression"
            )

        head = atom.head.name
        if head not in self._schema:
            raise PettaError(
                f"cannot {verb} {atom}: unknown persistent head {head!r}; "
                f"declared heads are {list(self._schema)!r}"
            )
        expected = self._schema[head]
        if len(atom.args) != expected:
            raise PettaError(
                f"cannot {verb} {atom}: {head!r} has arity {expected}, "
                f"got {len(atom.args)}"
            )

        wires = []
        for index, argument in enumerate(atom.args, start=1):
            if not is_ground(argument):
                raise PettaError(
                    f"cannot {verb} {atom}: argument {index} ({argument}) is not ground"
                )
            if isinstance(argument, Sym):
                wires.append(argument.to_wire())
                continue
            if isinstance(argument, Gnd):
                value = argument.value
                if type(value) in (bool, int, float, str):
                    wires.append(argument.to_wire())
                    continue
                raise PettaError(
                    f"cannot {verb} {atom}: argument {index} is a live Python "
                    f"object of type {type(value).__name__}; persistent facts "
                    "accept only numbers, symbols, strings, and booleans"
                )
            raise PettaError(
                f"cannot {verb} {atom}: argument {index} ({argument}) is not "
                "a number, symbol, string, or boolean"
            )
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
                raise PettaError(f"persistent fact space for {self._path} is closed")
            predicate = self._helpers[helper]
            goal = f"{self._module}:{predicate}"
            if arguments:
                goal += f"({arguments})"
            row = self._janus.query_once(goal, {} if inputs is None else inputs)
            if row is None or row.get("truth") is False:
                raise PettaError(
                    f"SWI-Prolog refused persistent operation {helper!r} for "
                    f"{self._path}: {goal} failed"
                )
            return row

    def _release_path(self) -> None:
        if not self._claimed:
            return
        with _STATE_LOCK:
            _ACTIVE_PATHS.discard(self._path)
        self._claimed = False
