"""examples/ch08-data/08-02-sequence-variables/01-segments.metta in Python: a pattern child that stands for a run.

MeTTa's gap glyph is Python's own Ellipsis, so `...` in a pattern child
position is the anonymous gap and reads the same in both notations. The named
one is `seg(V.rest)`, and the run it takes arrives as an ordinary Expression on
the answer row, which is why the expected values below are SLICES: a run of
children is what `order[2:]` already means in Python.

The `case` arm is where Python had the concept and did not know it: a star
pattern in `match/case` IS the named gap. It needs a function to live in, and
the example's `case` is a runnable that stores nothing, so the function goes in
a scratch space and the home space holds exactly the four atoms the example
adds to it.

Two claims stay at the engine because Python has no spelling for either. The
two-operand `unify` is an engine head, reached through `m.fn.unify`; the
refusal outside the proved-finite fragments is an EngineError whose message
carries the theorem, since the structured payload the MeTTa side reads with
`index-atom` is not exposed as an attribute.
"""

from metta import S, V, seg, solve
from metta.errors import EngineError


def twin(m):
    """Read every arity a head has, name a run, and meet the fence."""
    seven = S.Order(7, S.x, S.y)
    eight = S.Order(8)
    m += seven
    m += eight
    m += S.Order(9, S.z)
    m += S.Note(1)

    # A gap matches any number of children, zero included, so one pattern
    # reads every arity the head has, and it does not widen the head.
    assert len(list(m[(S.Order, ...)])) == 3
    assert len(list(m[(S.Note, ...)])) == 1

    # A named gap answers the run it took, as the expression those children
    # make, which is the slice of the row after the children the pattern fixed.
    assert [row.rest for row in m[(S.Order, 8, seg(V.rest))]] == [eight[2:]]
    assert [row.rest for row in m[(S.Order, 7, seg(V.rest))]] == [seven[2:]]

    # Parsing by unification: two gaps around a separator enumerate the
    # splits, one answer per split, with no recursion written.
    row = (S.a, S.b, S.SEP, S.c, S.SEP, S.d)
    splits = solve((V.pre, ..., S.SEP, ..., V.post), row)
    assert [(answer.pre, answer.post) for answer in splits] == [
        (S.a, S.d),
        (S.a, S.d),
    ]

    # A repeated named gap has to take the same run twice.
    repeated = (S.f, seg(V.run), S.mid, seg(V.run))
    twice = S.f(S.a, S.b, S.mid, S.a, S.b)
    assert [answer.run for answer in solve(repeated, twice)] == [twice[1:3]]
    assert list(solve(repeated, S.f(S.a, S.b, S.mid, S.c))) == []

    # A case arm reads a run the same way, and the first match wins.
    scratch = m.metta.space()

    @scratch.define
    def tail(order):
        match order:
            case (S.Order, id, *rest):
                return S.pair(id, rest)
            case _:
                return S.nope

    assert list(tail(seven)) == [S.pair(7, seven[2:])]
    assert list(tail(S.Note(1))) == [S.nope]

    # A marker written on the other operand of unify is data, so a gap
    # consumes one as a single child. Alpha equality, because the marker in the
    # answered run carries the engine's own fresh variable rather than the name
    # this file wrote.
    subject = S.f(S.a, S.b, seg(V.v))
    open_run = m.fn.unify(S.f(S.a, seg(V.u)), subject, V.u, S.none).one()
    assert open_run.alpha_eq(subject[2:])

    # The fence: general sequence unification is infinitary, so an ask outside
    # the three proved-finite fragments refuses and names the theorem.
    refusal = None
    try:
        m.fn.unify(S.f(seg(V.x), S.a), S.f(S.a, seg(V.x)), S.yes, S.no).one()
    except EngineError as error:
        refusal = error
    assert "Theorem 62" in str(refusal)
    assert "outside the proved finitary fragment" in str(refusal)

    # A marker a variable carries is data, never a gap: only what the program
    # wrote is read as one.
    m += S.Marked(..., S.tail)
    assert [row.slot for row in m[(S.Marked, V.slot, S.tail)]] == [S["..."]]


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 9502, 9502, 9502 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/01-segments.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
BUDGET = 9502
