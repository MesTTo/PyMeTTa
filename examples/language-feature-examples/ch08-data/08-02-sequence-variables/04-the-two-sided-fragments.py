"""examples/ch08-data/08-02-sequence-variables/04-the-two-sided-fragments.metta in Python: the two-sided fragments and the door that reaches them.

The last-position and linear-shallow calculi need a gap on BOTH sides, so they
need a door that hands the matcher two pieces of SYNTAX. `unify` is that door
and the only one, which is why every ask here goes through `m.fn.unify` rather
than through `solve`: `solve` lowers to `let`, whose subject is EVALUATED, so a
marker written there arrives as a value and a value's marker-shaped children
are data. That is not a limitation of Python's spelling, it is the same
one-sided reading `let` has in MeTTa, and 03 is the file it belongs to.

The four two-sided shapes and the trivial identity answered `none`, `no` and a
`mixed_roles` refusal until 2026-09-07, when the door began parsing both
operands; each one is now the answer its own calculus gives, and the identity
row agrees with upstream PeTTa, which has no reading of a gap at all and
unifies the two identical expressions. A pair outside all three fragments still
refuses, and 05-the-fence.py reads that refusal apart.
"""

from metta import Expression, S, V, seg
from metta.errors import EngineError


def twin(m):
    """Ask each two-sided shape through the door whose operands are syntax."""
    # One side with no gap is the one-sided fragment whichever side it is: a
    # gap written on the right alone consumes the left's children.
    assert m.fn.unify(S.f(S.a, S.b), S.f(S.a, seg(V.v)), V.v, S.none).one() == (
        S.f(S.a, S.b)[2:]
    )

    # Last position: the right side is longer by exactly its gap, so the run is
    # empty.
    assert m.fn.unify(
        S.f(S.a, S.b), S.f(S.a, S.b, seg(V.v)), V.v, S.none
    ).one() == Expression(())

    # A remainder that still holds the other side's gap keeps it, as the marker
    # that would match it, so the run IS the tail of the side it came from.
    # Alpha equality, because the marker in the answered run carries the
    # engine's own fresh variable rather than this file's name.
    longer = S.f(S.a, S.b, seg(V.v))
    open_run = m.fn.unify(S.f(S.a, seg(V.u)), longer, V.u, S.none).one()
    assert open_run.alpha_eq(longer[2:])
    whole = S.f(seg(V.v))
    whole_gap = m.fn.unify(S.f(seg(V.u)), whole, V.u, S.none).one()
    assert whole_gap.alpha_eq(whole[1:])

    # An anonymous gap is a name like any other here, absorbing the other
    # side's gap as one child of its run.
    assert list(m.fn.unify((S.f, ...), S.f(seg(V.v)), S.taken, S.none)) == [S.taken]

    # Linearity is not required in this fragment, so a name may occur twice and
    # its second occurrence solves the run its first took against what it
    # faces.
    repeated = m.fn.unify(
        (S.f, (S.g, seg(V.x)), (S.h, seg(V.x))),
        S.f(S.g(seg(V.y)), S.h(S.b)),
        V.x,
        S.none,
    )
    assert repeated.one() == S.f(S.b)[1:]

    # And the calculus keeps `X = X` as trivial rather than as a clash, so a
    # name written as a gap on both sides plays one role and the pair holds.
    assert list(m.fn.unify(S.f(seg(V.u)), S.f(seg(V.u)), S.yes, S.no)) == [S.yes]

    # The fragment is unitary: one answer or none, never a stream.
    assert len(list(m.fn.unify(S.f(S.a, S.b), S.f(S.a, S.b, seg(V.v)), V.v, S.none))) == 1

    # Linear shallow: two root gaps, each taking the other side's fixed child.
    pair = m.fn.unify(
        (S.f, seg(V.u), S.b), S.f(S.a, seg(V.v)), (V.u, V.v), S.no
    ).one()
    assert pair == Expression((S.f(S.a)[1:], S.f(S.b)[1:]))

    # What a gap absorbs is whole children, expressions included, so two gaps
    # can trade the settled children written between them.
    traded = m.fn.unify(
        (S.f, seg(V.u), (S.g, S.a)), S.f(S.g(S.b), seg(V.v)), (V.u, V.v), S.no
    ).one()
    assert traded == Expression(
        (Expression((S.g(S.b),)), Expression((S.g(S.a),)))
    )

    # Each of those answers once too, because each gap is pinned by the other
    # side's settled children.
    assert len(list(
        m.fn.unify((S.f, seg(V.u), S.b), S.f(S.a, seg(V.v)), (V.u, V.v), S.no)
    )) == 1

    # A space operand makes the ask a query, which is one-sided again: the
    # stored side is data. Both doors then answer the same rows.
    m += S.friend(S.Bob, S.Alice)
    m += S.friend(S.Carol, S.Alice)
    queried = list(m.fn.unify(m, S.friend(seg(V.who)), V.who, S.none))
    assert queried == [S.friend(S.Bob, S.Alice)[1:], S.friend(S.Carol, S.Alice)[1:]]
    assert [row.who for row in m[(S.friend, seg(V.who))]] == queried

    # Outside all three fragments the ask refuses. Kutsia's own witness is a
    # pair of root gaps sharing one name across a settled child, which is
    # neither all-final nor linear, so it has no certificate.
    refusal = None
    try:
        list(m.fn.unify((S.f, seg(V.x), S.a), S.f(S.a, seg(V.x)), S.yes, S.no))
    except EngineError as error:
        refusal = error
    assert "no_certificate" in str(refusal)


#: What this twin spends, its own tripwire, taken on the tree that
#: rewrote it onto the two-sided door, with the engine's .qlf set built,
#: which is what the gate leaves behind and what ships. The twin it
#: replaces asked through `solve` and priced 8469; the door changed, so the
#: number is a fresh measurement rather than a re-pin of that one.
#: [measured: 11233, 11233, 11233 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/04-the-two-sided-fragments.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 77; commit=f4ae837efd23791200846ba72556c2ce96a7d05a]
BUDGET = 11233
