"""examples/functions/partialdef.metta in Python: a definition answering a partial.

`(mp)` answers `(+)`, which takes both its arguments later, so `(mp 1 1)` is
2. `..` composes two partial applications, and `(plus1times2)` answers that
composition, so `(plus1times2 1)` is `(1 + 1) * 2`.

`..` is a decorated Python function under `name=".."`, because `..` is not a
Python identifier while its BODY is ordinary Python: `f1(f2(arg))` applies two
parameters in turn, which is the variable-head application the subset already
reads.

The other two definitions are equations, because their bodies are partial
applications of OPERATORS: `(+)`, `(* 2)` and `(+ 1)` cannot be written with
Python's `+` and `*`, which need both operands to be operators at all. They
are written by CALLING the symbol, so `S["+"]()` is `(+)` and `S["*"](2)` is
`(* 2)`. `plus1times2` also calls `..`, which no Python identifier spells.
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5503 to 4348, -1155 (-21.0%), by the twin contract
#: change: two `test` wrappers left the engine for `assert`, and the
#: operator partials are built by CALLING the symbol (`S["+"]()`,
#: `S["*"](2)`) rather than as tuples. Against the example's 6663 the ratio
#: is 0.6526 [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`].
#: The old figure priced a different program.
BUDGET = 4348


def twin(m):
    """Answer a partial application from a definition, then compose two."""
    # (= (mp) (+))
    # rung: the body is `(+)`, a zero-argument application of an operator head,
    #   which no Python spelling reaches (residue, P14.4)
    m += equation(S.mp()).to(S["+"]())

    assert m.eval(S.mp(1, 1)) == [2]

    @m.define(name="..")
    def compose(f1, f2, arg):
        # (= (.. $f1 $f2 $arg) ($f1 ($f2 $arg)))
        return f1(f2(arg))

    # (= (plus1times2) (.. (* 2) (+ 1)))
    # rung: the body calls `..`, which no Python identifier spells, and holds two
    #   operator partials (residue, P14.4)
    m += equation(S.plus1times2()).to(S[".."](S["*"](2), S["+"](1)))

    assert m.eval(S.plus1times2(1)) == [4]
