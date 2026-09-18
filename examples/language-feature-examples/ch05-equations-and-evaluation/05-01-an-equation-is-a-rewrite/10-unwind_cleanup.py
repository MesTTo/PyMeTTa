"""Purpose: apply the native unwind protocol from Python-built terms.

The handler is an ordinary stored equation. Deterministic completion skips it;
failure and caller cut apply it once to the native outcome product [tested:
python extensions/python/tools/twin_coverage.py examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/10-unwind_cleanup.metta;
commit=2d09b82e3ea1565d10fd8206e3b3cc9808ce6cb1].
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
#: fixture=SWI-Prolog 10.1.13, six assertions, empty source space; commit=2d09b82e3ea1565d10fd8206e3b3cc9808ce6cb1].
#: RE-PINNED 2026-09-18, 5974 to 4630 (-1344), the branch's landings since the
#: 09-10 pins, re-taken on the tip f06186a96: the compiled call law (e59104ace:
#: an Atom argument enters as written, a Python object crosses as a value, a
#: positional call of a bound callee is the plain application and a compiled
#: lambda is bare where it is applied), the one codec at the grounded call
#: (fd0af38f7, whose read of a call site's written keyword tail costs about six
#: inferences per translated site, read once since 7cc8fb863), the runnable
#: cache's dependency index written by the producer (a9e2c06d3, which takes
#: back the walk of the generated code 5416e741d charged at every miss), the
#: host patches of 09-17 and the class units of 09-13 to 09-16 the ladder in
#: docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 4630 to 4542 (-88), the trunk merged (f97c4b0a3,
#: petta's 61 commits since c75181adc) with the definition batch's load pushed
#: as the running load (2da1155e3): every example moved with the engine, 279 of
#: 294 cheaper (median -0.78%), through the compiled runnable envelope
#: executing each runnable form's fixed answer, name and fuel envelope from
#: compiled clauses, the trunk's trailed scopes and compiled context readers (a
#: b_getval/2 read per recorded assertion in place of the branch's thread-local
#: rows), the host listener door and the receipts loop probing the owner once
#: per set; serial minimum of three fresh processes through the lane's run_twin
#: [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 4542
