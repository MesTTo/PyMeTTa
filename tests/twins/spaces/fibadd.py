"""Purpose: examples/spaces/fibadd.metta in Python: an exponential call under a raised bound.

`fib(30)` on the naive two-call equation is a deliberately exponential tree,
and it exceeds the evaluator's default fuel, so the claim runs under a pragma
that raises the stack bound.

The original writes its equation with `add-atom` to show that route compiles
the same as a top-level `(= ...)` does. In Python there is only one route:
every definition arrives through a write, and `@m.define` is the definitional
door for a computation, so the distinction the original draws has nothing to
draw it against here.

The pragma itself is a TERM, named through the mention door: `fn.with_pragma`
is `with-pragma!`, rung 4 stripping the bang the way it strips a hyphen, and
`S.max_stack_depth` is the key. The modes door does not reach this bound. It
gained `stack=` in the P14 wave, but that is SWI's per-thread BYTE ceiling,
where `max-stack-depth` is the evaluator's branch-local reduction fuel, and the
two are different quantities the engine states separately (residue, P14.14)
[measured 2026-08-24: a 60,000-deep compiled recursion answers
`(Error 10002 StackOverflow)` inside `with metta.limits(stack=100_000_000)`
exactly as it does outside one; source: engine/metta.pl:194-196, "stack-limit
scopes SWI's per-thread byte ceiling ... max-stack-depth remains branch-local
reduction fuel"; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT:
`with m.limits(reductions=100_000_000): assert fib(30) == [832040]`, the mode
family carrying the branch allowance beside the two bounds it already carries.
"""

from metta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1


def twin(m):
    """Define the naive fib, then ask for fib(30) with the fuel raised."""

    @m.define
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    raised = (S.max_stack_depth(100_000_000),)
    assert m.fn.with_pragma(raised, S.fib(30)).one() == 832040
