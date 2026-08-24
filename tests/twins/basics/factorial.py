"""examples/basics/factorial.metta in Python: recursion through a conditional.

`@m.define` reads the function as syntax and writes the equation, so Python's
conditional expression IS MeTTa's `if` and the recursive call is the same call
the equation makes.

Compiled-body equality now lowers to the engine's `==` relation, so the stored
equation is the source equation rather than a host-equality approximation.
"""

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
BUDGET = 1


def twin(m):
    """Define the factorial and run it."""
    @m.define(name="facF")
    def fac_f(n):
        # (= (facF $n) (if (== $n 0) 1 (* $n (facF (- $n 1)))))
        return 1 if n == 0 else n * fac_f(n - 1)

    assert fac_f(10) == [3628800]
