"""examples/libraries/patrick_test.metta in Python: as-patterns, comprehension, and a lambda.

Three of lib_patrick's own forms, so all three stay named.

`mirror` is at the container door, recorded against P14.4: its body is a `let`
whose PATTERN is an as-pattern, `(@ $L (cons $head $tail))`, which names the
whole argument and destructures it at the same time. Python's `match` statement
has `as` and would spell it, and has no lowering in the compiled subset yet.

`for` reads like a comprehension and is not one: its body `(if (> $x 3) $x)` is
an `if` with NO else, which answers nothing for the items it rejects, and
Python's conditional expression requires the else. That two-armed `if` is why
this claim is a filter at all.

`iterate`'s step is `(|-> ($i $x) (+ $x $i))`, a MeTTa lambda, built as the term
it is. A Python `lambda i, x: x + i` is accepted in that position and answers
46 too, at 465 inferences against this spelling's 5,174, and the twin does NOT
take it: the counter does not see the ten janus crossings it spends, one per
element, which is the crossing the three-lane model prices per collection.
"""

from petta import S, V, equation, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 28309 to 27332, -977 (-3.45%), by the idiomatic
#: rewrite: three `test` wrappers and a `collapse` left the engine for
#: `assert` and `.all()`; the as-pattern, the filter and the lambda fold
#: still run there. Measured min-of-three with the MORK backend linked into
#: this worktree, which the earlier figure may not have been. Prior: 28309
#: was the last figure for the generator twin that yielded
#: `m.eval(S.test(...))` once per runnable form.
BUDGET = 27332


def twin(m):
    """Mirror a name around its head, filter six numbers, and fold ten."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_patrick)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    # The as-pattern names the whole argument and destructures it at the same
    # time. It is a function, so it goes in the body under a `let` that unifies
    # it with the argument: a head is a pattern and matches structurally.
    m += equation(S.mirror(V.A)).to(S.let(V.A, S["@"](V.L, S.cons(V.head, V.tail)), S.append(S.reverse(V.L), V.tail)))  # rung: this `let` unifies a PATTERN against its argument rather than binding a name to a value, which is the as-pattern the claim is about

    mirrored = m.fn("mirror")((S.h, S.a, S.n, S.n, S.e, S.s))
    assert list(mirrored) == [S.s, S.e, S.n, S.n, S.a, S.h, S.a, S.n, S.n, S.e, S.s]

    kept = m.fn("for").all(V.x, (1, 2, 3, 4, 5, 6), S["if"](V.x > 3, V.x))  # rung: a two-armed `if` answers NOTHING for what it rejects, which is what makes this a filter; Python's conditional expression has no such form
    assert kept == [4, 5, 6]

    assert m.fn("iterate")(0, 10, 1, S["|->"](expr(V.i, V.x), V.x + V.i)) == 46
