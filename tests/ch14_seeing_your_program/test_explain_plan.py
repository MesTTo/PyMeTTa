"""Purpose: explain() as the engine's own EXPLAIN.

The plan item names the join the matcher runs rather than the one the query
shape allows, `analyze=` is the same items plus a measurement of running the
query, an analysis that would mutate refuses until it is told to, a query
result re-explains itself without pulling a row, and the explanation is data a
space stores and matches back.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import contextlib
import re

import pytest

from metta import S, V, parse
from metta.errors import EngineError
from metta.results import Rows

TRIANGLE = "(match {space} (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))"
CHAIN = "(match {space} (, (edge $x $y) (edge $y $z)) ($x $z))"
EMPTY_FACTOR = "(match {space} (, (edge $x $y) (edge $y $z) (absent $z $x)) ($x $y $z))"


@pytest.fixture()
def m(metta):
    """A scratch space holding one triangle, dropped when the test ends."""
    with metta._new_space() as space:
        space.add(S.edge(1, 2), S.edge(2, 3), S.edge(3, 1))
        yield space


@contextlib.contextmanager
def pragma(space, key, wanted):
    """Set one engine-wide pragma for a block and put back what was there.

    `pragma!` writes ONE engine-wide setting, so it outlives the space that
    wrote it and the suite fails a test that leaves one behind; MeTTa's own
    scoped form is `with-pragma!`, which cannot span a PYTHON call. `none` is
    the engine's own spelling for the unset value, so absence restores as
    exactly absence. Every test that depends on a setting names it here,
    because the suite runs in a shuffled order and a process-wide switch read
    rather than set is a test that passes on its neighbours.
    """
    before = space.runtime.once(f"metta_pragma('{key}', Value)").get("Value", "none")
    space.run(f"!(pragma! {key} {wanted})")
    try:
        yield space
    finally:
        space.run(f"!(pragma! {key} {before})")


def planning(space, wanted="True"):
    """Cyclic-join planning, which is a declared choice rather than a default."""
    return pragma(space, "plan-cyclic-joins", wanted)


def _anonymous(atom):
    """One item as text with its variable numbering removed."""
    return re.sub(r"\$_\d+", "$_", str(atom))


def plan_of(space, form):
    """The mode word of the plan item for one match form."""
    return str(space.explain(form.format(space=space.name)).plan.children[1])


def test_the_plan_names_the_join_the_engine_runs(m):
    """Three shapes, three plans, and the fourth case that is not the shape.

    The last one is the point: the query is the same cyclic triangle, and one
    stored row carrying a variable declines the trie plan at its ground
    admission. The plan follows the ROUTE, so it reads nested-loop there.
    """
    with planning(m):
        assert plan_of(m, TRIANGLE) == "generic-join"
        assert plan_of(m, CHAIN) == "nested-loop"
        assert plan_of(m, EMPTY_FACTOR) == "empty-factor"
        m.add(S.edge(V.a, V.b))
        assert plan_of(m, TRIANGLE) == "nested-loop"


def test_the_plan_reads_nested_loop_while_planning_is_off(m):
    """The pragma is the gate, and explain reports the gate's answer."""
    with planning(m, "False"):
        assert plan_of(m, TRIANGLE) == "nested-loop"


def test_the_generic_join_plan_carries_its_order_and_its_relations(m):
    """The order is the query variables, the relations their column numbers."""
    with planning(m):
        plan = m.explain(TRIANGLE.format(space=m.name)).plan
        assert str(plan.children[1]) == "generic-join"
        order = plan.children[2]
        assert str(order.children[0]) == "order"
        assert len(order.children) == 4
        relations = plan.children[3]
        assert [str(child) for child in relations.children[1:]] == [
            "(edge 1 2)",
            "(edge 2 3)",
            "(edge 1 3)",
        ]


def test_the_nested_loop_plan_names_the_conjunct_it_leads_with(m):
    """The order item hoists what the matcher hoists, by asking the matcher.

    `cheapest_conjunct/6` leads with a conjunct that matches at most one row,
    and the item is that same call rather than a second reading of its rule.
    """
    m.add(S.only("z"))
    plan = m.explain(f"(match {m.name} (, (edge $x $y) (only $w)) ($x $w))").plan
    assert str(plan.children[1]) == "nested-loop"
    order = plan.children[2]
    assert [_anonymous(child) for child in order.children[1:]] == [
        "(only $_)",
        "(edge $_ $_)",
    ]


def test_the_materialized_item_reads_the_space_it_is_asked_about(m):
    """A space whose source relations are derived says so; one whose are not
    says that, which is the point of an item that can answer both ways.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose
    assert str(m.explain(CHAIN.format(space=m.name))["materialized"]) == (
        "(materialized False)"
    )
    with pragma(m, "materialize-source-relations", "True"), m._new_space() as derived:
        derived.run(
            "\n".join(f"(mz-edge n{i} n{i + 1})" for i in range(32))
            + "\n(= (mz-reach $x $y) (match &self (mz-edge $x $y) True))"
            + "\n(= (mz-reach $x $y) (match &self (mz-edge $x $z) (mz-reach $z $y)))"
        )
        assert [str(a) for a in derived.eval(S.mz_reach(S.n0, S.n32))] == ["True"]
        explained = derived.explain(f"(match {derived.name} (mz-edge $x $y) $x)")
        assert str(explained["materialized"]) == "(materialized True)"


def test_an_explanation_is_a_mapping_over_its_item_heads(m):
    """Every item reachable by its head, and every atom reachable in order."""
    explanation = m.explain(CHAIN.format(space=m.name))
    assert set(explanation) >= {
        "handles", "pushes", "source", "context", "annotations", "emits",
        "events", "writes", "on-error", "merge", "plan", "materialized",
    }
    assert explanation["plan"] is explanation.plan
    assert explanation["handles"] is explanation.route
    assert tuple(explanation.values()) == tuple(explanation.atoms)
    assert len(explanation.atoms) == len(explanation)
    assert not explanation.analyzed
    assert "materialized" in repr(explanation._repr_html_())


def test_an_explanation_is_data_a_space_stores_and_matches_back(m):
    """Everything is data, the machinery included: the items are atoms."""
    explanation = m.explain(CHAIN.format(space=m.name))
    with m._new_space() as store:
        store.add(*explanation.atoms)
        rows = store.match(S.writes(V.atomicity), into=Rows)
        assert [str(row.atomicity) for row in rows] == [
            str(explanation["writes"].children[1])
        ]


def test_analyze_numbers_equal_the_stats_of_the_same_query(m):
    """`analyze=True` is `stats()` around `eval()`, and says so exactly."""
    query = parse(TRIANGLE.format(space=m.name))
    m.eval(query)
    with m.stats() as counters:
        answers = m.eval(query)
    explanation = m.explain(query, analyze=True)
    assert explanation.analyzed
    assert explanation["inferences"].children[1].value == counters.inferences
    assert explanation["answers"].children[1].value == len(answers)
    assert explanation["cputime"].children[1].value >= 0.0
    assert "plan" in explanation


def test_analyze_refuses_a_query_that_writes_until_it_is_told_to(m):
    """A match template IS evaluated, so a writing template is a writing query."""
    writing = f"(match {m.name} (edge $x $y) (add-atom {m.name} (seen $x)))"
    with pytest.raises(ValueError, match="add-atom is writesState"):
        m.explain(writing, analyze=True)
    assert not m.match(S.seen(V.x), into=Rows)
    measured = m.explain(writing, analyze=True, allow_writes=True)
    assert measured["inferences"].children[1].value > 0
    assert len(m.match(S.seen(V.x), into=Rows)) == 3


def test_explaining_a_form_that_is_neither_a_match_nor_a_call_refuses(m):
    """The engine's own type_error(explainable, ...) reaches the caller whole.

    Its sentence names the two forms explain covers, so the refusal says what
    to write instead rather than only what was wrong.
    """
    with pytest.raises(EngineError, match="explainable"):
        m.explain("5")
    with pytest.raises(EngineError, match="explain covers"):
        m.explain(V.anything)


def test_rows_explain_re_explains_the_query_that_produced_them(m):
    """The lazy view explains without pulling, the eager one after pulling."""
    with planning(m):
        lazy = m.match(S.edge(V.x, V.y), S.edge(V.y, V.z), S.edge(V.z, V.x))
        assert str(lazy.explain().plan.children[1]) == "generic-join"
        assert len(list(lazy)) == 3
        eager = m.match(
            S.edge(V.x, V.y), S.edge(V.y, V.z), S.edge(V.z, V.x), into=Rows
        )
        assert str(eager.explain().plan.children[1]) == "generic-join"
        assert eager.explain(analyze=True)["answers"].children[1].value == 3


def test_a_rows_with_no_query_behind_it_refuses_to_explain():
    """A constructed table has no match form to explain, and says which door."""
    with pytest.raises(TypeError, match="retained its patterns"):
        Rows(("x",), [(1,)]).explain()


def test_the_metta_form_answers_the_same_items_as_the_python_door(m):
    """One mechanism, two faces: (explain ...) and Space.explain agree."""
    with planning(m):
        form = TRIANGLE.format(space=m.name)
        engine_side = m.run(f"!(explain {form})")[0][0]
        python_side = m.explain(form)
        # Two calls, two copies, so the plan's variables are numbered
        # separately; what has to agree is everything else.
        assert [_anonymous(child) for child in engine_side.children] == [
            _anonymous(atom) for atom in python_side.atoms
        ]
