"""Purpose: own the engine bootstrap and bridge. Consults MeTTa and the shim
exactly once per process, serializes calls made on the home engine, lets a
thread holding its own engine run without that lock, and turns Prolog
exceptions into the library's own errors for both Python surfaces.
Assumes:
  - JanusBridge.engine returns the documented integer engine identifier
    [source 2026-08-14:
    https://www.swi-prolog.org/pldoc/man?section=janus-thread-call-prolog]
Guarantees:
  - importing metta does not import janus_swi until an engine-backed API is
    used [tested test_package_import_does_not_require_janus]
  - Runtime classifies only the shim's exact reserved exception term shape
    [tested test_exception_names_nested_in_other_terms_stay_engine_errors,
    test_reserved_exception_shape_maps_by_kind]
  - reader errors expose the reader's diagnostic instead of Janus's unknown
    wrapper text [tested test_run_syntax_error_is_loud]
  - engine_thread attaches only a bare foreign thread and detaches exactly
    the engine it attached; an async landing can attach without waiting for
    a home-engine call that is itself awaiting that landing [tested:
    test_engine_thread_owns_only_its_attachment,
    test_a_transaction_commits_async_launch_before_its_landing;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - a rehydrated MettaError keeps the __cause__ it was raised with, so the
    boundary term never displaces the diagnosis [tested
    test_a_watcher_failure_is_distinguishable_from_a_failed_write]
  - a failed MeTTa assertion arrives as AssertionFailure and an engine fault
    as EngineError, neither an instance of the other [tested
    test_a_failing_assertion_is_a_different_exception_from_an_engine_fault]
  - the restricted-space formal maps to SpaceCapabilityError before the
    generic operation and engine classifiers [tested:
    test_a_restricted_space_cannot_reach_what_its_base_does_not_publish;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a call whose inputs the engine cannot accept fails on its OWN call, by
    kind and naming where in the input the offending text sits, and the next
    call is unaffected on every door [tested:
    test_text_with_no_utf8_encoding_is_refused_by_kind,
    test_a_refused_crossing_does_not_fail_the_next_call,
    test_no_door_leaves_the_next_call_carrying_the_refusal; commit=3b82643dd18ad5153bca71fa0c4bd09d59b0b7d0]
  - a Python exception raised inside the engine classifies the same through
    the goal-string door and the predicate door [tested:
    test_an_enumeration_refuses_answers,
    test_an_enumeration_refuses_answers_through_the_term_door_too;
    commit=3b82643dd18ad5153bca71fa0c4bd09d59b0b7d0]
  - the functional Janus door is selected by live thread identity, never a
    recyclable numeric identifier [tested:
    test_a_recycled_thread_identifier_never_selects_the_janus_fast_path;
    commit=af5821f5ffb7ce186e516706f003d02f5c1d3b4a]
Guarded by:
  - _LOCK serializes runtime creation and every call made on the HOME engine.
    A thread holding its own attached engine takes no process lock: it shares
    no engine with any other thread, and MeTTa's shared structures already
    carry their own Prolog mutexes because hyperpose workers have always
    reached the same database [tested
    test_define_from_two_threads_is_serialized]
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
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager, nullcontext, suppress
from importlib import resources
from pathlib import Path
from typing import Any, NoReturn, Protocol, cast

from ._config import config
from .errors import (
    AssertionFailure,
    EngineError,
    InferenceLimitError,
    Interrupted,
    MettaError,
    MettaOperationError,
    MettaSyntaxError,
    SpaceCapabilityError,
    TimeLimitError,
)

logger = logging.getLogger(__name__)


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
            # The predicate doors pass their arguments as the root tuple, so
            # the top level reads "argument 2" rather than a bare "[2]".
            pending.extend((f"{where}[{index}]" if where else f"argument {index}", item)
                           for index, item in enumerate(value))
    return None


_LOCK = threading.RLock()
# Reusable, so the call path picks a shared object instead of building a
# context manager on a path measured at 4.13M calls per second.
_NULL_LOCK: AbstractContextManager[None] = nullcontext()


class _CallLocks(threading.local):
    """Which lock this thread's engine calls take, decided once per thread.

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


# Threads start on the class default, so every thread that never attaches an
# engine of its own keeps exactly the previous behaviour.
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
    def heartbeat(self, interval: int) -> Any:
        del interval
        raise NotImplementedError

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


_STATE = _EngineState()

_EXCEPTION_TYPES = {
    "syntax": MettaSyntaxError,
    "time_limit": TimeLimitError,
    "inference_limit": InferenceLimitError,
    "interrupted": Interrupted,
    #The engine's JSON codec classifies its own refusals: a value JSON
    #cannot carry is a ValueError, a term that is not JSON data at all
    #is a TypeError. Plain built-ins, because the refusal is about the
    #caller's data, not about MeTTa.
    "value": ValueError,
    "type": TypeError,
}


def _reserved_message(kind: object, detail: object, fallback: str) -> str:
    """Say what a reserved exception means, in the caller's own terms.

    The thrown term is an envelope the Python side put there, so rendering
    it leaks janus framing: the caller who passed timeout=0.05 was reading
    `Unknown error term: metta_control_signal(time_limit,0.05)`.
    """
    if kind == "syntax":
        return detail if isinstance(detail, str) else fallback
    if kind == "time_limit":
        return f"the {detail} second time limit was reached"
    if kind == "inference_limit":
        return f"the {detail} inference limit was reached"
    if kind == "interrupted":
        return "interrupt() stopped the evaluation"
    return fallback


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


def bridge() -> JanusBridge:
    """Import and return janus without starting the MeTTa runtime."""
    janus = _STATE.janus
    if janus is not None:
        return janus
    with _LOCK:
        if _STATE.janus is None:
            try:
                _STATE.janus = cast(JanusBridge, importlib.import_module("janus_swi"))
            except ImportError as exc:
                _no_engine(exc)
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
    # metta/_engine.py -> metta -> python -> extensions -> the checkout root.
    return str(Path(__file__).resolve().parents[3])


def _bundled_runtime() -> str | None:
    """The wheel's own copy of engine/ and lib/, if this is an installed wheel."""
    package = __package__ or "metta"
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
    that, and the published verbosity door went quiet).
    """
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
                # mutated directly by tests and helper doors, so a cached
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
            self._janus.heartbeat(config.heartbeat_interval)

    # ------------------------------------------------------------------ startup

    def _consult_engine(self, metta_path: str, stack_limit: int) -> JanusBridge:
        """Stack limit, the seats, main.pl.

        `extensions` asks the engine to read every seat's control file and load
        what each declares. This names none of them: which seats exist is
        extensions/*/extension.pl and whether one is usable is that seat's own
        declaration. It used to test for MORK's shared library here and pass
        `mork`, which put a backend's build path in the embedding host.
        """
        logger.debug("consulting the MeTTa engine from %s", metta_path)
        root = Path(metta_path)
        # Through bridge(), so a missing or unloadable janus is refused with
        # the same words here as anywhere else: this is the FIRST crossing a
        # fresh install reaches, so it is the one a user meets.
        janus = bridge()
        janus.query_once(f"set_prolog_flag(stack_limit, {stack_limit})")
        janus.query_once("set_prolog_flag(argv, ['extensions'])")
        main_file = root / "engine" / "main.pl"
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
        if helper_file.is_file():
            janus.consult(str(helper_file))
        logger.debug("consulted the MeTTa engine")
        return janus

    def _consult_shim(self) -> None:
        """Load shim.pl next to this file, and expose the ops module to janus."""
        if _SHIM_LOADED.is_set():
            return
        callbacks = importlib.import_module(f"{__package__}._callbacks")
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
        _SHIM_LOADED.set()
        # The runtime-backed prelude compiled Python leans on; registered
        # with the shim so the two arrive together.
        prelude = importlib.import_module(f"{__package__}._prelude")
        prelude.install(self)
        logger.debug("installed the Python bridge prelude")
        # The contract ontology: the typed vocabulary seam declarations are
        # stated in, present before any user declaration can reference it.
        contract = importlib.import_module(f"{__package__}._contract")
        contract.install(self)
        logger.debug("installed the contract ontology")

    # -------------------------------------------------------------------- calls

    def once(self, goal: str, **inputs: Any) -> dict:
        """Run a goal once, returning its bindings dict.

        Raises EngineError when the engine throws and ValueError-shaped
        MettaSyntaxError when the reader refused source. A goal that simply
        fails returns an empty dict, which no shim entry point does on
        purpose, so callers treat it as an engine-side refusal.
        """
        with self._thread_lock() or _LOCK:
            try:
                row = self._janus.query_once(goal, inputs)
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
        if threading.current_thread() is self._home_thread:
            return _LOCK
        if _CALL_LOCKS.lock is _NULL_LOCK:
            return _NULL_LOCK
        # aio and remote workers attach an engine without going through
        # engine_thread(), so ask janus before deciding they are bare.
        return _NULL_LOCK if self._janus.engine() >= 0 else None

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
                value = self._janus.apply_once("user", predicate, *inputs, fail=_FAILED)
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
                truth = self._janus.cmd("user", predicate, *inputs)
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

        The cursor is drained under the lock before anything is yielded:
        janus queries belong to the engine, and interleaving user code that
        may call back into the engine with an open cursor is how a session
        deadlocks. That is why this is for the SMALL, bounded enumerations
        the library asks itself about, an operation's arities and a space's
        diagnostics, and why it is not the lazy route.

        The lazy route is an SWI engine, not a findall: metta_py_cursor_open
        holds the goal's state between pulls, metta_py_cursor_next takes one
        answer, and unrelated calls interleave freely, which a raw janus
        cursor forbids because its frames nest LIFO and it dies crossing
        threads. Space.stream() is that door in-process and
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
        with self._thread_lock() or _LOCK:
            try:
                rows = list(self._janus.query(goal, inputs))
            except self._janus.PrologError as exc:
                self._raise(exc)
            except SystemError as exc:
                self._lost_crossing(exc, inputs)
        return iter(rows)

    def _resynchronise(self) -> None:
        """Absorb an error a failed crossing left pending in the engine.

        The predicate doors (apply_once, cmd) leave a Python exception raised
        inside the engine PENDING, where the goal-string door clears it. The
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
        wording where an ATOM carries the same text; this is the raw goal door
        it never covered.
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

    def _raise(self, exc: BaseException) -> NoReturn:
        message = _clean_message(exc)
        term = getattr(exc, "term", None)
        if term is not None:
            original = self._original_python_error(term)
            if original is not None:
                # The library's own raise crossed Prolog and came back:
                # re-raise the very object, structured fields intact,
                # instead of an EngineError holding its transcript. Only
                # MettaError rehydrates; an op author's ValueError keeps
                # arriving wrapped, the boundary it crossed visible.
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
                error_type = (
                    _EXCEPTION_TYPES.get(kind) if isinstance(kind, str) else None
                )
                if error_type is not None:
                    raise error_type(_reserved_message(kind, row.get("Detail"), message)) from exc
            self._raise_assertion_failure(exc, term, message)
            self._raise_space_capability_error(exc, term, message)
            self._raise_operation_error(exc, term, message)
        raise EngineError(message) from exc

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
                "metta_assertion_failure(Error, Form, _Actual, _Expected), "
                "metta_py_operation_part(_Actual, Actual), "
                "metta_py_operation_part(_Expected, Expected)",
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
        raise AssertionFailure(
            message,
            operation=form,
            actual=row.get("Actual"),
            expected=row.get("Expected"),
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
        raise SpaceCapabilityError(
            message,
            space=space,
            operation=operation,
            capability=capability,
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
        raise MettaOperationError(
            message,
            operation=operation,
            kind=kind,
            expected=row.get("Expected"),
            culprit=row.get("Culprit"),
        ) from exc

    # ------------------------------------------------------------------- helpers

    def builtins(self) -> list[str]:
        row = self.once("metta_py_builtins(Names)")
        return list(row.get("Names", []))
