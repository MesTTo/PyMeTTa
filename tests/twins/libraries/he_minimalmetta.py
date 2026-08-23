"""examples/libraries/he_minimalmetta.metta in Python: the minimal instruction set, by hand.

This one file is deliberately NOT idiomatic in its body, and the reason is its
subject: `div` is written in minimal MeTTa, out of `chain`, `eval` and `unify`
alone, to exercise the instruction set 70,000 recursions deep. Assignment
lowers to `let*`, not to `chain`, so a compiled Python body would store a
different program and stop being the exercise. The equation therefore goes to
the container door and says exactly what the example says, which the residue
table records against P14.4.

Everything outside the equation is Python: the definition is built once and
named, and the claim is an ordinary comparison.

`with-pragma!` is named too. Modes are with-blocks on this surface, but
`m.limits` covers inferences and timeout, and the stack depth this exercise
raises has no block of its own.
"""

from petta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1

#: The 70,000-step interpreter exercise states a budget above the engine default.
DEEP_STACK = (S["max-stack-depth"](1_000_000),)


def twin(m):
    """Write integer division as chain, eval and unify, then run it 70,000 deep."""
    m.fn["import!"](m, S.library(S["lib_he"]))

    m += equation(S.div(V.x, V.y, V.accum)).to(
        S.chain(S.eval(S["-"](V.x, V.y)), V.r1,
          S.chain(S.eval(S["<"](V.r1, 0)), V.r2,
            S.chain(S.unify(V.r2, True,  # noqa: FBT003  -- True is the ATOM the comparison answers, matched against, not a flag
              V.accum,
              S.chain(S.eval(S["+"](1, V.accum)), V.inc,
                S.chain(S.eval(S.div(V.r1, V.y, V.inc)), V.r4, V.r4))), V.r3, V.r3))))

    counted = S.chain(S.eval(S.div(350000, 5, 0)), V.rr, V.rr)
    assert m.eval(S["with-pragma!"](DEEP_STACK, counted)) == [70000]
