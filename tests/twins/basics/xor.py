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

from petta import fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Define the xor guard, then check both of its true cases."""
    # The MeTTa name really is `check_xor` with an underscore, and `@m.define`
    # takes the Python name VERBATIM, so this file needs no `name=`. Worth
    # knowing because the two directions disagree: the guide's rung 4 says a
    # `def not_provable` lands as `not-provable`, and every other door here
    # applies that map (`S.check_xor` is the atom `check-xor`, a bare
    # `check_xor(...)` inside another body resolves `check-xor` first). Only
    # the decorator does not, which is why a hyphenated head is spelled
    # `@m.define(name="...")` throughout this corpus
    # [measured 2026-08-23 on this worktree; commit=WORKTREE].
    @m.define
    def check_xor(source, destination):
        # (= (check_xor $source $destination)
        #    (if (xor (== $source $destination) (> $source $destination)) 42 0))
        return 42 if fn.xor(source == destination, source > destination) else 0

    assert check_xor(2, 2) == [42]
    assert check_xor(4, 2) == [42]
