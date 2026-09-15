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
BUDGET = 9060
