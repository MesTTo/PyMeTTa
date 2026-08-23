"""Purpose: examples/performance/superpose_primes.metta in Python: four divisor searches.

Four eight-digit primes, each found by trial division, sharing one branch
budget. Both equations are ordinary Python functions under the decorator: the
recursion delegates by name, and the arithmetic is Python's own, which is what
the guide means by the syntax BEING the semantics.

Two things are worth knowing about what the body compiles to, because both are
the library's to close and neither changes an answer.

A compiled `if` wraps a condition that is not already a comparison in
`py-truthy`, and `==` inside a body lowers to the prelude's `py-eq`, so the
inner loop of a divisor search crosses to the host twice per iteration where
the original's `(== 0 (% $n $d))` crosses not at all. MeTTa's own `==` IS
reachable now, `fn["=="](0, n % d)`, which is what the residue asked for; it
does not help, because the `if` then wraps THAT in `py-truthy`. Measured
2026-08-23 on this tree, min of one fresh process each: the term door spends
531,461 inferences on these four searches, `fn["=="]` under a compiled `if`
spends 943,162, +77.5%, and the two stored bodies differ only by that wrapper
[commit=WORKTREE]. PERFECT: a compiled `if` that leaves an engine-Bool
condition alone.

`with-pragma!` stays a term for the second gap: the four searches overflow the
evaluator's default stack depth without it, and `m.limits` bounds inferences
and time but not stack depth (residue, P14.14). PERFECT:
`with m.limits(stack=1_000_000): ...`, the mode family carrying the pragma
vocabulary the way it carries the other two bounds.

Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, Expression, S, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1

#: The branch allowance these searches state above the evaluator's 100000
#: default. `m.limits` bounds inferences and time, not stack depth.
DEEP = (S["max-stack-depth"](1_000_000),)


def twin(m):
    """Define trial division, then ask it about four primes."""

    @m.define(name="find-divisor")
    def find_divisor(n, test_divisor):
        if test_divisor * test_divisor > n:
            return n
        if n % test_divisor == 0:
            return test_divisor
        return find_divisor(n, test_divisor + 1)

    @m.define(name="prime?")
    def prime(n):
        return n == fn.find_divisor(n, 2)

    # Four searches share one branch budget, so the benchmark states a finite
    # allowance above the evaluator's 100000 default.
    searches = (S["prime?"](53537257), S["prime?"](53781811),
                S["prime?"](54218443), S["prime?"](54734431))
    assert m.eval(S["with-pragma!"](DEEP, searches)) == [
        Expression((TRUE, TRUE, TRUE, TRUE))
    ]
