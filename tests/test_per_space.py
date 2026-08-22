"""Purpose: engine-backed tests for per-space equations: two spaces defining
one head, declarations visible in their own space, reduce resolving in the
space's module, and &self behaving exactly as before.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from petta import Expression, S, V


def test_two_spaces_can_define_the_same_head(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a, b = metta.new_space(), metta.new_space()
    a.run("(= (psp-f) 1)")
    b.run("(= (psp-f) 2)")
    assert a.run("!(psp-f)") == [[1]]
    assert b.run("!(psp-f)") == [[2]]


def test_a_space_does_not_answer_from_anothers_equations(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a, b = metta.new_space(), metta.new_space()
    a.run("(= (psp-only-a) 42)")
    # In b the name is another space's function: the term stays inert data
    # rather than answering 42 or raising.
    r = b.run("!(psp-only-a)")
    assert r == [[Expression((S["psp-only-a"],))]]


def test_self_still_shares_with_named_spaces(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # &self is the shared space: a function defined there reaches every space,
    # which is what keeps every existing single-space program working.
    metta.run("(= (psp-shared) 7)")
    a = metta.new_space()
    assert a.run("!(psp-shared)") == [[7]]


def test_declaration_in_a_named_space_is_visible_there(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a = metta.new_space()
    a.run("(: psp-a PspA)")
    assert a.run("!(get-type psp-a)") == [[S.PspA]]
    # And invisible from a sibling space.
    b = metta.new_space()
    assert b.run("!(get-type psp-a)") == [[S["%Undefined%"]]]


def test_reduce_reaches_a_named_spaces_function(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a = metta.new_space()
    a.run("(= (psp-dbl $x) (* $x 2))")
    # map-atom goes through reduce/2, the runtime dispatcher; it has to find
    # the equation in this space's module.
    assert a.run("!(map-atom (1 2 3) psp-dbl)") == [[Expression((2, 4, 6))]]


def test_equation_removal_is_per_space(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a, b = metta.new_space(), metta.new_space()
    a.run("(= (psp-r) 1)")
    b.run("(= (psp-r) 2)")
    a.remove("(= (psp-r) 1)")
    assert a.run("!(psp-r)") == [[Expression((S["psp-r"],))]]
    assert b.run("!(psp-r)") == [[2]]


def test_identical_equation_removal_keeps_the_twin(metta):
    """Two spaces holding the SAME equation, the shape every shared
    library import produces. The compiled-clause erasure is term-keyed,
    so without the module filter removing one twin erased the other
    space's clause and its bookkeeping record with it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    a, b = metta.new_space(), metta.new_space()
    a.run("(= (psp-twin $n) (+ $n 1))")
    b.run("(= (psp-twin $n) (+ $n 1))")
    assert a.remove("(= (psp-twin $n) (+ $n 1))") is True
    assert b.run("!(psp-twin 1)") == [[2]]
    # The survivor's own removal still finds its record: the term-wide
    # retractall would have stripped it and reported False here.
    assert b.remove("(= (psp-twin $n) (+ $n 1))") is True
    assert b.run("!(psp-twin 1)") == [[Expression((S["psp-twin"], 1))]]
    a.drop()
    b.drop()


def test_python_ops_reach_every_space(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @metta.register_op(name="psp-op-everywhere")
    def psp_op_everywhere(x: int) -> int:
        return x + 1

    a = metta.new_space()
    assert a.run("!(psp-op-everywhere 41)") == [[42]]


def test_eval_uses_the_spaces_own_equations(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a, b = metta.new_space(), metta.new_space()
    a.run("(= (psp-e) here)")
    b.run("(= (psp-e) there)")
    assert a.eval(Expression((S["psp-e"],))) == [S.here]
    assert b.eval(Expression((S["psp-e"],))) == [S.there]


def test_derivation_follows_the_spaces_module(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a = metta.new_space()
    a.run("(psp-par x y)\n(= (psp-anc $a $b) (match &self (psp-par $a $b) $b))")
    # &self in loaded source is the reserved token for the hosting space,
    # so the equation's match reads a's own atoms: the fact is there, the
    # proof exists, and the derivation shows the substituted space name.
    # Before the token landed this asserted the divergence instead (the
    # match consulted the engine-default &self and found nothing).
    (proof,) = a.derivation(S["psp-anc"](S.x, V.out))
    assert proof.answer == S.y
    assert a.space_name in str(proof)


def test_a_lambda_reaches_the_space_local_function_it_names(metta):
    """A lambda body compiles to a clause of its own, and that clause has to
    land in the space where the lambda was written. Asserted into `user` it
    could not see the space at all, because a module inherits from `user` and
    not the reverse, so every lambda form raised Unknown procedure on a
    space-local function while the same call written directly answered.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    a = metta.new_space()
    a.run("(= (psp-lam $x) (* $x 2))")
    assert a.run("!(psp-lam 21)") == [[42]]
    assert a.run("!(map-atom (1 2 3) $x (psp-lam $x))") == [[Expression((2, 4, 6))]]
    assert a.run("!(filter-atom (1 2 3) $x (> (psp-lam $x) 2))") == [[Expression((2, 3))]]
    assert a.run("!(foldl-atom (1 2 3) 0 $a $x (+ $a (psp-lam $x)))") == [[12]]
    assert a.run("!((|-> ($y) (psp-lam $y)) 21)") == [[42]]


def test_two_spaces_do_not_share_a_lambda_of_the_same_shape(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    a, b = metta.new_space(), metta.new_space()
    a.run("(= (psp-lam-shape $x) (* $x 2))")
    b.run("(= (psp-lam-shape $x) (* $x 10))")
    source = "!(map-atom (1 2 3) $x (psp-lam-shape $x))"
    assert a.run(source) == [[Expression((2, 4, 6))]]
    assert b.run(source) == [[Expression((10, 20, 30))]]


def test_equations_are_per_space_with_a_self_fallback_and_local_shadowing(metta):
    """The three-part rule the MeTTa class docstring states as a table.

    It used to say equations were "process-wide, which is the engine's own
    rule", while new_space() two hundred lines below said the opposite, that
    what it isolates is atoms AND equations. The second one is right, and it
    is still not the whole rule: there is a dynamic fallback to &self and
    local shadowing on top of the isolation.
    """
    s1 = metta.new_space()
    s2 = metta.new_space()
    try:
        # Defined in a named space: private to it, unreduced elsewhere.
        s1.run("(= (sc-only-s1) 1)")
        unreduced = Expression((S["sc-only-s1"],))
        assert s1.run("!(sc-only-s1)")[-1] == [1]
        assert metta.run("!(sc-only-s1)")[-1] == [unreduced]
        assert s2.run("!(sc-only-s1)")[-1] == [unreduced]

        # Defined in &self: reachable from every space, which is the fallback.
        metta.run("(= (sc-in-self) 9)")
        for space in (metta, s1, s2):
            assert space.run("!(sc-in-self)")[-1] == [9]

        # Defined in both: the local one wins where it exists.
        metta.run("(= (sc-both) fromself)")
        s1.run("(= (sc-both) froms1)")
        assert metta.run("!(sc-both)")[-1] == [S.fromself]
        assert s1.run("!(sc-both)")[-1] == [S.froms1]
        assert s2.run("!(sc-both)")[-1] == [S.fromself]
    finally:
        s1.drop()
        s2.drop()
