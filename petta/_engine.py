"""Purpose: the engine bridge. Consults PeTTa and the shim exactly once per
process, serializes janus calls behind one lock, and turns Prolog exceptions
into the library's own errors. Coordinates with the legacy petta.PeTTa class
through the package-level CONSULTED flag so both surfaces share one engine.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import importlib
import os
import sys
import threading
from typing import Any, Iterator, NoReturn

from .errors import (
    EngineError,
    InferenceLimitError,
    Interrupted,
    MettaSyntaxError,
    TimeLimitError,
)

_LOCK = threading.RLock()

# The failure sentinel for the functional calling convention: a private
# identity no predicate can answer, so a legitimate output is never
# mistaken for failure.
_FAILED = object()
_RUNTIME: "Runtime | None" = None


def started() -> bool:
    """Whether a runtime exists, without starting one."""
    return _RUNTIME is not None


def runtime(petta_path: str | None = None, verbose: bool = False) -> "Runtime":
    """The process's runtime, started on first use.

    There is exactly one engine per process, so a later caller cannot have
    a different tree: an explicit petta_path that disagrees with the one
    already consulted raises rather than being silently ignored. Verbosity
    is per-call state and simply applies.
    """
    global _RUNTIME
    with _LOCK:
        if _RUNTIME is None:
            _RUNTIME = Runtime(petta_path=petta_path, verbose=verbose)
        else:
            active = _RUNTIME.petta_path
            if (
                petta_path is not None
                and active is not None
                and os.path.abspath(petta_path) != os.path.abspath(active)
            ):
                raise ValueError(
                    f"the engine was consulted from {active!r} and cannot "
                    f"be reconsulted from {petta_path!r}: PeTTa keeps one "
                    f"engine per process. Start a new process for a "
                    f"different tree."
                )
            if verbose != _RUNTIME.verbose:
                _RUNTIME.verbose = verbose
                _RUNTIME.once(
                    "petta_py_set_silent(S)", S="false" if verbose else "true"
                )
        return _RUNTIME


def _clean_message(exc: BaseException) -> str:
    """The engine's words, without the janus frame around them."""
    text = str(exc)
    return text.strip()


class Runtime:
    """One consulted engine, shared by every space and operation.

    PeTTa compiles functions process-wide, so there is exactly one engine per
    process and this class refuses to pretend otherwise.
    """

    def __init__(self, petta_path: str | None = None, verbose: bool = False) -> None:
        import petta as pkg

        self.verbose = bool(verbose)
        with pkg.CONSULT_LOCK:
            if not pkg.CONSULTED:
                if petta_path is None:
                    petta_path = pkg._resolve_petta_path()
                self._consult_engine(pkg, petta_path)
                pkg.CONSULTED = True
            self.petta_path = petta_path
            self._janus = pkg.janus
            # The functional calling convention (apply_once, cmd) skips the
            # per-thread engine handling query_once performs: on a thread
            # with NO Prolog engine it aborts the PROCESS, observed and
            # bisected, while on a thread that attached one with
            # janus.attach_engine() it works and stays fast. The fast path
            # therefore runs on the consulting thread and on any thread
            # holding an attached engine; every other thread falls back to
            # the relational form with identical semantics.
            self._home_thread = threading.get_ident()
            if self._janus is None:
                # The legacy class consulted first through a mocked janus, or
                # a test set CONSULTED by hand; import the real bridge.
                self._janus = pkg.janus = importlib.import_module("janus_swi")
            self._consult_shim(pkg, petta_path)
            # Without a heartbeat, Python never processes a SIGINT while a
            # goal runs: probed, a Ctrl-C on query_once(repeat,fail) stayed
            # queued past 1.5s. With Prolog calling Python every 100,000
            # inferences the same signal raises KeyboardInterrupt within
            # ~10ms of engine time (this engine spins ~13M inferences/s),
            # and an interleaved A/B on a pure 3M-step loop measured parity
            # with no heartbeat at all; 10,000 cost ~2% on that loop
            # (probes in ai-tmp/janus-probes/11_interrupt_heartbeat).
            self._janus.heartbeat(100_000)

    # ------------------------------------------------------------------ startup

    def _consult_engine(self, pkg: Any, petta_path: str) -> None:
        """Mirror of the legacy startup: stack limit, optional MORK, main.pl."""
        morklib = os.path.join(petta_path, "mork_ffi", "target", "release", "libmork_ffi.so")
        janus = importlib.import_module("janus_swi")
        janus.query_once(f"set_prolog_flag(stack_limit, {pkg.DEFAULT_STACK_LIMIT})")
        if os.path.exists(morklib):
            orig = os.getcwd()
            os.chdir(petta_path)
            try:
                janus.query_once("set_prolog_flag(argv, ['mork'])")
            finally:
                os.chdir(orig)
        main_file = os.path.join(petta_path, "src", "main.pl")
        helper_file = os.path.join(petta_path, "python", "helper.pl")
        if not os.path.exists(main_file):
            raise FileNotFoundError(
                f"PeTTa runtime not found under {petta_path!r} (expected "
                f"{main_file!r}). Set PETTA_PATH or pass petta_path."
            )
        janus.consult(main_file)
        if os.path.exists(helper_file):
            janus.consult(helper_file)
        pkg.janus = janus

    def _consult_shim(self, pkg: Any, petta_path: str | None) -> None:
        """Load shim.pl next to this file, and expose the ops module to janus."""
        if getattr(pkg, "_SHIM_LOADED", False):
            return
        from . import _ops

        # janus reaches Python operations by importing petta_ops; the alias
        # makes that import resolve to the registry module.
        sys.modules.setdefault("petta_ops", _ops)
        shim = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shim.pl")
        self._janus.consult(shim)
        self._janus.query_once(
            "petta_py_set_silent(S)", {"S": "false" if self.verbose else "true"}
        )
        pkg._SHIM_LOADED = True
        # The runtime-backed prelude compiled Python leans on; registered
        # with the shim so the two arrive together.
        from . import _prelude

        _prelude.install(self)

    # -------------------------------------------------------------------- calls

    def once(self, goal: str, **inputs: Any) -> dict:
        """Run a goal once, returning its bindings dict.

        Raises EngineError when the engine throws and ValueError-shaped
        MettaSyntaxError when the reader refused source. A goal that simply
        fails returns an empty dict, which no shim entry point does on
        purpose, so callers treat it as an engine-side refusal.
        """
        with _LOCK:
            try:
                row = self._janus.query_once(goal, inputs)
            except Exception as exc:  # janus.PrologError and friends
                self._raise(goal, exc)
            if row is None or row.get("truth") is False:
                return {}
            return row

    def must(self, goal: str, **inputs: Any) -> dict:
        """Run a goal that is REQUIRED to succeed: a bridge entry point that
        fails has hit a bug or a refused input, and silence would let a
        write vanish. Failure raises; the semidet reading stays with once().
        """
        row = self.once(goal, **inputs)
        if not row:
            raise EngineError(
                f"the engine refused {goal.split('(')[0]}: the goal failed "
                f"rather than erring, which for this entry point means the "
                f"inputs were not accepted"
            )
        return row

    def _fast_ok(self) -> bool:
        """Whether this thread may use the functional convention: the
        consulting thread always, any other thread exactly when it holds
        an attached Prolog engine (janus.attach_engine()); bare foreign
        threads abort the process on apply_once and cmd, measured."""
        if threading.get_ident() == self._home_thread:
            return True
        try:
            return int(self._janus.engine()) >= 0
        except Exception:
            return False

    def apply(self, predicate: str, *inputs: Any) -> Any:
        """Run a shim predicate through janus's functional convention:
        leading ground input arguments, one output argument, answered
        directly. Measured 5.9x less calling overhead than the relational
        goal string on this machine (4.13M against 702k trivial calls per
        second), which is why every hot entry point crosses this way.
        Failure answers None, the semidet reading; errors classify exactly
        as once(). Off the consulting thread the same call routes through
        the relational form, since the functional one is main-thread-only
        in janus (a foreign-thread call aborts the process)."""
        if not self._fast_ok():
            names = [f"A{i}" for i in range(len(inputs))]
            goal = f"{predicate}({', '.join([*names, 'Out'])})"
            row = self.once(goal, **dict(zip(names, inputs)))
            return row.get("Out") if row else None
        with _LOCK:
            try:
                value = self._janus.apply_once(
                    "user", predicate, *inputs, fail=_FAILED
                )
            except Exception as exc:
                self._raise(predicate, exc)
        return None if value is _FAILED else value

    def apply_must(self, predicate: str, *inputs: Any) -> Any:
        """apply() for entry points REQUIRED to succeed, as must() is to
        once(): failure means refused inputs and raises."""
        value = self.apply(predicate, *inputs)
        if value is None:
            raise EngineError(
                f"the engine refused {predicate}: the goal failed rather "
                f"than erring, which for this entry point means the inputs "
                f"were not accepted"
            )
        return value

    def do(self, predicate: str, *inputs: Any) -> bool:
        """Run a void shim predicate (ground inputs, no outputs) through
        janus.cmd, the fastest crossing: True on success, False on
        failure, errors classified exactly as once(). Off the consulting
        thread the call routes through the relational form, as apply()
        does and for the same reason."""
        if not self._fast_ok():
            names = [f"A{i}" for i in range(len(inputs))]
            goal = f"{predicate}({', '.join(names)})" if names else predicate
            return bool(self.once(goal, **dict(zip(names, inputs))))
        with _LOCK:
            try:
                truth = self._janus.cmd("user", predicate, *inputs)
            except Exception as exc:
                self._raise(predicate, exc)
        return truth is True

    def do_must(self, predicate: str, *inputs: Any) -> None:
        """do() for entry points REQUIRED to succeed; failure raises."""
        if not self.do(predicate, *inputs):
            raise EngineError(
                f"the engine refused {predicate}: the goal failed rather "
                f"than erring, which for this entry point means the inputs "
                f"were not accepted"
            )

    def iter(self, goal: str, **inputs: Any) -> Iterator[dict]:
        """Enumerate a nondeterministic goal's answers.

        The cursor is drained under the lock before anything is yielded:
        janus queries belong to the engine, and interleaving user code that
        may call back into the engine with an open cursor is how a session
        deadlocks. Answer sets that must stream should provide a shim-side
        findall instead.
        """
        with _LOCK:
            try:
                rows = list(self._janus.query(goal, inputs))
            except Exception as exc:
                self._raise(goal, exc)
        return iter(rows)

    def _raise(self, goal: str, exc: BaseException) -> NoReturn:
        message = _clean_message(exc)
        # Reader refusals arrive tagged with their own functor by the shim
        # (petta_py_tag_reader), so classification is structural: a SQL
        # error that happens to say "syntax error" stays an EngineError.
        # The resource guards tag the same way (petta_py_limited).
        if "petta_syntax_error" in message:
            raise MettaSyntaxError(message) from exc
        if "petta_py_time_limit" in message:
            raise TimeLimitError(message) from exc
        if "petta_py_inference_limit" in message:
            raise InferenceLimitError(message) from exc
        if "petta_py_interrupted" in message:
            raise Interrupted(message) from exc
        raise EngineError(message) from exc

    # ------------------------------------------------------------------- helpers

    def builtins(self) -> list[str]:
        row = self.once("petta_py_builtins(Names)")
        return list(row.get("Names", []))
