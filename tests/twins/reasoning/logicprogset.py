"""Purpose: examples/reasoning/logicprogset.metta in Python: a set built by checking it.

`myf` says what a two-element set containing `a` and `b` is, and the example
then asks for one. Nothing constructs it: the first two conjuncts BIND `$M` by
membership and the third fixes its size, so the answer falls out of the search.

The clause is a `@m.rules` bundle because MeTTa's `and` is not Python's.
Python's `and` short-circuits on truthiness and lowers to a `let*`-then-`if`
chain; `(and (member a $M) (member b $M))` is a generate-and-test in which the
first conjunct binds for the second, and that binding IS the example. A rules
body EXECUTES, so `&` builds the conjunction term there, rung 3 of the descent
ladder, and `S.eq` builds the equality by its operator word.

The claim is `solve`, which is the relational `let`: the subject is evaluated,
its answer is unified with the pattern, and the subject's own variables come
back as bindings. That is what carries `$M` out, where an evaluation would
answer values.
"""

from metta import TRUE, S, V, equation, fn

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Say what the set is, then let the search find one."""

    @m.rules
    def membership(members):
        """The one equation, as a term: (and (and (member a $M) (member b $M)) (== (size-atom $M) 2))."""
        yield equation(S.myf(members)).to(
            fn.member(S.a, members)
            & fn.member(S.b, members)
            & S.eq(fn.size_atom(members), 2)  # rung: `len()` needs a value; $M is a variable the search has not bound yet
        )

    # `(a b)` is the two-member SET the search found. Calling the head is the
    # shorter spelling of that same two-element atom.
    # !(test (if (once (myf $M)) $M) (a b))
    assert m.solve(TRUE, fn.once(S.myf(V.M))).M == S.a(S.b)
