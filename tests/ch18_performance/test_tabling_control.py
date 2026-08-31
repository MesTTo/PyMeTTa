"""Purpose: the repaired tabling control plane. Declarations are
constructed module-qualified goals, so hyphenated and uppercase names
genuinely table, named spaces instrument their own implementation module,
repeated declarations are cumulative, clearing is per-predicate, untable
removes instrumentation, and failures are loud. Live declarations
reflect into &metta as (tabled space name arity) facts, and tabling
state dies with the space life: a dropped pooled module's tables cannot
answer its next life. Each test descends from a probe in
ai-tabling-review.md or ai-tmp/tabling-probes/ that demonstrated the
defect.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import S, V, catalog, match, reflection
from metta.errors import EngineError


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        space.run("!(import! (context-space) (library lib_tabling))")
        yield space


def _tabled_property(m, name, compiled_arity):
    row = m.runtime.once(
        "space_module(Space, _M), functor(_H, F, A), "
        "( predicate_property(_M:_H, tabled) -> T = true ; T = false )",
        Space=m.name, F=name, A=compiled_arity,
    )
    return row.get("T") == "true" or row.get("T") is True


def test_hyphenated_and_uppercase_names_genuinely_table(m):
    """P01d and P02d: the old helper interpolated names into source text,
    so an uppercase name parsed as a variable and a hyphenated name was a
    domain error, both silently answering True while tabling nothing.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(= (spin-down $n) (if (== $n 0) done (spin-down (- $n 1))))")
    m.run("(= (Upper_case $n) (+ $n 1))")
    assert m.run("!(tabled (spin-down $n))") == [[True]]
    assert m.run("!(tabled (Upper_case $n))") == [[True]]
    assert _tabled_property(m, "spin-down", 2)
    assert _tabled_property(m, "Upper_case", 2)
    with m.stats() as first:
        assert m.run(
            "!(with-pragma! ((max-stack-depth 1000000)) (spin-down 200000))"
        ) == [[S.done]]
    with m.stats() as second:
        assert m.run(
            "!(with-pragma! ((max-stack-depth 1000000)) (spin-down 200000))"
        ) == [[S.done]]
    # The second call answers from the table: orders of magnitude fewer
    # engine steps than the first recursion.
    assert second.inferences < first.inferences / 10


def test_repeated_declarations_are_cumulative(m):
    """P12: the old helper reconsulted a synthetic source file, so the
    second declaration REMOVED the first predicate's tabling.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(= (first-fn $n) (+ $n 1)) (= (second-fn $n) (+ $n 2))")
    assert m.run("!(tabled (first-fn $n))") == [[True]]
    assert m.run("!(tabled (second-fn $n))") == [[True]]
    assert _tabled_property(m, "first-fn", 2)
    assert _tabled_property(m, "second-fn", 2)
    # Declaring the same function again is idempotent, not an error.
    assert m.run("!(tabled (first-fn $n))") == [[True]]
    assert _tabled_property(m, "first-fn", 2)


def test_named_space_functions_instrument_their_own_module(m):
    """P10 and P10b: the old helper always targeted the module user, so a
    function living in a named space's module was never instrumented.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(= (scoped-fn $n) (* $n 2))")
    assert m.run("!(tabled (scoped-fn $n))") == [[True]]
    assert _tabled_property(m, "scoped-fn", 2)


def test_clear_preserves_unrelated_tables_and_untable_removes(m):
    """P09's per-predicate abolish contract, now a named operation, and
    untable/1 surfaced beside it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run(
        "(= (kept-fn $n) (+ $n 1)) (= (cleared-fn $n) (+ $n 2))\n"
        "!(tabled (kept-fn $n)) !(tabled (cleared-fn $n))\n"
        "!(kept-fn 1) !(cleared-fn 1)"
    )
    count = m.runtime.once(
        "space_module(Space, _M), aggregate_all(count, current_table(_M:_G, _), N)",
        Space=m.name,
    )["N"]
    assert count == 2
    assert m.run("!(table-clear (cleared-fn $n))") == [[True]]
    remaining = m.runtime.once(
        "space_module(Space, _M), aggregate_all(count, current_table(_M:_G, _), N)",
        Space=m.name,
    )["N"]
    assert remaining == 1
    assert m.run("!(untabled (cleared-fn $n))") == [[True]]
    assert not _tabled_property(m, "cleared-fn", 2)
    assert _tabled_property(m, "kept-fn", 2)
    assert m.run("!(table-clear-all)") == [[True]]


def test_declaring_a_function_before_it_exists_holds_the_declaration(m):
    """A declaration may precede its definition: it is HELD and installs
    when the function's clauses arrive, which is the reading order
    upstream's own examples/tabling_fib.metta uses. A name that is never
    defined simply never tables.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert m.run("!(tabled (held-fn $n))") == [[True]]
    assert not _tabled_property(m, "held-fn", 2)
    m.run("(= (held-fn $n) (+ $n 1))")
    assert m.run("!(held-fn 1)") == [[2]]
    assert _tabled_property(m, "held-fn", 2)
    assert m.run("!(untabled (held-fn $n))") == [[True]]


def test_declarations_reflect_into_metta(m):
    """A live declaration is a (tabled space name arity) fact in &metta,
    input arity; repetition never duplicates it, and undeclaring removes
    it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(= (reflected-fn $n) (+ $n 1))")
    assert m.run("!(tabled (reflected-fn $n))") == [[True]]
    pattern = S.tabled(S[m.name], S["reflected-fn"], V.a)
    assert [row.a for row in catalog.match(pattern)] == [1]
    assert m.run("!(tabled (reflected-fn $n))") == [[True]]
    assert len(catalog.match(pattern)) == 1
    assert m.run("!(untabled (reflected-fn $n))") == [[True]]
    assert not catalog.match(pattern)


def test_tabled_and_defined_catalog_rows_are_schema_checked(m):
    """The two reflection heads are declared catalog vocabulary, so their
    stored rows are queryable and malformed lookalikes are refused at write.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert catalog.match(S.kind(S.tabled, S.symbol, S.symbol, S.integer))
    assert catalog.match(S.kind(S.defined, S.symbol, S.symbol))
    with pytest.raises(EngineError, match="does not fit its declared kind"):
        m.run("!(add-atom &metta (tabled &bad missing-arity))")
    with pytest.raises(EngineError, match="does not fit its declared kind"):
        m.run("!(add-atom &metta (defined &bad))")


def test_live_call_populates_the_shared_table(m):
    """The Python Answers door runs on a held SWI engine cursor. Its first
    pull enters the declared predicate and leaves a shared table visible to
    the next door, including the engine's statistics service.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.add(S.live_route_edge(S.a, S.b))

    @m.define(name="live-route-reach")
    def live_route_reach(x, y):
        return match(m, S.live_route_edge(x, y), y)

    call = S["live-route-reach"](V.x, V.y)
    assert m.eval(S.tabled(call)) == [True]
    try:
        assert list(iter(live_route_reach(S.a, V.y))) == [S.b]
        [counted] = m.fn.table_stats(call)
        assert list(counted) == [
            S.tables(1),
            S.answers(1),
            S.complete_call(1),
            S.invalidated(0),
            S.reevaluated(0),
        ]
    finally:
        assert m.eval(S.untabled(call)) == [True]


def test_a_second_live_call_reuses_the_table_but_an_undeclared_control_does_not(m):
    """Measure the routing consequence, not only the table property: an
    identical live call reuses completed shared subgoals while the same
    undeclared recursion performs its exponential work again.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    refusal = S.cache(S["live-reuse-control"], S.refuse)
    catalog.add(refusal)

    @m.define(name="live-reuse-tabled")
    def live_reuse_tabled(n):
        return n if n < 2 else live_reuse_tabled(n - 1) + live_reuse_tabled(n - 2)

    @m.define(name="live-reuse-control")
    def live_reuse_control(n):
        return n if n < 2 else live_reuse_control(n - 1) + live_reuse_control(n - 2)

    declaration = S["live-reuse-tabled"](V.n)
    assert m.eval(S.tabled(declaration)) == [True]
    try:
        assert list(iter(live_reuse_tabled(18))) == [2584]
        with m.stats() as tabled_second:
            assert list(iter(live_reuse_tabled(18))) == [2584]

        assert list(iter(live_reuse_control(18))) == [2584]
        with m.stats() as control_second:
            assert list(iter(live_reuse_control(18))) == [2584]

        assert tabled_second.inferences < control_second.inferences / 20
    finally:
        assert m.eval(S.untabled(declaration)) == [True]
        catalog.remove(refusal)


def _module_table_count(runtime, space_name):
    return runtime.once(
        "space_module(Space, _M), "
        "aggregate_all(count, current_table(_M:_G, _), N)",
        Space=space_name,
    )["N"]


def test_pool_reuse_starts_tabling_clean(metta):
    """The import-reuse defect one layer down. Clause removal leaves the
    tabled property and the answer tables standing, so a reused pooled
    module answered its NEW definition from the dead life's cache with no
    tabling declared in the new life (probe p14_pool_table_leak). The
    clear now resets the module's tabling state whole.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    free = metta.runtime.once(
        "aggregate_all(count, metta_py_free_space(_), N)"
    )["N"]
    held = [metta._new_space() for _ in range(free)]
    try:
        with metta._new_space() as first_life:
            name = first_life.name
            first_life.run("!(import! (context-space) (library lib_tabling))")
            first_life.run("(= (leak-fn $n) (+ $n 1))")
            assert first_life.run("!(tabled (leak-fn $n))") == [[True]]
            assert first_life.run("!(leak-fn 5)") == [[6]]
        with metta._new_space() as second_life:
            assert second_life.name == name
            assert _module_table_count(metta.runtime, name) == 0
            assert not reflection.match(
                S.tabled(S[name], S["leak-fn"], V.a)
            )
            second_life.run("(= (leak-fn $n) (* $n 10))")
            assert second_life.run("!(leak-fn 5)") == [[50]]
    finally:
        for space in held:
            space.drop()


def test_dropped_space_leaves_shared_tabling_alone(metta):
    """A pooled space dying resets ITS module only: a function tabled in
    user through &self keeps its instrumentation and its &metta record.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("!(import! &self (library lib_tabling))")
    metta.run("(= (shared-keeper $n) (+ $n 3))")
    assert metta.run("!(tabled (shared-keeper $n))") == [[True]]
    try:
        with metta._new_space() as scratch:
            scratch.run("!(import! (context-space) (library lib_tabling))")
            scratch.run("(= (scratch-fn $n) (+ $n 1))")
            assert scratch.run("!(tabled (scratch-fn $n))") == [[True]]
        assert _tabled_property(metta, "shared-keeper", 2)
        assert len(
            reflection.match(S.tabled(S["&self"], S["shared-keeper"], V.a))
        ) == 1
    finally:
        assert metta.run("!(untabled (shared-keeper $n))") == [[True]]


def test_a_drop_untables_before_it_removes_any_clause(metta):
    """Dropping a space that tabled something removes clauses of a predicate
    that was tabled a moment earlier, and SWI does not allow the clauses of a
    tabled predicate to be modified while its tables stand. With the untabling
    ordered after the removal, sixty cycles of table-drop-recycle-redefine
    terminated the process abnormally inside libswipl in 3 runs of 3; with it
    ordered first, 0 of 4. The count is what makes this a gate: one cycle
    never showed it, which is why the symptom read as a flake for weeks.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("!(import! &self (library lib_tabling))")
    metta.run("(= (cycle-warm $n) (+ $n 1))")
    metta.run("!(tabled (cycle-warm $n))")
    metta.run("!(cycle-warm 1)")
    for _ in range(60):
        with metta._new_space() as first_life:
            first_life.run("!(import! (context-space) (library lib_tabling))")
            first_life.run("(= (cycle-fn $n) (+ $n 1))")
            first_life.run("!(tabled (cycle-fn $n))")
            assert first_life.run("!(cycle-fn 5)") == [[6]]
            first_life.run("(cycle-edge a b)")
            first_life.run("!(match (context-space) (cycle-edge $x $y) $x)")
        with metta._new_space() as second_life:
            second_life.run("(= (cycle-fn $n) (* $n 10))")
            assert second_life.run("!(cycle-fn 5)") == [[50]]


def test_an_equation_change_does_not_pay_for_a_dropped_table(metta):
    """A function change abolishes the tables MeTTa declared.

    Not every table variant the process has ever built.

    abolish_all_tables/0 walks the whole variant trie, and the trie keeps a
    variant for every table ever built, so once a space had tabled a deep
    recursion and been dropped, every later equation change paid for it:
    measured 2026-08-31, one equation change cost 10,353, 40,355 and 160,359
    inferences after a 5,000, 20,000 and 80,000-answer table was dropped,
    which is 2N. The 60-cycle test above spent 156 of its 162 seconds that
    way. Abolishing each declared function's own subgoals instead reads 377
    inferences at all three sizes, so this pins the CLASS: the cost may not
    grow with the size of a table that is already gone.
    """
    metta.run("!(import! &self (library lib_tabling))")
    metta.run("(= (cost-warm $n) (+ $n 1))")
    metta.run("!(tabled (cost-warm $n))")
    metta.run("!(cost-warm 1)")

    def change_cost(answers: int) -> int:
        with metta._new_space() as big:
            big.run("!(import! (context-space) (library lib_tabling))")
            big.run("(= (cost-deep $n) (if (== $n 0) done (cost-deep (- $n 1))))")
            big.run("!(tabled (cost-deep $n))")
            big.run(
                f"!(with-pragma! ((max-stack-depth 1000000)) (cost-deep {answers}))"
            )
        victim = metta._new_space()
        victim.run("(= (cost-changing $n) (+ $n 1))")
        try:
            with metta.stats() as block:
                victim.run("(= (cost-changing $n) (+ $n 2))")
        finally:
            victim.drop()
        return block.inferences

    small, large = change_cost(5_000), change_cost(20_000)
    assert large <= small * 2, (
        f"an equation change cost {small} inferences after a 5,000-answer table "
        f"was dropped and {large} after a 20,000-answer one, so it is still "
        f"paying for tables that no longer exist"
    )
    assert large < 5_000, f"one equation change cost {large} inferences"
