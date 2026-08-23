"""examples/libraries/test_memo_variant_nonground.metta in Python: keying on structure.

`shape-kind` answers `pair` for anything shaped like a Pair, whatever the
variable inside is called, so two non-ground calls that differ only in variable
name are one cache key.

The equation goes to the container door for two reasons already in the residue
table: its head carries a PATTERN, `(shape-kind (Pair $x $y))`, where a
decorated function's parameters are always plain variables; and its body is the
bare lowercase symbol `pair`, which a compiled body resolves as a function.

Both claims are the call door, `m.fn.shape_kind(S.Pair(V.a, 2))`. The argument
CARRIES a variable without the answer depending on it, and the call answers
`pair` either way, so the example's point survives: the two calls differ ONLY
in the variable's name.
"""

from petta import S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Ask the same shape twice, under two different variable names."""
    m.fn["import!"](m, S.library(S["lib_memo"]))

    m += equation(S["shape-kind"](S.Pair(V.x, V.y))).to(S.pair)
    m.eval(S.memoize(S["shape-kind"]))

    assert m.fn.shape_kind(S.Pair(V.a, 2)) == [S.pair]
    assert m.fn.shape_kind(S.Pair(V.b, 2)) == [S.pair]
