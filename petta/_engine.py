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
from typing import Any, Iterator

from .errors import EngineError, MettaSyntaxError

_LOCK = threading.RLock()
_RUNTIME: "Runtime | None" = None


def started() -> bool:
    """Whether a runtime exists, without starting one."""
    return _RUNTIME is not None


def runtime(petta_path: str | None = None, verbose: bool = False) -> "Runtime":
    """The process's runtime, started on first use."""
    global _RUNTIME
    with _LOCK:
        if _RUNTIME is None:
            _RUNTIME = Runtime(petta_path=petta_path, verbose=verbose)
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
            self._janus = pkg.janus
            if self._janus is None:
                # The legacy class consulted first through a mocked janus, or
                # a test set CONSULTED by hand; import the real bridge.
                self._janus = pkg.janus = importlib.import_module("janus_swi")
            self._consult_shim(pkg, petta_path)

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

    def _raise(self, goal: str, exc: BaseException) -> None:
        message = _clean_message(exc)
        lowered = message.lower()
        # The reader's own refusals: sread says "Parse error in form", the
        # top-level form scanner throws syntax_error/1, which SWI renders as
        # "Syntax error: ...".
        if "syntax error" in lowered or "syntax_error" in lowered or "parse error" in lowered:
            raise MettaSyntaxError(message) from exc
        raise EngineError(message) from exc

    # ------------------------------------------------------------------- helpers

    def builtins(self) -> list[str]:
        row = self.once("petta_py_builtins(Names)")
        return list(row.get("Names", []))
