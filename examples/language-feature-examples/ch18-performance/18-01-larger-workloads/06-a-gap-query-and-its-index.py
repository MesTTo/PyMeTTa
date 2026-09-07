"""examples/ch18-performance/18-01-larger-workloads/06-a-gap-query-and-its-index.metta in Python: what a gap query reads.

A gap pattern cannot use the store's arity-keyed read, so the candidate set is
enumerated per admissible arity with the pattern's own leading child written
into the head first. The store's first-argument index therefore still selects
the relation, and the size of every other relation is not in the cost.

`m.limits(inferences=)` is the scoped form of the example's `(inferences N
...)`, and it can say one thing the example cannot: an expired bound is a
control signal, so in MeTTa it ends the file, while here it is an
InferenceLimitError this twin catches. The node query is asked under the same
bound the edge queries fit inside, and it does not fit.

The bulk loader is the example's own equation rather than a Python loop, so the
space this twin leaves behind holds what the example's holds.
"""

from metta import S, V, equation, if_, seg
from metta.errors import InferenceLimitError

#: The bound both edge queries fit inside at either store size, measured on the
#: MeTTa side of this pair by lowering it until the ask stopped fitting: 57
#: inferences gap-free, 144 with a gap, against 46,070 for the same gap over the
#: node relation at 2,000 nodes.
BOUND = 1000


def twin(m):
    """Grow the store tenfold and ask the same two questions under one bound."""
    m += equation(S.nodes(V.n)).to(  # rung: a compiled body has no spelling for a space write inside a let
        if_(
            S.eq(V.n, 0),
            S.done,
            S.let(V.t, S.add_atom(m, S.node(V.n, S.tag)), S.nodes(V.n - 1)),  # rung: as above
        )
    )
    m += S.edge(S.a, S.b)
    m += S.edge(S.a, S.c)
    m += S.edge(S.a, S.d, S.e)

    # Two hundred atoms in a relation the edge queries never touch.
    assert m.fn.nodes(200) == [S.done]
    with m.limits(inferences=BOUND):
        assert len(list(m[(S.edge, S.a, V.y)])) == 2
        assert len(list(m[(S.edge, ..., V.y)])) == 3

    # Two thousand more, and the same bound holds: the gap query reads the edge
    # clauses and nothing else.
    assert m.fn.nodes(2000) == [S.done]
    with m.limits(inferences=BOUND):
        assert len(list(m[(S.edge, S.a, V.y)])) == 2
        assert len(list(m[(S.edge, ..., V.y)])) == 3

    # The gap query over the node relation itself answers 2,200 rows, and no
    # ask can answer 2,200 rows for fewer than 2,200 inferences, so an edge
    # query fitting under 1,000 cannot have read them.
    assert len(list(m[(S.node, ..., V.y)])) == 2200
    expired = None
    try:
        with m.limits(inferences=BOUND):
            list(m[(S.node, ..., V.y)])
    except InferenceLimitError as error:
        expired = error
    assert str(BOUND) in str(expired)

    # The gap decides the arity, so one pattern spans all three edge rows while
    # the fixed pattern reads only the two of its own length.
    assert sorted(row.y for row in m[(S.edge, S.a, V.y)]) == [S.b, S.c]
    wide = S.edge(S.a, S.d, S.e)
    assert sorted(row.rest for row in m[(S.edge, S.a, seg(V.rest))]) == [
        S.edge(S.a, S.b)[2:],
        S.edge(S.a, S.c)[2:],
        wide[2:],
    ]


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 51022, 51022, 51022 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch18-performance/18-01-larger-workloads/06-a-gap-query-and-its-index.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
BUDGET = 51022
