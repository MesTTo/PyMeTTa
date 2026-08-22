"""examples/spaces/spaces_succeedspredicate.metta in Python: a predicate that binds.

lib_spaces' `succeedsPredicate` takes a space, a relation and its arguments as
one tuple, and answers whether the relation holds. Ground arguments make it a
membership test, which is the first claim; variable arguments make it a
generator, and the second claim USES what it bound.

Those two claims sit on different rungs, and the reason is one gap. The
membership test is an ordinary Python call, because a boolean crosses whole.
The generating form is a term the engine evaluates, because the bindings the
predicate makes are not handed back at the call door, so the `if` that consumes
them has to run where they exist (residue, P14.10). Python's own `if` is the
door everywhere the bindings are already in hand, which is what makes this one
line the exception rather than the rule.

`import!` is a directive with no Python door yet, so the library arrives
through `m.fn` (residue, P14.13).
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 19938 to 19590, -348 (-1.7%), by the twin contract
#: change: two `(test ...)` terms became two Python `assert`s, so the `test`
#: wrapper left the engine twice while both predicate questions stayed in it,
#: one as a call and one as the `if` term that consumes its bindings. The
#: library import is the bulk of both sides. Against the example's 22365 the
#: ratio is 0.8759.
#: Prior: 19938, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 19590


def twin(m):
    """Ask a predicate a ground question, then a binding one."""
    here = S[m.space_name]
    m.fn("import!")(here, S.library(S.lib_spaces))
    succeeds = m.fn("succeedsPredicate")

    # Nothing matches, so the ground question is False.
    assert succeeds((here, S.friend, S.tim, S.tom)) is False

    m += (S.friend, S.a, S.b)

    # The binding question answers what it bound, in the engine, where the
    # bindings are.
    holds = S.succeedsPredicate((here, S.friend, V.a, V.b))
    asked = S["if"](holds, (V.a, V.b), S.NotFound)  # rung: the call door drops the bindings, so the branch runs where they still exist
    assert m.one(asked) == S.a(S.b)
