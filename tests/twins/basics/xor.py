"""examples/basics/xor.metta in Python: `xor` inside an equation.

Python's `^` would be the operator: on a built term it lowers to `(xor ...)`,
and inside a compiled body it is REFUSED, "the operator BitXor has no MeTTa
function". The two doors disagree, which the residue table records against
P14.4, so the body names `xor` through the static function namespace instead,
`fn.xor`, which is the mention door for an engine function and which reads and
autocompletes without the engine having to be running.

Two more places where the stored equation is not the original's, both
lowerings rather than choices. A compiled body's `==` becomes `(py-eq ...)`,
and a condition whose syntax is not boolean-valued wraps in `(py-truthy ...)`,
so `(if (xor (== $s $d) (> $s $d)) 42 0)` is stored as
`(if (py-truthy (xor (py-eq $s $d) (> $s $d))) 42 0)`. The answers agree; the
residue table records the divergence against P14.4.
"""

from metta import fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Define the xor guard, then check both of its true cases."""
    # The MeTTa name really is `check_xor` with an underscore, which the
    # naming ladder's own map does not produce: every door here, the decorator
    # included, turns a Python underscore into a hyphen, so `@m.define` alone
    # would store `check-xor` and the example's head would go unmatched. An
    # exact non-mechanical name is what `name=` is for.
    @m.define(name="check_xor")
    def check_xor(source, destination):
        # (= (check_xor $source $destination)
        #    (if (xor (== $source $destination) (> $source $destination)) 42 0))
        return 42 if fn.xor(source == destination, source > destination) else 0

    assert check_xor(2, 2) == [42]
    assert check_xor(4, 2) == [42]
