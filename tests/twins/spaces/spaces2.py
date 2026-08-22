"""examples/spaces/spaces2.metta in Python: what is stored and what is only run.

Four facts are stored, two `!(bar ...)` forms are only EVALUATED, and the last
claim collects everything the space actually holds. `(bar 42)` is nowhere,
because evaluating a form never stores it, and that is the whole distinction
the example draws.

The facts are plain tuples, which is the knowledge front's own shape: `(foo 42
42)` reads as `(S.foo, 42, 42)` and nests, so `(foo (42 42))` is
`(S.foo, (42, 42))`.

The original sorts before comparing, and this file counts instead, because the
two sorts are not the same sort. MeTTa's `msort` compares an expression element
by element, where `petta.order_key` compares length first, so the two disagree
whenever one expression is a longer version of another: msort answers
`((foo 42 42) (foo (42 42)))` and `sorted(key=order_key)` answers
`((foo (42 42)) (foo 42 42))` for the very atoms below [measured 2026-08-22;
reported to the integrator]. Answers are a multiset, `Counter` is the multiset
algebra, and a multiset needs no order at all.
"""

from collections import Counter

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5204 to 2801, -2403 (-46.2%), by the twin contract
#: change: the closing `(test (space (msort (collapse (superpose ...)))) ...)`
#: became three subscript queries, a `Counter` comparison and one call, so
#: `test`, `msort`, `collapse` and `superpose` all left the engine while the
#: three matches it wrapped stayed in it. Against the example's 8186 the ratio
#: is 0.3422.
#: Prior: 5204, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 2801


def twin(m):
    """Store four facts, run two forms, then collect what the space holds."""
    m += (S.foo, 1)
    m += (S.foo, 2)
    m += (S.foo, 42, 42)
    m += (S.foo, (42, 42))

    # Nothing defines bar, so each form answers itself, and neither is stored.
    assert m.eval(S.bar(42)) == [S.bar(42)]
    assert m.eval(S.bar(43)) == [S.bar(43)]

    @m.define
    def answer():
        return 42

    held = (
        [S.foo(row.x) for row in m[S.foo(V.x)]]
        + [S.foo(row.x, row.y) for row in m[S.foo(V.x, V.y)]]
        + [S.bar(row.x) for row in m[S.bar(V.x)]]
    )
    assert Counter(held) == Counter(
        [S.foo(1), S.foo(2), S.foo(42, 42), S.foo((42, 42))]
    )
    assert answer() == [42]
