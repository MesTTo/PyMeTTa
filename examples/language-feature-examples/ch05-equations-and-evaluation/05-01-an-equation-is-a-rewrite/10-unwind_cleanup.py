"""Purpose: apply the native unwind protocol from Python-built terms.

The handler is an ordinary stored equation. Deterministic completion skips it;
failure and caller cut apply it once to the native outcome product [tested:
python extensions/python/tools/twin_coverage.py examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/10-unwind_cleanup.metta;
commit=WORKTREE].
"""

from metta import S, V


def twin(m):
    """Observe deterministic success, failure and caller cut in the same space."""
    m += S["="](S.unwind_note(V.home, V.outcome), S.add_atom(V.home, S.unwound(V.outcome)))
    handler = S.unwind_note(m)

    assert m.eval(S.on_unwind(7, handler)) == [7]
    assert list(m[S.unwound(V.outcome)]) == []

    assert m.eval(S.on_unwind(S.superpose(()), handler)) == []
    assert [row.outcome for row in m[S.unwound(V.outcome)]] == [S.fail()]
    m -= S.unwound(S.fail())

    assert m.eval(S.once(S.on_unwind(S.superpose((1, 2)), handler))) == [1]
    assert [row.outcome for row in m[S.unwound(V.outcome)]] == [S["!"]()]


#: Both forms retain the same parameterized handler equation and final
#: (unwound (!)) fact. The twin measures 5974 inferences; the native form 6964
#: [measured: 5974 twin inferences; command=python extensions/python/tools/twin_coverage.py examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/10-unwind_cleanup.metta;
#: fixture=SWI-Prolog 10.1.13, six assertions, empty source space; commit=WORKTREE].
BUDGET = 5974
