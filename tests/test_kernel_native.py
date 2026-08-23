"""Purpose: differentially pin engine-native Python equality and truthiness.

Assumes:
  - ``petta_py_dispatch_det_host/3`` remains the current Python oracle for
    opaque values and for differential comparison.
Guarantees:
  - every wire-crossable scalar produces the same answer through the native
    dispatch and the retained host route [tested:
    test_wire_scalars_match_the_python_host_oracle; commit=50e914ec00b986964784af05521b224f3456655c]
  - Python's named edge cases and expression-container truth rules retain
    their exact answers [tested: test_python_edge_cases_and_containers;
    commit=50e914ec00b986964784af05521b224f3456655c]
Fails when:
  - a new wire value class is routed natively without implementing Python's
    comparison and truth protocols for it.
"""

from __future__ import annotations

import math

from hypothesis import given
from hypothesis import strategies as st

from petta import Expression, S, Symbol, ground

SCALARS = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**63), max_value=2**63 - 1),
    st.floats(width=64, allow_infinity=True, allow_nan=True),
    st.text(),
)


def _wire(value):
    return ground(value).to_wire()


def _routes(space, operation, *values):
    wires = [_wire(value) for value in values]
    if len(wires) == 2:
        goal = (
            "petta_py_decode_shared(WA, A, _), "
            "petta_py_decode_shared(WB, B, _), "
            "petta_py_dispatch_det_host(Op, [A, B], Host), "
            "petta_py_dispatch_det(Op, [A, B], Native)"
        )
        row = space.runtime.once(goal, WA=wires[0], WB=wires[1], Op=operation)
    else:
        goal = (
            "petta_py_decode_shared(W, A, _), "
            "petta_py_dispatch_det_host(Op, [A], Host), "
            "petta_py_dispatch_det(Op, [A], Native)"
        )
        row = space.runtime.once(goal, W=wires[0], Op=operation)
    return row["Host"], row["Native"]


@given(left=SCALARS, right=SCALARS)
def test_wire_scalars_match_the_python_host_oracle(metta, left, right):
    """Native equality is a differential implementation, not a new policy."""
    host, native = _routes(metta, "py-eq", left, right)
    assert native == host

    host, native = _routes(metta, "py-truthy", left)
    assert native == host


def test_python_edge_cases_and_containers(metta):
    """Pin cases where Python differs from term identity or Prolog truth."""
    equality_cases = [
        (1, 1, True),
        (1, 1.0, True),
        (1.5, 1.5, True),
        (True, 1, True),
        ("same", "same", True),
        (None, None, True),
        (-0.0, 0.0, True),
        (math.nan, math.nan, False),
        (1, "1", False),
    ]
    for left, right, expected in equality_cases:
        host, native = _routes(metta, "py-eq", left, right)
        assert host == native == ("true" if expected else "false")

    # A Python string is not a MeTTa symbol merely carrying the same text.
    row = metta.runtime.once(
        "petta_py_decode_shared(WA, A, _), "
        "petta_py_decode_shared(WB, B, _), "
        "petta_py_dispatch_det_host('py-eq', [A, B], Host), "
        "petta_py_dispatch_det('py-eq', [A, B], Native)",
        WA=ground("same").to_wire(),
        WB=Symbol("same").to_wire(),
    )
    assert row["Host"] == row["Native"] == "false"

    for value, expected in [
        (0, False),
        (0.0, False),
        (3, True),
        ("", False),
        ("x", True),
        (None, False),
        (False, False),
        (True, True),
    ]:
        host, native = _routes(metta, "py-truthy", value)
        assert host == native == ("true" if expected else "false")

    for atom, expected in [(Expression(), False), (Expression(S.x), True)]:
        row = metta.runtime.once(
            "petta_py_decode_shared(W, A, _), "
            "petta_py_dispatch_det_host('py-truthy', [A], Host), "
            "petta_py_dispatch_det('py-truthy', [A], Native)",
            W=atom.to_wire(),
        )
        assert row["Host"] == row["Native"] == ("true" if expected else "false")
