"""examples/libraries/memo_variant_nonground.metta in Python: keying on structure.

`shape-kind` answers `pair` for anything shaped like a Pair, whatever the
variable inside is called, so two non-ground calls that differ only in variable
name are one cache key.

The equation goes to the container door because its head carries a PATTERN,
`(shape-kind (Pair $x $y))`, where a decorated function's parameters are always
plain variables. A `match` statement in a compiled body does lower to the case
tower and would destructure the argument, but it stores a different program: a
head pattern that misses answers the call back as data, where a case tower with
no matching arm prunes the branch. That gap is the residue entry.

Both claims are the call door, `m.fn.shape_kind(S.Pair(V.a, 2))`. The argument
CARRIES a variable without the answer depending on it, and the call answers
`pair` either way, so the example's point survives: the two calls differ ONLY
in the variable's name.
"""

from metta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1


def twin(m):
    """Ask the same shape twice, under two different variable names."""
    m.fn["import!"](m, S.library(S["lib_memo"]))

    m += equation(S.shape_kind(S.Pair(V.x, V.y))).to(S.pair)
    m.eval(S.memoize(m.fn.shape_kind))

    assert m.fn.shape_kind(S.Pair(V.a, 2)) == [S.pair]
    assert m.fn.shape_kind(S.Pair(V.b, 2)) == [S.pair]
