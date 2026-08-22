"""Purpose: the in-language measure library, lib/lib_measure.metta, driven
through the public surface only. The library is pure MeTTa over explicit
(weight value) pair data; nothing in the Python library wraps it, so these
tests import it the way any program does.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest


@pytest.fixture
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta._new_space()
    space.run("!(import! (context-space) (library lib_measure))")
    return space


def test_ws_total_and_normalize(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert m.run("!(ws-total ((2.0 x) (6.0 y)))") == [[8.0]]
    (rows,) = m.run("!(ws-normalize ((2.0 x) (6.0 y)))")
    assert rows[0].children[0].children[0].value == 0.25
    assert rows[0].children[1].children[0].value == 0.75


def test_ws_best_is_argmax(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (rows,) = m.run("!(ws-best ((0.2 low) (0.7 high) (0.1 mid)))")
    assert str(rows[0]) == "high"


def test_ws_normalize_refuses_zero_mass(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (rows,) = m.run("!(ws-normalize ((0.0 x)))")
    assert "nonzero total mass" in str(rows[0])


def test_ws_softmax_refuses_zero_temperature(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (rows,) = m.run("!(ws-softmax ((1.0 x)) 0.0)")
    assert "nonzero temperature" in str(rows[0])
