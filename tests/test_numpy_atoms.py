"""Purpose: verify optional NumPy scalar values use native engine numbers.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import Gnd
from petta import testing as pt
from petta.atoms import from_wire

pytest.importorskip("numpy")
hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given


@given(pt.numpy_scalars())
def test_numpy_scalar_strategy_round_trips_through_the_engine(metta, scalar):
    atom = Gnd(scalar)
    row = metta.runtime.once(
        "petta_py_decode_shared(W, _T, _), petta_py_encode(_T, W2)",
        W=atom.to_wire(),
    )
    assert from_wire(row["W2"]) == atom
