"""Purpose: prove the CeTTa bridge: PeTTa queries answered over atoms
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

import petta
from petta import S, V, testing

_MODULE_PATH = Path(__file__).resolve().parents[1] / "examples" / "integration" / "cetta_space.py"


def _cetta_binary():
    named = os.environ.get("PETTA_CETTA")
    if named and os.access(named, os.X_OK):
        return named
    return shutil.which("cetta")


def _cetta_space_module():
    examples_root = str(_MODULE_PATH.parents[1])
    sys.path.insert(0, examples_root)
    try:
        specification = _importlib_util.spec_from_file_location(
            "petta_example_cetta_space", _MODULE_PATH
        )
        module = _importlib_util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(examples_root)


@pytest.fixture
def cetta_space():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    binary = _cetta_binary()
    if binary is None:
        pytest.skip("PETTA_CETTA does not name a cetta binary and none is on PATH")
    module = _cetta_space_module()
    return module.CettaSpace(cetta=binary)


def test_metta_reaches_atoms_matched_by_cetta(cetta_space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = petta.MeTTa().new_space()
    try:
        m.register_space(cetta_space, "&cetta")
        m.run("!(add-atom &cetta (edge a b))")
        m.run("!(add-atom &cetta (edge a c))")
        m.run("!(add-atom &cetta (edge b c))")
        (group,) = m.run("!(collapse (match &cetta (edge a $x) $x))")
        assert sorted(str(atom) for atom in group[0]) == ["b", "c"]
    finally:
        m.unregister_space("&cetta")
        m.drop()


def test_removal_is_by_unification_and_takes_one_occurrence(cetta_space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    cetta_space.add(S.edge(S.a, S.b))
    cetta_space.add(S.edge(S.a, S.c))
    cetta_space.add(S.other(S.a))
    # Two atoms unify with the pattern and removal is multiset subtraction,
    # so the first removal takes the older one and leaves the other standing.
    assert cetta_space.remove(S.edge(S.a, V.x)) is True
    assert [str(atom) for atom in cetta_space.atoms()] == ["(edge a c)", "(other a)"]
    assert cetta_space.remove(S.edge(S.a, V.x)) is True
    assert [str(atom) for atom in cetta_space.atoms()] == ["(other a)"]
    assert cetta_space.remove(S.edge(S.a, V.x)) is False


def test_the_conformance_kit_certifies_the_cetta_provider(cetta_space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    report = testing.check_space_provider(
        cetta_space,
        atoms_to_store=[S.edge(S.a, S.b), S.edge(S.a, S.c), S.fact(S.f(S.k), S.k)],
    )
    assert any("over-approximation holds over" in line for line in report)


def test_the_kit_catches_cettas_rational_tree_divergence(cetta_space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # (fact $y $y) against a stored (fact (f $x) $x) is a rational-tree
    # match: PeTTa's matcher answers it (Prolog unification, no occurs
    # check) and CeTTa's refuses it. The kit's repeated-variable fold is
    # exactly the probe that finds such divergences, and this pin is the
    # measured record of one: a semantic difference between two MeTTa
    # implementations surfacing as a loud conformance refusal rather
    # than as silently missing answers in production.
    with pytest.raises(AssertionError, match="did not answer"):
        testing.check_space_provider(
            cetta_space,
            atoms_to_store=[S.fact(S.f(V.x), V.x)],
        )


def test_cetta_answers_bind_inside_petta_unification():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    binary = _cetta_binary()
    if binary is None:
        pytest.skip("PETTA_CETTA does not name a cetta binary and none is on PATH")
    from petta import expr
    from petta.atoms import Gnd

    m = petta.MeTTa().new_space()
    try:
        module = _cetta_space_module()
        matcher = module.CettaMatch(
            "(sol 2) (sol -2)",
            "!(match &self (sol $s) (sol $s))",
            m.parse,
            cetta=binary,
        )
        rows = m.eval(expr(S.unify, Gnd(matcher), expr(S.sol, V.x), V.x, S.none))
        assert sorted(str(atom) for atom in rows) == ["-2", "2"]
    finally:
        m.drop()
