"""Purpose: the specification's acceptance demonstration, whole: two
backends that did not exist when the contract was written attach with
atoms plus one transport and zero engine edits. &sql-acc is stdlib
sqlite3 under closed-world bag semantics with transactional writes;
&vec-acc is a cosine index under open-world ranked semantics with a
best-first emission promise. Every assertion here is one of the spec's
own expected bullets, so this file failing means the acceptance claim
is false, not that a test is stale.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import sqlite3

import pytest

from metta import Answer, Expression, S
from metta.atoms import Variable, parse
from metta.errors import EngineError
from metta.foreign import SpaceProvider
from metta.testing import check_space_provider


class SqlEdges(SpaceProvider):
    """One table edge(a, b); WHERE from bound positions, LIMIT from the
    licensed bound, INSERT under the engine's transaction.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def __init__(self):  # noqa: D107  -- the test double construction contract is local to its containing scenario
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("CREATE TABLE edges (a TEXT, b TEXT)")
        self.connection.executemany(
            "INSERT INTO edges VALUES (?, ?)",
            [("a", "b"), ("b", "c"), ("c", "d"), ("d", "d")],
        )
        self.executed = []

    def atoms(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        rows = self.connection.execute("SELECT a, b FROM edges")
        return (parse(f"(edge {a} {b})") for a, b in rows)

    def match(self, pattern, *, limit=None):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        where, arguments = [], []
        if isinstance(pattern, Expression) and len(pattern.children) == 3:
            for column, child in zip(("a", "b"), pattern.children[1:], strict=True):
                if not isinstance(child, Variable):
                    where.append(f"{column} = ?")
                    arguments.append(str(child))
        sql = "SELECT a, b FROM edges"
        if where:
            sql += " WHERE " + " AND ".join(where)
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        self.executed.append(sql)
        rows = self.connection.execute(sql, arguments)
        return (parse(f"(edge {a} {b})") for a, b in rows)

    def add(self, atom):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        _, a, b = atom.children
        self.connection.execute(
            "INSERT INTO edges VALUES (?, ?)", (str(a), str(b))
        )

    def begin(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        self.connection.execute("BEGIN")

    def commit(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        self.connection.commit()

    def rollback(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        self.connection.rollback()


@pytest.fixture
def sql(metta, request):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name = f"&sql-{request.node.name[-18:].replace('_', '')}"
    provider = SqlEdges()
    metta._register_space(provider, name)
    metta._at(name).context("closed-world")
    metta.annotations(name, "bag")
    metta._at(name).handles("(edge $x $y)", "Exact")
    metta._at(name).handles("(edge $x $x)", "Sound")
    metta._at(name).writes("transactional")
    yield name, provider
    metta._unregister_space(name)


def test_sql_context_passes_the_conformance_kit():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert check_space_provider(SqlEdges()) != []


def test_sql_context_routes_the_bound_exactly_as_declared(metta, sql):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, provider = sql
    out = metta.run(
        f"!(collapse (take 2 (match {name} (edge $x $y) (edge $x $y))))"
    )
    assert provider.executed == ["SELECT a, b FROM edges LIMIT 2"]
    assert str(out[0][0]) == "((edge a b) (edge b c))"

    provider.executed.clear()
    metta.run(
        f"!(collapse (take 2 (match {name}"
        " (, (edge $x $y) (edge $y $z)) (path $x $z))))"
    )
    assert all("LIMIT" not in sql for sql in provider.executed)


def test_sql_context_explains_its_own_route(metta, sql):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, _provider = sql
    out = metta.run(f"!(explain (match {name} (edge $x $y) $y))")
    explained = {str(item.children[0]): item for item in out[0][0].children}
    assert "Exact" in str(explained["handles"])
    assert str(explained["pushes"].children[1]) == "True"
    assert str(explained["writes"].children[1]) == "transactional"
    assert str(explained["context"].children[1]) == "closed-world"


def test_sql_context_rolls_back_with_the_engine(metta, sql):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, provider = sql
    with pytest.raises(EngineError):
        metta.run(
            f"!(transaction (chain (add-atom {name} (edge x y)) $_"
            " (error boom)))"
        )
    rows = provider.connection.execute(
        "SELECT COUNT(*) FROM edges WHERE a = 'x'"
    ).fetchone()
    assert rows[0] == 0


def test_sql_context_permits_negation_over_its_closed_world(metta, sql):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name, _provider = sql
    metta.run(f"(= (acc-has $x $y) (match {name} (edge $x $y) True))")
    assert str(metta.run("!(not-provable (acc-has q q))")[0][0]) == "True"
    assert str(metta.run("!(not-provable (acc-has a b))")[0][0]) == "False"


class CosineIndex(SpaceProvider):
    """(near <key> $hit) over stored vectors, best first, honouring the
    licensed bound; pure python cosine, no array dependency.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def __init__(self, emit_in_order=True):  # noqa: D107, FBT002  -- the test double construction contract is local to its containing scenario; the boolean is established API data and positional compatibility is part of the call shape
        self.vectors = {
            "espresso": (0.9, 0.1, 0.0),
            "latte": (0.8, 0.3, 0.0),
            "granite": (0.0, 0.1, 0.9),
        }
        self.limits = []
        self.emit_in_order = emit_in_order

    def _cosine(self, a, b):
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm = lambda v: sum(x * x for x in v) ** 0.5  # noqa: E731
        return round(dot / (norm(a) * norm(b)), 6)

    def match(self, pattern, *, limit=None):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        self.limits.append(limit)
        query = str(pattern.children[1])
        anchor = self.vectors[query]
        scored = sorted(
            ((key, self._cosine(anchor, vec)) for key, vec in self.vectors.items()),
            key=lambda pair: -pair[1],
        )
        if not self.emit_in_order:
            scored = list(reversed(scored))
        if limit is not None:
            scored = scored[:limit]
        for key, cosine in scored:
            yield Answer(
                value=Expression(S.near, S[query], S[key]), k=cosine
            )


def _vec_context(metta, name, *, best_first=True):
    provider = CosineIndex(emit_in_order=best_first)
    metta._register_space(provider, name)
    metta._at(name).context("open-world")
    metta.annotations(name, "ranked")
    metta._at(name).source("repeated")
    metta._at(name).handles("(near (in $q) $hit)", "Exact", det="semidet")
    metta._at(name).handles("(near $q $hit)", "Refuse")
    if best_first:
        metta._at(name).emits("best-first")
    return provider


def test_vec_context_pushes_top_k_under_its_three_declarations(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _vec_context(metta, "&vec-push")
    out = metta.run("!(collapse (top 2 (match &vec-push (near espresso $h) $h)))")
    assert provider.limits == [2]
    assert str(out[0][0]) == "(espresso latte)"


def test_vec_context_withholds_the_push_without_the_emission_promise(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    provider = _vec_context(metta, "&vec-uo", best_first=False)
    out = metta.run("!(collapse (top 2 (match &vec-uo (near espresso $h) $h)))")
    # No emits declaration: the engine takes every answer and orders them
    # itself, so the out-of-order provider cannot cost an answer.
    assert provider.limits == [None]
    assert str(out[0][0]) == "(espresso latte)"


def test_vec_context_refuses_the_open_shape_loudly(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _vec_context(metta, "&vec-ref")
    with pytest.raises(EngineError, match="Refuse"):
        metta.run("!(collapse (match &vec-ref (near $q $h) $h))")


def test_vec_context_refuses_negation_over_its_open_world(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _vec_context(metta, "&vec-neg")
    metta.run("(= (acc-near $q $h) (match &vec-neg (near (in $q) $h) True))")
    with pytest.raises(EngineError, match="closed-world"):
        metta.run("!(not-provable (acc-near espresso granite))")
