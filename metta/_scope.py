"""Purpose: project lib_thread's scope handle across Python engine calls.

Guarantees: ownership, deadlines, cancellation and joins reside in lib_thread;
Python carries one ContextVar and translates completion receipts [tested:
extensions/python/tests/ch17_concurrency_and_the_loop/test_scopes.py; commit=c6e1198c490a824b96f6fc6e1c0622a542917024].
Owns resources: ContextVar tokens are restored by suspend(); host resources
are retained and released by lib_thread:scope_host_resource/4 [tested:
extensions/python/tests/ch17_concurrency_and_the_loop/test_scopes.py; commit=c6e1198c490a824b96f6fc6e1c0622a542917024].
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from . import _callbacks

if TYPE_CHECKING:
    from concurrent.futures import Future

CURRENT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "metta_scope", default=None
)


class Cancelled(BaseException):
    """Cancellation delivered by the named lib_thread scope."""

    def __init__(self, scope: str) -> None:
        """Retain the engine's identity so a deadline suppresses only itself."""
        super().__init__(f"scope {scope} was cancelled")
        self.scope = scope


@contextmanager
def suspend() -> Iterator[None]:
    """Make a management crossing outside the scope being managed."""
    token = CURRENT.set(None)
    try:
        yield
    finally:
        CURRENT.reset(token)


def bind(text: str, inputs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Bind the scope as data so Janus caches query shapes, not scope lifetimes."""
    scope = CURRENT.get()
    if scope is None:
        return text, inputs
    variable = "__MettaScope"
    while variable in text or variable in inputs:
        variable += "_"
    return f"lib_thread:scope_call({variable}, ({text}))", {**inputs, variable: scope}


def current() -> str | None:
    """The scope this code runs under: the engine's while the engine is calling in.

    Inside a callback the engine may hold a scope the host never entered (a
    `(scope ...)` body that called a Python operation), so the engine is asked;
    everywhere else the host's own ContextVar is the whole answer, and a door
    access costs no engine call to find that out.
    """
    if _callbacks.entered():
        from ._engine import active_runtime  # noqa: PLC0415 -- engine imports this context

        rt = active_runtime()
        if rt is not None:
            with suspend():
                row = rt.must(
                    "(current_predicate(lib_thread:scope_current/1) -> "
                    "lib_thread:scope_current(Scope); Scope=none)"
                )
            if row["Scope"] != "none":
                return str(row["Scope"])
    return CURRENT.get()


def attach(space: Any) -> bool:
    """Attach Python cleanup to a space already owned by the library."""
    with suspend():
        row = space._rt.must(
            "(current_predicate(lib_thread:scope_attach_space/3) -> "
            "lib_thread:scope_attach_space(Name, none, Scoped); Scoped=false)",
            Name=space._name,
        )
        scoped = row["Scoped"] in (True, "true")
        if scoped:
            space._rt.must(
                "lib_thread:scope_attach_space(Name, Host, _)",
                Name=space._name, Host=space.drop,
            )
    return scoped


def own(kind: str, value: Any) -> str | None:
    """Enrol a host resource before handing it to its caller."""
    scope = current()
    if scope is None:
        return None
    from ._engine import active_runtime, runtime  # noqa: PLC0415 -- engine imports this context

    with suspend():
        row = (active_runtime() or runtime()).must(
            "lib_thread:scope_host_resource(Scope, Kind, Object, Token)",
            Scope=scope, Kind=kind, Object=value,
        )
    return str(row["Token"])


def own_future(future: Future[Any]) -> None:
    """Publish Executor completion to the scope's existing failure policy."""
    token = own("future", lambda _scope_id: future.cancel())
    if token is None:
        return

    def completed(done: Future[Any]) -> None:
        error = None if done.cancelled() else done.exception()
        finished(token, error)

    future.add_done_callback(completed)


def finished(token: str | None, error: BaseException | None = None) -> None:
    """Publish a host child's completion to its library-owned receipt queue."""
    if token is None:
        return
    from ._engine import active_runtime, runtime  # noqa: PLC0415 -- engine imports this context

    if isinstance(error, Cancelled):
        error = None
    with suspend():
        (active_runtime() or runtime()).must(
            "lib_thread:scope_host_done(Token, Error)",
            Token=token, Error="none" if error is None else error,
        )
