# PyMeTTa by example

Run a complete example from the repository root:

```sh
PYTHONPATH=extensions/python/examples \
  python extensions/python/examples/basics/first_steps.py
```

The excerpts keep source indentation, and `...` marks omitted lines; run the linked files for their imports, setup, and output checks.

## Start here

### [basics/first_steps.py](basics/first_steps.py)

Run MeTTa source, build atoms in Python, query with joins, and evaluate.

`extensions/python/examples/basics/first_steps.py`

```python
m = MeTTa().space()
...
check("run", m.run("(= (double $x) (* $x 2))\n!(double 21)"), [[42]])
...
m.add(S.Parent(S.Tom, S.Bob), S.Parent(S.Bob, S.Ann), S.Parent(S.Ann, S.Zoe))
rows = m.match(S.Parent(V.gp, V.p), S.Parent(V.p, V.gc))
check("join count", len(rows), 2)
check("first grandparent", (rows[0].gp, rows[0].gc), (S.Tom, S.Ann))
...
check("eval", m.eval(S.superpose(Expression(1, 2, 3))), [1, 2, 3])
```

## Spaces backed by something else

### [integration/sqlite_space.py](integration/sqlite_space.py)

MeTTa declarations relate edge and document atoms to SQLite tables, and `metta.tables` derives provider operations from them.

`extensions/python/examples/integration/sqlite_space.py`

```python
    tables.declare(m, name, "(bridge (edge $a $b) (row edges (a $a) (b $b)))")
...
    provider = TableBridge.from_context(m, name, connection)
...
    provider = attach_sqlite(m, "&crm")
    m.run("!(add-atom &crm (edge a b))")
    m.run("!(add-atom &crm (edge b b))")
    m.run("!(add-atom &crm (edge b c))")
...
    (group,) = m.run("!(collapse (match &crm (edge $x $x) $x))")
    check("the diagonal derives WHERE a = b", [str(a) for a in group[0]], ["b"])
```

### [integration/duckdb_space.py](integration/duckdb_space.py)

A database becomes a space whose matches push bound positions into SQL and join rows with native facts.

`extensions/python/examples/integration/duckdb_space.py`

```python
    conn = duckdb.connect(":memory:")
    conn.execute("create table users (id integer, name text)")
    conn.execute("insert into users values (1, 'Ada'), (2, 'Bob'), (3, 'Cy')")
...
    provider = attach_database(m, "&crm", conn)
...
    check("pushdown filter", m.run("!(match &crm (users 2 $n) $n)"), [["Bob"]])
```

### [integration/networkx_space.py](integration/networkx_space.py)

View a space's expressions as a NetworkX graph, run a graph algorithm, and write its answer back as atoms.

`extensions/python/examples/integration/networkx_space.py`

```python
    graph = to_graph(m, "(edge $x $y)")
    check("every stored link is an edge", graph.number_of_edges(), 4)
...
    route = nx.shortest_path(graph, parse("a"), parse("d"))
    check("networkx answers the shortest path", [str(n) for n in route], ["a", "d"])
...
    scores = nx.degree_centrality(graph)
    m.add(*(Expression((parse("central"), node, ground(round(score, 3))))
            for node, score in scores.items()))
```

### [integration/cmetta_space.py](integration/cmetta_space.py)

A space delegates matching to a C MeTTa runtime reached as a subprocess.

`extensions/python/examples/integration/cmetta_space.py`

```python
    space = CMettaSpace(cmetta=cmetta)
    _space_declarations._register_space(m, space, "&cmetta")
    m.run("!(add-atom &cmetta (edge a b))")
    m.run("!(add-atom &cmetta (edge a c))")
    (group,) = m.run("!(collapse (match &cmetta (edge a $x) $x))")
    check("cmetta matches, this engine binds", sorted(str(a) for a in group[0]),
          ["b", "c"])
```

### [integration/persistent_migration.py](integration/persistent_migration.py)

Migrate a persistent space's schema through the public factory.

`extensions/python/examples/integration/persistent_migration.py`

```python
    with space(
        backing={"new": 1},
        journal=journal,
        sync="close",
        rename={"old": "new"},
    ) as migrated:
        check(
            "migration renames the stored head",
            list(migrated.atoms()),
            [S.new(S.value)],
        )
```

### [integration/provider_policy.py](integration/provider_policy.py)

Enforce request-specific policy at a foreign space boundary.

`extensions/python/examples/integration/provider_policy.py`

```python
    def should_run(self, capability, /, **request) -> bool:
        """Reserve system-headed additions for the catalog loader."""
        return capability != "add" or request["atom"].head != S.system

    def refusal(self, capability, /, **request):
        """Explain the one request this provider declines."""
        if capability == "add" and request["atom"].head == S.system:
            return "system facts are written by the catalog loader"
        return None
```

### [integration/provider_worlds.py](integration/provider_worlds.py)

Let a foreign provider receive bounds and commit immutable worlds.

`extensions/python/examples/integration/provider_worlds.py`

```python
    rows = space.match(S.item(V.number), limit=1)
    check("an exact provider receives the answer bound", len(rows), 1)
    check("the bounded matcher stopped at the requested count", provider.limits, [1])

    space.covers("writesState")
    world = space.reify()
    try:
        answers, successor = world.eval(S.add_atom(S["&self"], S.item(3)))
        try:
            check("world evaluation leaves the provider untouched", len(provider.rows), 3)
            check("the successor records the write", answers, [True])
            space.commit(successor)
        finally:
            successor.close()
    finally:
        world.close()
```

### [integration/registration_lifecycle.py](integration/registration_lifecycle.py)

Discover integrations without loading them and undo global hooks.

`extensions/python/examples/integration/registration_lifecycle.py`

```python
    check("entry-point discovery is an unloaded mapping", isinstance(integrate.entry_points(), dict))

    integrate.register_object_type(claims_target, "ExtensionTargetProtocol")
    integrate.register_repr(claims_target, format_target)
    integrate.register_reflector(claims_target, reflect_target)
    try:
        check("the protocol type is active", space.cast(target, "ExtensionTargetProtocol") is target)
        check("the protocol representation is active", str(ground(target)), "<extension target>")
        check("the reflector writes its facts", integrate.reflect(space, "registered", target), 1)
        check("the reflected fact is queryable", space.match(S.reflected(V.name))[0].name, S.registered)
    finally:
        integrate.unregister_reflector(claims_target, reflect_target)
        integrate.unregister_repr(claims_target, format_target)
        integrate.unregister_object_type(claims_target, "ExtensionTargetProtocol")
```

### [integration/remote_controls.py](integration/remote_controls.py)

Apply authorization and finite cursor ownership to a remote space.

`extensions/python/examples/integration/remote_controls.py`

```python
    def read_only(request: _moved_metta_remote__gateway.Request) -> bool:
        """Admit health and reads of one named space; refuse every write."""
        seen_requests.append((request.operation, request.space))
        return request.operation == "health" or (
            request.space == served_name
            and request.operation in {"match", "atoms", "ask", "next", "stop"}
        )

    with _moved_metta_remote__gateway.serve(
        served,
        spaces=[served_name],
        authorize=read_only,
        cursor_idle=30,
        cursor_limit=1,
    ) as server:
        transport = _moved_metta_remote__transport.connect(server.url, timeout=5)
        client = _moved_metta_remote__client.RemoteSpace(transport, served_name)
        capabilities = client.server_capabilities()
```

### [integration/python_objects.py](integration/python_objects.py)

Translate an Enum into symbols and a dataclass into an expression, then rebuild Python objects from answers.

`extensions/python/examples/integration/python_objects.py`

```python
class Mood(Enum):
    calm = 1
    stormy = 2


@dataclass
class Robot:
    name: str
    mood: Mood


projected = project(Robot("R2", Mood.calm))
check("projection", str(projected.atom), '(Robot "R2" calm)')
m.add(*projected.declarations, projected.atom)
m.add(project(Robot("HAL", Mood.stormy)).atom)
...
rebuilt = build(projected.atom)
check("rebuild", isinstance(rebuilt, Robot) and rebuilt.mood, Mood.calm)
```

### [integration/multishot_solving.py](integration/multishot_solving.py)

Change a program between solves without rebuilding its world, using program parts and togglable facts.

`extensions/python/examples/integration/multishot_solving.py`

```python
horizon = 0
while not proved("d", horizon):
    horizon += 1
    step.ground(horizon)
check("the goal proves at the shortest horizon", horizon, 3)
...
blocked = External(m, S.blocked(S.c))
blocked.assign(True)
...
blocked.assign(False)
check("and gone when withdrawn", m.match(S.blocked(V.x)), [])
```

### [integration/web_routes.py](integration/web_routes.py)

Represent a route table as facts, dispatch by unification, and use typed variables for path parameters.

`extensions/python/examples/integration/web_routes.py`

```python
app = Router(m, "app")
...
@app.get("/users/{id:int}", effect="pureStructural")
def read_user(id):
    return f"user {id}"
...
check("a typed route", app.dispatch("GET", "/users/7"), Response(200, "user 7"))
...
check("no match is 404", app.dispatch("GET", "/nowhere").status, 404)
check("a refused parameter is 422", app.dispatch("GET", "/users/abc").status, 422)
```

### [integration/routing_equations.py](integration/routing_equations.py)

An app is a space, routes are equations, a catch-all supplies the 404, and middleware is composition.

`extensions/python/examples/integration/routing_equations.py`

```python
app = MeTTa().space()
app.run(
    '(= (route home) (Page 200 "Welcome"))\n'
    '(= (route about) (Page 200 "About us"))\n'
    "(= (route $other) (NotFound 404 $other))\n"
    "(= (handle $req) (once (route $req)))\n"
    "(= (logged $req) (let $res (handle $req) (Logged $req $res)))"
)
check("a route", app.run("!(handle home)"), [[Expression(S.Page, 200, "Welcome")]])
check("the 404", app.run("!(handle nowhere)"), [[Expression(S.NotFound, 404, S.nowhere)]])
check("middleware is composition", app.run("!(logged about)"),
      [[Expression(S.Logged, S.about, Expression(S.Page, 200, "About us"))]])
```

### [data/array_interop.py](data/array_interop.py)

Use one operation set for DLPack libraries, with NumPy flowing through the same MeTTa functions as torch.

`extensions/python/examples/data/array_interop.py`

```python
arrays.install(m, default=numpy)

check("matmul over numpy",
      m.run("!(t-tolist (matmul (tensor ((1.0 2.0))) (tensor ((3.0) (4.0)))))"),
      [[Expression(Expression(11.0))]])
```

## Defining and running

### [operations/python_definitions.py](operations/python_definitions.py)

Compile Python definitions into MeTTa while keeping a callable Python twin.

`extensions/python/examples/operations/python_definitions.py`

```python
@m.define
def fact(n):
    if n == 0:
        return 1
    return n * fact(n - 1)

check("equations run", m.run("!(fact 6)"), [[720]])
check("the Python twin agrees", fact.py(6), 720)
check("calling the name evaluates", fact(6), [720])
```

### [operations/annotation_contracts.py](operations/annotation_contracts.py)

Annotations control evaluation and become facts derived from a compiled definition's source.

`extensions/python/examples/operations/annotation_contracts.py`

```python
@m.pure
def anyatom(term: metta.Atom) -> metta.Atom:
    return term

@m.pure
def anyval(term):
    return term
...
m.run("(= (side) 42)")
check("Atom preserves the call", m.run("!(anyatom (side))"), [[m.parse("(side)")]])
check("ordinary input reduces", m.run("!(anyval (side))"), [[42]])
```

### [operations/effect_ranks.py](operations/effect_ranks.py)

Classify an operation with a decorator and read the rank it carries.

`extensions/python/examples/operations/effect_ranks.py`

```python
@m.pure
def either(x: int):
    """Declared pure and written as a GENERATOR, which is what lifts it."""
    yield x
    yield x + 1
...
LATTICE = {
    S.double(2): (1, E.pureStructural),
    S.tally("&self"): (1, E.readOnlyLookup),
    S.either(1): (2, E.nondeterministicReadOnly),
    S.note(1): (1, E.writesState),
    S.clock(): (1, E.oracleIO),
    S["car-atom"](S.cons(S.a, S.b)): (1, E.pureStructural),
    S["get-atoms"](S["&self"]): (len(list(m.self)), E.nondeterministicReadOnly),
    S["and"](V.a, V.b): (4, E.nondeterministicReadOnly),
}

for term, (answers, rank) in LATTICE.items():
    check(f"{term} answers {answers}", len(m.eval(term)), answers)
    check(f"{term} is {rank}", m.self.effect_plan(term).effect, rank)
```

### [operations/property_instances.py](operations/property_instances.py)

Generate ground property-test instances from a symbolic pattern.

`extensions/python/examples/operations/property_instances.py`

```python
shared = find(
    testing.from_pattern(S.edge(V.node, V.node), max_leaves=2),
    lambda _atom: True,
)
check("generated instances are ground", shared.vars, ())
check("repeated named variables share a draw", shared[1], shared[2])

anonymous = find(
    testing.from_pattern(S.pair(Variable("_"), Variable("_")), max_leaves=2),
    lambda atom: atom[1] != atom[2],
)
check("anonymous occurrences draw independently", anonymous[1] != anonymous[2])
```

### [operations/engine_controls.py](operations/engine_controls.py)

Use per-call bounds, scoped limits, engine counters, and captured print output.

`extensions/python/examples/operations/engine_controls.py`

```python
with m.limits(stack=4_000_000):
    check(
        "a scoped stack-byte ceiling leaves a finite call unchanged",
        m.eval("(+ 20 22)"),
        [42],
    )
...
with m.stats() as s:
    list(m.match(S.edge(V.a, V.b), S.edge(V.b, V.c)))
check("the stats block counts the engine steps spent", s.inferences > 100)

with m.capture() as output:
    groups = m.run("!(println! (hello world)) !(+ 1 2)")
check("captured print output", "(hello world)" in output.text)
check("the answers still arrive beside it", groups[1], [3])
```

### [operations/runtime_configuration.py](operations/runtime_configuration.py)

Configure process-wide runtime and presentation settings represented as `(limit ...)` rows once the engine is running.

`extensions/python/examples/operations/runtime_configuration.py`

```python
config.configure(
    heartbeat_interval=25_000,
    declaration_limit=64,
    display_rows=7,
)

with MeTTa() as context:
    check("the configured runtime starts", context.eval("(+ 20 22)"), [42])
...
    context.run("!(add-atom &metta (limit display-rows 3))")
    check("a rewritten row is what the seat reads", config.display_rows, 3)
```

### [operations/error_handling.py](operations/error_handling.py)

Classify a false MeTTa claim separately from an engine fault.

`extensions/python/examples/operations/error_handling.py`

```python
    try:
        space.run("!(test (+ 1 1) 3)")
    except AssertionFailure as failure:
        check("the failed form is structured", failure.operation, "test")
        check("the actual result is structured", failure.actual, 2)
        check("the expected result is structured", failure.expected, 3)
```

### [operations/explaining_a_query.py](operations/explaining_a_query.py)

Explain which join the matcher will run and measure the query with `analyze=True`.

`extensions/python/examples/operations/explaining_a_query.py`

```python
m.run("!(pragma! plan-cyclic-joins True)")

e = m.explain("(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))")
check("the plan names the join that will run", str(e.plan.children[1]), "generic-join")
...
measured = m.explain(
    "(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))", analyze=True
)
check("analyze counts the answers", measured["answers"].children[1].value, 3)
check("analyze counts the inferences", measured["inferences"].children[1].value > 0)
```

### [operations/concurrency_handles.py](operations/concurrency_handles.py)

Use multi-argument pool work and nonblocking mailbox reads.

`extensions/python/examples/operations/concurrency_handles.py`

```python
    with space.pool(workers=2) as pool:
        check(
            "starmap spreads each argument tuple in input order",
            list(
                pool.starmap(
                    lambda left, right: space.eval(S["+"](left, right))[0],
                    [(1, 2), (3, 4)],
                )
            ),
            [3, 7],
        )

    with space, channel(max=1) as mailbox:
        check("try_recv returns immediately when empty", mailbox.try_recv() is None)
        mailbox.send(S.job(7))
        check("try_recv takes a waiting term", mailbox.try_recv(), S.job(7))
        check("the take leaves the mailbox empty", mailbox.try_recv() is None)
```

### [operations/saga_compensation.py](operations/saga_compensation.py)

Recover committed external-style steps through saga receipts.

`extensions/python/examples/operations/saga_compensation.py`

```python
    orders.run(
        "(= (undo-add (did add-atom ($space $atom) $result)) "
        "(remove-atom $space $atom))"
    )
    orders.compensates("add-atom", "undo-add")

    try:
        with orders.saga(receipts) as saga:
            check(
                "a committed step answers normally",
                saga.run(S.add_atom(orders, S.booked(S.Ada))),
                [True],
            )
            check(
                "the committed step leaves a queryable receipt",
                len(receipts.match(S.did(V.operation, V.arguments, V.result))),
                1,
            )
            raise CancelOrderError  # noqa: TRY301 -- exceptional scope exit is the behavior being demonstrated
    except CancelOrderError:
        pass

    check("exceptional exit ran the compensation", orders.match(S.booked(V.who)), [])
    check("successful recovery retired the receipt", receipts.atoms(), [])
```

## Reasoning

### [reasoning/pln_uncertain_reasoning.py](reasoning/pln_uncertain_reasoning.py)

Drive the engine's PLN library from Python and destructure answers carrying strength and confidence.

`extensions/python/examples/reasoning/pln_uncertain_reasoning.py`

```python
m.eval(S["=>"](S.smokes(V.x), S.cancer(V.x), S.stv(0.6, 0.9)))
m.add(equation(S.smokes(S.anna)).to(S.stv(1.0, 0.95)))
# The answer is a tuple of (conclusion (stv strength confidence)) pairs.
(answers,) = m.eval(S["?"](S.cancer(S.anna)))
(pair,) = answers
conclusion, stv = pair[0], pair[1]
check("conclusion", str(conclusion), "(cancer anna)")
strength, confidence = float(stv[1]), float(stv[2])
check("uncertainty carried", 0.0 < strength < 1.0 and 0.0 < confidence < 1.0)
check("modus ponens strength", strength, 0.6)
```

### [reasoning/neurosymbolic_addition.py](reasoning/neurosymbolic_addition.py)

An exact rule propagates a sum constraint backwards to sharpen uncertain perception.

`extensions/python/examples/reasoning/neurosymbolic_addition.py`

```python
@m.define
def consistent_with(x, y, total):
    """The same join, keeping only hypotheses whose sum is `total`, and
    answering what the FIRST observation was under that constraint.
    """
    a = match((S.sees, x, V.da, V.wa), (V.da, V.wa))
    b = match((S.sees, y, V.db, V.wb), (V.db, V.wb))
    if a[0] + b[0] == total:
        return (a[1] * b[1], a[0])
    return ()
...
kept = tuple(tuple(row) for row in consistent_with(S.a, S.b, KNOWN_SUM) if len(row) == 2)
posterior = m.fn.ws_normalize(m.fn.ws_collapse(kept).one()).one()
sharpened = dict((int(p[1]), float(p[0])) for p in posterior)
check("the constraint picks the true digit", int(m.fn.ws_best(posterior).one()), 1)
check("and is more confident than perception alone", sharpened[1] > alone[1])
```

### [reasoning/custom_matchers.py](reasoning/custom_matchers.py)

Give grounded atoms their own matching logic through an object's `match_` method.

`extensions/python/examples/reasoning/custom_matchers.py`

```python
class Regex:
    def __init__(self, pattern):
        self.pattern = re.compile(pattern)

    def match_(self, other):
        text = other.value if isinstance(other, Grounded) else str(other)
        if self.pattern.search(str(text)):
            yield other

starts_with_a = Grounded(Regex("^a"))
(hit,) = m.eval(S.unify(starts_with_a, S.abbey, S.hit, S.miss))
check("regex value matches", hit, S.hit)
(miss,) = m.eval(S.unify(starts_with_a, S.zebra, S.hit, S.miss))
check("regex value refuses", miss, S.miss)
```

### [reasoning/evolutionary_search.py](reasoning/evolutionary_search.py)

Rewrite a population space each generation, with Python variation and fitness operations and a MeTTa stopping rule.

`extensions/python/examples/reasoning/evolutionary_search.py`

```python
@m.io(name="next-generation")
def next_generation() -> bool:
    rows = m.match(S.member(V.i, V.g))
    scored = sorted(rows, key=lambda r: -fitness(r.g))
    parents = [r.g for r in scored[: len(scored) // 2]]
    del m[S.member(V.i, V.g)]          # the drain: every match, one crossing
    for index in range(16):
        a, b = random.sample(parents, 2)
        m.add(S.member(index, breed(a, b)))
    return True
...
m.run(
    "(= (best) (max-atom (collapse (match (context-space) (member $i $g) (fitness $g)))))\n"
    "(= (evolve! $gen)\n"
    "   (if (== (best) 8)\n"
    "       (Perfect after $gen generations)\n"
    "       (if (> $gen 60)\n"
    "           (Stopped at (best))\n"
    "           (let $next (next-generation) (evolve! (+ $gen 1))))))"
)
(outcome,) = m.eval(S["evolve!"](0))
```

### [reasoning/literature_discovery.py](reasoning/literature_discovery.py)

Find a hypothesis across a vocabulary gap and return a provenance polynomial naming its sources.

`extensions/python/examples/reasoning/literature_discovery.py`

```python
m.add_tagged_rule(
    S.abc,
    S.suggests(V.agent, V.condition),
    S.reports(V.agent, S.lowers, V.factor),
    S.reports(V.factor, S.aggravates, V.condition),
)
...
near_fish_oil = S.unify(G(Like(S.fish_oil)), V.agent, TRUE, S.superpose(()))
...
found = m.match(S.suggests(V.agent, S.raynaud), where=near_fish_oil, under=prov).one()
...
check(
    "and the answer carries its citations",
    str(found.annotation),
    "(plus (times (times abc p1) p2) (times (times abc p4) p5))",
)
```

## Larger pieces

### [gallery/family_algebras.py](gallery/family_algebras.py)

Run one family relation in every logical direction under every carrier.

`extensions/python/examples/gallery/family_algebras.py`

```python
def family_ancestor(ancestor, descendant):
    """Relate each ancestor to every descendant below it."""
    yield match((S.Parent, ancestor, descendant), True)  # noqa: FBT003 -- the staged result is the MeTTa truth atom
    yield family_ancestor(match((S.Parent, ancestor, V.middle), V.middle), descendant)
...
claim(
    "counting: both free",
    S.family_ancestor(V.ancestor, V.descendant),
    lambda term: _under(family, term, counting),
)
# -> (family-ancestor $ancestor $descendant)
# => (Count 12)
...
claim(
    "provenance: ground to ground",
    S.family_ancestor(S.Tom, S.Jim),
    lambda term: _under(family, term, prov),
)
# -> (family-ancestor Tom Jim)
# => (Answers (Answer (family-ancestor Tom Jim) one))
```

### [gallery/ecosystem_graph.py](gallery/ecosystem_graph.py)

Express a NetworkX shortest-path algorithm as one MeTTa operation.

`extensions/python/examples/gallery/ecosystem_graph.py`

```python
@space.reads
def ecosystem_shortest_path(source, target):
    """Project edge atoms, run NetworkX, and return one structural path."""
    graph = to_graph(space, S.edge(V.start, V.end))
    return S.Path(*nx.shortest_path(graph, source, target))

path = claim(
    "ecosystem shortest path",
    S.ecosystem_shortest_path(S.a, S.d),
    space.eval,
)[0]
# -> (ecosystem-shortest-path a d)
# => (Path a b c d)
claim("write result back", S.add_atom(space, path), space.eval)
```

### [gallery/git_like_worlds.py](gallery/git_like_worlds.py)

Branch, diff, and commit immutable worlds like local repository heads.

`extensions/python/examples/gallery/git_like_worlds.py`

```python
parent.covers("writesState")
base = parent.reify()
branches = {}
...
def branch(name):
    """Return an evaluator that records one immutable successor by name."""

    def evaluate(term):
        answers, successor = base.eval(term)
        branches[name] = successor
        return answers

    return evaluate
...
def compare_worlds(term):
    """Expose the exact two-sided multiset diff between the successors."""
    launch_only, abort_only = branches["launch"].diff(branches["abort"])
    return [S.Diff(S.Launch(*launch_only), S.Abort(*abort_only), term.children[1])]
...
    def commit_selected(term):
        """Commit the branch named by the checked structural term."""
        selected = str(term.children[1])
        parent.commit(branches[selected])
        return parent.atoms()
```

### [gallery/journaled_observed_store.py](gallery/journaled_observed_store.py)

Validate, transact, observe, close, and replay a journaled fact store.

`extensions/python/examples/gallery/journaled_observed_store.py`

```python
        orders = engine.space(
            "&gallery-orders",
            journal=journal,
            schema={"Order": 2},
            sync="close",
        )
...
        orders.pre_add(judge)
...
        subscription = orders.subscribe(S.Order(V.order_id, V.total), observed)
...
            transaction = S.progn(
                S.add_atom(orders, S.Order(1, 25)),
                S.add_atom(orders, S.Order(2, 40)),
            )

            def commit(term):
                orders.transaction(lambda: orders.eval(term))
                return orders.atoms()
...
            subscription.cancel()
            orders.drop()

        reopened = engine.space(
            "&gallery-orders-reopened",
            journal=journal,
            schema={"Order": 2},
            sync="close",
        )
```

### [gallery/linda_coordination.py](gallery/linda_coordination.py)

Coordinate one Linda tuple through watch, peek, and take.

`extensions/python/examples/gallery/linda_coordination.py`

```python
changes = mailbox.watch(S.Job(V.job_id))
...
    def watch_event(term):
        """Read the committed add event from the already-open watch."""
        event = next(changes)
        return [S.Event(S[event.action], event.bindings["job-id"], term.children[2])]
...
    def peek(term):
        """Peek the pattern carried by the checked structural operation."""
        return [mailbox.peek(term.children[2], deadline=1.0)]
...
    def take(term):
        """Take the pattern carried by the checked structural operation."""
        return [mailbox.take(term.children[2], deadline=1.0)]
```

### [gallery/symbolic_tensors.py](gallery/symbolic_tensors.py)

Lower a symbolic tensor identity to one numeric GEMM operation.

`extensions/python/examples/gallery/symbolic_tensors.py`

```python
@rules
def gallery_linalg(left, right):
    """Cancel a double transpose and select the GEMM primitive."""
    yield equation(S.MM(S.T(S.T(left)), right)).to(S.gallery_gemm(left, right))
...
gallery_linalg.lower(S.topdown, requires=S.blas, space=space)
...
claim(
    "symbolic lowering reaches GEMM",
    S.MM(
        S.T(S.T(S.Matrix(S.Row(1.0, 2.0)))),
        S.Matrix(S.Row(3.0), S.Row(4.0)),
    ),
    evaluate_under_tropical,
)
# -> (MM (T (T (Matrix (Row 1.0 2.0)))) (Matrix (Row 3.0) (Row 4.0)))
# => (Answer (Matrix (Row 11.0)) 0)
```

### [live/standing_queries.py](live/standing_queries.py)

Use spaces as actor mailboxes and standing queries as subscriptions, with delivery inside the engine's write.

`extensions/python/examples/live/standing_queries.py`

```python
transcript = []

def ping_actor(event):
    n = event.bindings["n"].value
    transcript.append(("ping", n))
    if n < 3:
        m.add(S.pong(n))


def pong_actor(event):
    n = event.bindings["n"].value
    transcript.append(("pong", n))
    m.add(S.ping(n + 1))

ping = m.subscribe(S.ping(V.n), ping_actor)
pong = m.subscribe(S.pong(V.n), pong_actor)
...
m.add(S.ping(1))
check("the exchange ran itself", transcript,
      [("ping", 1), ("pong", 1), ("ping", 2), ("pong", 2), ("ping", 3)])
```

## Every language construct, in Python

[language-feature-examples/](language-feature-examples/) contains the separate Python twins of the shipped MeTTa corpus, driven by `tools/twin_coverage.py`.

## How these stay checked

`extensions/python/tests/repository/test_examples.py` runs the 37 topical programs and checks their completion markers; examples needing an unavailable optional dependency skip with a message naming it.
