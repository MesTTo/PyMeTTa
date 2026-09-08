"""Purpose: prove Python builds the same reified plans lib_strategy executes,
through the library's own rows rather than through a list kept in the package.

Assumes: ``m += lib.strategy`` imports ``lib/lib_strategy/lib_strategy.metta`` through the
normal library door.
Guarantees:
  - a library face is exactly the library's own declared heads, spelled Python's
    way, and every one of them is a Symbol rather than a host object [tested:
    test_a_library_face_is_its_own_rows; commit=WORKTREE]
  - a head the library does not declare refuses on the line that names it, and
    says where it IS reachable; `id` is that case, because lib_strategy's own
    source says the engine supplies it [tested:
    test_a_head_the_library_does_not_declare_refuses; commit=WORKTREE]
  - a Python-built plan remains queryable as stored data and executes through
    strategy-apply with the library's left-biased composition semantics
    [tested: test_python_strategy_terms_use_the_shipped_basis; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import pytest

import metta as metta_package
from metta import Expression, Grounded, S, Symbol, V, lib, library


def test_a_library_face_is_its_own_rows():
    """The face's names are the library's rows, and nothing else is."""
    face = library.face("lib_strategy")
    heads = {row.name for row in library.rows("lib_strategy")}

    assert {face[head] for head in heads} == {Symbol(head) for head in heads}
    assert all(isinstance(face[head], Symbol) for head in heads)
    assert not any(isinstance(face[head], Grounded) for head in heads)
    # Python's own casing of the head, keyword escape included, and the exact
    # bracket door for a head outside identifier grammar.
    assert face.try_ == S["try"]
    assert face.stratego_all == S["stratego-all"]
    assert face.stratego_one == S["stratego-one"]
    assert face.TP == S["TP"]
    assert face["◁"] == S["◁"]
    # The attribute roster IS the row roster mapped through Python's own
    # casing, one attribute per head and back again, so a head the library
    # gains appears here with no edit anywhere in the package. `◁` is not an
    # identifier, so it keeps only its bracket door.
    reached = {str(getattr(face, alias)) for alias in dir(face)}
    assert reached == heads - {"◁"}
    assert len(dir(face)) == len(reached)
    assert not hasattr(metta_package, "strategies")
    assert "strategies" not in metta_package.__all__


def test_a_head_the_library_does_not_declare_refuses():
    """`id` is the engine's, which the library's own source says out loud."""
    face = library.face("lib_strategy")
    assert "id" not in {row.name for row in library.rows("lib_strategy")}
    with pytest.raises(AttributeError, match=r"no lib_strategy head attribute named 'id'"):
        face.id  # noqa: B018  -- the attribute read IS the refusal under test
    # Python's `operator` words name ENGINE heads and are left out of a
    # library face, so `add` is not silently `+` here.
    with pytest.raises(AttributeError, match=r"no lib_strategy head attribute named 'add'"):
        face.add  # noqa: B018  -- the attribute read IS the refusal under test


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
    strategy = library.face("lib_strategy")
    with metta._new_space() as space:
        space += lib.strategy
        space.run(
            "(= (python-strategy-step python-a) python-b)\n"
            "(= (python-strategy-step python-b) python-c)\n"
            "(= (python-strategy-step $x) Empty)"
        )

        plan = strategy.seq(
            strategy.try_(S["python-strategy-step"]), metta_package.fn.id
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
