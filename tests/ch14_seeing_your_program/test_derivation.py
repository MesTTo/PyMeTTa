"""Purpose: engine-backed tests for proof trees, validation, and rendering.
Guarantees:
  - parsing, projections, completeness checks, and both renderers handle 600
    nested proof steps without using Python recursion [tested:
    test_deep_proof_consumers_treat_depth_as_data;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
  - an empty proof list means NO PROOF and cannot mean anything else: an
    exhausted budget raises and a depth cutoff answers a non-empty partial
    tree, so the three outcomes stay distinguishable [tested:
    test_an_empty_proof_list_can_only_mean_no_proof;
    commit=538a9be9411e620822e1ec593f617c017f49e597]
  - derivation's public contract names effect execution and the speculative
    rollback boundary, and both behaviors are exercised [tested:
    test_derivation_effects_are_explicit_and_speculation_discards_engine_writes;
    commit=418bed011dfc47bb2c2d9e6b51e0d2a6f7b7e729]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from unittest import mock

import pytest

from metta import Expression, S, V, Variable
from metta.derivation import Builtin, Derivation, Fact, Step, Truncated
from metta.errors import InferenceLimitError, TimeLimitError


def test_multi_step_proof_names_equations_and_facts(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run(
        "(par-d Tom Bob)\n(par-d Bob Ann)\n"
        "(= (anc-d $x $y) (match &self (par-d $x $y) $y))\n"
        "(= (anc-d $x $y) (let $m (match &self (par-d $x $m0) $m0) (anc-d $m $y)))"
    )
    proofs = metta.derivation(S["anc-d"](S.Tom, S.Ann))
    assert len(proofs) == 1
    proof = proofs[0]
    assert proof.answer == S.Ann
    assert {f.atom for f in proof.facts} == {
        S["par-d"](S.Tom, S.Bob),
        S["par-d"](S.Bob, S.Ann),
    }
    assert len(proof.rules) == 2
    text = str(proof)
    assert "by (= (anc-d $a $b)" in text
    assert "fact (par-d Tom Bob)" in text


def test_every_proof_enumerates(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run(
        "(par-e Tom Bob)\n(par-e Bob Ann)\n"
        "(= (anc-e $x $y) (match &self (par-e $x $y) $y))\n"
        "(= (anc-e $x $y) (let $m (match &self (par-e $x $m0) $m0) (anc-e $m $y)))"
    )
    proofs = metta.derivation(S["anc-e"](S.Tom, V.who))
    answers = {p.answer for p in proofs}
    assert answers == {S.Bob, S.Ann}


def test_depth_bound_marks_runaway_search_as_partial(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("(= (loop-d $x) (loop-d $x))")
    (proof,) = metta.derivation(S["loop-d"](1), depth=5)
    assert not proof.complete
    assert proof.truncations
    assert isinstance(proof.truncations[0], Truncated)


def test_conditional_derivation_exposes_the_recursive_branch(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run(
        "(= (fact-tree $n) "
        "(if (== $n 0) 1 (* $n (fact-tree (- $n 1)))))"
    )

    (proof,) = metta.derivation(S["fact-tree"](2))

    assert proof.answer == 2
    assert len(proof.rules) == 3
    assert "(fact-tree 1)" in str(proof)
    assert not any(
        isinstance(node, Builtin) and "fact-tree" in node.text
        for node in _walk_nodes(proof.children)
    )


def test_disjunction_derivation_enumerates_each_taken_branch(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("(= (pick-tree) (superpose (1 2 3)))")
    proofs = metta.derivation(S["pick-tree"]())
    assert {proof.answer for proof in proofs} == {1, 2, 3}
    assert all(proof.complete for proof in proofs)


def test_derivation_honours_a_cut(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A cut prunes the equations after it. Recorded as a leaf and called,
    # it pruned nothing, so the proof list carried a conclusion the program
    # cannot reach: run answered first, derivation proved first and second.
    metta.run("(= (cut-tree $x) (let $c (cut) first))")
    metta.run("(= (cut-tree $x) second)")
    assert metta.run("!(cut-tree 1)") == [[S.first]]
    assert [proof.answer for proof in metta.derivation(S["cut-tree"](1))] == [S.first]


def test_derivation_still_enumerates_equations_without_a_cut(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("(= (open-tree $x) one)")
    metta.run("(= (open-tree $x) two)")
    assert [proof.answer for proof in metta.derivation(S["open-tree"](1))] == [S.one, S.two]


def test_a_cut_inside_once_stays_inside_it(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # once/1 is a cut barrier: the cut may not prune the equations beside
    # the one it sits in.
    metta.run("(= (barrier-tree $x) (let $c (once (cut)) first))")
    metta.run("(= (barrier-tree $x) second)")
    assert [proof.answer for proof in metta.derivation(S["barrier-tree"](1))] == [
        S.first,
        S.second,
    ]


def test_once_and_findall_derivations_expose_their_inner_goals(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run(
        "(= (once-tree) (once (superpose (1 2)))) "
        "(= (findall-tree) (collapse (superpose (1 2))))"
    )
    once_proof = metta.derivation(S["once-tree"]())[0]
    findall_proof = metta.derivation(S["findall-tree"]())[0]

    leaves = [
        node.text
        for proof in (once_proof, findall_proof)
        for node in _walk_nodes(proof.children)
        if isinstance(node, Builtin)
    ]
    assert all("once(" not in leaf and "findall(" not in leaf for leaf in leaves)
    assert any("1=1" in leaf for leaf in leaves)
    assert any("2=2" in leaf for leaf in leaves)


def test_depth_exhaustion_returns_a_partial_proof(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    depth = 40
    peano = "z"
    for _ in range(depth):
        peano = f"(s {peano})"
    metta.run("(= (dep-tree z) 0) (= (dep-tree (s $n)) (+ 1 (dep-tree $n)))")

    (partial,) = metta.derivation(f"(dep-tree {peano})", depth=10)
    (complete,) = metta.derivation(f"(dep-tree {peano})")

    assert not partial.complete
    assert partial.truncations
    assert complete.complete
    assert complete.answer == depth
    assert metta.derivation("(dep-tree not-a-peano)") == []


def test_unbounded_derivation_obeys_resource_guards(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("(= (loop-guard-d $x) (loop-guard-d $x))")
    with pytest.raises(InferenceLimitError):
        metta.derivation(S["loop-guard-d"](1), inferences=2_000)


def test_an_empty_proof_list_can_only_mean_no_proof(metta):
    """The three ways a search can end stay separable, so `[]` says one thing.

    A reasoner that cannot tell "I proved there is no proof" from "I ran out
    of budget" has to cache the distinction alongside the budget that produced
    it, and then maintain that cache against new evidence. PeTTa does not need
    the cache because the three outcomes have three different shapes, and this
    pins that so a friendlier `[]` on exhaustion cannot quietly replace the
    raise.
    """
    metta.run("(= (tri-d 0) done)\n(= (tri-d $n) (tri-d (- $n 1)))")

    # Budget exhaustion RAISES. It never answers the empty list.
    for guard in ({"inferences": 2_000}, {"timeout": 1e-06}):
        with pytest.raises((InferenceLimitError, TimeLimitError)):
            metta.derivation(S["tri-d"](1), **guard)

    # A depth cutoff answers a NON-EMPTY partial tree that says it is partial.
    shallow = metta.derivation(S["tri-d"](2), depth=1)
    assert shallow, "a truncated search answered nothing, which reads as no proof"
    assert not any(proof.complete for proof in shallow)
    assert all(proof.truncations for proof in shallow)

    # A larger budget REFINES it, so truncation was never a final answer.
    deep = metta.derivation(S["tri-d"](2), depth=20)
    assert any(proof.complete and not proof.truncations for proof in deep)

    # Only a genuinely unprovable target is empty.
    assert metta.derivation(S["tri-d-absent"](1)) == []


def test_a_derivation_sees_new_evidence_without_being_invalidated(metta):
    """Nothing caches the empty answer, so nothing has to be invalidated."""
    metta.run("(= (inv-d $x) (match &self (ev-d $x) found))")
    assert metta.derivation(S["inv-d"](1)) == []
    metta.run("(ev-d 1)")
    assert metta.derivation(S["inv-d"](1)), "the earlier empty answer went stale"


def test_derivation_effects_are_explicit_and_speculation_discards_engine_writes(
    metta,
):
    """Effectful premises run; speculation is the explicit write fence."""
    assert "effectful operations" in type(metta).derivation.__doc__
    assert "space.speculative()" in type(metta).derivation.__doc__

    with metta._new_space() as space:
        space.run("(= (derivation-remember $x) (add-atom &self (seen $x)))")
        assert space.derivation("(derivation-remember one)")
        assert space.derivation("(derivation-remember two)")
        assert S.seen(S.one) in space
        assert S.seen(S.two) in space

        with space.speculative():
            assert space.derivation("(derivation-remember discarded)")
        assert S.seen(S.discarded) not in space


@pytest.mark.parametrize("depth", [0, -1, True, 1.5])
def test_derivation_depth_must_be_a_positive_integer_or_none(metta, depth):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="positive integer or None"):
        metta.derivation(S.anything(), depth=depth)


def test_html_rendering(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("(fact-h here)\n(= (find-h) (match &self (fact-h $x) $x))")
    (proof,) = metta.derivation(S["find-h"]())
    assert "<pre>" in proof._repr_html_()
    assert isinstance(proof, Derivation)
    assert isinstance(proof.facts[0], Fact)


@pytest.mark.parametrize(
    ("tree", "message"),
    [
        (Expression(S.derivation), "malformed derivation"),
        (Expression(S.derivation, Expression(S.wrong, S.call, S.out)), "answer node"),
        (Expression(S.derivation, Expression(S.answer, S.call)), "answer node"),
        (
            Expression(
                S.derivation,
                Expression(S.answer, S.call, S.out),
                Expression(S.step, Expression(S.wrong, S.call, S.out), S.equation),
            ),
            "call node",
        ),
        (
            Expression(
                S.derivation,
                Expression(S.answer, S.call, S.out),
                Expression(S.fact, S.space),
            ),
            "fact node",
        ),
        (
            Expression(
                S.derivation,
                Expression(S.answer, S.call, S.out),
                Expression(S.builtin, S.one, S.two),
            ),
            "builtin node",
        ),
        (
            Expression(
                S.derivation,
                Expression(S.answer, S.call, S.out),
                Expression(S.truncated),
            ),
            "truncated node",
        ),
    ],
)
def test_malformed_derivation_nodes_are_named(tree, message):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match=message):
        Derivation.from_atom(tree)


def test_derivation_facts_deduplicate_in_first_seen_order():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    fact_a = Expression(S.fact, S["&self"], S.a(1))
    fact_b = Expression(S.fact, S["&self"], S.b(2))
    tree = Expression(
        S.derivation,
        Expression(S.answer, S.call, S.out),
        fact_a,
        fact_b,
        fact_a,
    )
    proof = Derivation.from_atom(tree)
    assert [fact.atom for fact in proof.facts] == [S.a(1), S.b(2)]


def test_a_recursive_proof_omits_the_engine_stack_charge(metta):
    """The engine's recursion counter is not a premise of the program.

    engine/spaces/foreign.pl's metta_instrument_recursive_clause/3 opens
    every recursive equation's clause with the stack charge that
    engine/metta/control.pl's metta_fuel_step_goal/3 builds. Walked as
    ordinary goals, it put `builtin
    system:b_getval('$metta_fuel_remaining',off)` and `builtin off==off`
    in front of the premises of every recursive step, so the tour's own
    ancestor proof read three lines of engine plumbing to five of
    program.
    """
    metta.run(
        "(par-c Tom Bob)\n(par-c Bob Ann)\n"
        "(= (anc-c $x $y) (match &self (par-c $x $y) $y))\n"
        "(= (anc-c $x $y) (let $m (match &self (par-c $x $m0) $m0) (anc-c $m $y)))"
    )
    (proof,) = metta.derivation(S["anc-c"](S.Tom, S.Ann))

    leaves = [
        node.text
        for node in _walk_nodes(proof.children)
        if isinstance(node, Builtin)
    ]
    assert not any("metta_fuel_remaining" in leaf for leaf in leaves)
    assert not any("off==off" in leaf for leaf in leaves)
    # the recursive step itself is still there, with both its premises
    assert len(proof.rules) == 2
    assert {f.atom for f in proof.facts} == {
        S["par-c"](S.Tom, S.Bob),
        S["par-c"](S.Bob, S.Ann),
    }


def test_a_recursive_proofs_equation_keeps_one_variable_per_source_variable(metta):
    """One $n in the source is one variable in every instance that fired.

    The tree crosses as wire terms, and the sharing decoder rebuilds one
    variable per NAME, so an equation whose occurrences crossed under two
    names comes back holding two. Its consumer then binds the call through
    one of them and the other stays free: (fact-r 3) read
    (= (fact-r $_17642) (if (> $_17642 0) (* $_17642 (fact-r (- $_2528 1))) 1))
    and substituting 3 left (- $_2528 1), which is not a term the engine can
    evaluate. metta_py_encode_tree/4 names the tree's variables once, from
    term_variables/2, so an occurrence cannot pick up a second name.
    """
    metta.run("(= (fact-r $n) (if (> $n 0) (* $n (fact-r (- $n 1))) 1))")
    (proof,) = metta.derivation(S["fact-r"](3))

    steps = [node for node in _walk_nodes(proof.children) if isinstance(node, Step)]
    assert len(steps) >= 4
    for step in steps:
        assert len(_variable_names(step.equation)) == 1


def _variable_names(atom):
    names = set()

    def visit(item):
        if isinstance(item, Variable):
            names.add(item.name)
        return item

    atom.map(visit)
    return names


def _walk_nodes(nodes):
    for node in nodes:
        yield node
        if hasattr(node, "children"):
            yield from _walk_nodes(node.children)


def _deep_derivation_tree(depth):
    call = Expression(S.call, S.recur, S.value)
    equation = Expression(S["="], S.recur, S.recur)
    node = Expression(S.fact, S["&self"], S.base)
    for _ in range(depth):
        node = Expression(S.step, call, equation, node)
    tree = Expression(
        S.derivation,
        Expression(S.answer, S.root, S.value),
        node,
    )
    return tree, equation


def test_deep_proof_consumers_treat_depth_as_data():
    """A depth-600 proof parses, projects, and renders completely."""
    depth = 600
    tree, equation = _deep_derivation_tree(depth)

    proof = Derivation.from_atom(tree)

    node = proof.children[0]
    observed_depth = 0
    while isinstance(node, Step):
        assert len(node.children) == 1
        observed_depth += 1
        node = node.children[0]
    assert observed_depth == depth
    assert node == Fact("&self", S.base)
    assert proof.facts == [Fact("&self", S.base)]
    assert proof.rules == [equation]
    assert proof.complete
    assert proof.truncations == []

    rendered = str(proof)
    assert len(rendered.splitlines()) == 2 * depth + 2
    assert proof.children[0].render(1) == "\n".join(rendered.splitlines()[1:])


def test_a_node_class_and_its_row_declare_the_same_fields():
    """One grammar, one class: the parser reads the row and nothing else.

    Each node class used to be built by counting positions in the atom by
    hand, so a field added to the grammar and not to the class, or the other
    way round, was a wrong answer rather than a refusal. The row IS the field
    list now, and `_check_rows()` holds the pair to each other at import --
    which is why every one of the five agrees here, and why planting a
    disagreement is refused with both sides named.
    """
    from dataclasses import fields as dataclass_fields

    from metta.derivation import _DERIVATION, _LEAVES, _STEP, _check_rows

    for row in (_DERIVATION, _STEP, *_LEAVES):
        declared = tuple(
            one.name for one in dataclass_fields(row.node) if one.name != "children"
        )
        assert declared == row.names, row.head

    # The row's own field list, one field longer than the class it projects
    # to. `names` is derived from `fields`, so the plant goes in the source.
    planted = _STEP._replace(fields=(*_STEP.fields, ("invented", str)))
    with (
        mock.patch("metta.derivation._STEP", planted),
        pytest.raises(
            ValueError, match=r"the step row declares .*invented.*Step carries"
        ),
    ):
        _check_rows()
