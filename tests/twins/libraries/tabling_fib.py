"""examples/libraries/tabling_fib.metta in Python: memoised recursion, declared once.

`@m.cache` is the whole file. It is the `functools.lru_cache` shape lowered onto
the engine's tabling declaration, so it compiles the equations and declares the
table in one act, in the order tabling requires: the function must exist before
the name can be instrumented, which is why the example declares AFTER defining
and why a decorator cannot get that wrong.

Nothing here imports lib_tabling by hand. The declaration needs it and the
decorator asks for it, which is what a declaration over a call means.
"""

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Define fib, table it, and take the thirtieth in linear time."""
    @m.cache
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    assert fib(30) == [832040]
