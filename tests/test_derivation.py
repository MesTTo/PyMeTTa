"""Purpose: engine-backed tests for proof trees, validation, and rendering.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import pytest

from petta import (
    Builtin,
    Derivation,
    Fact,
    InferenceLimitError,
    S,
    Truncated,
    V,
    expr,
)


def test_multi_step_proof_names_equations_and_facts(metta):
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


def test_every_proof_enumerates(metta):
    metta.run(
        "(par-e Tom Bob)\n(par-e Bob Ann)\n"
        "(= (anc-e $x $y) (match &self (par-e $x $y) $y))\n"
        "(= (anc-e $x $y) (let $m (match &self (par-e $x $m0) $m0) (anc-e $m $y)))"
    )
    proofs = metta.derivation(S["anc-e"](S.Tom, V.who))
    answers = {p.answer for p in proofs}
    assert answers == {S.Bob, S.Ann}


def test_depth_bound_marks_runaway_search_as_partial(metta):
    metta.run("(= (loop-d $x) (loop-d $x))")
    (proof,) = metta.derivation(S["loop-d"](1), depth=5)
    assert not proof.complete
    assert proof.truncations
    assert isinstance(proof.truncations[0], Truncated)


def test_conditional_derivation_exposes_the_recursive_branch(metta):
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


def test_disjunction_derivation_enumerates_each_taken_branch(metta):
    metta.run("(= (pick-tree) (superpose (1 2 3)))")
    proofs = metta.derivation(S["pick-tree"]())
    assert {proof.answer for proof in proofs} == {1, 2, 3}
    assert all(proof.complete for proof in proofs)


def test_derivation_honours_a_cut(metta):
    # A cut prunes the equations after it. Recorded as a leaf and called,
    # it pruned nothing, so the proof list carried a conclusion the program
    # cannot reach: run answered first, derivation proved first and second.
    metta.run("(= (cut-tree $x) (let $c (cut) first))")
    metta.run("(= (cut-tree $x) second)")
    assert metta.run("!(cut-tree 1)") == [[S.first]]
    assert [proof.answer for proof in metta.derivation(S["cut-tree"](1))] == [S.first]


def test_derivation_still_enumerates_equations_without_a_cut(metta):
    metta.run("(= (open-tree $x) one)")
    metta.run("(= (open-tree $x) two)")
    assert [proof.answer for proof in metta.derivation(S["open-tree"](1))] == [S.one, S.two]


def test_a_cut_inside_once_stays_inside_it(metta):
    # once/1 is a cut barrier: the cut may not prune the equations beside
    # the one it sits in.
    metta.run("(= (barrier-tree $x) (let $c (once (cut)) first))")
    metta.run("(= (barrier-tree $x) second)")
    assert [proof.answer for proof in metta.derivation(S["barrier-tree"](1))] == [
        S.first,
        S.second,
    ]


def test_once_and_findall_derivations_expose_their_inner_goals(metta):
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


def test_depth_exhaustion_returns_a_partial_proof(metta):
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


def test_unbounded_derivation_obeys_resource_guards(metta):
    metta.run("(= (loop-guard-d $x) (loop-guard-d $x))")
    with pytest.raises(InferenceLimitError):
        metta.derivation(S["loop-guard-d"](1), inferences=2_000)


@pytest.mark.parametrize("depth", [0, -1, True, 1.5])
def test_derivation_depth_must_be_a_positive_integer_or_none(metta, depth):
    with pytest.raises(ValueError, match="positive integer or None"):
        metta.derivation(S.anything(), depth=depth)


def test_html_rendering(metta):
    metta.run("(fact-h here)\n(= (find-h) (match &self (fact-h $x) $x))")
    (proof,) = metta.derivation(S["find-h"]())
    assert "<pre>" in proof._repr_html_()
    assert isinstance(proof, Derivation)
    assert isinstance(proof.facts[0], Fact)


@pytest.mark.parametrize(
    ("tree", "message"),
    [
        (expr(S.derivation), "malformed derivation"),
        (expr(S.derivation, expr(S.wrong, S.call, S.out)), "answer node"),
        (expr(S.derivation, expr(S.answer, S.call)), "answer node"),
        (
            expr(
                S.derivation,
                expr(S.answer, S.call, S.out),
                expr(S.step, expr(S.wrong, S.call, S.out), S.equation),
            ),
            "call node",
        ),
        (
            expr(
                S.derivation,
                expr(S.answer, S.call, S.out),
                expr(S.fact, S.space),
            ),
            "fact node",
        ),
        (
            expr(
                S.derivation,
                expr(S.answer, S.call, S.out),
                expr(S.builtin, S.one, S.two),
            ),
            "builtin node",
        ),
        (
            expr(
                S.derivation,
                expr(S.answer, S.call, S.out),
                expr(S.truncated),
            ),
            "truncated node",
        ),
    ],
)
def test_malformed_derivation_nodes_are_named(tree, message):
    with pytest.raises(ValueError, match=message):
        Derivation.from_atom(tree)


def test_derivation_facts_deduplicate_in_first_seen_order():
    fact_a = expr(S.fact, S["&self"], S.a(1))
    fact_b = expr(S.fact, S["&self"], S.b(2))
    tree = expr(
        S.derivation,
        expr(S.answer, S.call, S.out),
        fact_a,
        fact_b,
        fact_a,
    )
    proof = Derivation.from_atom(tree)
    assert [fact.atom for fact in proof.facts] == [S.a(1), S.b(2)]


def _walk_nodes(nodes):
    for node in nodes:
        yield node
        if hasattr(node, "children"):
            yield from _walk_nodes(node.children)
