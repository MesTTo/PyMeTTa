"""Purpose: the web-routing functor, engine-backed: routes as facts, typed
path parameters, registration order, 404 and 422, middleware, router
nesting, and MeTTa programs reading and extending the route table.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S, V, web


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


def test_routes_dispatch_with_typed_parameters(m):
    app = web.router(m)

    @app.get("/users/{id:int}")
    def read_user(id):
        return f"user {id}"

    @app.get("/health")
    def health():
        return "ok"

    assert app.dispatch("GET", "/users/7") == web.Response(200, "user 7")
    assert app.dispatch("GET", "/health") == web.Response(200, "ok")
    # The parameter arrives as its converted type, not text.
    assert isinstance(app.dispatch("GET", "/users/7").body, str)


def test_missing_route_is_404_and_bad_parameter_is_422(m):
    app = web.router(m)

    @app.get("/users/{id:int}")
    def read_user(id):
        return id

    assert app.dispatch("GET", "/nowhere").status == 404
    assert app.dispatch("POST", "/users/7").status == 404  # method matters
    # The path matched a route's shape; the parameter refused its type.
    assert app.dispatch("GET", "/users/abc").status == 422


def test_registration_order_wins_like_fastapi(m):
    app = web.router(m)

    @app.get("/users/me")
    def read_me():
        return "me"

    @app.get("/users/{name}")
    def read_user(name):
        return f"user {name}"

    # The literal route registered first shadows the variable one.
    assert app.dispatch("GET", "/users/me").body == "me"
    assert app.dispatch("GET", "/users/ada").body == "user ada"


def test_a_typed_route_falls_through_to_a_later_match(m):
    app = web.router(m)

    @app.get("/items/{id:int}")
    def by_number(id):
        return f"number {id}"

    @app.get("/items/{name}")
    def by_name(name):
        return f"name {name}"

    assert app.dispatch("GET", "/items/7").body == "number 7"
    assert app.dispatch("GET", "/items/rope").body == "name rope"


def test_middleware_wraps_dispatch(m):
    app = web.router(m)
    seen = []

    @app.get("/ping")
    def ping():
        return "pong"

    @app.middleware
    def logging(request, call_next):
        seen.append(request)
        response = call_next(request)
        return web.Response(response.status, f"[{response.body}]")

    assert app.dispatch("GET", "/ping") == web.Response(200, "[pong]")
    assert seen == [("GET", "/ping")]


def test_routers_nest_with_prefixes(m):
    api = web.router(m)

    @api.get("/status")
    def status():
        return "green"

    app = web.router(m)
    app.include(api, prefix="/v1")
    assert app.dispatch("GET", "/v1/status").body == "green"
    assert app.dispatch("GET", "/status").status == 404


def test_metta_reads_and_extends_the_route_table(m):
    app = web.router(m, name="app")

    @app.get("/users/{id:int}")
    def read_user(id):
        return id

    # The table is facts: a MeTTa program can query it.
    rows = m.query(S.route(S.app, S.GET, V.pattern, V.handler, V.k))
    assert [str(r.handler) for r in rows] == ["read-user"]

    # And extend it: an equation added from MeTTa dispatches identically.
    m.run('(= (pong) "from metta")')
    m.run("!(add-atom (context-space) (route app GET (ping) pong 99))")
    assert app.dispatch("GET", "/ping") == web.Response(200, "from metta")


def test_handlers_answer_response_terms(m):
    app = web.router(m)

    @app.get("/teapot")
    def teapot():
        from petta import expr

        return expr(S.response, 418, "short and stout")

    assert app.dispatch("GET", "/teapot") == web.Response(418, "short and stout")


def test_custom_converters_and_route_introspection(m):
    app = web.router(m)
    app.converter("upper", str.upper)

    @app.get("/shout/{word:upper}")
    def shout(word):
        return word

    assert app.dispatch("GET", "/shout/hey").body == "HEY"
    # A caster that refuses reads as 422, exactly like the built-ins.
    def picky(text):
        raise ValueError("no")

    app.converter("picky", picky)

    @app.get("/never/{x:picky}")
    def never(x):
        return x

    assert app.dispatch("GET", "/never/thing").status == 422
    assert [r.path for r in app.routes] == ["/shout/{word:upper}", "/never/{x:picky}"]
    with pytest.raises(ValueError):
        app.add_route("GET", "/bad/{x:unknown}", "shout")


def test_every_verb_has_its_decorator(m):
    app = web.router(m)
    for verb in ("post", "put", "delete", "patch", "head", "options"):
        @getattr(app, verb)(f"/{verb}")
        def handler(v=verb):
            return v
    for verb in ("POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
        assert app.dispatch(verb, f"/{verb.lower()}").status == 200
