"""Purpose: examples/libraries/patrick_iterate_fib.metta in Python: fib by iteration, not recursion.

`iterate` runs a step function n times over a carried state, so the hundredth
Fibonacci number costs a hundred steps rather than a tree of calls. `iterate`
and `first` are lib_patrick's own and stay named.

Both equations are at the container door, and both reasons are already in the
residue table. `fib-step`'s head destructures its second argument,
`(fib-step $i ($a $b))`, where a decorated function's parameters are always
plain variables; and `fib`'s body PASSES `fib-step` as data, where a compiled
body resolves a lowercase free name as a function to call, and cannot spell a
hyphen at all.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 31840 to 31217, -623 (-1.96%), by the idiomatic
#: rewrite: the one `test` wrapper left the engine for `assert`; both
#: equations are the same stored atoms, so the hundred iterations are
#: untouched. Measured min-of-three with the MORK backend linked into this
#: worktree, which the earlier figure may not have been. Prior: 31840 was the
#: last figure for the generator twin that yielded `m.eval(S.test(...))` once
#: per runnable form.
BUDGET = 31217


def twin(m):
    """Carry a pair a hundred times, then take its first half."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_patrick)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    # One step: the pair (a b) becomes (b a+b).
    m += equation(S["fib-step"](V.i, Expression((V.a, V.b)))).to(Expression((V.b, V.a + V.b)))
    m += equation(S.fib(V.n)).to(S.first(S.iterate(0, V.n, (0, 1), S["fib-step"])))

    assert m.fn("fib")(100) == 354224848179261915075
