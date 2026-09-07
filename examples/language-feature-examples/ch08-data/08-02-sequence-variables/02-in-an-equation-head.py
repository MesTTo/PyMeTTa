"""examples/ch08-data/08-02-sequence-variables/02-in-an-equation-head.metta in Python: a gap in the head of an equation.

A head that carries a gap is a function of variable arity, and Python's own
variadic spelling does not reach it: a compiled `def f(*xs)` is refused,
because `*args` has no MeTTa image at the parameter position. The equation is
therefore written as DATA, `equation(lhs).to(rhs)` under the write door, which
is the rung below the decorator and the one the ledger keeps for a head Python
cannot spell.

Everything else is ordinary. The runs the heads answer are slices of the calls
that produced them, the two-gap head answers once per split, and `fn.<name>`
calls each head the space now holds.
"""

from metta import S, V, equation, seg


def twin(m):
    """Install eight segment-headed equations and ask what each answers."""
    # A head whose only child is a gap: the whole argument list as one run.
    m += equation(S.allof(seg(V.xs))).to(S.kept(V.xs))  # rung: *args is refused at a compiled parameter
    # A gap between fixed children destructures instead.
    m += equation(S.middle(S.row(S.start, seg(V.mid), S.end))).to(V.mid)  # rung: as above
    # Two gaps in one head make the call nondeterministic.
    m += equation(S.split(S.row(seg(V.before), S.SEP, seg(V.after)))).to(  # rung: as above
        S.pair(V.before, V.after)
    )
    # An ordinary name keeps the run as one expression; a written marker
    # splices it into the expression around it.
    m += equation(S.project(S.head(seg(V.xs), S.tail))).to(  # rung: as above
        S.rebuilt(S.before, V.xs, S.after)
    )
    m += equation(S.splice(S.head(seg(V.xs), S.tail))).to(  # rung: as above
        S.rebuilt(S.before, seg(V.xs), S.after)
    )
    # One name in both roles, which only an equation head admits.
    m += equation(S.echoes((seg(V.xs), S.tag, V.xs))).to(S.yes)  # rung: as above
    # A gap head and an ordinary head are additive.
    m += equation(S.kind(S.row(...))).to(S.row_shaped)  # rung: as above
    m += equation(S.kind(V.other)).to(S.anything)  # rung: as above

    assert m.fn.allof() == [S.kept(S.allof()[1:])]
    assert m.fn.allof(S.a) == [S.kept(S.allof(S.a)[1:])]
    assert m.fn.allof(S.a, S.b, S.c) == [S.kept(S.allof(S.a, S.b, S.c)[1:])]

    filled = S.row(S.start, S.a, S.b, S.end)
    assert m.fn.middle(filled) == [filled[2:4]]
    assert m.fn.middle(S.row(S.start, S.end)) == [S.row()[1:]]

    # One call, one answer per split, shortest prefix first.
    splittable = S.row(S.a, S.SEP, S.b, S.SEP, S.c)
    assert list(m.fn.split(splittable)) == [
        S.pair(splittable[1:2], splittable[3:]),
        S.pair(splittable[1:4], splittable[5:]),
    ]

    written = S.head(S.a, S.b, S.tail)
    assert m.fn.project(written) == [S.rebuilt(S.before, written[1:3], S.after)]
    assert m.fn.splice(written) == [S.rebuilt(S.before, S.a, S.b, S.after)]

    # The ordinary occurrence stands for the expression the run makes, so the
    # call agrees only when the tail repeats the run.
    assert m.fn.echoes((S.a, S.b, S.tag, S.a(S.b))) == [S.yes]
    assert m.fn.echoes((S.tag, S.row()[1:])) == [S.yes]
    assert list(m.fn.echoes((S.a, S.b, S.tag, S.a(S.c)))) == []

    assert list(m.fn.kind(S.row(S.a, S.b))) == [S.row_shaped, S.anything]
    assert list(m.fn.kind(7)) == [S.anything]


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 16115, 16115, 16115 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/02-in-an-equation-head.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
#: RE-PINNED 2026-09-07, 16115 to 16179 (+64), 16176 of it is drift between
#: a403e56b4 and this branch's base, and 3 is this change: the twin writes no
#: unify at all, and 3 is what its equation heads pay for the subject case
#: metta_seq_atoms/2 now distinguishes [measured 2026-09-07: min-of-3 serial
#: fresh processes, this branch against the same twin on its base 5a85f5602;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 16179
