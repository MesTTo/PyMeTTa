"""examples/libraries/tabling_fib.metta in Python: memoised recursion, declared once.

`@m.cache` is the whole file. It is the `functools.lru_cache` shape lowered onto
the engine's tabling declaration, so it compiles the equations and declares the
table in one act, in the order tabling requires: the function must exist before
the name can be instrumented, which is why the example declares AFTER defining
and why a decorator cannot get that wrong.

Nothing here imports lib_tabling by hand. The declaration needs it and the
decorator asks for it, which is what a declaration over a call means.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 83268 to 82247, -1021 (-1.23%), by the idiomatic
#: rewrite: the `test` wrapper and the separate `tabled` declaration left the
#: engine: `@m.cache` says the definition and the declaration in one act, and
#: the memoised recursion is everything else. Measured min-of-three with the
#: MORK backend linked into this worktree, which the earlier figure may not
#: have been. Prior: 83268 was the last figure for the generator twin that
#: yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 82247


def twin(m):
    """Define fib, table it, and take the thirtieth in linear time."""
    @m.cache
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    assert fib(30) == [832040]
