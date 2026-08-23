"""Purpose: examples/libraries/patrick_test.metta in Python: as-patterns, comprehension, and a lambda.

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
46 too, and the twin does NOT take it: it spends one janus crossing per
element, which is the crossing the three-lane model prices per collection.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Mirror a name around its head, filter six numbers, and fold ten."""
    m.eval(S["import!"](m, S.library(S["lib_patrick"])))

    # The as-pattern names the whole argument and destructures it at the same
    # time. It is a function, so it goes in the body under a `let` that unifies
    # it with the argument: a head is a pattern and matches structurally.
    m += equation(S.mirror(V.A)).to(S.let(V.A, S["@"](V.L, S.cons(V.head, V.tail)), S.append(S.reverse(V.L), V.tail)))  # rung: this `let` unifies a PATTERN against its argument rather than binding a name to a value, which is the as-pattern the claim is about

    [mirrored] = m.fn.mirror((S.h, S.a, S.n, S.n, S.e, S.s))
    assert list(mirrored) == [S.s, S.e, S.n, S.n, S.a, S.h, S.a, S.n, S.n, S.e, S.s]

    # DEFECT, and the two lines below are what it costs. Both of these ought
    # to read `m.fn["for"](...)` and `m.fn.iterate(...)`, the call door. Their
    # arguments carry variables the TERM binds, `$x` for the comprehension and
    # `$i`/`$x` for the lambda, and the answer view reads every variable in a
    # call as the caller's own and answers binding rows instead of the term.
    # Until it distinguishes them, the claim is stated through `eval`.
    kept = m.eval(S["for"](V.x, (1, 2, 3, 4, 5, 6), S["if"](V.x > 3, V.x)))  # rung: a two-armed `if` answers NOTHING for what it rejects, which is what makes this a filter; Python's conditional expression has no such form
    assert kept == [4, 5, 6]

    step = S["|->"](Expression((V.i, V.x)), V.x + V.i)
    assert m.eval(S.iterate(0, 10, 1, step)) == [46]
