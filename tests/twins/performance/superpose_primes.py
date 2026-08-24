"""Purpose: examples/performance/superpose_primes.metta in Python: four divisor searches.

Four eight-digit primes, each found by trial division, sharing one branch
budget. Both equations are ordinary Python functions under the decorator: the
recursion delegates by name, and the arithmetic is Python's own, which is what
the guide means by the syntax BEING the semantics.

One thing is worth knowing about what the body compiles to, and it is the
reason the two equality tests name their head.

Python's `==` inside a compiled body lowers to the prelude's `py-eq`, a host
crossing per iteration where the original's `(== 0 (% $n $d))` crosses not at
all, and a compiled `if` used to wrap any non-comparison condition in
`py-truthy` besides. MeTTa's own `==` is declared `(-> $t $t Bool)`, so a
compiled `if` now emits it bare, and `fn.eq(0, n % test_divisor)` stores
exactly the original's condition [measured 2026-08-23 on the merged tree, min
of one fresh process each: 922,119 inferences with the Python operators and
539,720 with the named head, against the example's 543,116; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].

`with-pragma!` stays a term for the one gap left: the four searches overflow the
evaluator's default stack depth without it, and `m.limits` bounds inferences
and time but not stack depth (residue, P14.14). PERFECT:
`with m.limits(stack=1_000_000): ...`, the mode family carrying the pragma
vocabulary the way it carries the other two bounds.

Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, Expression, S, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1

#: The branch allowance these searches state above the evaluator's 100000
#: default. `m.limits` bounds inferences and time, not stack depth.
DEEP = (S.max_stack_depth(1_000_000),)


def twin(m):
    """Define trial division, then ask it about four primes."""

    @m.define
    def find_divisor(n, test_divisor):
        if test_divisor * test_divisor > n:
            return n
        if fn.eq(0, n % test_divisor):  # rung: `==` lowers to the prelude's `py-eq`, a host crossing per iteration, where the example writes MeTTa's own `==`
            return test_divisor
        return find_divisor(n, test_divisor + 1)

    @m.define(name="prime?")
    def prime(n):
        return fn.eq(n, fn.find_divisor(n, 2))  # rung: the same host crossing, in answer position

    # Four searches share one branch budget, so the benchmark states a finite
    # allowance above the evaluator's 100000 default.
    searches = (S["prime?"](53537257), S["prime?"](53781811),
                S["prime?"](54218443), S["prime?"](54734431))
    assert m.fn.with_pragma(DEEP, searches).one() == Expression((TRUE, TRUE, TRUE, TRUE))
