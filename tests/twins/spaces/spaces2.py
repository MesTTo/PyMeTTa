"""Purpose: examples/spaces/spaces2.metta in Python: what is stored and what is only run.

Four facts are stored, two `!(bar ...)` forms are only EVALUATED, and the last
claim collects everything the space actually holds. `(bar 42)` is nowhere,
because evaluating a form never stores it, and that is the whole distinction
the example draws.

The facts are plain tuples, which is the knowledge front's own shape: `(foo 42
42)` reads as `(S.foo, 42, 42)` and nests, so `(foo (42 42))` is
`(S.foo, (42, 42))`.

The original sorts before comparing, and so does this file: `sorted(atoms)`
is `msort`, because atoms carry the engine's own elementwise order. That was
not true when this twin was first written, when the shipped key compared an
expression's LENGTH first and disagreed with `msort` whenever one expression
was a longer version of another, which is exactly the pair below; the twin
counted with `Counter` to avoid the question. `Atom.__lt__` now reads the
engine's order, so the ordinary spelling is the correct one again
[measured 2026-08-23: `sorted` and `msort` both answer
`((foo 42 42) (foo (42 42)))` for this file's own atoms; commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1


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
    assert sorted(held) == [S.foo(1), S.foo(2), S.foo(42, 42), S.foo((42, 42))]
    assert answer() == [42]
