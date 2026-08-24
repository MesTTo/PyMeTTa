"""examples/libraries/he_minimalmetta.metta in Python: the minimal instruction set, by hand.

This one file is deliberately NOT idiomatic in its body, and the reason is its
subject: `div` is written in minimal MeTTa, out of `chain`, `eval` and `unify`
alone, to exercise the instruction set 70,000 recursions deep. Assignment
lowers to `let*`, not to `chain`, so a compiled Python body would store a
different program and stop being the exercise. The equation therefore goes to
the container door and says exactly what the example says, which the residue
table records against P14.4.

Inside that built body the arithmetic is still Python's own, because an
operator with a VARIABLE operand builds the term: `V.x - V.y` is `(- $x $y)`
and `1 + V.accum` is `(+ 1 $accum)`. The comparison takes its WORD, `S.lt`,
since the four rich comparisons order atoms rather than building terms. The
four-argument `unify` is the conditional matcher, which the exported two-
argument `unify` is not, so it is spelled at the mention door.

Everything outside the equation is Python: the definition is built once and
named, and the claim is an ordinary comparison.

`with-pragma!` is named too, and this is the one mode in the folder no
with-block reaches. `m.limits` grew a `stack=` keyword, but it is SWI's stack
size in BYTES: measured 2026-08-24, this same 350,000-step run under
`m.limits(stack=8_000_000_000)` still answers
`(Error (div 278580 5 14284) StackOverflow)`, where `with-pragma!` raising
`max-stack-depth` answers 70000. The residue entry says so.

The pragma takes the attribute door, not a bracket. A trailing `!` has no
Python image, so `m.fn.with_pragma` resolves `with-pragma!` by rung 4's own
fallback, and because the resolved name ends in `!` the call performs on the
line that writes it.
"""

from metta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1

#: The 70,000-step interpreter exercise states a budget above the engine default.
DEEP_STACK = (S.max_stack_depth(1_000_000),)


def twin(m):
    """Write integer division as chain, eval and unify, then run it 70,000 deep."""
    m.fn["import!"](m, S.library(S["lib_he"]))

    m += equation(S.div(V.x, V.y, V.accum)).to(
        S.chain(S.eval(V.x - V.y), V.r1,
          S.chain(S.eval(S.lt(V.r1, 0)), V.r2,
            S.chain(S.unify(V.r2, True,  # noqa: FBT003  -- True is the ATOM the comparison answers, matched against, not a flag
              V.accum,
              S.chain(S.eval(1 + V.accum), V.inc,
                S.chain(S.eval(S.div(V.r1, V.y, V.inc)), V.r4, V.r4))), V.r3, V.r3))))

    counted = S.chain(S.eval(S.div(350000, 5, 0)), V.rr, V.rr)
    assert m.fn.with_pragma(DEEP_STACK, counted) == [70000]
