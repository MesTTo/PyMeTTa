"""Purpose: own the engine bootstrap and bridge. Consults MeTTa and the shim
exactly once per process, serializes calls made on the home engine, lets a
thread holding its own engine run without that lock, lets Janus give bare
threads temporary engines for relational calls, and turns Prolog exceptions
into the library's own errors for both Python surfaces.
Assumes:
  - JanusBridge.engine returns the documented integer engine identifier
    [source 2026-08-14:
    https://www.swi-prolog.org/pldoc/man?section=janus-thread-call-prolog]
Guarantees:
  - Runtime.builtins carries the supplied native space identity into the
    catalogue query [tested:
    test_a_parametric_namespace_lists_resolves_and_inherits_native_functions;
    commit=WORKTREE].
  - runtime() with no configuration request reads the published runtime
    without acquiring the home-engine lock, so a child can finish while its
    scope joins on that engine [tested:
    test_scope_joins_a_cancelled_request_on_a_borrowed_async_worker;
    commit=c6e1198c490a824b96f6fc6e1c0622a542917024].
  - Runtime.once/iter/apply/do install lib_thread:scope_call/2 at engine
    boundaries and preserve its reserved cancellation identity [tested:
    test_deadline_uses_the_library_scope_and_stops_a_running_engine,
    test_an_outer_deadline_is_not_lost_at_a_nested_scope; commit=c6e1198c490a824b96f6fc6e1c0622a542917024].
  - importing metta does not import janus_swi until an engine-backed API is
    used [tested test_package_import_does_not_require_janus]
  - Runtime classifies only the shim's exact reserved exception term shape
    [tested test_exception_names_nested_in_other_terms_stay_engine_errors,
    test_reserved_exception_shape_maps_by_kind]
  - reader errors expose the reader's diagnostic instead of Janus's unknown
    wrapper text [tested test_run_syntax_error_is_loud], and a reader failure
    that named a line carries it as MettaSyntaxError.line rather than only
    inside that text [tested: test_a_json_error_line_names_its_input_line,
    error_kinds:a_syntax_envelope_carries_its_line; commit=52e95b50cc5acdc0e41f97b444ab244ad1301433]
  - a value or type control signal reaches Python as the sentence its thrower
    composed, so the JSON codec's own refusal is what a caller reads
    [tested: test_a_json_run_refuses_a_live_host_object_with_the_codecs_sentence;
    commit=8d67307403c1e41ccf058bd3c8d4c079dd7cf7d5]
  - engine_thread attaches only a bare foreign thread and detaches exactly
    the engine it attached; an async landing can attach without waiting for
    a home-engine call that is itself awaiting that landing [tested:
    test_engine_thread_owns_only_its_attachment,
    test_a_transaction_commits_async_launch_before_its_landing;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - every engine refusal this seat classifies arrives carrying the catalog
    row's .ground and .remedy for its kind, with the remedy's <field> holes
    filled from that very ball, and a kind whose row was removed still raises
    its own class with neither
    [tested: extensions/python/tests/repository/test_refusal_rows.py;
    commit=f33b7ab0200e6dc74c88fb4c7f827bf545a447ed]
  - a rehydrated MettaError keeps the __cause__ it was raised with, so the
    boundary term never displaces the diagnosis [tested
    test_a_watcher_failure_is_distinguishable_from_a_failed_write]
  - a group made only of MettaError leaves rehydrates whole, while an
    operation author's exception group remains an EngineError [tested:
    test_multiple_watcher_failures_are_grouped_after_every_delivery,
    test_an_op_authors_exception_group_stays_wrapped; commit=d8673a8488a111f1c01c778af3ed11b845c284a8]
  - a failed MeTTa assertion arrives as AssertionFailure and an engine fault
    as EngineError, neither an instance of the other [tested
    test_a_failing_assertion_is_a_different_exception_from_an_engine_fault]
  - a failing comparison over answers carries its two directed bag differences
    into .missing and .excess as decoded atoms, and a form that computed
    neither reports None for both [tested:
    test_a_two_sided_difference_arrives_as_two_bags,
    test_a_form_with_no_bag_comparison_reports_neither_bag; commit=71de27a76dd16684941e3e090de0d17299d96493]
  - the restricted-space formal maps to SpaceCapabilityError before the
    generic operation and engine classifiers [tested:
    test_a_restricted_space_cannot_reach_what_its_base_does_not_publish;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a call whose inputs the engine cannot accept fails on its OWN call, by
    kind and naming where in the input the offending text sits, and the next
    call is unaffected through every interface [tested:
    test_text_with_no_utf8_encoding_is_refused_by_kind,
    test_a_refused_crossing_does_not_fail_the_next_call,
    test_no_door_leaves_the_next_call_carrying_the_refusal; commit=3b82643dd18ad5153bca71fa0c4bd09d59b0b7d0]
  - a Python exception raised inside the engine classifies the same through
    the goal-string call and the predicate call [tested:
    test_an_enumeration_refuses_answers,
    test_an_enumeration_refuses_answers_through_the_term_door_too;
    commit=3b82643dd18ad5153bca71fa0c4bd09d59b0b7d0]
  - the functional Janus API is selected by live thread identity, never a
    recyclable numeric identifier [tested:
    test_a_recycled_thread_identifier_never_selects_the_janus_fast_path;
    commit=af5821f5ffb7ce186e516706f003d02f5c1d3b4a]
  - a bare thread's relational call uses Janus's temporary engine without the
    home-engine lock, so a blocking call cannot freeze unrelated engine work
    [tested:
    test_a_bare_thread_blocking_in_the_engine_does_not_freeze_other_calls;
    commit=6ffd7e3bbfc653f10817c48f30cd56572960e43f]
  - booted() publishes only after the shim, Python prelude, and contract
    ontology all finish; a failed prelude or contract install retries whole
    on the next construction [tested:
    test_a_failed_python_runtime_install_retries_whole;
    commit=7f1b7a27ed5044c1df8885f4cdf831654dff25fc]
  - engine_message delivers an engine message as a metta.engine record at the
    level its SWI kind maps to, and neither a broken handler nor an unmapped
    kind reaches the engine [tested:
    test_an_engine_warning_becomes_a_warning_record,
    test_an_engine_error_becomes_an_error_record,
    test_a_broken_handler_cannot_poison_the_crossing,
    test_the_kind_map_covers_swis_own_levels; commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41]
  - the package root logger carries the library NullHandler from this module,
    so a record nobody configured a handler for does not reach
    logging.lastResort and print a second copy of a line SWI already wrote
    [tested: test_the_package_root_carries_the_library_null_handler;
    commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41]
  - a child that inherited a booted engine across fork() refuses at its first
    crossing, naming the fork and the remedy, rather than answering out of
    half a runtime; the same handler resets the locks fork left held so the
    child reaches that refusal instead of deadlocking [tested:
    test_a_forked_child_refuses_the_inherited_engine,
    test_a_fork_resets_the_engine_locks; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
Guarded by:
  - _LOCK serializes runtime creation and every call made on the HOME engine.
    A thread holding its own attached engine takes no process lock: it shares
    no engine with any other thread, and MeTTa's shared structures already
    carry their own Prolog mutexes because hyperpose workers have always
    reached the same database [tested
    test_define_from_two_threads_is_serialized]
  - query_once and query on a bare foreign thread take no process lock because
    Janus attaches and detaches a private temporary engine around that call
    [source: https://www.swi-prolog.org/pldoc/man?section=janus-thread-call-prolog]
  - CONSULT_LOCK and the startup events publish completed consultation
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib
import logging
import os
import sys
import threading
import traceback
from collections import deque
from collections.abc import Hashable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager, nullcontext, suppress
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn, Protocol, cast

from metta._lazy import lazy

if TYPE_CHECKING:
    import metta._spaces.lifetime as _scope
else:
    _scope = lazy('metta._spaces.lifetime')

from metta._atoms.model import Atom
from metta._atoms.wire import _atom_from_wire
from metta._catalog.bounds import config
from metta._errors.errors import (
    AssertionFailure,
    EngineError,
    Ground,
    MettaError,
    MettaOperationError,
    MettaSyntaxError,
    Remedy,
    ResourceLimitError,
    RestraintError,
    SpaceCapabilityError,
    refusal_classes,
    refusing,
)

logger = logging.getLogger(__name__)

# The library-author NullHandler, on the package's root logger rather than on
# this module's. Without it a record with no configured handler reaches
# logging.lastResort, a StreamHandler at WARNING, so an engine warning that
# SWI has already printed to stderr would print a SECOND time from Python.
# It sits here rather than in metta/__init__.py because importing logging is
# not free at package import and every logger in this package belongs to a
# module that imports this one.
logging.getLogger("metta").addHandler(logging.NullHandler())

#: Engine messages arrive here. The name is "metta.engine" and not this
#: module's own "metta._binding.runtime": it is the ENGINE speaking, and a program
#: filtering or formatting its messages should not have to know which file
#: carries the bridge.
_ENGINE_LOGGER = logging.getLogger("metta.engine")

#: SWI's message kinds against logging's levels. SWI's kinds are names rather
#: than a numeric scale, so the mapping is by name, and a kind with no row is
#: INFO, which is where banner and help belong. `information` is a second
#: informational kind and not a typo for the first: `time/1`, `explain/1` and
#: `shell/2` all print at it [source: SWI-Prolog 10.1.13
#: library/statistics.pl:72,352, library/explain.pl:97, library/shell.pl:149].
_MESSAGE_LEVELS = {
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "informational": logging.INFO,
    "information": logging.INFO,
    "debug": logging.DEBUG,
}


def engine_message(kind: str, text: str, file: str, line: int) -> bool:
    """Deliver one engine message as a ``metta.engine`` log record.

    The shim's ``user:thread_message_hook/3`` calls this and then FAILS, so
    SWI still prints the message itself. This is an additional reader, not a
    replacement.

    It runs on the thread that emitted the message, and that thread is one
    Python drove into Prolog: the hook clause is thread-local and belongs to
    the thread that consulted the shim, so a message emitted on a Prolog
    worker thread finds no clause and prints as it always did. That is the
    whole thread-safety argument, and it is why nothing here has to ask
    whether Python is reachable.

    Nothing raised here may cross back into the engine, because it would
    poison whichever crossing happened to be running. A fault while logging
    is logging's own business, so this takes logging's own policy, the one
    ``logging.Handler.handleError`` applies.
    """
    try:
        _ENGINE_LOGGER.log(
            _MESSAGE_LEVELS.get(kind, logging.INFO),
            # The engine's text is DATA, never a format string: a message
            # naming a percentage would otherwise be a formatting error.
            # The rendered lines end in the newline SWI would have printed,
            # and a log record's message does not carry its own line break.
            "%s",
            text.rstrip("\n"),
            # The engine's own vocabulary on the record, so a filter selects
            # on the kind SWI used and a formatter can print the location its
            # stderr line carries. Not `pathname` and `lineno`: those are
            # LogRecord's own fields for the CALL SITE, which is this file.
            extra={
                "metta_kind": kind,
                "metta_file": file or None,
                "metta_line": line if line >= 0 else None,
            },
        )
    except Exception:  # noqa: BLE001  -- a logging fault must not reach Prolog
        if logging.raiseExceptions:
            traceback.print_exc(file=sys.stderr)
    return True


def heartbeat_tick() -> None:
    """Enter Python so CPython can run the signal handlers it has queued.

    The engine's interrupt poll, called by ``prolog:heartbeat/0`` every
    ``config.heartbeat_interval`` inferences. The body is empty on purpose:
    only CPython runs CPython's signal handlers, it runs them between
    bytecodes on the main thread, and nothing enters CPython while Prolog is
    spinning. Crossing at all is the whole mechanism, so a Ctrl-C during a
    long evaluation raises KeyboardInterrupt instead of waiting for the
    evaluation to end.

    The rung below is janus's own ``janus_swi.heartbeat(N)``, which arms the
    same SWI flag with a hook calling its own empty ``heartbeat_tick``. This
    seat arms its own hook instead, because a hook that is not counted cannot
    be subtracted, and ``MeTTa.stats()`` reports the block's work rather than
    the poll's [tested: test_a_measurement_is_the_same_with_the_poll_dense].
    """


def _is_metta_failure(error: BaseException) -> bool:
    """Whether one exception, including every leaf of a group, is ours."""
    if isinstance(error, MettaError):
        return True
    return isinstance(error, BaseExceptionGroup) and all(
        _is_metta_failure(member) for member in error.exceptions
    )


def _unencodable(inputs: Any) -> str | None:
    """Where a janus input holds text with no UTF-8 encoding, described.

    Python allows an unpaired surrogate in a str, and every surrogateescape
    decode makes them: os.listdir over a filename whose bytes are not UTF-8
    hands back exactly this. UTF-8 has no encoding for one, so the conversion
    into a Prolog term fails inside janus's C.

    Walked only after a crossing has already failed, with an explicit stack
    rather than recursion because the input is the caller's structure and may
    nest arbitrarily. That structure may also be CYCLIC -- a list holding
    itself is a thing a caller can build and hand over -- and this runs while
    reporting an error, which is the worst place to spin, so containers are
    visited once by identity. Nothing on the succeeding path pays for this.
    """
    pending: list[tuple[str, Any]] = [("", inputs)]
    seen: set[int] = set()
    while pending:
        where, value = pending.pop()
        if isinstance(value, (Mapping, list, tuple)):
            if id(value) in seen:
                continue
            seen.add(id(value))
        if isinstance(value, str):
            if value.isascii():
                continue
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                return (
                    f"{where or 'the input'} contains an unpaired surrogate at "
                    f"position {exc.start}, which has no UTF-8 encoding"
                )
        elif isinstance(value, Mapping):
            pending.extend((f"{where}[{key!r}]" if where else str(key), item)
                           for key, item in value.items())
        elif isinstance(value, (list, tuple)):
            # The predicate calls pass their arguments as the root tuple, so
            # the top level reads "argument 2" rather than a bare "[2]".
            pending.extend((f"{where}[{index}]" if where else f"argument {index}", item)
                           for index, item in enumerate(value))
    return None


_LOCK = threading.RLock()
# Reusable, so the call path picks a shared object instead of building a
# context manager on a path measured at 4.13M calls per second.
_NULL_LOCK: AbstractContextManager[None] = nullcontext()


class _CallLocks(threading.local):
    """Whether this thread may use the functional Janus calls, and their lock.

    _LOCK serialises use of the home engine. A thread that attached its own
    engine through engine_thread() shares that engine with nobody, so
    serialising it against the home engine protects nothing and costs all the
    parallelism [tested:
    extensions/python/tests/ch14_seeing_your_program/test_engine_pool.py::test_pool_runs_work_concurrently].

    The choice is made when the engine is attached rather than putting a
    janus.engine() crossing on every call a pool worker makes.  The original
    A/B measured 72 ns for per-call dispatch against 43 ns for the direct
    lock and 59 ns for one thread-local read; the promoted probe and historical
    fixture are durable in benchmarks.thread_lock_dispatch [source:
    extensions/python/benchmarks/thread_lock_dispatch.py; commit=8fc1a4e204be4200862af7a3819a28a0d6279ea1].

    What makes running free safe is that MeTTa's shared structures already
    carry their own Prolog mutexes, because hyperpose workers have always
    reached the same database: '$metta_specializer' in specializer.pl,
    '$metta_native_storage' in spaces.pl, metta_loader around
    process_metta_string in filereader.pl, and a per-function mutex in
    lib_memo.pl. SWI keeps individual dynamic predicates consistent itself.
    """

    lock: AbstractContextManager[Any] = _LOCK


# Threads start on the class default. _thread_lock distinguishes a bare thread
# from the home thread before returning it, because the bare thread must use
# relational Janus calls on a temporary engine rather than the functional form.
_CALL_LOCKS = _CallLocks()

CONSULT_LOCK = threading.Lock()
CONSULTED = threading.Event()
_SHIM_LOADED = threading.Event()

# The failure sentinel for the functional calling convention: a private
# identity no predicate can answer, so a legitimate output is never
# mistaken for failure.
_FAILED = object()


class JanusBridge(Protocol):
    """The janus operations MeTTa uses across the package."""

    PrologError: type[Exception]

    def apply_once(self, module: str, predicate: str, *inputs: Any, fail: Any) -> Any:  # noqa: ARG002  -- the override preserves the SpaceProvider or runtime protocol signature
        del fail
        raise NotImplementedError

    def attach_engine(self) -> Any: ...
    def cmd(self, module: str, predicate: str, *inputs: Any) -> bool: ...
    def consult(self, path: str, data: str | None = None) -> Any: ...
    def detach_engine(self) -> Any: ...
    def engine(self) -> int: ...
    def prolog(self) -> Any: ...
    def query(
        self, goal: str, inputs: Mapping[str, Any] | None = None
    ) -> Iterator[dict[str, Any]]: ...
    def query_once(
        self, goal: str, inputs: Mapping[str, Any] | None = None
    ) -> dict[str, Any] | None: ...
    def version_str(self, version: int | None = None) -> str:
        del version
        raise NotImplementedError


class _EngineState:
    """Mutable process singleton state, changed only under engine locks."""

    def __init__(self) -> None:
        self.janus: JanusBridge | None = None
        self.runtime: Runtime | None = None
        # janus's own record release, captured when the deferred Term release
        # is installed. Held here rather than reached through the bridge at
        # drain time, because it is janus's PRIVATE primitive and the bridge
        # protocol describes the public surface.
        self.erase_record: Any = None


_STATE = _EngineState()

#: Which class this seat raises for each refusal kind, DERIVED from the
#: engine's own `(refusal ...)` rows through the generated table rather than
#: written out here. It used to be seven kinds against the engine's thirteen,
#: and the six it omitted -- `stack` and `source` among them -- arrived as a
#: bare EngineError with the ball's own sentence and nothing to react to
#: [source: extensions/python/metta/_errors/refusals.py:70; the two gaps were recorded in
#: tests/data/error-kinds.json until this table stopped being hand-written; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
_EXCEPTION_TYPES = refusal_classes()


def _reserved_message(kind: object, detail: object, fallback: str) -> str:
    """Say what a reserved exception means, in the caller's own terms.

    The thrown term is an envelope the Python side put there, so rendering
    it leaks janus framing: the caller who passed timeout=0.05 was reading
    `Unknown error term: metta_control_signal(time_limit,0.05)`.

    A bound may expire with no detail to name. That is SWI's own
    `inference_limit_exceeded` or `time_limit_exceeded` ball, which arrives
    unenveloped from a nested query and knows only which resource ran out;
    the sentence says exactly that rather than naming a limit of `None`.
    """
    if kind in ("syntax", "value", "type"):
        # The detail IS the refusal the thrower wrote: the reader's sentence,
        # or the codec's "JSON cannot carry ...". Without this the value and
        # type kinds fell through to the fallback, and a caller who asked the
        # JSON codec to carry a live host object read `Unknown error term:
        # metta_control_signal(type, "JSON cannot carry ...")` around the
        # sentence shim.pl's metta_py_json_rethrow/1 had already composed
        # [measured 2026-09-07].
        return detail if isinstance(detail, str) else fallback
    if kind == "time_limit":
        return (
            "the time limit was reached"
            if detail is None
            else f"the {detail} second time limit was reached"
        )
    if kind == "inference_limit":
        return (
            "the inference limit was reached"
            if detail is None
            else f"the {detail} inference limit was reached"
        )
    if kind == "interrupted":
        return "interrupt() stopped the evaluation"
    if kind == "restraint" and isinstance(detail, list) and len(detail) == 3:
        word, bound, call = detail
        return f"the ({word} {bound}) restraint declared for the table of {call} tripped"
    return fallback


def _restraint_fields(detail: object) -> tuple[str | None, int | None, str | None]:
    """The three fields a restraint signal carries: word, bound and call.

    lib_tabling throws `metta_control_signal(restraint, [Word, Bound, Call])`
    and janus hands the list over as a Python list; anything else is a
    detail this side does not know, and the error then carries only its
    sentence. Three typed values rather than a keyword dict, because the
    codec module compiles under mypyc as an option and mypyc refuses to pass
    a `dict[str, object]` as keywords typed `int | None`.
    """
    if isinstance(detail, list) and len(detail) == 3:
        word, bound, call = detail
        return (
            str(word),
            bound if isinstance(bound, int) and not isinstance(bound, bool) else None,
            str(call),
        )
    return (None, None, None)


def started() -> bool:
    """Whether a runtime exists, without starting one."""
    return _STATE.runtime is not None


def active_runtime() -> Runtime | None:
    """Return the runtime when one exists, without starting it."""
    return _STATE.runtime


def booted() -> bool:
    """Whether the engine and its shim are consulted in this process,
    without booting anything: the probe deferred work wants.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return _SHIM_LOADED.is_set()


#: How each platform's package manager installs SWI-Prolog, so the refusal
#: below can name a command rather than a requirement. Keyed by sys.platform.
# closed-set: decides; policy=how each platform's package manager installs SWI-Prolog, so a refusal names a command; reads=none, it is the source
_SWI_INSTALL = {
    "linux": "sudo apt install swi-prolog   (or your distribution's equivalent)",
    "darwin": "brew install swi-prolog",
    "win32": "winget install SWI-Prolog.SWI-Prolog",
}


def _no_engine(exc: ImportError) -> NoReturn:
    """Say what is missing and the command that fixes it.

    MeTTa runs on SWI-Prolog, which is a program rather than a Python package,
    so pip cannot install it and the failure lands here as janus failing to
    load its extension. What a user saw was the linker's own words --
    `ImportError: libswipl.so.9: cannot open shared object file` -- which name
    neither SWI-Prolog nor anything to do about it.

    The two cases need different answers and the difference is observable:
    with no `swipl` on PATH the engine is absent, and with one there it is
    present and janus was built against a DIFFERENT one. That second case is
    reachable by upgrading SWI after installing, because pip caches the wheel
    it built for you and reuses it [measured 2026-08-29: a clean venv on a box
    carrying SWI 10 installed a cached janus built against SWI 9 and failed on
    libswipl.so.9].
    """
    import shutil  # noqa: PLC0415  -- the failure path pays this, not the import

    swipl = shutil.which("swipl")
    install = _SWI_INSTALL.get(sys.platform, "install SWI-Prolog 9.3 or later")
    absent = isinstance(exc, ModuleNotFoundError) and exc.name == "janus_swi"
    if absent and swipl is None:
        # Nothing is in place: name both steps, in the order they must happen,
        # because the second cannot build without the first.
        msg = (
            f"MeTTa runs on SWI-Prolog, which is a program rather than a "
            f"Python package, so pip cannot install it and there is no "
            f"`swipl` on your PATH. Two steps, in this order:\n\n"
            f"    {install}\n"
            f"    pip install 'pymetta[engine]'\n"
        )
    elif absent:
        # The engine is here and only the bridge is missing, which is what a
        # plain `pip install pymetta` leaves on a machine that has SWI.
        msg = (
            f"SWI-Prolog is installed at {swipl}, and the Python bridge to it "
            f"is not. It is an extra, so that installing this package cannot "
            f"fail inside its build:\n\n"
            f"    pip install 'pymetta[engine]'\n"
        )
    else:
        # janus is installed and cannot load: it was built against a different
        # SWI than the one on this machine.
        msg = (
            f"SWI-Prolog is installed at {swipl or 'an unknown location'}, but "
            f"the janus_swi bridge was built against a different one and "
            f"cannot load. pip caches the copy it builds for you, so this is "
            f"what upgrading SWI after installing looks like. Rebuild the "
            f"bridge against the SWI you have:\n\n"
            f"    pip install --no-cache-dir --force-reinstall --no-binary "
            f"janus_swi janus_swi\n\n"
            f"The loader's own words were: {exc}"
        )
    raise EngineError(msg) from exc


# Work a finaliser handed over because it may not do it itself, drained by the
# next engine crossing at a point the library chose.
#
# WHY A FINALISER MAY NOT CALL PROLOG AT ALL. Three crashes, all the same
# shape. Two were janus_swi.Term.__del__ reaching PL_erase on a thread with no
# engine, where signalGCThread dereferences a null LD. The third was the cyclic
# collector running a finaliser that called rt.do/2 to close a cursor, in the
# middle of a Hypothesis draw, and SWI aborting on
# `assert(0)` at src/pl-rec.c:1560 in copy_record -- the default arm of its
# switch over record tags, which is what reading an ALREADY ERASED record looks
# like [source: SWI-Prolog 10.1.13 src/pl-rec.c:1560 copy_record, reached from
# janus_swi 1.5.3 janus.c py_unify_record;
# commit=2421d06e697daffb0797c307a798131616ebdd8e]. A finaliser runs
# at a point no caller chooses -- inside a garbage collection pass, on any
# thread, possibly while that thread is already inside another crossing -- and
# within one cycle the collector finalises members in no defined order, so the
# handle a finaliser wants to use can already be dead. None of that can be made
# safe one call site at a time. So a finaliser only ever appends here.
#
# A deque because its append and popleft are single bytecodes under the
# interpreter lock, so a finaliser never takes a lock and can never deadlock
# against a caller that already holds one.
_ERASE_RECORD = "erase"
_CALL_PREDICATE = "call"
_DEFERRED_WORK: deque[tuple[Any, ...]] = deque()
_DRAINING = threading.local()


def defer_engine_call(
    predicate: str, *inputs: Any, _enqueue: Any = _DEFERRED_WORK.append
) -> None:
    """Hand a shim call to the next engine crossing. For finalisers only.

    The queue holds a reference to every input, which is the point as much as
    the deferral is: a cursor handle kept alive here cannot be finalised before
    the call that uses it, which is the ordering the cyclic collector does not
    give.

    The enqueue itself is a DEFAULT ARGUMENT, for the reason `released` below
    binds this module's own function as one: see _defer_record_erase.
    """
    _enqueue((_CALL_PREDICATE, predicate, inputs))


def _defer_record_erase(record: int, _enqueue: Any = _DEFERRED_WORK.append) -> None:
    """Hand a janus record to the next engine crossing. For finalisers only.

    The deque's own `append` is a DEFAULT ARGUMENT, bound at definition time,
    because at
    interpreter shutdown CPython clears this module's globals while finalisers
    are still running. Reading the global instead, a Term that survived to that
    point reached `None.append(...)` and printed
    `AttributeError: 'NoneType' object has no attribute 'append'` out of a
    deallocator -- after pytest's session had ended, so no filter, no
    unraisable hook and no exit status could see it
    [measured 2026-09-07: a cursor left open at exit printed it on every run].
    `released` already binds THIS function the same way, citing asyncio's
    `_ProactorBasePipeTransport.__del__`; the binding just stopped one level
    too early. It binds the bound METHOD rather than the deque, which is what
    `_warn=warnings.warn` does in the precedent and what keeps this out of
    pylint's dangerous-default-value, a rule that is right about every mutable
    default except one whose identity is the point.
    """
    _enqueue((_ERASE_RECORD, record))


def _install_deferred_term_release(janus: Any) -> None:
    """Make janus never call into Prolog from a finaliser.

    THE DEFECT. janus_swi.Term.__del__ calls _swipl.erase, which is PL_erase,
    which unregisters the record's atoms; when the last reference to one goes,
    unregister_atom calls considerAGC, and once the margin is passed that calls
    signalGCThread, whose first act is truePrologFlag(PLFLAG_GCTHREAD) --
    LD->prolog_flag.mask.flags[..] with no null guard. On a thread with no
    engine LD is null and the process dies with SIGSEGV
    [source: SWI-Prolog 10.1.13 src/pl-incl.h:2839 truePrologFlag,
    src/pl-thread.c:7353 signalGCThread, src/pl-atom.c:1475 considerAGC;
    commit=2421d06e697daffb0797c307a798131616ebdd8e].

    THE SECOND DEFECT, in the same method. janus 1.5.3 clears `self.record`,
    an attribute nothing reads, where it means `self._record`
    [source: janus_swi 1.5.3 janus.py:485-488; commit=2421d06e697daffb0797c307a798131616ebdd8e]. A
    released
    Term therefore keeps a dangling record id, and anything that passes it back
    to Prolog reaches PL_recorded on freed memory, which is the copy_record
    assertion above. Clearing the attribute janus reads makes its own guard
    real: py_unify_record starts with `(v=PyLong_AsLongLong(r)) && ...`, so a
    zero record fails the crossing cleanly instead of reading freed memory.

    _swipl.engine() is PL_thread_self(), which returns -1 exactly when LD is
    null [source: SWI-Prolog 10.1.13 src/pl-thread.c:1739 PL_thread_self;
    commit=2421d06e697daffb0797c307a798131616ebdd8e]. That is the same variable whose nullness
    faults, read
    through janus's own public API rather than a proxy for it; the deferral
    does not consult it, because a finaliser on a thread that HAS an engine is
    still a finaliser and still unsafe, but the drain does.

    WHY A METHOD REPLACEMENT AND NOT A SUBCLASS. janus's C constructs every
    Term by calling the class it reads once from the janus module and caches in
    a static, and py_is_record tests a candidate with
    `cls == py_term_constructor()`, an identity comparison
    [source: janus_swi 1.5.3 janus.c:1547 py_term_constructor, :1627
    py_is_record; commit=2421d06e697daffb0797c307a798131616ebdd8e]. A subclass fails that test, so a
    Term of
    ours would stop being recognised as a record on the way back into Prolog.
    Replacing the method on the one class object janus already caches reaches
    every instance, including the ones its C creates, and changes no identity.

    This depends on janus PRIVATE structure -- the attribute name _record, and
    Term.__del__ being a Python method that can be replaced -- so
    test_the_janus_term_shape_the_deferred_release_depends_on fails loudly if a
    janus release changes either.
    [tested: test_the_janus_term_shape_the_deferred_release_depends_on,
    test_a_finalised_term_defers_its_record_and_goes_inert,
    test_deferred_work_is_drained_by_the_next_engine_crossing;
    commit=2421d06e697daffb0797c307a798131616ebdd8e]
    """
    term = getattr(janus, "Term", None)
    if term is None:
        # A bridge with no Term hands out no records, so there is nothing here
        # that could reach PL_erase. That is the substituted bridge the startup
        # tests install, and refusing it would make this repair decide whether
        # the engine can boot at all. A REAL janus that renamed Term is caught
        # by test_the_janus_term_shape_the_deferred_release_depends_on, which
        # asserts the release is installed on the janus this engine ships with.
        return
    swipl = getattr(janus, "_swipl", None)
    if swipl is None or not hasattr(term, "__del__"):
        msg = (
            "janus_swi exposes Term but not Term.__del__ and _swipl, which the "
            "deferred record release replaces; this janus is not the one this "
            "engine was written against (1.5.3)"
        )
        raise EngineError(msg)
    # Captured whether or not the release is already installed, so a second
    # bridge() over a fresh _STATE still has the primitive its queue needs.
    _STATE.erase_record = swipl.erase
    if getattr(term.__del__, "__module__", None) == __name__:
        return

    # _defer is bound as a default rather than read as a global, because a
    # finaliser can run during interpreter shutdown after this module's
    # namespace has been torn down. It is the same reason asyncio's transports
    # write `def __del__(self, _warn=warnings.warn)`
    # [source: https://github.com/python/cpython/blob/main/Lib/asyncio/proactor_events.py,
    # _ProactorBasePipeTransport.__del__;
    # commit=2421d06e697daffb0797c307a798131616ebdd8e].
    def released(
        self: Any,
        _defer: Any = _defer_record_erase,
    ) -> None:
        """Hand this Term's record to the next crossing and go inert."""
        record = getattr(self, "_record", 0)
        if not record:
            return
        self._record = 0
        _defer(record)

    # Named for what it does and renamed on installation, rather than defined
    # as `__del__`, which reads as a module-level dunder to the linter. The
    # installed marker is __module__, which the rename leaves at this module
    # and janus's own leaves at janus_swi.janus: a real property of the
    # function rather than an attribute bolted onto it, so both the
    # already-installed test above and the shape test read the same thing.
    released.__name__ = "__del__"
    released.__qualname__ = "Term.__del__"
    term.__del__ = released


# ------------------------------------------------------------------- fork

#: What a forked child is told, once, wherever it touches the engine. SWI's
#: own words are the ground, twice over. `fork/1` raises
#: `permission_error(fork, process, main)` off the only thread, because
#: "Forking a Prolog process with threads will typically deadlock because only
#: the calling thread is cloned in the fork, while all thread synchronization
#: are cloned" [source: https://www.swi-prolog.org/pldoc/doc_for?object=fork/1;
#: commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]. And the engine's own C, above `PL_cleanup_fork()`, the one
#: fork-related entry point it exposes: that call "must be called between
#: fork() and exec() to remove traces of Prolog that are not supposed to leak
#: into the new process ... the code cannot lock or unlock any mutex as the
#: behaviour of mutexes is undefined over fork()", and its `pthread_atfork`
#: repair sits behind an `O_ATFORK` its own comment marks "Not yet default"
#: [source: https://github.com/SWI-Prolog/swipl-devel/blob/master/src/pl-thread.c,
#: PL_cleanup_fork and reinit_threads_after_fork; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]. So the
#: supported shape is fork-then-exec, and a child that keeps running as a
#: second Prolog is not a shape SWI has.
#:
#: Typically, not always: a forked child on this box answered `!(+ 3 4)`,
#: `!(hyperpose ((+ 1 1) (+ 2 2)))` and `garbage_collect_atoms`
#: [measured 2026-09-07 with this handler removed; fixture=one boot, then
#: os.fork(), the child running each program and writing its answer down a
#: pipe; load 44 on 32 cores; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]. That is
#: exactly why the refusal is here rather than left to a crash: the inherited
#: engine LOOKS fine, and a child that reads a plausible answer out of half a
#: runtime is the silently-wrong class this library refuses. It is also why
#: this hook only FLIPS state and never raises: an exception inside an
#: after-fork handler is routed to sys.unraisablehook and the fork proceeds
#: anyway [source: CPython Modules/posixmodule.c, run_at_forkers calling
#: PyErr_FormatUnraisable; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb], so the loud refusal has to wait
#: for the next real crossing. PyTorch answers the same hazard the same way,
#: with `torch.cuda._is_in_bad_fork()` read lazily rather than at the fork
#: [source: https://github.com/pytorch/pytorch/blob/main/torch/csrc/utils/device_lazy_init.cpp,
#: register_fork_handler_for_device_init; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb].
_FORK_REFUSAL = (
    "this process inherited a Prolog engine across fork(), and SWI-Prolog "
    "does not survive one: the child clones only the forking thread while it "
    "clones every thread synchronisation, so the engine's own threads are "
    "gone and its locks may be held by nobody. Start the child with the "
    "forkserver or spawn start method, which metta.parallel.ProcessPool does "
    "for you, or boot the engine in the child rather than before the fork."
)


class _ForkPoisonError(Exception):
    """Never raised; it stands in for janus's PrologError on a dead bridge.

    Runtime names ``self._janus.PrologError`` in its except clauses, and an
    except clause is evaluated while an exception is already in flight, so
    that attribute has to answer a real exception class rather than refuse.
    """


class _ForkedBridge:
    """The bridge a forked child keeps: every janus entry point refuses.

    Substitution rather than a flag every crossing tests. A boolean read in
    ``Runtime.apply`` would be paid by every call in every process for a
    hazard almost none of them meet; replacing the bridge object costs the
    forked child alone and leaves the fast path exactly as it was.
    """

    #: Read, never called, so it stays a real attribute rather than a refusal.
    PrologError = _ForkPoisonError

    def __init__(self, parent: int) -> None:
        """Remember the pid this child was forked from, for the refusal to name."""
        self._parent = parent

    def _refuse(self, *_args: Any, **_kwargs: Any) -> NoReturn:
        msg = f"{_FORK_REFUSAL} (pid {os.getpid()} was forked from pid {self._parent})"
        raise EngineError(msg)

    def __getattr__(self, name: str) -> Any:
        """Answer the refusal for every janus name, present and future.

        Written as one hook rather than a dozen one-line methods because the
        set it has to cover is janus's, not this file's: a bridge call added
        to JanusBridge later is refused here without anyone remembering to.
        """
        if name.startswith("__"):
            raise AttributeError(name)
        return self._refuse


def forked() -> bool:
    """Whether this process inherited an engine across a fork, and so refuses."""
    return isinstance(_STATE.janus, _ForkedBridge)


def _refuse_inherited_engine() -> None:
    """Poison an inherited engine in the child, and reset what fork left held.

    Installed as ``os.register_at_fork(after_in_child=...)`` on this module's
    import, so the hazard is answered where it belongs -- any fork of a
    process that booted an engine -- rather than only for the pool that
    happens to know about it.

    The locks come first and are reset rather than released, the repair
    CPython applies to its own after a fork (``logging`` reinitialises its
    module and handler locks in ``_after_at_fork_child_reinit_locks``): only
    the forking thread survives, so a lock another thread held at fork time
    is held forever, and a child that deadlocked there would never reach the
    refusal below.

    The deferred queue is emptied rather than drained. Every record in it
    belongs to the PARENT's engine, and erasing one here is
    ``PL_erase`` against another process's memory.
    """
    global _LOCK, CONSULT_LOCK  # noqa: PLW0603  # pylint: disable=global-statement # a fork leaves the old locks held by vanished threads
    _LOCK = threading.RLock()
    _CallLocks.lock = _LOCK
    CONSULT_LOCK = threading.Lock()
    _DEFERRED_WORK.clear()
    _STATE.erase_record = None
    if _STATE.janus is None or isinstance(_STATE.janus, _ForkedBridge):
        return
    poison = cast("JanusBridge", _ForkedBridge(os.getppid()))
    _STATE.janus = poison
    if _STATE.runtime is not None:
        _STATE.runtime._janus = poison


os.register_at_fork(after_in_child=_refuse_inherited_engine)


def bridge() -> JanusBridge:
    """Import and return janus without starting the MeTTa runtime."""
    janus = _STATE.janus
    if janus is not None:
        return janus
    with _LOCK:
        if _STATE.janus is None:
            try:
                module = importlib.import_module("janus_swi")
            except ImportError as exc:
                _no_engine(exc)
            _install_deferred_term_release(module)
            _STATE.janus = cast(JanusBridge, module)
        return _STATE.janus


def _resolve_metta_path() -> str:
    """Locate the configured, bundled, or checkout MeTTa runtime tree.

    importlib.resources for the bundled case, because that is the supported
    way to locate package data and the one that keeps working when the package
    is not an ordinary directory on disk. This is latent for MeTTa itself,
    since wheels are normally unpacked, and it is not latent for the pattern:
    every downstream library shipping a .pl beside its Python copies whatever
    the engine does, so getting it right once here is what gives them the
    right thing to copy.

    The engine needs a real filesystem PATH either way, because SWI consults
    files, so as_file() materialises one for the duration and the fallback to
    __file__ stays for a source checkout, where the package is not installed
    at all.
    """
    configured = os.environ.get("METTA_PATH")
    if configured:
        return str(Path(configured).resolve())

    bundled = _bundled_runtime()
    if bundled is not None:
        return bundled
    # _binding/runtime.py -> _binding -> metta -> python -> extensions -> root.
    return str(Path(__file__).resolve().parents[4])


def _bundled_runtime() -> str | None:
    """The wheel's own copy of engine/ and lib/, if this is an installed wheel."""
    if not __package__:
        return None
    package = __package__.split('.', 1)[0]
    try:
        root = resources.files(package) / "_runtime"
    except (ModuleNotFoundError, TypeError):
        return None
    try:
        with resources.as_file(root) as path:
            if (path / "engine" / "main.pl").is_file():
                return str(path)
    except (FileNotFoundError, NotADirectoryError, OSError):
        return None
    return None


@contextmanager
def engine_thread() -> Iterator[None]:
    """Attach a Prolog engine to this thread for the duration of the block.

    The consulting thread and an already attached worker keep their existing
    engine. A bare foreign thread gets one engine and releases it on exit,
    including exceptional exit.
    """
    # Reading the already-published runtime needs no home-engine mutex. This
    # matters when a foreign completion thread is the event that will unblock
    # a home-engine call: taking _LOCK here would wait behind that call while
    # that call waited for this thread, the async-landing deadlock.
    active = active_runtime()
    janus = (active if active is not None else runtime())._janus
    try:
        already_attached = janus.engine() >= 0
    except Exception as exc:
        msg = "could not inspect this thread's Prolog engine"
        raise EngineError(msg) from exc
    if already_attached:
        yield
        return

    attached = False
    try:
        janus.attach_engine()
        attached = True
        if janus.engine() < 0:
            msg = "janus did not attach a Prolog engine"
            raise RuntimeError(msg)  # noqa: TRY301  -- the raise stays inside this rollback boundary so the same handler records the failure
    except Exception as exc:
        if attached:
            janus.detach_engine()
        msg = "could not attach a Prolog engine to this thread"
        raise EngineError(msg) from exc
    # This thread now owns an engine nobody else can reach, so its calls need
    # no process lock. Decided here, once, rather than on every call.
    previous_lock = _CALL_LOCKS.lock
    _CALL_LOCKS.lock = _NULL_LOCK
    try:
        yield
    finally:
        _CALL_LOCKS.lock = previous_lock
        try:
            janus.detach_engine()
        except Exception as exc:
            msg = "could not detach this thread's Prolog engine"
            raise EngineError(msg) from exc


def runtime(metta_path: str | None = None, verbose: bool | None = None) -> Runtime:  # noqa: FBT001  -- the boolean is established API data and positional compatibility is part of the call shape
    """The process's runtime, started on first use.

    There is exactly one engine per process, so a later caller cannot have
    a different tree: an explicit metta_path that disagrees with the one
    already consulted raises rather than being silently ignored. Verbosity
    applies when a caller SAYS something (verbose=True or verbose=False);
    the default None leaves the session as it is, so a constructor that
    merely reaches the runtime cannot silence a verbose session the way the
    old always-applied False default did (minting a context home did exactly
    that, and the published verbosity setting went quiet).
    """
    if metta_path is verbose is None:
        ready = active_runtime()
        if ready is not None:
            return ready
    with _LOCK:
        if _STATE.runtime is None:
            logger.debug("starting the shared MeTTa runtime")
            _STATE.runtime = Runtime(metta_path=metta_path, verbose=bool(verbose))
        else:
            active = _STATE.runtime.metta_path
            if (
                metta_path is not None
                and active is not None
                and Path(metta_path).resolve() != Path(active).resolve()
            ):
                msg = (
                    f"the engine was consulted from {active!r} and cannot "
                    f"be reconsulted from {metta_path!r}: MeTTa keeps one "
                    f"engine per process. Start a new process for a "
                    f"different tree."
                )
                raise ValueError(
                    msg
                )
            if verbose is not None:
                # Always write on an explicit ask: the engine flag is also
                # mutated directly by tests and helper calls, so a cached
                # mirror comparison here would skip a needed update against
                # stale shadow state. The write is idempotent and cheap.
                _STATE.runtime.verbose = verbose
                _STATE.runtime.once(
                    "metta_host_set_silent(S)", S="false" if verbose else "true"
                )
        return _STATE.runtime


def _clean_message(exc: BaseException) -> str:
    """The engine's words, without the janus frame around them."""
    return str(exc).strip()


def _answer_bag(wires: object) -> tuple[Atom, ...] | None:
    """One directed bag difference an assertion reported, as atoms.

    None is the engine's own absence, an unbound bag, meaning the failing form
    computed no such difference; an empty tuple is a computed and empty one,
    and a harness reads the two differently. The elements arrive on the answer
    wire, so they decode into the same atoms an answer would.
    """
    if wires is None:
        return None
    return tuple(_atom_from_wire(wire) for wire in cast("list[Any]", wires))


class Runtime:
    """One consulted engine, shared by every space and operation.

    MeTTa compiles functions process-wide, so there is exactly one engine per
    process and this class refuses to pretend otherwise.
    """

    def __init__(self, metta_path: str | None = None, verbose: bool = False) -> None:  # noqa: FBT001, FBT002  -- the boolean is established API data and positional compatibility is part of the call shape
        self.verbose = bool(verbose)
        with CONSULT_LOCK:
            if not CONSULTED.is_set():
                if metta_path is None:
                    metta_path = _resolve_metta_path()
                with config._startup() as startup:
                    _STATE.janus = self._consult_engine(metta_path, startup[0])
                CONSULTED.set()
            self.metta_path = metta_path
            self._janus = bridge()
            # The functional calling convention (apply_once, cmd) skips the
            # per-thread engine handling query_once performs: on a thread
            # with NO Prolog engine it aborts the PROCESS, observed and
            # bisected, while on a thread that attached one with
            # janus.attach_engine() it works and stays fast. The fast path
            # therefore runs on the consulting thread and on any thread
            # holding an attached engine; every other thread falls back to
            # the relational form with identical semantics.
            self._home_thread = threading.current_thread()
            self._consult_shim()
            # Without a heartbeat, Python never processes a SIGINT while a
            # goal runs: probed, a Ctrl-C on query_once(repeat,fail) stayed
            # queued past 1.5s. At the default 100,000-inference interval,
            # the same signal raises KeyboardInterrupt within
            # ~10ms of engine time (this engine spins ~13M inferences/s),
            # and an interleaved A/B on a pure 3M-step loop measured parity
            # with no heartbeat at all; 10,000 cost ~2% on that loop.
            # config.heartbeat_interval exposes that latency/cost tradeoff
            # [tested: test_sigint_interrupts_a_running_evaluation].
            #
            # Through the shim rather than janus.heartbeat(), which would
            # install a hook of janus's own that no counter can see: the
            # shim's hook does the same crossing and counts itself, so
            # stats() reports the measured block's work and not the poll's
            # [tested: test_a_measurement_is_the_same_with_the_poll_dense].
            self._janus.cmd(
                "user", "metta_py_heartbeat_arm", config.heartbeat_interval
            )

    # ------------------------------------------------------------------ startup

    def _consult_engine(self, metta_path: str, stack_limit: int) -> JanusBridge:
        """Configure the stack limit, load extensions, and call the engine boot door.

        `extensions` asks the engine to read every extension's control file
        and load what each declares. This names none of them: which extensions
        exist is defined by extensions/*/extension.pl, and whether one is
        usable is that extension's own declaration. It used to test for MORK's
        shared library here and pass `mork`, which put a backend's build path
        in the embedding host.
        """
        logger.debug("consulting the MeTTa engine from %s", metta_path)
        root = Path(metta_path)
        # Through bridge(), so a missing or unloadable janus is refused with
        # the same words here as anywhere else: this is the FIRST crossing a
        # fresh install reaches, so it is the one a user meets.
        janus = bridge()
        janus.query_once(f"set_prolog_flag(stack_limit, {stack_limit})")
        janus.query_once("set_prolog_flag(argv, ['extensions'])")
        main_file = root / "engine" / "qlf_boot.pl"
        helper_file = root / "extensions" / "python" / "helper.pl"
        if not main_file.is_file():
            msg = (
                f"MeTTa runtime not found under {metta_path!r} (expected "
                f"{main_file!r}). Set METTA_PATH or pass metta_path."
            )
            raise FileNotFoundError(
                msg
            )
        janus.consult(str(main_file))
        janus.query_once("metta_qlf_boot:qlf_load_engine")
        if helper_file.is_file():
            janus.consult(str(helper_file))
        logger.debug("consulted the MeTTa engine")
        return janus

    def _consult_shim(self) -> None:
        """Load shim.pl next to this file, and expose the ops module to janus."""
        if _SHIM_LOADED.is_set():
            return
        callbacks = importlib.import_module("metta._binding.callbacks")
        # janus reaches Python operations by importing metta_ops; the alias
        # makes that import resolve to the registry module.
        sys.modules.setdefault("metta_ops", callbacks)
        shim = str(Path(__file__).with_name("shim.pl"))
        logger.debug("consulting the Python bridge shim from %s", shim)
        self._janus.consult(shim)
        self._janus.query_once(
            "metta_host_set_silent(S)",
            {"S": "false" if self.verbose else "true"},
        )
        # The runtime-backed prelude compiled Python leans on; registered
        # with the shim so the two arrive together.
        prelude = lazy('metta._declare.prelude')
        prelude.install(self)
        logger.debug("installed the Python bridge prelude")
        # The contract ontology: the typed vocabulary used by interface
        # declarations, present before any user declaration can reference it.
        contract = importlib.import_module("metta._catalog.kinds")
        contract.install(self)
        logger.debug("installed the contract ontology")
        # This is a completion flag, not a progress flag. A failed prelude or
        # contract install leaves it clear so the next Runtime retries the
        # whole Python layer instead of publishing a half-booted engine.
        _SHIM_LOADED.set()

    # -------------------------------------------------------------------- calls

    def once(self, goal: str, **inputs: Any) -> dict:
        """Run a goal once, returning its bindings dict.

        Raises EngineError when the engine throws and ValueError-shaped
        MettaSyntaxError when the reader refused source. A goal that simply
        fails returns an empty dict, which no shim entry point does on
        purpose, so callers treat it as an engine-side refusal.
        """
        with self._relational_lock():
            try:
                row = self._janus.query_once(*_scope.bind(goal, inputs))
            except self._janus.PrologError as exc:
                self._raise(exc)
            except SystemError as exc:
                self._lost_crossing(exc, inputs)
            if row is None or row.get("truth") is False:
                return {}
            return row

    def must(self, goal: str, **inputs: Any) -> dict:
        """Run a goal that is REQUIRED to succeed: a bridge entry point that
        fails has hit a bug or a refused input, and silence would let a
        write vanish. Failure raises; the semidet reading stays with once().
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        row = self.once(goal, **inputs)
        if not row:
            msg = (
                f"the engine refused {goal.split('(', maxsplit=1)[0]}: the goal failed "
                f"rather than erring, which for this entry point means the "
                f"inputs were not accepted"
            )
            raise EngineError(
                msg
            )
        return row

    def consult(self, name: str, *, data: str | None = None) -> None:
        """Load Prolog source into the engine: a path, or source held in
        memory under a name of the caller's choosing.

        Every other engine call in this package takes the lock and routes its
        failures through _raise. The two consults did neither, in a package
        that ships a thread pool and an async surface, so a syntax error in a
        library's shipped .pl arrived as a raw janus PrologError that a
        caller's `except MettaError` missed.

        The engine side raises what SWI would only have printed, which is the
        half no wrapper here could reach: a syntax error inside a consulted
        file goes through print_message/2 and the load then succeeds with the
        predicate undefined.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        goal = "consult_global(File)" if data is None else "consult_string_global(Name, Text)"
        inputs = {"File": name} if data is None else {"Name": name, "Text": data}
        self.once(goal, **inputs)

    def _thread_lock(self) -> AbstractContextManager[Any] | None:
        """The lock this thread's engine calls take, or None when this thread
        must fall back to the relational form.

        This replaces the older _fast_ok() and answers both questions from the
        live Thread object, because the two have the same answer: a thread
        may use the functional convention exactly when it holds an engine of
        its own, and a thread holding its own engine is exactly the thread
        that needs no process lock. Folding them keeps the home path at the
        cost it had before per-engine locking existed.  On the space-name
        benchmark, adding one thread-local read to this arm cost 15.5 million
        retired instructions, +0.61%; the promoted A/B retains the command and
        fixture [source: extensions/python/benchmarks/thread_lock_dispatch.py;
        commit=8fc1a4e204be4200862af7a3819a28a0d6279ea1].

        Bare foreign threads abort the process on apply_once and cmd
        (measured), which is why they answer None rather than a lock.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        # Every crossing consults this: apply and do directly, once and iter
        # through _relational_lock. Draining here rather than at each of the
        # four is one place a new crossing cannot forget.
        self._drain_deferred()
        if threading.current_thread() is self._home_thread:
            return _LOCK
        if _CALL_LOCKS.lock is _NULL_LOCK:
            return _NULL_LOCK
        # aio and remote workers attach an engine without going through
        # engine_thread(), so ask janus before deciding they are bare.
        return _NULL_LOCK if self._janus.engine() >= 0 else None

    def _relational_lock(self) -> AbstractContextManager[Any]:
        """Serialize the home engine and leave private engines independent.

        Janus gives query_once() and query() a temporary engine on a bare
        foreign thread. Taking the home lock around that private engine did
        not protect either one; it only let a blocking foreign query prevent
        the home thread, including the call that would unblock it, from
        running.
        """
        lock = self._thread_lock()
        return _NULL_LOCK if lock is None else lock

    def _drain_deferred(self) -> None:
        """Do the work finalisers handed over, here, where it is safe.

        Called from _thread_lock, which every crossing consults before taking
        any lock and before the crossing itself. That is the point this library
        chose: ordinary Python on a thread whose engine is attached and which
        is not inside a janus call.

        Guarded three ways. It returns on a thread with no engine, because
        erasing a record there is the crash the deferral exists to prevent. It
        returns while already draining, because a deferred call re-enters this
        through the crossing it makes. And a work item that raises is dropped
        rather than requeued: it runs with no caller to answer to, and a failed
        cursor close must not be able to fail the unrelated call that happened
        to drain it, nor spin forever.

        Popped one at a time inside try/except rather than tested with `while
        queue`, because another thread can empty the queue between the test and
        the pop; that is the shape jedi's CompiledSubprocess.run uses to drain
        its own deletion queue
        [source: https://github.com/davidhalter/jedi/blob/master/jedi/inference/compiled/subprocess/__init__.py,
        CompiledSubprocess.run; commit=2421d06e697daffb0797c307a798131616ebdd8e].
        [tested: test_deferred_work_is_drained_by_the_next_engine_crossing,
        test_a_failing_deferred_call_does_not_fail_the_crossing_that_drains_it;
        commit=2421d06e697daffb0797c307a798131616ebdd8e]
        """
        if not _DEFERRED_WORK or getattr(_DRAINING, "active", False):
            return
        if self._janus.engine() < 0:
            return
        _DRAINING.active = True
        try:
            while True:
                try:
                    item = _DEFERRED_WORK.popleft()
                except IndexError:
                    return
                try:
                    if item[0] is _ERASE_RECORD:
                        _STATE.erase_record(item[1])
                    else:
                        self.do(item[1], *item[2])
                except Exception:
                    # A finaliser's work has no caller to raise to.
                    logger.debug("deferred engine work failed", exc_info=True)
        finally:
            _DRAINING.active = False

    def apply(self, predicate: str, *inputs: Any) -> Any:
        """Run a shim predicate through janus's functional convention:
        leading ground input arguments, one output argument, answered
        directly. Measured 5.9x less calling overhead than the relational
        goal string on this machine (4.13M against 702k trivial calls per
        second), which is why every hot entry point crosses this way.
        Failure answers None, the semidet reading; errors classify exactly
        as once(). Off the consulting thread the same call routes through
        the relational form, since the functional one is main-thread-only
        in janus (a foreign-thread call aborts the process).
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        lock = self._thread_lock()
        if lock is None:
            names = [f"A{i}" for i in range(len(inputs))]
            goal = f"{predicate}({', '.join([*names, 'Out'])})"
            row = self.once(goal, **dict(zip(names, inputs, strict=True)))
            return row.get("Out") if row else None
        with lock:
            try:
                scope = _scope.CURRENT.get()
                value = (
                    self._janus.apply_once("user", predicate, *inputs, fail=_FAILED)
                    if scope is None else self._janus.apply_once(
                        "lib_thread", "scope_apply", scope, predicate,
                        list(inputs), fail=_FAILED,
                    )
                )
            except self._janus.PrologError as exc:
                self._resynchronise()
                self._raise(exc)
            except SystemError as exc:
                self._lost_crossing(exc, inputs)
        return None if value is _FAILED else value

    def apply_must(self, predicate: str, *inputs: Any) -> Any:
        """apply() for entry points REQUIRED to succeed, as must() is to
        once(): failure means refused inputs and raises.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        value = self.apply(predicate, *inputs)
        if value is None:
            msg = (
                f"the engine refused {predicate}: the goal failed rather "
                f"than erring, which for this entry point means the inputs "
                f"were not accepted"
            )
            raise EngineError(
                msg
            )
        return value

    def do(self, predicate: str, *inputs: Any) -> bool:
        """Run a void shim predicate (ground inputs, no outputs) through
        janus.cmd, the fastest crossing: True on success, False on
        failure, errors classified exactly as once(). Off the consulting
        thread the call routes through the relational form, as apply()
        does and for the same reason.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        lock = self._thread_lock()
        if lock is None:
            names = [f"A{i}" for i in range(len(inputs))]
            goal = f"{predicate}({', '.join(names)})" if names else predicate
            return bool(self.once(goal, **dict(zip(names, inputs, strict=True))))
        with lock:
            try:
                scope = _scope.CURRENT.get()
                truth = (
                    self._janus.cmd("user", predicate, *inputs)
                    if scope is None else self._janus.cmd(
                        "lib_thread", "scope_do", scope, predicate, list(inputs)
                    )
                )
            except self._janus.PrologError as exc:
                self._resynchronise()
                self._raise(exc)
            except SystemError as exc:
                self._lost_crossing(exc, inputs)
        return truth is True

    def do_must(self, predicate: str, *inputs: Any) -> None:
        """do() for entry points REQUIRED to succeed; failure raises."""
        if not self.do(predicate, *inputs):
            msg = (
                f"the engine refused {predicate}: the goal failed rather "
                f"than erring, which for this entry point means the inputs "
                f"were not accepted"
            )
            raise EngineError(
                msg
            )

    def iter(self, goal: str, **inputs: Any) -> Iterator[dict]:
        """Enumerate a nondeterministic goal's answers, all of them.

        The cursor is drained before anything is yielded, while its engine is
        exclusive to this call: the home engine is locked, while attached and
        temporary engines belong to this thread. Interleaving user code that
        may call back into the engine with an open cursor is how a session
        deadlocks. That is why this is for the SMALL, bounded enumerations the
        library asks itself about, an operation's arities and a space's
        diagnostics, and why it is not the lazy route.

        The lazy route is an SWI engine, not a findall: metta_py_cursor_open
        holds the goal's state between pulls, metta_py_cursor_next takes one
        answer, and unrelated calls interleave freely, which a raw janus
        cursor forbids because its frames nest LIFO and it dies crossing
        threads. Space.stream() is that interface in-process and
        RemoteSpace.stream() is the same lifecycle over the wire. A
        shim-side findall would only move the drain, not remove it.

        JANUS CARRIES EVERY NAMED VARIABLE OF `goal` BOTH WAYS, taking it from
        `inputs` and converting it back on the way out, so one still unbound
        when the goal succeeds raises `Arguments are not sufficiently
        instantiated` from that conversion rather than from the goal. The
        message names neither, so it reads as a Prolog instantiation error
        somewhere inside the goal. A variable used only inside a findall
        counts: it is still a goal variable and the findall leaves it unbound.
        Give a leading underscore to anything not wanted back
        [measured 2026-08-31: `X = 1, freeze(Y, true)` raises, while
        `X = 1, freeze(_Y, true)` answers `{X, truth}`].
        """
        with self._relational_lock():
            try:
                rows = list(self._janus.query(*_scope.bind(goal, inputs)))
            except self._janus.PrologError as exc:
                self._raise(exc)
            except SystemError as exc:
                self._lost_crossing(exc, inputs)
        return iter(rows)

    def _resynchronise(self) -> None:
        """Absorb an error a failed crossing left pending in the engine.

        The predicate calls (apply_once, cmd) leave a Python exception raised
        inside the engine PENDING, where the goal-string call clears it. The
        next janus call is the one that reports it, and on the failure path
        that next call is janus's own PrologError.__str__, which runs
        message_to_string/2 to render the very error being classified: the
        classification then died on the pending error and the caller received
        a raw janus PrologError instead of its own exception [tested:
        test_a_raising_builtin_names_the_metta_operation_not_the_host_predicate].

        One sacrificial goal takes the pending error so whatever follows sees
        a clean engine. Only ever run once a call has already failed, so the
        succeeding path pays nothing.
        """
        with suppress(Exception):
            self._janus.query_once("true")

    def _lost_crossing(self, exc: SystemError, inputs: Any) -> NoReturn:
        """Recover from an input conversion that failed inside janus's C.

        janus reports such a failure as a bare ``SystemError`` naming nothing,
        and the Python exception it set stays pending in the engine: measured
        2026-08-29, the NEXT call, however unrelated, is the one that raises
        it, and the call after that is clean again. On a server that made one
        peer's malformed payload fail a different peer's request.

        So the failure is made local here, the way a database client discards
        a connection's pending results after a framing error rather than
        letting the next statement read them: one sacrificial goal absorbs the
        pending error, and this call raises for its own input. Nothing is
        spent on the succeeding path, because the recovery runs only once a
        crossing has already been lost.

        The refusal matches _atoms_core._encodable, which already gives this
        wording where an ATOM carries the same text; this is the raw goal
        interface it never covered.
        """
        self._resynchronise()
        reason = _unencodable(inputs)
        if reason is None:
            msg = f"the engine could not accept this call's inputs: {exc}"
            raise EngineError(msg) from exc
        msg = (
            f"this call cannot cross to the engine: {reason}. Repair the "
            f"text, or carry it whole with metta.ground(text)."
        )
        raise ValueError(msg) from None

    def _refused[ExcT: BaseException](self, error: ExcT, term: object) -> ExcT:
        """The same error, carrying the catalog's ground and remedy for its kind.

        Its longhand is `refusing(error, ground=..., remedy=...)` at the raise
        site, which is what a refusal this library makes on its OWN already
        writes. An engine refusal has no such site here: the class is chosen
        from the kind the engine read off the ball, so the two parts are read
        from the same table, with the remedy's `<field>` holes filled from
        this very ball [source: engine/spaces/catalog.pl, the (refusal ...)
        rows; engine/metta/registration.pl, metta_host_refusal/6].

        A ball whose kind carries no row, and a classifier that itself fails,
        both leave the error exactly as it was: documentation missing is never
        a reason for a refusal to arrive as something else.
        """
        try:
            row = self._janus.query_once(
                "metta_py_refusal(Error, _Kind, _Fields, _Class, Ground, Remedy)",
                {"Error": term},
            )
        except self._janus.PrologError:
            return error
        if row is None or row.get("truth") is False:
            return error
        try:
            ground = Ground.from_atom(_atom_from_wire(row["Ground"]))
            remedy = Remedy.from_atom(_atom_from_wire(row["Remedy"]))
        except (KeyError, TypeError, ValueError):
            return error
        return refusing(error, ground=ground, remedy=remedy)

    def _classified(self, message: str, term: object) -> BaseException:
        """The class the ball's own KIND names, dressed with its row.

        The tail of the classifier chain. Every branch above it takes a shape
        apart that the row does not carry -- an assertion's two answer bags, a
        builtin refusal's culprit -- and builds a class with more fields than
        the kind declares. What is left is a ball the engine has already
        classified and whose class the row already names, and reading that here
        is what stopped a stack overflow and a missing source arriving as a
        bare EngineError with nothing to react to [source:
        engine/metta/registration.pl, metta_host_error_kind/3; the two were
        recorded as gaps in tests/data/error-kinds.json until this existed].

        A ball whose kind carries no row, and a classifier that itself fails,
        both answer EngineError with the ball's own message: documentation
        missing is never a reason for a refusal to arrive as something else.
        """
        try:
            row = self._janus.query_once(
                "metta_py_refusal(Error, Kind, Fields, _Class, Ground, Remedy)",
                {"Error": term},
            )
        except self._janus.PrologError:
            return EngineError(message)
        if row is None or row.get("truth") is False:
            return EngineError(message)
        kind = row.get("Kind")
        error_class = (
            _EXCEPTION_TYPES.get(kind, EngineError)
            if isinstance(kind, str)
            else EngineError
        )
        # The parts the ball carried, under the names its kind declares, which
        # are the keywords the class takes: `refusal-sync` holds every class to
        # its row's field list, so this cannot pass one the class refuses.
        carried = {
            str(name): value
            for name, value in row.get("Fields") or ()
        }
        error = error_class(message, **carried)
        try:
            ground = Ground.from_atom(_atom_from_wire(row["Ground"]))
            remedy = Remedy.from_atom(_atom_from_wire(row["Remedy"]))
        except (KeyError, TypeError, ValueError):
            return error
        return refusing(error, ground=ground, remedy=remedy)

    def _raise(self, exc: BaseException) -> NoReturn:
        message = _clean_message(exc)
        term = getattr(exc, "term", None)
        if term is not None:
            original = self._original_python_error(term, base=BaseException)
            if original is not None and _is_metta_failure(original):
                # The library's own raise crossed Prolog and came back:
                # re-raise the very object, structured fields intact, instead
                # of an EngineError holding its transcript. A group rehydrates
                # only when every leaf is a MettaError; an op author's own
                # exception, grouped or plain, stays wrapped so the boundary
                # it crossed remains visible.
                #
                # An error that already chose its own cause keeps it. `from
                # exc` here would overwrite the diagnosis with the plumbing:
                # SubscriberError is raised `from` the watcher's own
                # exception, and that is the thing a caller needs to read.
                # The boundary term stays reachable as __context__ either way.
                if original.__cause__ is not None or original.__suppress_context__:
                    raise original
                raise original from exc
            try:
                row = self._janus.query_once(
                    "metta_control_signal_info(Error, Kind, Detail)", {"Error": term}
                )
            except self._janus.PrologError as classifier_error:
                msg = (
                    f"{message}; the exception classifier failed: "
                    f"{_clean_message(classifier_error)}"
                )
                raise EngineError(
                    msg
                ) from exc
            if row is not None and row.get("truth") is not False:
                kind = row.get("Kind")
                detail = row.get("Detail")
                if kind == "interrupted" and isinstance(detail, list) and len(detail) == 2 and detail[0] == "scope":
                    raise _scope.Cancelled(str(detail[1])) from exc
                error_type = (
                    _EXCEPTION_TYPES.get(kind) if isinstance(kind, str) else None
                )
                if error_type is RestraintError:
                    detail = row.get("Detail")
                    restraint, bound, call = _restraint_fields(detail)
                    raise self._refused(
                        RestraintError(
                            _reserved_message(kind, detail, message),
                            restraint=restraint,
                            bound=bound,
                            call=call,
                        ),
                        term,
                    ) from exc
                if error_type is MettaSyntaxError:
                    raise self._refused(
                        MettaSyntaxError(
                            _reserved_message(kind, row.get("Detail"), message),
                            line=self._syntax_line(term),
                        ),
                        term,
                    ) from exc
                if error_type is not None:
                    detail = row.get("Detail")
                    # The bound the ball named IS the `limit` field its row
                    # declares, so the caller reads the number rather than the
                    # sentence around it; every other kind here declares none.
                    carried = (
                        {"limit": detail}
                        if issubclass(error_type, ResourceLimitError)
                        and detail is not None
                        else {}
                    )
                    raise self._refused(
                        error_type(_reserved_message(kind, detail, message), **carried),
                        term,
                    ) from exc
            self._raise_assertion_failure(exc, term, message)
            self._raise_space_capability_error(exc, term, message)
            self._raise_operation_error(exc, term, message)
            raise self._classified(message, term) from exc
        raise EngineError(message) from exc

    def _syntax_line(self, term: object) -> int | None:
        """The 1-based line a reader failure named, or None when it named none.

        A second query rather than a fourth argument on
        metta_control_signal_info/3: only this one kind has a place as well as
        a sentence, and the crossing is paid on a path that is already
        raising. shim.pl's metta_control_signal_line/2 FAILS where no line was
        recorded, which is what None means here.
        """
        try:
            row = self._janus.query_once(
                "metta_control_signal_line(Error, Line)", {"Error": term}
            )
        except self._janus.PrologError:
            return None
        if row is None or row.get("truth") is False:
            return None
        line = row.get("Line")
        return line if isinstance(line, int) else None

    def _raise_assertion_failure(self, exc: BaseException, term: object, message: str) -> None:
        """Raise AssertionFailure when the program's own claim is what failed.

        Ahead of the operation classifier because a failed assertion carries
        a MeTTa operation too, and it is the more specific reading: `test`
        and `assert` did not refuse a value, they reported a false claim.
        """
        try:
            # The intermediates are _-prefixed because janus converts every
            # NAMED variable of the query and an assertion form that carries
            # no expected value leaves one free, which janus reports as
            # "Arguments are not sufficiently instantiated" rather than as
            # absence. metta_py_operation_part/2 maps that absence to None.
            row = self._janus.query_once(
                "metta_assertion_failure(Error, Form, _Actual, _Expected, "
                "_Missing, _Excess), "
                "metta_py_operation_part(_Actual, Actual), "
                "metta_py_operation_part(_Expected, Expected), "
                "metta_py_answer_bag(_Missing, Missing), "
                "metta_py_answer_bag(_Excess, Excess)",
                {"Error": term},
            )
        except self._janus.PrologError as classifier_error:
            msg = (
                f"{message}; the assertion classifier failed: "
                f"{_clean_message(classifier_error)}"
            )
            raise EngineError(
                msg
            ) from exc
        if row is None or row.get("truth") is False:
            return
        form = row.get("Form")
        if not isinstance(form, str):
            return
        raise self._refused(
            AssertionFailure(
                message,
                operation=form,
                actual=row.get("Actual"),
                expected=row.get("Expected"),
                missing=_answer_bag(row.get("Missing")),
                excess=_answer_bag(row.get("Excess")),
            ),
            term,
        ) from exc

    def _original_python_error(
        self, term: object, base: type[BaseException] = MettaError
    ) -> BaseException | None:
        """The live exception a Python callback raised, when the Prolog
        term still carries the object reference and the object is a
        `base`. _raise keeps the default, the library's own exceptions;
        transaction() widens it, because a transaction body is the
        caller's own code and its ValueError should arrive as itself.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        try:
            row = self._janus.query_once(
                "metta_py_original_exception(Error, Obj)", {"Error": term}
            )
        except self._janus.PrologError:
            return None
        if not row or row.get("truth") is False:
            return None
        obj = row.get("Obj")
        return obj if isinstance(obj, base) else None

    def _raise_space_capability_error(
        self, exc: BaseException, term: object, message: str
    ) -> None:
        """Raise SpaceCapabilityError with the refusal's stable fields."""
        try:
            row = self._janus.query_once(
                "metta_py_space_capability_error(Error, Space, Operation, Capability)",
                {"Error": term},
            )
        except self._janus.PrologError as classifier_error:
            msg = (
                f"{message}; the capability classifier failed: "
                f"{_clean_message(classifier_error)}"
            )
            raise EngineError(msg) from exc
        if row is None or row.get("truth") is False:
            return
        space = row.get("Space")
        operation = row.get("Operation")
        capability = row.get("Capability")
        if (
            not isinstance(space, str)
            or not isinstance(operation, str)
            or not isinstance(capability, str)
        ):
            return
        raise self._refused(
            SpaceCapabilityError(
                message,
                space=space,
                operation=operation,
                capability=capability,
            ),
            term,
        ) from exc

    def _raise_operation_error(self, exc: BaseException, term: object, message: str) -> None:
        """Raise MettaOperationError when the term names a MeTTa operation."""
        try:
            row = self._janus.query_once(
                "metta_py_operation_error(Error, Operation, Kind, Expected, Culprit)",
                {"Error": term},
            )
        except self._janus.PrologError as classifier_error:
            msg = (
                f"{message}; the operation classifier failed: "
                f"{_clean_message(classifier_error)}"
            )
            raise EngineError(
                msg
            ) from exc
        if row is None or row.get("truth") is False:
            return
        operation, kind = row.get("Operation"), row.get("Kind")
        if not isinstance(operation, str) or not isinstance(kind, str):
            return
        raise self._refused(
            MettaOperationError(
                message,
                operation=operation,
                kind=kind,
                expected=row.get("Expected"),
                culprit=row.get("Culprit"),
            ),
            term,
        ) from exc

    # ------------------------------------------------------------------- helpers

    def builtins(self, space: Hashable | None = None) -> list[str]:
        """Function and special-form names, process-wide or callable from one space.

        Without a space this is every name the translator knows as a
        function anywhere in the engine, the pool a symbol completion or a
        lint suggestion draws from. With a space it is what THAT space can
        call: its own equations, the ones it inherits, ``&self``'s shared
        ones and the builtins, which is what a space's function namespace
        lists and resolves.
        """
        if space is None:
            row = self.once("metta_py_builtins(Names)")
        else:
            row = self.once("metta_py_builtins(Space, Names)", Space=space)
        return list(row.get("Names", []))
