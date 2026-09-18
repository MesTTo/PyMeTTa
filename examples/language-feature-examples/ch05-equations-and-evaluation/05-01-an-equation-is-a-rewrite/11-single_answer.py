"""Purpose: observe an editable native equation through the one-answer door.

A failed alternative leaves one answer. Completed values stay held, and a
native equation replacement changes the next call [tested:
python extensions/python/tools/twin_coverage.py examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/11-single_answer.metta;
commit=eec241dcf822db6c4c1d1ecdb6092a6a9f3c7851].
"""

from metta import Expression, S


def twin(m):
    """Count answers, retain data and observe a rewritten native equation."""
    first = S["="](S.unique_value(), 11)
    m += first
    m += S["="](S.unique_value(), S.superpose(()))

    assert m.eval(S.eval_one(S["+"](1, 2))) == [3]
    assert m.eval(S.eval_one(S.unique_value())) == [11]
    held = S["+"](2, 3)
    assert m.eval(S.eval_one(S.noeval(held))) == [held]
    assert m.eval(S.eval_one(S.noeval(()))) == [Expression()]

    m -= first
    m += S["="](S.unique_value(), 22)
    assert m.eval(S.eval_one(S.unique_value())) == [22]


#: Five fresh processes retain the same two native equations and agree on
#: 9060 twin inferences and 8991 native inferences [measured: 9060 inferences;
#: command=python extensions/python/tools/twin_coverage.py examples/ch05-equations-and-evaluation/05-01-an-equation-is-a-rewrite/11-single_answer.metta;
#: fixture=SWI-Prolog 10.1.13, five assertions, empty source space; commit=eec241dcf822db6c4c1d1ecdb6092a6a9f3c7851].
#: RE-PINNED 2026-09-18, 9060 to 7098 (-1962), the branch's landings since the
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
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 7098
