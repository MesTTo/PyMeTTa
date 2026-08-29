"""Purpose: prove the CeTTa bridge: this engine's queries answered over atoms
whose matching runs in the sibling C MeTTa runtime, certified by the
conformance kit and driven from MeTTa source.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import shutil
import sys
from importlib import util as _importlib_util
from pathlib import Path

import pytest

import metta
from metta import S, V, testing

_MODULE_PATH = Path(__file__).resolve().parents[2] / "examples" / "integration" / "cmetta_space.py"


def _cmetta_binary():
    named = os.environ.get("METTA_CMETTA")
    if named and os.access(named, os.X_OK):
        return named
    return shutil.which("cmetta")


def _cmetta_space_module():
    examples_root = str(_MODULE_PATH.parents[1])
    sys.path.insert(0, examples_root)
    try:
        specification = _importlib_util.spec_from_file_location(
            "metta_example_cmetta_space", _MODULE_PATH
        )
        module = _importlib_util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(examples_root)


@pytest.fixture
def cmetta_space():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    binary = _cmetta_binary()
    if binary is None:
        pytest.skip("METTA_CMETTA does not name a cmetta binary and none is on PATH")
    module = _cmetta_space_module()
    return module.CMettaSpace(cmetta=binary)


def test_metta_reaches_atoms_matched_by_cmetta(cmetta_space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = metta.MeTTa().space()
    try:
        m._register_space(cmetta_space, "&cmetta")
        m.run("!(add-atom &cmetta (edge a b))")
        m.run("!(add-atom &cmetta (edge a c))")
        m.run("!(add-atom &cmetta (edge b c))")
        (group,) = m.run("!(collapse (match &cmetta (edge a $x) $x))")
        assert sorted(str(atom) for atom in group[0]) == ["b", "c"]
    finally:
        m._unregister_space("&cmetta")
        m.drop()


def test_removal_is_by_unification_and_takes_one_occurrence(cmetta_space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    cmetta_space.add(S.edge(S.a, S.b))
    cmetta_space.add(S.edge(S.a, S.c))
    cmetta_space.add(S.other(S.a))
    # Two atoms unify with the pattern and removal is multiset subtraction,
    # so the first removal takes the older one and leaves the other standing.
    assert cmetta_space.remove(S.edge(S.a, V.x)) is True
    assert [str(atom) for atom in cmetta_space.atoms()] == ["(edge a c)", "(other a)"]
    assert cmetta_space.remove(S.edge(S.a, V.x)) is True
    assert [str(atom) for atom in cmetta_space.atoms()] == ["(other a)"]
    assert cmetta_space.remove(S.edge(S.a, V.x)) is False


def test_the_conformance_kit_certifies_the_cmetta_provider(cmetta_space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    report = testing.check_space_provider(
        cmetta_space,
        atoms_to_store=[S.edge(S.a, S.b), S.edge(S.a, S.c), S.fact(S.f(S.k), S.k)],
    )
    assert any("over-approximation holds over" in line for line in report)


def test_the_kit_catches_cmettas_rational_tree_divergence(cmetta_space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # (fact $y $y) against a stored (fact (f $x) $x) is a rational-tree
    # match: MeTTa's matcher answers it (Prolog unification, no occurs
    # check) and CeTTa's refuses it. The kit's repeated-variable fold is
    # exactly the probe that finds such divergences, and this pin is the
    # measured record of one: a semantic difference between two MeTTa
    # implementations surfacing as a loud conformance refusal rather
    # than as silently missing answers in production.
    with pytest.raises(AssertionError, match="did not answer"):
        testing.check_space_provider(
            cmetta_space,
            atoms_to_store=[S.fact(S.f(V.x), V.x)],
        )


def test_cmetta_answers_bind_inside_metta_unification():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    binary = _cmetta_binary()
    if binary is None:
        pytest.skip("METTA_CMETTA does not name a cmetta binary and none is on PATH")
    from metta import Expression
    from metta.atoms import Grounded

    m = metta.MeTTa().space()
    try:
        module = _cmetta_space_module()
        matcher = module.CMettaMatch(
            "(sol 2) (sol -2)",
            "!(match &self (sol $s) (sol $s))",
            m.parse,
            cmetta=binary,
        )
        rows = m.eval(Expression(S.unify, Grounded(matcher), Expression(S.sol, V.x), V.x, S.none))
        assert sorted(str(atom) for atom in rows) == ["-2", "2"]
    finally:
        m.drop()
