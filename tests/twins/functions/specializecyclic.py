"""Purpose: spell the cyclic higher-order specialization example in Python.

Two mutually recursive pairs, each carrying the function it was called with.
The pairs are the reason both take the `@m.rules` shape of the definitional
decorator rather than `@m.define`: `f1`'s body calls `f2` and `f2`'s body
calls `f1`, and a compiled body resolves a free name against what the engine
knows AT DECORATION TIME, so whichever is written first cannot name the other.
At the rule door both are ordinary built terms and the cycle closes when the
bundle lands.

Assumes:
  - the four equations and two runnable claims mirror
    examples/functions/specializecyclic.metta in source order
    [source: examples/functions/specializecyclic.metta lines 1-15; commit=WORKTREE]
Guarantees:
  - twin installs every equation and proves both runnable claims
    [tested: test_a_shipped_twin_agrees_with_its_example_end_to_end; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, equation, if_

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships.
#: Before the wave this file carried an EMPIRICAL envelope rather than a point,
#: minimum 26325, maximum 26409 over 28 observations under
#: `full-lane/218/workers=32`, because its cost moves with the scheduler; the
#: re-pin pass has to give it an envelope again rather than a point
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Install both cycles and ask each one through the same function value."""

    @m.rules
    def cyclic(f, a, n):
        """The mutually recursive equations, admitted as one rule bundle."""
        # (= (f1 $f $a) (if (< $a 0) ($f nevercalled 42)
        #                   (if (== $a 0) (f2 $f (- $a 1)) finish)))
        #
        yield equation(S.f1(f, a)).to(
            if_(
                S.lt(a, 0),
                Expression((f, S.nevercalled, 42)),
                if_(S.eq(a, 0), S.f2(f, a - 1), S.finish),
            )
        )
        # (= (f2 $f $a) (if (< $a 0) ($f nevercalled 42) (f1 $f $a)))
        yield equation(S.f2(f, a)).to(
            if_(S.lt(a, 0), Expression((f, S.nevercalled, 42)), S.f1(f, a))
        )
        # (= (f3 $f $n) (if (== $n 0) finish (f4 $f $n)))
        yield equation(S.f3(f, n)).to(if_(S.eq(n, 0), S.finish, S.f4(f, n)))
        # (= (f4 $f $n) (f3 $f (- $n 1)))
        yield equation(S.f4(f, n)).to(S.f3(f, n - 1))

    assert m.eval(S.f1(S.add, 2)) == [S.finish]
    assert m.eval(S.f3(S.add, 1)) == [S.finish]
