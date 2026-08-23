"""Purpose: pin the second P14 Python library-surface wave.

Guarantees:
  - a tuple whose first element is its head is one subscript pattern, complete
    expression patterns form a join, mixed tuple mistakes refuse, list writes
    stream atoms, and deletion drains every occurrence or raises KeyError
    [tested: test_subscript_one_pattern_and_bulk_delete_laws; commit=WORKTREE]
"""  # noqa: D205  -- the contract is one continuous invariant

import pytest

from petta import S, V, space


def test_subscript_one_pattern_and_bulk_delete_laws() -> None:
    """Subscript dispatch follows pattern shape instead of flattening facts."""
    facts = space()
    facts += [
        (S.Parent, S.Tom, S.Bob),
        (S.Parent, S.Pam, S.Bob),
        (S.Female, S.Pam),
        (S.Tag,),
    ]

    parents = facts[(S.Parent, V.person, S.Bob)]
    assert parents.person == [S.Tom, S.Pam]
    assert facts[(V.only,)].only == [S.Tag]

    joined = facts[
        S.Parent(V.person, S.Bob),
        S.Female(V.person),
    ]
    assert joined.person == [S.Pam]

    with pytest.raises(TypeError, match=r"one pattern.*join"):
        _ = facts[S.Parent(V.person, S.Bob), S.Female]

    del facts[(S.Parent, V.person, S.Bob)]
    assert facts[(S.Parent, V.person, S.Bob)] == []
    with pytest.raises(KeyError):
        del facts[(S.Parent, V.person, S.Bob)]
