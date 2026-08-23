"""examples/basics/factorial.metta in Python: recursion through a conditional.

`@m.define` reads the function as syntax and writes the equation, so Python's
conditional expression IS MeTTa's `if` and the recursive call is the same call
the equation makes.

What is STORED is not quite what the original stores, and the difference is
worth reading back rather than believing. A compiled body's `==` lowers to
the prelude's `py-eq`, a host crossing, where the original writes MeTTa's own
`(== $n 0)`; the operator table calls `==` taken, for Python's own structural
equality, and the method form `a.eq(b)` that builds `(== a b)` has no body
equivalent. The two answer alike on every input this example has. The second
claim below is that reading, so the divergence is checked rather than
described, and the residue table records it against P14.4.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Define the factorial, run it, and read back the equation it stored."""
    @m.define(name="facF")
    def fac_f(n):
        # (= (facF $n) (if (== $n 0) 1 (* $n (facF (- $n 1)))))
        return 1 if n == 0 else n * fac_f(n - 1)

    assert fac_f(10) == [3628800]

    condition = m.query(S["="](S.facF(V.n), V.body)).one().body[1]
    assert condition[0] == S["py-eq"]
