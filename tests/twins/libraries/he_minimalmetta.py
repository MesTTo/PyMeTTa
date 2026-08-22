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

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 83244559 to 83244402, -157 (-0.00%), by the
#: idiomatic rewrite: nothing moved. The 70,000 recursions are the whole
#: cost, the equation is the same atom built the same way, and the difference
#: is one `test` wrapper. Measured min-of-three with the MORK backend linked
#: into this worktree, which the earlier figure may not have been. Prior:
#: 83244559 was the last figure for the generator twin that yielded
#: `m.eval(S.test(...))` once per runnable form.
BUDGET = 83244402

#: The 70,000-step interpreter exercise states a budget above the engine default.
DEEP_STACK = (S["max-stack-depth"](1_000_000),)


def twin(m):
    """Write integer division as chain, eval and unify, then run it 70,000 deep."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_he)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    m += equation(S.div(V.x, V.y, V.accum)).to(
        S.chain(S.eval(S["-"](V.x, V.y)), V.r1,
          S.chain(S.eval(S["<"](V.r1, 0)), V.r2,
            S.chain(S.unify(V.r2, True,  # noqa: FBT003  -- True is the ATOM the comparison answers, matched against, not a flag
              V.accum,
              S.chain(S.eval(S["+"](1, V.accum)), V.inc,
                S.chain(S.eval(S.div(V.r1, V.y, V.inc)), V.r4, V.r4))), V.r3, V.r3))))

    counted = S.chain(S.eval(S.div(350000, 5, 0)), V.rr, V.rr)
    assert m.one(S["with-pragma!"](DEEP_STACK, counted)) == 70000
