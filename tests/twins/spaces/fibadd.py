"""Purpose: examples/spaces/fibadd.metta in Python: an exponential call under a raised bound.

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
the pragma is a term (residue, P14.10). PERFECT:
`with m.limits(stack=100_000_000): assert fib(30) == [832040]`, the mode family
carrying the pragma vocabulary the way it carries the other two bounds.
"""

from petta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Define the naive fib, then ask for fib(30) with the fuel raised."""

    @m.define
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    raised = ((S["max-stack-depth"], 100_000_000),)
    assert m.answers(S["with-pragma!"](raised, S.fib(30))).one() == 832040
