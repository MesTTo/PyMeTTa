"""Purpose: the Express/FastAPI route example on the lingua-franca reading,
built HERE, on the core surface alone, because that is the point: an app is
a space, the route table is facts, a request is a term, dispatch is
unification in registration order, path parameters are typed variables, the
404 is the absence of a match and the 422 a parameter refusing its type.
The router below is the whole implementation, not an import: some eighty
lines on top of add, query, unify and eval carry FastAPI's routing
semantics, and a MeTTa program extends the running table by adding a fact.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from dataclasses import dataclass
from typing import Any, Callable

from _common import check, done

from petta import MeTTa, S, V, expr
from petta.atoms import Expr, Gnd, Sym, Var, decode, encode, unify, variables

#: FastAPI's path converters: the caster runs after the structural match,
#: the pydantic-after-match order, so /users/abc against /users/{id:int}
#: is a 422, not a 404.
CASTERS: dict[str, Callable[[str], Any]] = {"str": str, "int": int, "float": float}


@dataclass(frozen=True)
class Response:
    status: int
    body: Any


class Router:
    """Routes on a space. The decorator registers the handler as an
    ordinary operation and adds the fact (route app GET (users $id)
    handler k); dispatch reads the facts back per request, so a route a
    MeTTa program added serves identically. Handler operation names are
    process-wide, the engine's own rule for functions."""

    def __init__(self, m, name: str) -> None:
        self._m = m
        self.name = name
        self._casters: dict[int, tuple] = {}
        self._count = 0

    def get(self, path: str) -> Callable:
        def wrap(fn: Callable) -> Callable:
            handler = fn.__name__.replace("_", "-")
            self._m.op(fn, name=handler, typed=False)
            self.add_route("GET", path, handler)
            return fn

        return wrap

    def add_route(self, method: str, path: str, handler: str) -> None:
        segments, casters = [], []
        for segment in path.strip("/").split("/"):
            if segment.startswith("{") and segment.endswith("}"):
                name, _, converter = segment[1:-1].partition(":")
                segments.append(Var(name))
                casters.append(CASTERS[converter or "str"])
            else:
                segments.append(Sym(segment))
        self._casters[self._count] = tuple(casters)
        self._m.add(
            expr(S.route, S[self.name], S[method], Expr(segments),
                 S[handler], self._count)
        )
        self._count += 1

    def dispatch(self, method: str, path: str) -> Response:
        request = Expr([Sym(s) for s in path.strip("/").split("/") if s])
        table = self._m.query(
            expr(S.route, S[self.name], S[method.upper()],
                 V.pattern, V.handler, V.k)
        )
        matched = False
        for row in sorted(table, key=lambda r: int(decode(r.k))):
            pattern = row.pattern
            if not isinstance(pattern, Expr) or len(pattern) != len(request):
                continue
            bindings = unify(pattern, request)
            if bindings is None:
                continue
            matched = True
            casters = self._casters.get(
                int(decode(row.k)),
                tuple(str for c in pattern.children if isinstance(c, Var)),
            )
            try:
                values = [
                    caster(str(bindings[name]))
                    for name, caster in zip(variables(pattern), casters)
                ]
            except (ValueError, TypeError):
                continue  # the parameter refused; a later route may accept
            answers = self._m.eval(expr(Sym(str(row.handler)),
                                        *[encode(v) for v in values]))
            body = answers[0] if answers else None
            return Response(200, decode(body) if isinstance(body, Gnd) else body)
        return Response(422 if matched else 404,
                        "unprocessable" if matched else "not found")


m = MeTTa().fresh_space()
app = Router(m, "app")


# The FastAPI shape: a decorator, a typed path parameter, a handler.
@app.get("/users/{id:int}")
def read_user(id):
    return f"user {id}"


@app.get("/users/{id:int}/karma")
def karma(id):
    return id * 10


check("a typed route", app.dispatch("GET", "/users/7"), Response(200, "user 7"))
check("params arrive converted", app.dispatch("GET", "/users/7/karma").body, 70)
check("no match is 404", app.dispatch("GET", "/nowhere").status, 404)
check("a refused parameter is 422", app.dispatch("GET", "/users/abc").status, 422)

# The table is facts, so MeTTa reads it like any facts...
handlers = m.query(S.route(S.app, S.GET, V.p, V.h, V.k))
check("the table is facts", sorted(str(r.h) for r in handlers), ["karma", "read-user"])

# ...and extends it: a route whose handler is a MeTTa equation, added by a
# MeTTa program, dispatching through the very same table.
m.run('(= (pong) "pong from metta")')
m.run("!(add-atom (context-space) (route app GET (ping) pong 99))")
check(
    "a MeTTa-added route serves",
    app.dispatch("GET", "/ping"),
    Response(200, "pong from metta"),
)
done("web_routes")
