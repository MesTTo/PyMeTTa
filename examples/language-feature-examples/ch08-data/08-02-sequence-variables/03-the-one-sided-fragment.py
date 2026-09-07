"""examples/ch08-data/08-02-sequence-variables/03-the-one-sided-fragment.metta in Python: the fragment every gap ask lands in.

One side carries no gap at all, which is what every door in either notation
hands the matcher: `solve(pattern, row)` faces a built row, `space[pattern]`
faces stored atoms. So matching is the enumeration of the pattern's splits and
nothing more.

The expected runs are written as SLICES of the row they came out of, because a
run of children is exactly what Python's slice already means, and reading them
back is the ordinary atom protocol: `isinstance`, `len` and indexing.
"""

from metta import Expression, S, V, seg, solve


def twin(m):
    """Enumerate splits, take empty runs, repeat a name, and join a conjunct."""
    # Shortest first, one answer per split, so a two-gap pattern parses a
    # sequence with no recursion written.
    full = S.row(S.a, S.b, S.SEP, S.c, S.SEP, S.d)
    splits = solve((seg(V.pre), S.SEP, seg(V.post)), full[1:])
    assert [(answer.pre, answer.post) for answer in splits] == [
        (full[1:3], full[4:]),
        (full[1:5], full[6:]),
    ]

    # Zero children is a run, so the empty case needs no separate arm.
    assert [answer.r for answer in solve((S.row, seg(V.r)), S.row())] == [S.row()[1:]]
    three = S.row(S.a, S.b, S.c)
    assert [answer.r for answer in solve((S.row, seg(V.r)), three)] == [three[1:]]

    # The run is an ordinary expression: read it the way any other is read.
    run = solve((S.row, seg(V.r)), S.row(S.a, S.b)).one().r
    assert isinstance(run, Expression)
    assert len(run) == 2
    assert run[0] == S.a

    # A repeated named gap has to take the same run twice, and "the same" is
    # the engine's own comparison rather than sameness of spelling.
    repeated = (S.f, seg(V.x), S.g, seg(V.x))
    twice = S.f(S.a, S.b, S.g, S.a, S.b)
    assert [answer.x for answer in solve(repeated, twice)] == [twice[1:3]]
    assert list(solve(repeated, S.f(S.a, S.b, S.g, S.c))) == []
    assert len(list(solve(repeated, S.f(1, S.g, 1.0)))) == 1

    # Distinct anonymous gaps are distinct variables, so neither constrains the
    # other; what pins this pattern down is the literal `g` between them. These
    # three patterns carry no name to project, so they ask through the engine's
    # own two-operand head: `solve` needs a variable in one of its sides.
    anonymous = m.fn.unify((S.f, ..., S.g, ...), S.f(S.a, S.g, S.b, S.c), S.matched, S.no)  # rung: solve refuses a wholly ground ask
    assert list(anonymous) == [S.matched]

    # A gap below the root matches inside a child, and a settled child that
    # disagrees refutes every split rather than some of them.
    nested = m.fn.unify((S.f, (S.g, ...), S.b), S.f(S.g(1, 2), S.b), S.matched, S.no)  # rung: as above
    assert list(nested) == [S.matched]
    clash = m.fn.unify((S.A, ..., S.D), S.A(S.b, S.c, S.E), S.matched, S.no)  # rung: as above
    assert list(clash) == [S.no]

    # Against a space the stored side is the value, so a gap pattern reads
    # every arity the gap can span and joins with an ordinary conjunct.
    m += S.edge(S.a, S.b)
    m += S.edge(S.b, S.c, S.d)
    m += S.tag(S.b, S.hot)
    assert [row.last for row in m[(S.edge, S.a, ..., V.last)]] == [S.b]
    joined = m.match((S.edge, ..., V.mid), (S.tag, V.mid, V.heat))
    assert [(row.mid, row.heat) for row in joined] == [(S.b, S.hot)]


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 7851, 7851, 7851 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/03-the-one-sided-fragment.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
BUDGET = 7851
