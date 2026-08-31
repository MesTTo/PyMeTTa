"""Purpose: pin compiled assert and space-removal statement spellings.
Guarantees:
  - assert continues on truth and otherwise answers the Error algebra with a
    lazy explicit reason [tested: test_compiled_assert_lowers_to_the_error_algebra;
    commit=6a695598aaf5951530cb8efe9afe46977afe541c]
  - a Space-typed ``-=`` removes one occurrence while ``del space[pattern]``
    removes every match from the passed target and both keep absence loud
    [tested:
    test_compiled_removal_statements_preserve_one_many_missing_and_target_scope;
    commit=6a695598aaf5951530cb8efe9afe46977afe541c]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from metta import Expression, S, Space, V
from metta.vocabularies import EffectClass


def _guarded(value):
    assert value > 0
    return S.kept(value)


def _guarded_message(value):
    assert value > 0, f"positive value required, got {value}"
    return S.kept(value)


def _branched_assert(ok):
    assert ok
    yield S.left
    yield S.right


def _remove_one(target: Space, atom):
    target -= atom
    return S.done


def _remove_many(target: Space, pattern):
    del target[pattern]
    return S.done


def test_compiled_assert_lowers_to_the_error_algebra(metta):
    """True, false, message, and nondeterministic continuations stay distinct."""
    program = metta._new_space()
    guarded = program.define(_guarded)
    messaged = program.define(_guarded_message)
    branched = program.define(_branched_assert)

    assert guarded(2) == [S.kept(2)]
    assert guarded(-1) == [S.Error(S[">"](-1, 0), S.AssertionError)]
    assert messaged(-2) == [
        S.Error(S[">"](-2, 0), "positive value required, got -2")
    ]
    assert branched(True) == [S.left, S.right]  # noqa: FBT003  -- boolean is term data
    assert branched(False) == [  # noqa: FBT003  -- boolean is term data
        S.Error(False, S.AssertionError)  # noqa: FBT003  -- boolean is term data
    ]


def test_compiled_removal_statements_preserve_one_many_missing_and_target_scope(metta):
    """One, all, absent, and nonambient target cases use removal forms."""
    program = metta._new_space()
    target = metta._new_space()
    remove_one = program.define(_remove_one)
    remove_many = program.define(_remove_many)

    assert remove_one.facts.effect is EffectClass.writesState
    assert remove_many.facts.effect is EffectClass.writesState

    # `-=` is Python's in-place DIFFERENCE and set difference is total: every
    # copy goes and absence is not an error. `del` is Python's own `del` and
    # still raises on a pattern that matches nothing.
    target.add(S.item(1), S.item(1), S.item(2), S.keep())
    assert remove_one(target, S.item(1)) == [S.done]
    assert target.atoms().count(S.item(1)) == 0
    assert program.atoms() != target.atoms()

    assert remove_many(target, S.item(V.which)) == [S.done]
    assert target.atoms() == [S.keep()]

    assert remove_one(target, S.absent) == [S.done]
    (missing_many,) = remove_many(target, S.missing(V.which))
    expected = S.Error(
        S["remove-atom"](target, S.missing(V.which)),
        "remove-atom: atom is not in the space",
    )
    assert isinstance(missing_many, Expression)
    assert missing_many.alpha_eq(expected)
    assert target.atoms() == [S.keep()]
