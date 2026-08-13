"""Purpose: the Express/FastAPI route example on the lingua-franca reading:
an app is a space, the route table is facts, a request is a term, dispatch
is unification in registration order, path parameters are typed variables,
the 404 is the absence of a match and the 422 a parameter refusing its
type. The proof of the common tongue is at the end: a route added by a
MeTTa program, naming a MeTTa equation as its handler, serves through the
same dispatch as the Python-decorated ones.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from petta import MeTTa, S, V, web

m = MeTTa().fresh_space()
app = web.router(m, name="app")


# The FastAPI shape: a decorator, a typed path parameter, a handler.
@app.get("/users/{id:int}")
def read_user(id):
    return f"user {id}"


@app.get("/users/{id:int}/karma")
def karma(id):
    return id * 10


check("a typed route", app.dispatch("GET", "/users/7"), web.Response(200, "user 7"))
check("params arrive converted", app.dispatch("GET", "/users/7/karma").body, 70)
check("no match is 404", app.dispatch("GET", "/nowhere").status, 404)
check("a refused parameter is 422", app.dispatch("GET", "/users/abc").status, 422)

# Middleware wraps dispatch, FastAPI's call_next reading.
@app.middleware
def bracket(request, call_next):
    response = call_next(request)
    return web.Response(response.status, f"[{response.body}]")


check("middleware composes", app.dispatch("GET", "/users/7").body, "[user 7]")

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
    web.Response(200, "[pong from metta]"),
)
done("15_web_routes")
