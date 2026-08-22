"""examples/spaces/fibadd.metta in Python: an exponential call under a raised bound.

`fib(30)` on the naive two-call equation is a deliberately exponential tree,
and it exceeds the evaluator's default fuel, so the claim runs under a pragma
that raises the stack bound.

The original writes its equation with `add-atom` to show that route compiles
the same as a top-level `(= ...)` does. In Python there is only one route:
every definition arrives through a write, and `@m.define` is the definitional
door for a computation, so the distinction the original draws has nothing to
draw it against here.

`with-pragma!` has no with-block spelling yet. `m.limits()` is the modes door
and carries `inferences=` and `timeout=`, not the stack bound this needs, so
the pragma is a term (residue, P14.10).
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 28278972 to 28278815, -157 (-0.0%), by the twin
#: contract change: `(test (with-pragma! ...) 832040)` became one `assert`, so
#: only the `test` wrapper left the engine. Everything that costs anything here
#: is the 1.3-million-call fib tree itself, which is why the delta is three
#: figures against twenty-eight million. Against the example's 28280836 the
#: ratio is 0.9999.
#: Prior: 28278972, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 28278815


def twin(m):
    """Define the naive fib, then ask for fib(30) with the fuel raised."""

    @m.define
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    raised = ((S["max-stack-depth"], 100_000_000),)
    assert m.one(S["with-pragma!"](raised, S.fib(30))) == 832040
