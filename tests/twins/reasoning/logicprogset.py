"""Purpose: examples/reasoning/logicprogset.metta in Python: a set built by checking it.

`myf` says what a two-element set containing `a` and `b` is, and the example
then asks for one. Nothing constructs it: the first two conjuncts BIND `$M` by
membership and the third fixes its size, so the answer falls out of the search.

The equation stays at the container door because MeTTa's `and` is not Python's.
Python's `and` short-circuits on truthiness and lowers to a `let*`-then-`if`
chain; `(and (member a $M) (member b $M))` is a generate-and-test in which the
first conjunct binds for the second, and that binding IS the example. So the
term is built as it is, with `&` for `and` and `.eq` for the equality term,
since `==` between atoms is Python's own structural equality.

The claim keeps `if` and `once` for a reason worth stating: an evaluation
answers VALUES, and `$M` is a BINDING. There is no Python door that hands back
an evaluation's bindings, so the variable has to be carried out of the term by
the term itself; `space[pattern]` binds only over stored atoms, and nothing
here is stored.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2948 to 2719, -229 (-7.77%), by the twin contract
#: change: the `test` wrapper left the engine for Python's own `assert`. The
#: search itself did not move. Against the example's 5305 the ratio is 0.5125
#: [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/reasoning/logicprogset.metta`]. Prior: ADDED 2026-08-22 at 2948 by
#: the wave-3 twin baseline.
BUDGET = 2719


def twin(m):
    """Say what the set is, then let the search find one."""
    m += equation(S.myf(V.M)).to(
        S.member(S.a, V.M) & S.member(S.b, V.M)
        & S["size-atom"](V.M).eq(2)  # rung: `len()` needs a value; $M is a variable the search has not bound yet
    )

    # `(a b)` is the two-member SET the search found, not a call, so it is built
    # with Expression rather than as `S.a(S.b)`, which would read as one.
    assert m.eval(S["if"](S.once(S.myf(V.M)), V.M)) == [Expression((S.a, S.b))]  # rung: $M is a binding no Python door hands back, and (a b) is a set rather than a call
