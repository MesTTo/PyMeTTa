"""examples/translation/translatepredicate.metta in Python: a Prolog goal inline.

`translatePredicate` compiles its argument straight into the clause the
translator is building, so `(is $x 2)` and `(+ $x 40 $z)` are Prolog goals that
run where the equation runs, and `progn` sequences them so the second sees what
the first bound.

That sequencing has to happen in one engine call, which is why this file is one
term rather than three Python statements: the first goal binds `$x` and the
second reads it, and a Python variable cannot hold a binding the engine has not
finished making (residue, P14.10). Everything else is ordinary: the term is
built at the `S.` door and asked once.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 685 to 535, -150 (-21.9%), by the twin contract
#: change: `(test (progn ...) 42)` became one `assert`, so only the `test`
#: wrapper left the engine and the two translated goals stayed in it. Against
#: the example's 2261 the ratio is 0.2366.
#: Prior: 685, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 535


def twin(m):
    """Run two Prolog goals in sequence, and read what the second bound."""
    translate = S.translatePredicate
    goals = S.progn(translate(S["is"](V.x, 2)), translate(S["+"](V.x, 40, V.z)), V.z)
    assert m.one(goals) == 42
