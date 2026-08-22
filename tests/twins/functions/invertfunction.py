"""Purpose: examples/functions/invertfunction.metta in Python: functions run backwards.

Unifying a pattern with what a call PRODUCES makes the call run backwards and
its variables come out bound, so destructuring a list with `cons` and
destructuring it with an ordinary user function are the same act. The last
form does it through arithmetic, where `#+` is the constraint path, so
`(g $X $Y 35)` solves `$X + 35 = 42`.

`f` is an ordinary Python function: `append((x,), y)` is `(append ($X) $Y)`,
where the one-element Python tuple is the one-element expression.

`g` takes the `@rules` shape of the definitional decorator, because its body
names `#+`, which no Python identifier spells; in the equational shape it is
the ordinary subscripted symbol the subscript form exists for.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8043 to 6756, -1287 (-16.0%), by the twin contract
#: change: three `test` wrappers left the engine for `assert`; the three
#: backward calls, which are the file, stayed. Against the example's 10800
#: the ratio is 0.6256 [measured 2026-08-22 min-of-3, `twin_coverage.py
#: --measure`]. The old figure priced a different program.
BUDGET = 6756


def twin(m):
    """Destructure a list three ways, one of them through arithmetic."""

    def solve(pattern, subject, answer):
        """Unify `pattern` with what `subject` produces, then answer `answer`.

        Either side may be the call, which is what makes it run BACKWARDS: the
        call's own variables come out bound. This is MeTTa's `let`, which
        dissolves into Python's assignment when the subject is a call and the
        pattern is a fresh name; the direction used here, a pattern the call
        has to reach, has no Python spelling at all. The design's name for the
        door it wants is `solve` (ai-python-first-revamp-discussion.md section
        9g, idea 1), and the residue table records it against P14.4.
        """
        return S.let(pattern, subject, answer)  # rung: relational let

    append = m.fn("append")

    @m.define
    def f(x, y):
        # (= (f $X $Y) (append ($X) $Y))
        return append((x,), y)

    # rung: the body names `#+`, which no Python identifier spells (residue, P14.4)
    @rules
    def constrained(x, y, z):
        # (= (g $X $Y $Z) (append ((#+ $X $Z)) $Y))
        yield equation(S.g(x, y, z)).to(S.append(((S["#+"], x, z),), y))

    m.add(*constrained)

    items = (1, 2, 3, 4, 5, 6)
    split = Expression((1, (2, 3, 4, 5, 6)))

    # List destructuring, through the cons constructor.
    assert m.one(solve(S.cons(V.Head, V.Tail), items, (V.Head, V.Tail))) == split
    # And through an ordinary user function, which is the point.
    assert m.one(solve(S.f(V.Head, V.Tail), items, (V.Head, V.Tail))) == split
    # A more complex case: the constraint solves 42 = $X + 35.
    assert m.one(
        solve(S.g(V.X, V.Y, 35), (42, 2, 3), (V.X, V.Y, 40))
    ) == Expression((7, (2, 3), 40))
