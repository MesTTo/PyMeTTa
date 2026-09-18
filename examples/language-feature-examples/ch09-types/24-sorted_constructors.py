"""Purpose: examples/ch09-types/24-sorted_constructors.metta in Python.

The example exposes sorted operations and equations themselves. Their atom
builders preserve that exact declaration surface, including its untyped control.
[tested: translator_constructors; commit=2398951d3272ad02b2c2d7b1e2b610c8e332c1f5]
"""

from metta import S, V, arrow, equation, ground, typed


def twin(m):
    """Build the same declarations and compare all three reductions."""
    m += typed(S.SortedPoint, arrow(S.Number, S.Number, S.SortedPoint))
    # rung: these head patterns teach the arrow/equation layer directly.
    m += equation(S.sorted_x(S.SortedPoint(V.x, V.y))).to(V.x)
    m += equation(S.plain_x(S.PlainPoint(V.x, V.y))).to(V.x)
    m += equation(S.make_sorted_point(V.x, V.y)).to(S.SortedPoint(V.x, V.y))
    m += equation(S.sorted_norm(S.SortedPoint(V.x, V.y))).to(
        S.sqrt_math(S["+"](S["*"](V.x, V.x), S["*"](V.y, V.y)))
    )
    assert m.type(S.SortedPoint(3, 4)) == S.SortedPoint
    assert m.fn.sorted_x(S.SortedPoint(3, 4)) == [3]
    assert m.fn.sorted_norm(S.SortedPoint(3, 4)) == [5.0]
    assert m.fn.make_sorted_point(ground("bad"), 4) == [
        S.Error(S.SortedPoint(ground("bad"), 4), S.BadArgType(1, S.Number, S.String))
    ]

    projections = {
        S.constructor_control: 3,
        S.constructor_sorted: S.sorted_x(S.SortedPoint(3, 4)),
        S.constructor_plain: S.plain_x(S.PlainPoint(3, 4)),
    }
    for head, projection in projections.items():
        # rung: one equation template keeps the three measured loops identical
        # apart from the projection whose cost the example compares.
        m += equation(head(V.n, V.sum)).to(
            S["if"](
                S["=="](V.n, 0), V.sum,
                S.let(V.x, projection, head(S["-"](V.n, 1), S["+"](V.sum, V.x))),
            )
        )
    assert m.fn.constructor_control(20, 0) == [60]
    assert m.fn.constructor_sorted(20, 0) == [60]
    assert m.fn.constructor_plain(20, 0) == [60]


#: Construction proofs remove the repeated strict check, and the retained
#: sorted field projection removes its call. Declaration publication and
#: invalidation remain inside this complete-example count.
#: [measured: 19782 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure
#: examples/ch09-types/24-sorted_constructors.metta; fixture=min of three
#: serial fresh processes with native engine artifacts; commit=2398951d3272ad02b2c2d7b1e2b610c8e332c1f5].
#: RE-PINNED 2026-09-18, 19782 to 19852 (+70), the branch's landings since the
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
BUDGET = 19852
