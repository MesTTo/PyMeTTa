"""examples/control/if2.metta in Python: a symbol is not a variable.

`(is-var a)` asks about the ATOM `a`, so the answer is False and the else arm
runs. The then arm `(() (+ 1 1))` is an expression whose first element is the
empty expression, and Python's own empty tuple is that atom.

The `if` is Python's conditional expression, compiled. The condition is not:
`is-var` is hyphenated, and a compiled body reaches a function only by a name
it can write, so the question is asked at the call instead. That costs nothing
in fidelity, because a call evaluates its arguments before it runs exactly as
`if` evaluates its condition before it chooses; `(branch (is-var a))` reduces
its argument first and the compiled `if` sees the same False. The hyphen is
the wall, and it is filed as residue.

One lowering worth naming: a test position that is not already boolean by its
syntax wraps in `py-truthy`, so the equation stored is
`(if (py-truthy $flag) (() (+ 1 1)) (+ 2 2))`. That is Python's own rule for
what counts as true, made explicit rather than assumed.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1040 to 4052, +3012 (+289.6%), by lifting this twin
#: to the definitional door now that the band pays for authoring: the `if`
#: ENTERED the engine as a compiled Python conditional expression. The
#: condition still crosses as a term, because `is-var` is hyphenated and a
#: compiled body reaches a function only by a name it can write, so an
#: argument reduction is what pays for it beside the decorator's authoring
#: cost. Measured min-of-3 over fresh processes with the MORK backend linked
#: in; against the example's 2365 the ratio is 1.7133, and the ceiling is
#: 4822, the example plus 10% plus 2221 to author 1 definition. Prior: 1040,
#: the term-door twin the old band forced.
BUDGET = 4052


def twin(m):
    """Ask whether a symbol is a variable, and take the arm that answers."""
    @m.define
    def branch(flag):
        # (if <flag> (() (+ 1 1)) (+ 2 2))
        return ((), 1 + 1) if flag else 2 + 2

    # !(test (if (is-var a) (() (+ 1 1)) (+ 2 2)) 4)
    assert branch(S["is-var"](S.a)) == [4]
