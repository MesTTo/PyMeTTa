"""Purpose: the pure-Python structures on the atom kernel: PatternMap's
dict-law and dispatch, MatchIndex against the brute-force oracle, AlphaSet
as alpha_eq membership, and the module's engine-freedom.
Guarantees:
  - petta.structures imports and works in a process that never loads janus
    [tested test_structures_are_engine_free, subprocess-proven]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import subprocess
import sys

import pytest
from hypothesis import given
from hypothesis import strategies as st

from petta import S, V, expr, val
from petta.atoms import unify
from petta.structures import AlphaSet, MatchIndex, PatternMap
from petta.testing import atoms as atom_strategy


def test_patternmap_ground_keys_are_dict_keys():
    pm = PatternMap()
    pm[S.route(S.home)] = "home"
    pm[S.route(S.away)] = "away"
    assert pm[S.route(S.home)] == "home"
    assert len(pm) == 2
    pm[S.route(S.home)] = "home2"  # overwrite, dict law
    assert pm[S.route(S.home)] == "home2"
    del pm[S.route(S.away)]
    assert len(pm) == 1
    with pytest.raises(KeyError):
        pm[S.route(S.away)]
    with pytest.raises(KeyError):
        del pm[S.route(S.gone)]


def test_patternmap_pattern_keys_are_alpha_one_entry():
    pm = PatternMap()
    pm[S.route(V.x)] = "fallback"
    # The same key under a renamed variable IS the same key.
    pm[S.route(V.y)] = "fallback2"
    assert len(pm) == 1
    assert pm[S.route(V.z)] == "fallback2"
    del pm[S.route(V.anything)]
    assert len(pm) == 0


def test_patternmap_matching_answers_the_dispatch_question():
    pm = PatternMap()
    pm[S.route(S.home)] = "exact"
    pm[S.route(V.page)] = "any-route"
    pm[V.everything] = "catch-all"
    pm[S.other(S.thing, S.two)] = "unrelated"
    hits = {value for _, value in pm.matching(S.route(S.home))}
    assert hits == {"exact", "any-route", "catch-all"}
    hits = {value for _, value in pm.matching(S.route(S.away))}
    assert hits == {"any-route", "catch-all"}
    # A probe with variables reaches ground entries it unifies with.
    hits = {value for _, value in pm.matching(S.other(V.a, V.b))}
    assert "unrelated" in hits


def test_patternmap_refuses_source_text():
    with pytest.raises(TypeError, match="never parses"):
        PatternMap()["(route home)"] = 1


def test_matchindex_routes_and_removes():
    inbox = MatchIndex()
    inbox.add(S.order(V.id, S.express), "rush")
    inbox.add(S.order(V.id, S.standard), "slow")
    inbox.add(S.order(val(7), V.tier), "seven")
    assert len(inbox) == 3
    hits = [value for _, value in inbox.matches(S.order(val(7), S.express))]
    assert hits == ["rush", "seven"]
    assert inbox.remove(S.order(V.id, S.express), "rush") is True
    assert inbox.remove(S.order(V.id, S.express), "rush") is False
    assert [v for _, v in inbox.matches(S.order(val(7), S.express))] == ["seven"]


def test_matchindex_nonlinear_patterns_are_exact():
    inbox = MatchIndex()
    inbox.add(S.pair(V.x, V.x), "same")
    inbox.add(S.pair(V.x, V.y), "any")
    assert [v for _, v in inbox.matches(S.pair(S.a, S.a))] == ["same", "any"]
    assert [v for _, v in inbox.matches(S.pair(S.a, S.b))] == ["any"]


@given(
    patterns=st.lists(atom_strategy(max_leaves=5), min_size=0, max_size=8),
    probe=atom_strategy(max_leaves=5, ground=True),
)
def test_matchindex_agrees_with_brute_force(patterns, probe):
    index = MatchIndex()
    for position, pattern in enumerate(patterns):
        index.add(pattern, position)
    answered = [value for _, value in index.matches(probe)]
    expected = [
        position
        for position, pattern in enumerate(patterns)
        if unify(pattern, probe) is not None
    ]
    assert answered == expected


def test_alphaset_is_alpha_membership():
    rules = AlphaSet()
    rules.add(expr(S["="], S.inc(V.x), expr(S["+"], V.x, 1)))
    assert expr(S["="], S.inc(V.n), expr(S["+"], V.n, 1)) in rules
    rules.add(expr(S["="], S.inc(V.q), expr(S["+"], V.q, 1)))
    assert len(rules) == 1  # the renamed twin is the same element
    rules.add(S.pair(V.x, V.y))
    rules.add(S.pair(V.x, V.x))
    assert len(rules) == 3  # different sharing is a different element
    rules.discard(S.pair(V.a, V.b))
    assert len(rules) == 2
    assert S.pair(V.a, V.a) in rules


@given(members=st.lists(atom_strategy(max_leaves=5), max_size=8),
       probe=atom_strategy(max_leaves=5))
def test_alphaset_matches_pairwise_alpha_eq(members, probe):
    from petta import alpha_eq

    held = AlphaSet(members)
    assert (probe in held) == any(alpha_eq(probe, member) for member in members)


def test_structures_are_engine_free():
    # A fresh interpreter uses the structures and never imports janus.
    code = (
        "import sys\n"
        "from petta.structures import PatternMap, MatchIndex, AlphaSet\n"
        "from petta.atoms import Sym, Var, Expr\n"
        "pm = PatternMap(); pm[Expr([Sym('r'), Var('x')])] = 1\n"
        "assert list(pm.matching(Expr([Sym('r'), Sym('a')])))\n"
        "mi = MatchIndex(); mi.add(Expr([Sym('r'), Var('x')]), 'h')\n"
        "assert list(mi.matches(Expr([Sym('r'), Sym('a')])))\n"
        "s = AlphaSet([Var('x')]); assert Var('y') in s\n"
        "assert 'janus_swi' not in sys.modules, 'the engine was imported'\n"
        "print('engine-free ok')\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, done.stderr
    assert "engine-free ok" in done.stdout


# ------------------------------------------------------------ engine-backed


def test_tabledmap_caches_and_stays_fresh(metta):
    from petta.structures import TabledMap

    kb = metta.new_space()
    kb.add(S.price(S.apple, 3), S.price(S.pear, 4))
    kb.run(
        f"(= (tm-cheapest) (min-atom (collapse "
        f"(match {kb.space_name} (price $i $p) $p))))"
    )
    prices = TabledMap(kb, "tm-cheapest", arity=0)
    assert prices[()] == 3
    first = prices.stats()
    assert first["tables"] == 1
    assert prices[()] == 3  # a table hit, not a recomputation
    assert prices.stats()["complete-call"] > first["complete-call"]
    # The write invalidates: SWI's incremental tabling under a literal
    # space name, the safety functools.cache does not have.
    kb.add(S.price(S.plum, 1))
    assert prices[()] == 1
    assert prices.stats()["invalidated"] >= 1
    assert () in prices
    prices.clear()
    assert prices[()] == 1


def test_tabledmap_mapping_edges(metta):
    from petta import PettaError
    from petta.structures import TabledMap

    m = metta.new_space()
    m.run("(= (tm-half $x) (if (== (% $x 2) 0) (/ $x 2) (empty)))")
    halves = TabledMap(m, "tm-half")
    assert halves[4] == 2
    with pytest.raises(KeyError):
        halves[3]  # the call answers nothing: absent key
    assert (4 in halves) is True and (3 in halves) is False
    with pytest.raises(PettaError, match="argument"):
        halves[(1, 2)]


def test_liveview_mirrors_the_space(metta):
    from petta.structures import LiveView

    sp = metta.new_space()
    with LiveView(sp, S.alert(V.level)) as alerts:
        sp.add(S.alert(S.red), S.alert(S.red), S.alert(S.amber))
        assert len(alerts) == 3 == sp.count()
        assert alerts.count(S.alert(S.red)) == 2
        # One removal OPERATION takes every copy, and the view mirrors
        # the engine's own retractall reading rather than decrementing.
        sp.remove(S.alert(S.red))
        assert len(alerts) == 1 and S.alert(S.red) not in alerts
        sp.remove(S.alert(V.q))
        assert len(alerts) == 0 == sp.count()
        sp.add(S.other(1))  # a non-matching write is not the view's business
        assert len(alerts) == 0


def test_closureview_terminates_and_stays_fresh(metta):
    from petta.structures import ClosureView

    g = metta.new_space()
    g.add(S.linkage(S.a, S.b), S.linkage(S.b, S.c), S.linkage(S.c, S.a))
    # A node that NAMES a defined function, deliberately: the specializer
    # once cloned the tabled closure for such an argument and the clone
    # lost its tabling, a 27,525-frame divergence. The guard in
    # maybe_specialize_call refuses to specialize tabled functions, and
    # this line keeps the trap armed without depending on test order.
    g.run("(= (d $x) (* $x 2))")
    # A cyclic SYMMETRIC closure is the nontermination case tabling
    # exists for; the class tables from birth, so this returns.
    reach = ClosureView(g, "linkage", symmetric=True)
    assert (S.c, S.a) in reach
    assert (S.a, S.nowhere) not in reach
    assert {str(x) for x in reach.reachable(S.a)} == {"a", "b", "c"}
    g.add(S.linkage(S.c, S.d))
    assert (S.a, S.d) in reach  # fresh after the write
    # The closure is a MeTTa function too, callable from source.
    got = g.run("!(collapse (linkage-closure d $y))")
    assert len(list(got[0][0])) == 4
