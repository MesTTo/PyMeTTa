"""Purpose: the Express/FastAPI route example on the lingua-franca reading,
built HERE, on the core surface alone, because that is the point: an app is
a space, the route table is facts, a request is a term, dispatch is
unification in registration order, path parameters are typed variables, the
404 is the absence of a match and the 422 a parameter refusing its type.
The router below is the whole implementation, not an import: some eighty
lines on top of add, query, unify and eval carry FastAPI's routing
semantics, and a MeTTa program extends the running table by adding a fact.
What it deliberately is not: `path.strip("/")` makes "" and "/" one route, so
a trailing-slash policy and its redirect are a real framework's job and not
shown; and dispatch scans the method's whole table per request, which is the
point being made legible rather than a routing index, so it is linear in the
number of routes.
Guarantees:
  - handler registration derives declarations from the callable rather than
    selecting an untyped boolean mode [tested:
    test_example_runs_and_verifies_itself; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from _common import check, done

from petta import MeTTa, S, V, Expression
from petta import wire
from petta.atoms import Expression, Grounded, Symbol, Variable, unify

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
            # Compile FIRST. Registering the operation and then compiling left
            # an unknown converter raising with the handler registered and no
            # route to reach it: a name the engine answers and the table has
            # never heard of.
            segments, casters = self.compile(path)
            handler = fn.__name__.replace("_", "-")
            self._m.op(fn, name=handler)
            self.add_route("GET", segments, casters, handler)
            return fn

        return wrap

    def compile(self, path: str) -> tuple[list, tuple]:
        segments, casters, named = [], [], set()
        for segment in path.strip("/").split("/"):
            if not (segment.startswith("{") and segment.endswith("}")):
                segments.append(Symbol(segment))
                continue
            name, _, converter = segment[1:-1].partition(":")
            if name in named:
                # Two segments named $id are ONE variable, so unification ties
                # them together and there is one binding for two casters.
                # /{x:int}/{x:float} accepted /7/7/2.5 and passed the float as
                # the next parameter.
                raise ValueError(f"{path!r} names {name!r} twice")
            named.add(name)
            segments.append(Variable(name))
            if converter and converter not in CASTERS:
                raise ValueError(
                    f"{path!r} asks for the converter {converter!r}; "
                    f"this router has {sorted(CASTERS)}"
                )
            casters.append(CASTERS[converter or "str"])
        return segments, tuple(casters)

    def add_route(self, method: str, segments: list, casters: tuple,
                  handler: str) -> None:
        self._casters[self._count] = casters
        self._m.add(
            Expression(S.route, S[self.name], S[method], Expression(segments),
                 S[handler], self._count)
        )
        self._count += 1

    def dispatch(self, method: str, path: str) -> Response:
        request = Expression([Symbol(s) for s in path.strip("/").split("/") if s])
        table = self._m.query(
            Expression(S.route, S[self.name], S[method.upper()],
                 V.pattern, V.handler, V.k)
        )
        matched = False
        for row in sorted(table, key=lambda r: int(wire.decode(r.k))):
            pattern = row.pattern
            if not isinstance(pattern, Expression) or len(pattern) != len(request):
                continue
            bindings = unify(pattern, request)
            if bindings is None:
                continue
            matched = True
            casters = self._casters.get(
                int(wire.decode(row.k)),
                tuple(str for c in pattern.children if isinstance(c, Variable)),
            )
            try:
                # strict, because the two lists agreeing is the whole reason
                # a repeated parameter name is refused at compile time; a
                # silent truncation here is how /{x:int}/{x:float} passed a
                # float on as the next parameter.
                values = [
                    caster(str(bindings[name]))
                    for name, caster in zip(pattern.vars, casters, strict=True)
                ]
            except (ValueError, TypeError):
                continue  # the parameter refused; a later route may accept
            answers = self._m.eval(Expression(Symbol(str(row.handler)),
                                        *[wire.encode(v) for v in values]))
            # Exactly one. A handler that answers nothing is not a 404, and a
            # handler that answers twice is not its first answer; both used to
            # be rewritten into a response the caller could not tell from a
            # real one.
            if len(answers) != 1:
                raise ValueError(
                    f"{row.handler} answered {len(answers)} times for "
                    f"{method} {path}; a route handler answers exactly once"
                )
            body = answers[0]
            return Response(200, wire.decode(body) if isinstance(body, Grounded) else body)
        return Response(422 if matched else 404,
                        "unprocessable" if matched else "not found")


m = MeTTa().space()
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

# A path naming one parameter twice is one variable with two casters, so it is
# refused where it is written rather than misreading a request later.
try:
    app.get("/twice/{x:int}/{x:float}")(lambda x: x)
    check("a repeated parameter name is refused", "not refused", "refused")
except ValueError as refused:
    check("a repeated parameter name is refused", "names 'x' twice" in str(refused), True)

# An unknown converter is refused BEFORE the handler is registered, so no name
# is left answering with nothing routing to it.
try:
    app.get("/unknown/{x:uuid}")(lambda x: x)
    check("an unknown converter is refused", "not refused", "refused")
except ValueError:
    check("and its handler was never registered", m.is_function("<lambda>"), False)

# A handler answers exactly once. Nothing and twice are both mistakes, and
# rewriting either into a response hides them.
m.run("(= (twice) a)")
m.run("(= (twice) b)")
m.run("!(add-atom (context-space) (route app GET (double) twice 98))")
try:
    app.dispatch("GET", "/double")
    check("a two-answer handler is refused", "not refused", "refused")
except ValueError as refused:
    check("a two-answer handler is refused", "answered 2 times" in str(refused), True)

done("web_routes")
