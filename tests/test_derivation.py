"""Purpose: engine-backed tests for proof trees and their rendering.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from petta import Derivation, Fact, S, V


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


def test_depth_bound_stops_runaway_search(metta):
    metta.run("(= (loop-d $x) (loop-d $x))")
    assert metta.derivation(S["loop-d"](1), depth=5) == []


def test_html_rendering(metta):
    metta.run("(fact-h here)\n(= (find-h) (match &self (fact-h $x) $x))")
    (proof,) = metta.derivation(S["find-h"]())
    assert "<pre>" in proof._repr_html_()
    assert isinstance(proof, Derivation)
    assert isinstance(proof.facts[0], Fact)
