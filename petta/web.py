"""Purpose: the web-routing functor, FastAPI's semantics on the engine: an
app is a space, the route table is facts, a request is a term, dispatch is
unification in registration order, path parameters are variables with
FastAPI's typed converters, the 404 is the absence of a match and the 422 a
match whose parameter refuses its type. The facts are the single source of
truth: dispatch reads the table back from the space every request, handlers
are called BY NAME through the engine, so a Python function registered as
an operation and a MeTTa equation added by a program dispatch identically,
and a MeTTa program can read or extend the route table like any facts.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: query strings and request bodies once a transport
    integration needs them; today requests are method plus path, the
    routing semantics themselves.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Callable

from .atoms import (
    Atom,
    Expr,
    Gnd,
    Sym,
    Var,
    alpha_eq,
    decode,
    encode,
    expr,
    unify,
    variables,
)

__all__ = ["router", "Router", "Route", "Response"]

#: FastAPI's path converters: the spelling in {name:int} to the caster that
#: runs after the structural match, exactly the pydantic-after-match order,
#: so /users/abc against /users/{id:int} is a 422, not a 404.
_CASTERS: dict[str, Callable[[str], Any]] = {
    "str": str,
    "int": int,
    "float": float,
}

_APP_NAMES = itertools.count(1)


@dataclass(frozen=True)
class Response:
    """What a dispatch answers: a status and a decoded body."""

    status: int
    body: Any

    def __iter__(self):  # (status, body) unpacking
        yield self.status
        yield self.body


@dataclass(frozen=True)
class Route:
    """One compiled route: the MeTTa pattern its fact carries, the casters
    its parameters run, and the handler name the engine will evaluate."""

    method: str
    path: str
    pattern: Expr
    params: tuple[str, ...]
    casters: tuple[Callable[[str], Any], ...]
    handler: str
    index: int


def _segments(path: str) -> list[str]:
    trimmed = path.strip("/")
    return trimmed.split("/") if trimmed else []


def _compile(method: str, path: str, handler: str, index: int) -> Route:
    """A path template into the pattern its route fact stores: literal
    segments are symbols, {name} and {name:type} are variables, so the
    fact (route app GET (users $id) handler k) is the whole routing rule."""
    atoms: list[Atom] = []
    params: list[str] = []
    casters: list[Callable[[str], Any]] = []
    for segment in _segments(path):
        if segment.startswith("{") and segment.endswith("}"):
            inner = segment[1:-1]
            name, _, converter = inner.partition(":")
            converter = converter or "str"
            if converter not in _CASTERS:
                raise ValueError(
                    f"unknown path converter {converter!r} in {path!r}; "
                    f"the converters are {sorted(_CASTERS)}"
                )
            if not name.isidentifier():
                raise ValueError(
                    f"path parameter {name!r} in {path!r} is not a name"
                )
            atoms.append(Var(name))
            params.append(name)
            casters.append(_CASTERS[converter])
        else:
            atoms.append(Sym(segment))
    return Route(
        method=method,
        path=path,
        pattern=Expr(atoms),
        params=tuple(params),
        casters=tuple(casters),
        handler=handler,
        index=index,
    )


class Router:
    """Routes on a space, FastAPI-shaped.

        app = web.router(m, name="app")

        @app.get("/users/{id:int}")
        def read_user(id):
            return f"user {id}"

        app.dispatch("GET", "/users/7")      # Response(200, 'user 7')

    The decorator registers the function as an ordinary operation and adds
    the fact (route app GET (users $id) read-user 0) to the space. dispatch
    reads its app's facts back in registration order, first match winning
    as in FastAPI, casts each parameter, and evaluates (read-user 7)
    through the engine. A MeTTa program that adds its own route fact naming
    an equation gets dispatched exactly the same way; several routers share
    one space without sharing tables, since each reads its own app name.
    """

    def __init__(self, m, prefix: str = "", name: str | None = None) -> None:
        self._m = m
        self._prefix = prefix.rstrip("/")
        self.name = name if name is not None else f"app-{next(_APP_NAMES)}"
        self._routes: list[Route] = []
        self._middleware: list[Callable] = []

    # ------------------------------------------------------------ registration

    def route(self, method: str, path: str) -> Callable:
        """The general decorator; get/post/put/delete spell it per method."""

        def wrap(fn: Callable) -> Callable:
            handler = fn.__name__.replace("_", "-")
            self._m.op(fn, name=handler, typed=False)
            self.add_route(method, path, handler)
            return fn

        return wrap

    def get(self, path: str) -> Callable:
        return self.route("GET", path)

    def post(self, path: str) -> Callable:
        return self.route("POST", path)

    def put(self, path: str) -> Callable:
        return self.route("PUT", path)

    def delete(self, path: str) -> Callable:
        return self.route("DELETE", path)

    def add_route(self, method: str, path: str, handler: str) -> Route:
        """A route for a handler the engine already answers: a registered
        operation or a MeTTa equation, named rather than imported."""
        compiled = _compile(
            method.upper(), self._prefix + path, handler, len(self._routes)
        )
        self._routes.append(compiled)
        self._m.add(
            expr(
                Sym("route"),
                Sym(self.name),
                Sym(compiled.method),
                compiled.pattern,
                Sym(handler),
                compiled.index,
            )
        )
        return compiled

    def include(self, other: "Router", prefix: str = "") -> None:
        """Another router's routes, re-registered here under a prefix, the
        APIRouter nesting: the routes join this table in order, after the
        ones already registered, under this router's own app name."""
        for route in other._routes:
            self.add_route(route.method, prefix + route.path, route.handler)

    def middleware(self, fn: Callable) -> Callable:
        """FastAPI-shaped middleware: fn(request, call_next) -> Response,
        outermost first. request is the (method, path) pair."""
        self._middleware.append(fn)
        return fn

    # --------------------------------------------------------------- dispatch

    def dispatch(self, method: str, path: str) -> Response:
        """One request through the table: the routing semantics."""

        def call(request: tuple[str, str]) -> Response:
            return self._dispatch(*request)

        handler = call
        for middleware in reversed(self._middleware):
            handler = _wrap_middleware(middleware, handler)
        return handler((method.upper(), path))

    def _dispatch(self, method: str, path: str) -> Response:
        request = Expr([Sym(s) for s in _segments(path)])
        matched = False
        for pattern, handler, index in self._table(method):
            if len(pattern) != len(request):
                continue
            bindings = unify(pattern, request)
            if bindings is None:
                continue
            matched = True
            casters = self._casters(index, pattern)
            values = []
            ok = True
            for name, caster in zip(variables(pattern), casters):
                try:
                    values.append(caster(str(bindings[name])))
                except (ValueError, TypeError):
                    ok = False
                    break
            if not ok:
                continue
            return self._call(handler, values)
        if matched:
            # A route matched structurally but a parameter refused its
            # type, and no later route accepted: FastAPI's 422.
            return Response(422, "unprocessable")
        return Response(404, "not found")

    def _table(self, method: str) -> list[tuple[Expr, str, int]]:
        """This app's routes read back from the space, registration order:
        the facts are the table, so MeTTa-added routes serve too."""
        rows = self._m.query(
            expr(
                Sym("route"),
                Sym(self.name),
                Sym(method),
                Var("pattern"),
                Var("handler"),
                Var("k"),
            )
        )
        table = [
            (row.pattern, str(row.handler), int(decode(row.k)))
            for row in rows
            if isinstance(row.pattern, Expr)
        ]
        table.sort(key=lambda entry: entry[2])
        return table

    def _casters(self, index: int, pattern: Expr) -> tuple[Callable, ...]:
        """The registered casters for a registered route; a route added
        from MeTTa has none declared, so its parameters stay text. The
        pattern must alpha-match the registered one, so a MeTTa fact
        reusing a registered index cannot borrow the wrong converters."""
        if 0 <= index < len(self._routes) and alpha_eq(
            pattern, self._routes[index].pattern
        ):
            return self._routes[index].casters
        return tuple(str for c in pattern.children if isinstance(c, Var))

    def _call(self, handler: str, values: list[Any]) -> Response:
        answers = self._m.eval(expr(Sym(handler), *[encode(v) for v in values]))
        if not answers:
            return Response(404, "not found")
        answer = answers[0]
        if (
            isinstance(answer, Expr)
            and len(answer) == 3
            and answer.head == Sym("response")
        ):
            return Response(int(decode(answer[1])), _plain(answer[2]))
        return Response(200, _plain(answer))


def _plain(value: Any) -> Any:
    if isinstance(value, Gnd):
        return decode(value)
    return value


def _wrap_middleware(middleware: Callable, inner: Callable) -> Callable:
    def wrapped(request: tuple[str, str]) -> Response:
        return middleware(request, inner)

    return wrapped


def router(m, prefix: str = "", name: str | None = None) -> Router:
    """A router on this space; the module's one entry point."""
    return Router(m, prefix, name)
