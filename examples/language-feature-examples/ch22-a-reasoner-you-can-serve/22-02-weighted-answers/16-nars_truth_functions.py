"""examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/16-nars_truth_functions.metta in Python: the arithmetic under NARS.

Every function here takes and answers `(stv <frequency> <confidence>)` atoms,
which are ordinary data, so `S.stv(1.0, 0.9)` is the whole of the notation and
each claim is one call through the function namespace.

Every name keeps its underscore, so every one comes through the exact
subscript door: the host-convention map would read `Truth_w2c` as
`Truth-w2c`, which the library does not ship.

Two of the family answer a BARE PAIR rather than an `(stv ...)`, which is
upstream PeTTa's own shape for them and matters to a caller: a bare pair does
not match an `(stv $f $c)` pattern.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib

#: The default truth value the three structural rules stand on.
DEFAULT = S.stv(1.0, 0.9)


def twin(m):
    """Each truth function once, on the values that pin its shape."""
    m += lib.nars
    f = m.fn

    # The two directions of the confidence-to-evidence map, c = w / (w + 1).
    assert f["Truth_w2c"](9.0) == [0.9]
    assert f["Truth_w2c"](0.0) == [0.0]
    assert f["Truth_w2c"](1.0) == [0.5]
    assert abs(f["Truth_c2w"](0.9)[0].value - 9.0) < 1e-9
    assert f["Truth_c2w"](0.0) == [0.0]
    assert abs(f["Truth_w2c"](f["Truth_c2w"](0.75)[0])[0].value - 0.75) < 1e-9

    # Deduction multiplies frequencies and multiplies the product into the
    # confidences: a chain is no stronger than its weakest link.
    assert f["Truth_Deduction"](DEFAULT, DEFAULT) == [S.stv(1.0, 0.81)]
    assert f["Truth_Deduction"](S.stv(0.5, 0.9), DEFAULT) == [S.stv(0.5, 0.405)]

    # Abduction keeps the second frequency and CONVERTS the evidence, so the
    # answer is a weaker confidence rather than a scaled one.
    weakened = S.stv(1.0, 0.44751381215469616)
    assert f["Truth_Abduction"](DEFAULT, DEFAULT) == [weakened]
    assert f["Truth_Induction"](DEFAULT, DEFAULT) == [weakened]

    # Induction is abduction with the operands swapped, which is its whole
    # definition.
    assert f["Truth_Induction"](S.stv(0.5, 0.9), S.stv(1.0, 0.8)) == f["Truth_Abduction"](
        S.stv(1.0, 0.8), S.stv(0.5, 0.9)
    )

    # Exemplification answers frequency 1.0 whatever went in.
    assert f["Truth_Exemplification"](DEFAULT, DEFAULT) == [weakened]
    assert f["Truth_Exemplification"](S.stv(0.2, 0.9), S.stv(0.2, 0.9)) == [
        S.stv(1.0, 0.03138318481208834)
    ]

    # Negation flips the frequency and keeps the confidence.
    assert f["Truth_Negation"](DEFAULT) == [S.stv(0.0, 0.9)]
    assert f["Truth_Negation"](S.stv(0.0, 0.9)) == [DEFAULT]

    # The three structural rules are the binary ones against the default.
    assert f["Truth_StructuralDeduction"](DEFAULT) == [S.stv(1.0, 0.81)]
    assert f["Truth_StructuralDeduction"](S.stv(0.5, 0.9)) == f["Truth_Deduction"](
        S.stv(0.5, 0.9), DEFAULT
    )
    assert f["Truth_StructuralDeductionNegated"](DEFAULT) == [S.stv(0.0, 0.81)]
    assert f["Truth_StructuralIntersection"](S.stv(0.8, 0.9)) == [S.stv(0.8, 0.81)]

    # Intersection multiplies both components: the and of two independent
    # beliefs.
    assert f["Truth_Intersection"](S.stv(0.8, 0.9), S.stv(0.5, 0.9)) == [S.stv(0.4, 0.81)]

    # `Truth_or` is the probabilistic or on plain NUMBERS, the one member of
    # the family that takes and answers one.
    assert f["Truth_or"](0.5, 0.5) == [0.75]
    assert f["Truth_or"](0.0, 0.0) == [0.0]
    assert f["Truth_or"](1.0, 0.0) == [1.0]

    # The symmetric relations, both built on that or.
    assert f["Truth_Comparison"](DEFAULT, DEFAULT) == [weakened]
    assert f["Truth_Comparison"](S.stv(0.0, 0.9), S.stv(0.0, 0.9)) == [S.stv(0.0, 0.0)]
    assert f["Truth_Resemblance"](DEFAULT, S.stv(0.5, 0.9)) == [S.stv(0.5, 0.81)]
    assert f["Truth_Analogy"](DEFAULT, S.stv(0.5, 0.9)) == [S.stv(0.5, 0.405)]

    # Difference is the and-not.
    assert f["Truth_Difference"](DEFAULT, S.stv(0.25, 0.9)) == [S.stv(0.75, 0.81)]

    # The decomposition rules, each named for the polarity of its three
    # positions.
    assert f["Truth_DecomposePNN"](DEFAULT, S.stv(0.0, 0.9)) == [S.stv(0.0, 0.81)]
    assert f["Truth_DecomposeNPP"](S.stv(0.0, 0.9), DEFAULT) == [S.stv(1.0, 0.81)]
    assert f["Truth_DecomposePNP"](DEFAULT, S.stv(0.0, 0.9)) == [S.stv(1.0, 0.81)]
    assert f["Truth_DecomposePPP"](DEFAULT, DEFAULT) == f["Truth_DecomposeNPP"](
        f["Truth_Negation"](DEFAULT)[0], DEFAULT
    )

    # TWO of the family answer a bare pair rather than an (stv ...).
    assert f["Truth_Union"](S.stv(0.5, 0.9), S.stv(0.5, 0.9)) == [(0.75, 0.81)]
    assert f["Truth_DecomposeNNN"](S.stv(0.0, 0.9), S.stv(0.0, 0.9)) == [(0.0, 0.81)]

    # Eternalize treats an event's confidence as evidence, so it weakens.
    assert f["Truth_Eternalize"](S.stv(0.8, 0.9)) == [S.stv(0.8, 0.4736842105263158)]

    # Revision ADDS evidence: the only rule here that can RAISE a confidence.
    assert f["Truth_Revision"](DEFAULT, S.stv(0.0, 0.9)) == [
        S.stv(0.5, 0.9473684210526316)
    ]
    assert f["Truth_Revision"](S.stv(1.0, 0.5), S.stv(1.0, 0.5)) == [
        S.stv(1.0, 0.6666666666666666)
    ]
    # And the ceiling in it is a NARS law: no amount of evidence makes a
    # belief certain.
    assert f["Truth_Revision"](S.stv(1.0, 0.99), S.stv(1.0, 0.99)) == [S.stv(1.0, 0.99)]

    # Expectation is the decision-making projection onto [0,1].
    assert f["Truth_Expectation"](DEFAULT) == [0.95]
    assert f["Truth_Expectation"](S.stv(0.0, 0.9)) == [0.04999999999999999]
    assert f["Truth_Expectation"](S.stv(0.5, 0.9)) == [0.5]
    assert f["Truth_Expectation"](S.stv(1.0, 0.0)) == [0.5]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 118441 inferences, 0.9613x the example's 123208; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 118441
