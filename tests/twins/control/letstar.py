"""examples/control/letstar.metta in Python: sequential bindings.

Inside a compiled body `x = 1` IS a `let*` binding: the decorator folds a
statement list into nested bindings around what follows it, so the Python for
this file is three lines of ordinary function body and the equation stored is
`(let* (($x 1)) (let* (($y 2)) (+ $x $y)))`, the same nesting the source
writes flat.

It was written as a term until the band learned to pay for authoring a
definition, which is the only thing that had ever stopped it.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 595 to 2526, +1931 (+324.5%), by lifting this twin
#: to the definitional door now that the band pays for authoring: the two
#: bindings ENTERED the engine as compiled Python assignments, which is what
#: a `let*` binding is; the whole of the increase is `@m.define`'s authoring
#: cost, and the equation stored is the same nesting the source writes flat.
#: Measured min-of-3 over fresh processes with the MORK backend linked in;
#: against the example's 1824 the ratio is 1.3849, and the ceiling is 4227,
#: the example plus 10% plus 2221 to author 1 definition. Prior: 595, the
#: term-door twin the old band forced.
BUDGET = 2526


def twin(m):
    """Bind two names in order, then add them."""
    @m.define
    def summed():
        # (let* (($x 1) ($y 2)) (+ $x $y))
        x = 1
        y = 2
        return x + y

    # !(test (let* (($x 1) ($y 2)) (+ $x $y)) 3)
    assert summed() == [3]
