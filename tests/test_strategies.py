"""Purpose: prove Python builds the same reified plans lib_strategy executes.

Assumes: ``m += lib.strategy`` imports ``lib/lib_strategy.metta`` through the
normal library door.
Guarantees:
  - the satellite exports fifteen Symbols and no grounded callback
    [tested: test_strategy_exports_are_reified_atoms; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa]
  - a Python-built plan remains queryable as stored data and executes through
    strategy-apply with the library's left-biased composition semantics
    [tested: test_python_strategy_terms_use_the_shipped_basis; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import importlib

import metta as metta_package
from metta import Expression, Grounded, S, Symbol, V, lib


def test_strategy_exports_are_reified_atoms():
    """Importing the satellite exposes data, never executable host objects."""
    strategies = importlib.import_module("metta.strategies")
    exported = {name: getattr(strategies, name) for name in strategies.__all__}

    assert len(exported) == 15
    assert all(isinstance(value, Symbol) for value in exported.values())
    assert not any(isinstance(value, Grounded) for value in exported.values())
    assert strategies.try_ == S["try"]
    assert strategies.stratego_all == S["stratego-all"]
    assert strategies.stratego_one == S["stratego-one"]
    assert metta_package.strategies is strategies
    assert "try_" not in metta_package.__all__
    assert not hasattr(metta_package, "try_")


def test_python_strategy_terms_use_the_shipped_basis(metta):
    """One stored Python plan is queried whole, then lowered and evaluated.

    The library import goes into a scoped space, not the shared fixture:
    lib_strategy declares three-argument arrows for `choice`, `seq` and kin,
    and an import into the session's ``&self`` makes those declarations reach
    every space in the process for the rest of the worker's life. That is how
    this file broke test_per_ask_evaluation's zero-argument `choice` in
    whichever worker ran both [measured 2026-08-26: the bisected pairing
    answers (Error (choice) IncorrectNumberOfArguments)].
    """
    strategies = metta_package.strategies
    with metta._new_space() as space:
        space += lib.strategy
        space.run(
            "(= (python-strategy-step python-a) python-b)\n"
            "(= (python-strategy-step python-b) python-c)\n"
            "(= (python-strategy-step $x) Empty)"
        )

        plan = strategies.seq(
            strategies.try_(S["python-strategy-step"]), strategies.id
        )
        assert isinstance(plan, Expression)
        assert not any(isinstance(atom, Grounded) for atom in plan)

        space.add(S["python-strategy-plan"](S.fast, plan))
        stored = (
            space.match(S["python-strategy-plan"](S.fast, V.strategy)).one().strategy
        )
        assert stored == plan

        applied = S["strategy-apply"](stored, S["python-a"])
        assert space.eval(applied) == [S["python-b"]]
