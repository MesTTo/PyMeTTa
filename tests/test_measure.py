"""Purpose: validate Python weighted-relation boundaries and explicit
lib_measure refusals for undefined normalization and softmax inputs.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest
from petta import Gnd, S, expr, measure


def test_pairs_requires_an_expression_of_exact_pairs():
    with pytest.raises(ValueError, match="expression of pairs"):
        measure.pairs(S.not_a_superposition)
    with pytest.raises(ValueError, match="pair 0.*exactly two"):
        measure.pairs(expr(expr(0.5, S.value, S.extra)))
    with pytest.raises(ValueError, match="nonnumeric weight"):
        measure.pairs(expr(expr(S.heavy, S.value)))


def test_weighted_relation_decodes_only_grounded_primitive_inputs(metta):
    seen = []

    def weights(value):
        seen.append(value)
        return [1.0]

    measure.weighted_relation(metta, "decoded-weight", weights, [S.answer])
    metta.run('!(decoded-weight "text")')
    metta.run("!(decoded-weight symbol)")
    metta.run("!(decoded-weight (structured value))")
    assert seen[0] == "text" and isinstance(seen[0], str)
    assert seen[1] == S.symbol
    assert seen[2] == S.structured(S.value)


def test_weighted_relation_raw_atoms_is_explicit(metta):
    seen = []
    measure.weighted_relation(
        metta,
        "raw-weight",
        lambda value: seen.append(value) or [1.0],
        [S.answer],
        raw_atoms=True,
    )
    metta.run('!(raw-weight "text")')
    assert isinstance(seen[0], Gnd)
    assert seen[0].value == "text"


def test_measure_guards_undefined_normalization_and_softmax(metta):
    with metta.fresh_space() as space:
        measure.install(space)
        assert space.run("!(ws-normalize ())") == [[expr()]]
        zero = space.run("!(ws-normalize ((0.0 a) (0.0 b)))")[0][0]
        cancel = space.run("!(ws-normalize ((1.0 a) (-1.0 b)))")[0][0]
        cold = space.run("!(ws-softmax ((1.0 a)) 0.0)")[0][0]
        assert str(zero).endswith('"ws-normalize requires nonzero total mass")')
        assert str(cancel).endswith('"ws-normalize requires nonzero total mass")')
        assert str(cold).endswith('"ws-softmax requires a nonzero temperature")')
