"""examples/basics/xor.metta in Python: `xor` inside an equation.

Python's `^` would be the operator: on a built term it lowers to `(xor ...)`,
and inside a compiled body it is REFUSED, "the operator BitXor has no MeTTa
function". The two doors disagree, which the residue table records against
P14.4, so the body names `xor` instead, which compiles because the engine
knows that name. `m.fn("xor")` binds it so the Python is valid to read and to
run: `check_xor.py(2, 2)` still answers, which is the twin `@m.define`
promises.

Two more places where the stored equation is not the original's, both
lowerings rather than choices. A compiled body's `==` becomes `(py-eq ...)`,
and a condition whose syntax is not boolean-valued wraps in `(py-truthy ...)`,
so `(if (xor (== $s $d) (> $s $d)) 42 0)` is stored as
`(if (py-truthy (xor (py-eq $s $d) (> $s $d))) 42 0)`. The answers agree; the
residue table records the divergence against P14.4.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-23, 4226 to 4454, +228, by the p14-tabling merge, the
#: sole change between the two readings: admission analysis on its
#: definitions. Ratio 4454/6311 = 0.7058 [measured 2026-08-23 min-of-3 via
#: tools/twin_coverage.py --measure]. Prior:
#: RE-PINNED 2026-08-22, 5500 to 4226, -1274 (-23.2%), by the twin contract
#: change: two `test` wrappers left the engine for `assert`, and both calls
#: go through the decorated function rather than through a built `(test
#: ...)` term. Against the example's 5984 the ratio is 0.7062 [measured
#: 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old figure
#: priced a different program.
BUDGET = 4454


def twin(m):
    """Define the xor guard, then check both of its true cases."""
    xor = m.fn("xor")

    @m.define
    def check_xor(source, destination):
        # (= (check_xor $source $destination)
        #    (if (xor (== $source $destination) (> $source $destination)) 42 0))
        return 42 if xor(source == destination, source > destination) else 0

    assert check_xor(2, 2) == [42]
    assert check_xor(4, 2) == [42]
