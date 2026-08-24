"""examples/basics/factorial.metta in Python: recursion through a conditional.

`@m.define` reads the function as syntax and writes the equation, so Python's
conditional expression IS MeTTa's `if` and the recursive call is the same call
the equation makes.

Compiled-body equality now lowers to the engine's `==` relation, so the stored
equation is the source equation rather than a host-equality approximation.
"""

#: Inferences this twin spends, its own tripwire. INTERIM PIN 2026-08-24,
#: identity.py's and spaces3.py's own precedent: two lane tests fixture on
#: this file's REAL point budget, so it is priced ahead of the corpus-wide
#: pass and re-priced there with everything else. Min-of-3 on the Stage D
#: integration merge, three identical readings [measured 2026-08-24 through
#: twin_coverage --measure on the merged tree at 5e02a52d].
BUDGET = 4788


def twin(m):
    """Define the factorial and run it."""
    @m.define(name="facF")
    def fac_f(n):
        # (= (facF $n) (if (== $n 0) 1 (* $n (facF (- $n 1)))))
        return 1 if n == 0 else n * fac_f(n - 1)

    assert fac_f(10) == [3628800]
