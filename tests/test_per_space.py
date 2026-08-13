"""Purpose: engine-backed tests for per-space equations: two spaces defining
one head, declarations visible in their own space, reduce resolving in the
space's module, and &self behaving exactly as before.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from petta import S, V, expr


def test_two_spaces_can_define_the_same_head(metta):
    a, b = metta.fresh_space(), metta.fresh_space()
    a.run("(= (psp-f) 1)")
    b.run("(= (psp-f) 2)")
    assert a.run("!(psp-f)") == [[1]]
    assert b.run("!(psp-f)") == [[2]]


def test_a_space_does_not_answer_from_anothers_equations(metta):
    a, b = metta.fresh_space(), metta.fresh_space()
    a.run("(= (psp-only-a) 42)")
    # In b the name is another space's function: the term stays inert data
    # rather than answering 42 or raising.
    r = b.run("!(psp-only-a)")
    assert r == [[expr(S["psp-only-a"])]]


def test_self_still_shares_with_named_spaces(metta):
    # &self is the shared space: a function defined there reaches every space,
    # which is what keeps every existing single-space program working.
    metta.run("(= (psp-shared) 7)")
    a = metta.fresh_space()
    assert a.run("!(psp-shared)") == [[7]]


def test_declaration_in_a_named_space_is_visible_there(metta):
    a = metta.fresh_space()
    a.run("(: psp-a PspA)")
    assert a.run("!(get-type psp-a)") == [[S.PspA]]
    # And invisible from a sibling space.
    b = metta.fresh_space()
    assert b.run("!(get-type psp-a)") == [[S["%Undefined%"]]]


def test_reduce_reaches_a_named_spaces_function(metta):
    a = metta.fresh_space()
    a.run("(= (psp-dbl $x) (* $x 2))")
    # map-atom goes through reduce/2, the runtime dispatcher; it has to find
    # the equation in this space's module.
    assert a.run("!(map-atom (1 2 3) psp-dbl)") == [[expr(2, 4, 6)]]


def test_equation_removal_is_per_space(metta):
    a, b = metta.fresh_space(), metta.fresh_space()
    a.run("(= (psp-r) 1)")
    b.run("(= (psp-r) 2)")
    a.remove("(= (psp-r) 1)")
    assert a.run("!(psp-r)") == [[expr(S["psp-r"])]]
    assert b.run("!(psp-r)") == [[2]]


def test_identical_equation_removal_keeps_the_twin(metta):
    """Two spaces holding the SAME equation, the shape every shared
    library import produces. The compiled-clause erasure is term-keyed,
    so without the module filter removing one twin erased the other
    space's clause and its bookkeeping record with it."""
    a, b = metta.fresh_space(), metta.fresh_space()
    a.run("(= (psp-twin $n) (+ $n 1))")
    b.run("(= (psp-twin $n) (+ $n 1))")
    assert a.remove("(= (psp-twin $n) (+ $n 1))") is True
    assert b.run("!(psp-twin 1)") == [[2]]
    # The survivor's own removal still finds its record: the term-wide
    # retractall would have stripped it and reported False here.
    assert b.remove("(= (psp-twin $n) (+ $n 1))") is True
    assert b.run("!(psp-twin 1)") == [[expr(S["psp-twin"], 1)]]
    a.drop()
    b.drop()


def test_python_ops_reach_every_space(metta):
    @metta.op
    def psp_op_everywhere(x: int) -> int:
        return x + 1

    a = metta.fresh_space()
    assert a.run("!(psp-op-everywhere 41)") == [[42]]


def test_eval_uses_the_spaces_own_equations(metta):
    a, b = metta.fresh_space(), metta.fresh_space()
    a.run("(= (psp-e) here)")
    b.run("(= (psp-e) there)")
    assert a.eval(expr(S["psp-e"])) == [S.here]
    assert b.eval(expr(S["psp-e"])) == [S.there]


def test_derivation_follows_the_spaces_module(metta):
    a = metta.fresh_space()
    a.run("(psp-par x y)\n(= (psp-anc $a $b) (match &self (psp-par $a $b) $b))")
    # The equation lives in a's module; the fact was stored in a as well, but
    # the equation's own match names &self, so the proof must still resolve
    # the clause through a's module to exist at all.
    proofs = a.derivation(S["psp-anc"](S.x, V.out))
    # The match inside looks at &self, which does not hold (psp-par x y); the
    # honest outcome is no proof, and no crash.
    assert proofs == []
